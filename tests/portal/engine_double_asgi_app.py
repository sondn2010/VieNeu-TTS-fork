"""Deterministic double of the phase 4 engine contract (`/internal/v1/render`,
`/v1/audio/speech` stream, `/v1/voices`), used by `EngineClient`'s own tests
(phase 3) and every later phase that exercises the engine without the real
model (phases 5, 10, 13).

Run with `run_engine_double_server`, a *real* loopback HTTP server (not an
in-process ASGI transport): an in-process transport just replays whatever a
route handler raises, with no HTTP framing in between, so it cannot
reproduce a genuine transport-level failure (connection refused, a body that
ends before its declared length) the way a real socket does.
"""
from __future__ import annotations

import asyncio
import contextlib
import socket
import threading
import time
import wave
from dataclasses import dataclass, field
from io import BytesIO
from typing import Iterator, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

SAMPLE_RATE = 48_000
SERVICE_KEY = "engine-double-service-key"

_DEFAULT_VOICES = [
    {"id": "Hải Đăng", "name": "Hải Đăng", "description": "Nam · Bắc", "gender": "male",
     "featured": True, "aliases": ["Minh Quân"]},
    {"id": "Mai Anh", "name": "Mai Anh", "description": "Nữ · Bắc", "gender": "female",
     "featured": False, "aliases": []},
]


@dataclass
class EngineDoubleState:
    """A test flips these before a call to control the double's behavior;
    `requests` records every call made, for assertions."""

    fail_with: Optional[int] = None   # 429 | 503 | 400 | 422, applied to every route
    slow_render_sec: float = 0.0
    truncate_stream: bool = False
    voices: list = field(default_factory=lambda: [dict(v) for v in _DEFAULT_VOICES])
    requests: list = field(default_factory=list)


def _wav_bytes(seconds: float = 0.2) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def make_engine_double(state: EngineDoubleState) -> FastAPI:
    app = FastAPI()

    def _auth(authorization: str = Header(default="")) -> None:
        if authorization != f"Bearer {SERVICE_KEY}":
            raise HTTPException(401, "invalid api key")

    def _maybe_fail() -> None:
        if state.fail_with is not None:
            raise HTTPException(state.fail_with, f"engine double: forced {state.fail_with}")

    @app.post("/internal/v1/render")
    async def render(req: Request, _auth_ok: None = Depends(_auth)) -> Response:
        body = await req.json()
        state.requests.append({"path": "render", "body": body})
        _maybe_fail()
        if state.slow_render_sec:
            await asyncio.sleep(state.slow_render_sec)
        return Response(
            content=_wav_bytes(), media_type="audio/wav",
            headers={"X-Audio-Duration-Seconds": "0.200", "X-Sample-Rate": str(SAMPLE_RATE),
                     "X-Request-Id": "double-rnd-1"},
        )

    @app.post("/v1/audio/speech")
    async def speech(req: Request, _auth_ok: None = Depends(_auth)) -> StreamingResponse:
        body = await req.json()
        state.requests.append({"path": "speech", "body": body})
        _maybe_fail()

        async def gen():
            pcm = b"\x00\x00" * int(SAMPLE_RATE * 0.5)
            if state.truncate_stream:
                yield pcm[: len(pcm) // 2]
                raise RuntimeError("engine double: forced truncation")
            yield pcm

        return StreamingResponse(gen(), media_type="audio/pcm")

    @app.get("/v1/voices")
    async def voices(_auth_ok: None = Depends(_auth)) -> dict:
        state.requests.append({"path": "voices", "body": None})
        _maybe_fail()
        return {"object": "list", "data": state.voices}

    return app


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def run_engine_double_server(state: EngineDoubleState) -> Iterator[str]:
    app = make_engine_double(state)
    port = _free_loopback_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
