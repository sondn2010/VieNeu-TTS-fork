"""``POST /internal/v1/render`` for ``apps/openai_speech.py``: a one-shot, full
render (not streamed) that the portal's synchronous generate and worker async
paths call. Kept in its own module so ``openai_speech.py`` does not grow.

Imports ``apps.openai_speech`` as a module (not specific names) so this file can
be imported *from* ``openai_speech.py`` without a circular-import failure: by
the time any route handler below actually runs, ``openai_speech.py`` has long
finished executing, so every ``api.*`` attribute it uses exists.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

import apps.openai_speech as api

router = APIRouter()


class RenderRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    voice: Optional[str] = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    format: str = "wav"
    sample_rate: int = Field(default_factory=lambda: api.SAMPLE_RATE)


def _collect(chunks) -> np.ndarray:
    parts = [np.asarray(c, dtype=np.float32) for c in chunks if c is not None and len(c)]
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


@router.post("/internal/v1/render", dependencies=[Depends(api._auth)])
def render(req: RenderRequest):
    eng = api.engine()
    fmt = req.format.lower()
    if fmt not in ("mp3", "wav"):
        raise HTTPException(400, f"format '{fmt}' not supported; use 'mp3' or 'wav'")
    if fmt == "mp3" and not api._mp3_available():
        raise HTTPException(415, "mp3 encoding is not available on this engine; use format='wav'")
    if req.sample_rate not in api.RATES:
        raise HTTPException(400, f"sample_rate must be one of {api.RATES}")
    if req.voice and eng.tts.resolve_voice_name(req.voice) is None:
        raise HTTPException(400, f"unknown voice '{req.voice}'; see GET /v1/voices")
    if eng.stream_error() is not None:
        raise HTTPException(503, "speech engine is down; restart the server (see /health)")

    rid = f"rnd-{uuid.uuid4().hex[:8]}"
    t0 = time.perf_counter()
    # Reuses the streaming path's own admission gate and slot discipline (no new
    # scheduler, no parallel `tts.infer`): a plain SpeechRequest at sampling
    # defaults, fully consumed here instead of streamed to the client.
    speech_req = api.SpeechRequest(input=req.text, voice=req.voice, sample_rate=req.sample_rate)
    eng.acquire()
    slot = api._Slot(eng)
    # `_speech_chunks` releases the slot in its own `finally` once this generator
    # is exhausted or raises — fully consuming it here (success or error) is
    # enough; nothing here needs a second release.
    audio = _collect(api._speech_chunks(eng, speech_req, rid, slot, req.text))

    if req.speed != 1.0 and len(audio):
        import librosa
        audio = librosa.effects.time_stretch(audio, rate=req.speed)

    duration_s = len(audio) / req.sample_rate
    body = api._encode_audio(audio, fmt, rate=req.sample_rate)
    media = "audio/mpeg" if fmt == "mp3" else "audio/wav"
    headers = {
        "X-Audio-Duration-Seconds": f"{duration_s:.3f}",
        "X-Sample-Rate": str(req.sample_rate),
        "X-Request-Id": rid,
        "Cache-Control": "no-store",
    }
    api.log.info("%s rendered: fmt=%s speed=%.2f duration=%.2fs wall=%.2fs active=%d",
                 rid, fmt, req.speed, duration_s, time.perf_counter() - t0, eng.active)
    return Response(content=body, media_type=media, headers=headers)
