"""HTTP client for the speech engine (`apps/openai_speech.py`): render, stream
and voice-list calls mapped to a small typed-error contract instead of raw
httpx exceptions, so a caller's charge-after-success logic never has to parse
status codes or guess which failures are retryable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from ..config import Settings


class EngineError(Exception):
    """Base for every typed engine error."""


class EngineBusy(EngineError):
    """429: the engine's stream/queue slots are full."""


class EngineUnavailable(EngineError):
    """503, a connect/timeout failure, or a stream that ended before its full
    body arrived — callers must never charge for this."""


class EngineRejected(EngineError):
    """400/422: the engine rejected the request itself (unknown voice, text
    over the engine's own input limit, ...)."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RenderedAudio:
    audio: bytes
    duration_seconds: float
    sample_rate: int


@dataclass(frozen=True)
class EngineVoice:
    id: str
    name: str
    description: str
    gender: str
    featured: Optional[bool]
    aliases: list


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        return str(body.get("error", {}).get("message", resp.text))
    except Exception:   # noqa: BLE001 - best-effort message extraction only
        return resp.text


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 200:
        return
    if resp.status_code == 429:
        raise EngineBusy(_error_message(resp))
    if resp.status_code in (400, 422):
        raise EngineRejected(_error_message(resp), status_code=resp.status_code)
    # 401/403 mean our own service key is misconfigured; 5xx is the engine
    # itself failing. Either way the caller cannot recover by changing the
    # request, so both surface as "the engine is down" rather than a reject.
    raise EngineUnavailable(f"engine returned {resp.status_code}: {_error_message(resp)}")


class EngineClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.ENGINE_URL:
            raise ValueError("ENGINE_URL is required")
        self._base_url = settings.ENGINE_URL.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.ENGINE_SERVICE_KEY}"}
        self._timeout_sec = float(settings.ENGINE_TIMEOUT_SEC)
        self._sec_per_char = settings.ENGINE_SEC_PER_CHAR

    def _render_timeout(self, chars: int) -> float:
        return self._timeout_sec + chars * self._sec_per_char

    def render(
        self, text: str, engine_voice_name: Optional[str], speed: float = 1.0,
        fmt: str = "mp3", timeout: Optional[float] = None,
    ) -> RenderedAudio:
        body = {"text": text, "voice": engine_voice_name, "speed": speed, "format": fmt}
        try:
            with httpx.Client(timeout=timeout if timeout is not None else self._render_timeout(len(text))) as client:
                resp = client.post(f"{self._base_url}/internal/v1/render", json=body, headers=self._headers)
            _raise_for_status(resp)
        except EngineError:
            raise
        except Exception as exc:   # noqa: BLE001 - any transport failure is "unavailable"
            raise EngineUnavailable(f"engine render failed: {exc}") from exc
        return RenderedAudio(
            audio=resp.content,
            duration_seconds=float(resp.headers.get("X-Audio-Duration-Seconds", 0.0)),
            sample_rate=int(resp.headers.get("X-Sample-Rate", 0)),
        )

    async def open_stream(
        self, text: str, engine_voice_name: Optional[str], sample_rate: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Async iterator of raw PCM16 bytes (`response_format=pcm`) at
        `sample_rate` (the engine's native rate when omitted). A failure
        mid-stream — of any shape, since an in-process ASGI double cannot
        reproduce a real transport's specific exception type — raises
        `EngineUnavailable` instead of yielding a silently truncated body,
        so a caller never charges for it.
        """
        body = {"input": text, "voice": engine_voice_name, "response_format": "pcm"}
        if sample_rate is not None:
            body["sample_rate"] = sample_rate
        client = httpx.AsyncClient(timeout=self._timeout_sec)
        try:
            async with client.stream(
                "POST", f"{self._base_url}/v1/audio/speech", json=body, headers=self._headers
            ) as resp:
                if resp.status_code != 200:
                    await resp.aread()
                    _raise_for_status(resp)
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk
        except EngineError:
            raise
        except Exception as exc:   # noqa: BLE001
            raise EngineUnavailable(f"engine stream failed: {exc}") from exc
        finally:
            await client.aclose()

    def list_voices(self) -> list:
        try:
            with httpx.Client(timeout=self._timeout_sec) as client:
                resp = client.get(f"{self._base_url}/v1/voices", headers=self._headers)
            _raise_for_status(resp)
        except EngineError:
            raise
        except Exception as exc:   # noqa: BLE001
            raise EngineUnavailable(f"engine voices failed: {exc}") from exc
        data = resp.json().get("data", [])
        return [
            EngineVoice(
                id=v["id"], name=v["name"], description=v.get("description", ""),
                gender=v.get("gender", ""), featured=v.get("featured"),
                aliases=list(v.get("aliases") or []),
            )
            for v in data
        ]
