"""Script Lab: analyse text (<= 50 000 chars) and render a short audio preview (<= 3 000 chars).

Rendering runs in a worker thread so the event loop stays responsive; each session has at
most one render in flight, and the provider (phase 6) owns engine slot/lock semantics.
Full-chapter batch rendering belongs to the ``vieneu-preprocess`` CLI.
"""
from __future__ import annotations

import json
import logging
import secrets
from typing import Optional

import anyio
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response

from .admin_app import AdminApp
from .models import Session
from .preprocess_bridge import PreprocessFailed, run_preprocess
from .script_lab_state import RenderedAudio
from .web import apply_security_headers

log = logging.getLogger("vieneu.admin")

MAX_ANALYSIS_CHARS = 50_000
MAX_RENDER_CHARS = 3_000
AUDIO_FORMATS = {"wav": "audio/wav", "flac": "audio/flac"}


def _voice_map(speakers: list[str], voices: list[str], allowed: list[str]) -> dict[str, str]:
    """Pair repeated form fields speaker[i] -> voice[i]; drop blanks and unknown voices."""
    known = set(allowed)
    return {s.strip(): v for s, v in zip(speakers, voices) if s.strip() and v and v in known}


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store, lab = app.deps, app.web, app.store, app.lab
    write = [Depends(deps.csrf_protect)]

    def partial(request: Request, session: Session, name: str, status: int = 200, **ctx) -> Response:
        return web.render(request, f"partials/{name}", session, status=status, **ctx)

    @router.get("/script-lab", name="admin_script_lab")
    def page(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        return web.render(request, "script_lab.html", session, engine_available=app.engine_available(),
                          max_analysis=MAX_ANALYSIS_CHARS, max_render=MAX_RENDER_CHARS)

    @router.post("/script-lab/preprocess", name="admin_script_lab_preprocess", dependencies=write)
    def preprocess(request: Request, session: Session = Depends(deps.current_session),
                   text: str = Form("")) -> Response:
        if not text.strip():
            return partial(request, session, "message.html", 400, error="Paste some text first.")
        if len(text) > MAX_ANALYSIS_CHARS:
            return partial(request, session, "message.html", 400,
                           error=f"Analysis is limited to {MAX_ANALYSIS_CHARS:,} characters.")
        try:
            result = run_preprocess(text, store.enabled_lexicon())
        except PreprocessFailed as e:
            return partial(request, session, "message.html", 500, error=str(e))
        chunks = result.to_json()
        payload = json.dumps(chunks, ensure_ascii=False, indent=2)
        lab.save_json(session.token_hash, payload)
        speakers = list(dict.fromkeys(c.speaker for c in result.chunks))
        voices = app.engine_voices()
        return partial(request, session, "script_result.html", result=result, chunks_json=payload,
                       chunk_count=len(chunks), speakers=speakers, voices=voices,
                       engine_available=app.engine_available(),
                       renderable=len(text) <= MAX_RENDER_CHARS, max_render=MAX_RENDER_CHARS)

    @router.get("/script-lab/download.json", name="admin_script_lab_download")
    def download_json(session: Session = Depends(deps.current_session)) -> Response:
        payload = lab.get_json(session.token_hash)
        if payload is None:
            raise HTTPException(404, "Run an analysis first.")
        return apply_security_headers(Response(payload, media_type="application/json; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="script.json"'}))

    @router.post("/script-lab/render", name="admin_script_lab_render", dependencies=write)
    async def render(request: Request, session: Session = Depends(deps.current_session),
                     text: str = Form(""), fmt: str = Form("wav"), speaker: list[str] = Form([]),
                     voice: list[str] = Form([])) -> Response:
        if fmt not in AUDIO_FORMATS:
            return partial(request, session, "message.html", 400, error="Format must be WAV or FLAC.")
        if not text.strip():
            return partial(request, session, "message.html", 400, error="Paste some text first.")
        if len(text) > MAX_RENDER_CHARS:
            return partial(request, session, "message.html", 400,
                           error=f"In-app rendering is limited to {MAX_RENDER_CHARS:,} characters; "
                                 "use the vieneu-preprocess CLI for longer texts.")
        if not app.engine_available():
            return partial(request, session, "message.html", 503, error="Engine not loaded.")
        if not lab.begin_render(session.token_hash):
            return partial(request, session, "message.html", 429, error="A render is already running.")
        provider = app.tts_provider

        def work() -> bytes:
            voices = _voice_map(speaker, voice, app.engine_voices())
            result = run_preprocess(text, store.enabled_lexicon(), voices)
            data = provider.render(result, voices, fmt)  # type: ignore[union-attr]
            if not isinstance(data, (bytes, bytearray)) or not data:
                raise RuntimeError("the TTS provider returned no audio")
            return bytes(data)

        try:
            data = await anyio.to_thread.run_sync(work)
        except PreprocessFailed as e:
            return partial(request, session, "message.html", 500, error=str(e))
        except HTTPException as e:  # e.g. 429 when every engine slot is busy
            return partial(request, session, "message.html", e.status_code, error=str(e.detail))
        except Exception:
            log.exception("Script Lab render failed")
            return partial(request, session, "message.html", 500, error="Rendering failed; see the server log.")
        finally:
            lab.end_render(session.token_hash)
        audio = RenderedAudio(data, fmt, secrets.token_hex(4))
        lab.save_audio(session.token_hash, audio)
        return partial(request, session, "render_result.html", audio=audio, size_kb=len(data) // 1024)

    @router.get("/script-lab/audio", name="admin_script_lab_audio")
    def audio(session: Session = Depends(deps.current_session), download: Optional[int] = Query(None),
              v: str = Query("", max_length=16)) -> Response:
        rendered = lab.get_audio(session.token_hash)
        if rendered is None:
            raise HTTPException(404, "No rendered audio for this session.")
        disposition = "attachment" if download else "inline"
        resp = Response(rendered.data, media_type=AUDIO_FORMATS[rendered.fmt], headers={
            "Content-Disposition": f'{disposition}; filename="script-lab.{rendered.fmt}"'})
        return apply_security_headers(resp)
