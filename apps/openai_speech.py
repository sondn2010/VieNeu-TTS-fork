"""
VieNeu-TTS — OpenAI-compatible speech API (streaming), CPU or GPU.
==================================================================
Drop-in for ``POST /v1/audio/speech``: any OpenAI SDK / Pipecat / LiveKit /
Vercel AI client works by changing ``base_url``. Audio streams as it is
generated — the first bytes leave ~115 ms after the request on an RTX 3060,
~600 ms on a 6-core CPU (see docs/streaming.vi.md for every number).

    uv run python -m apps.openai_speech                 # http://127.0.0.1:8000
    VIENEU_BACKEND=onnx uv run python -m apps.openai_speech   # force CPU

    from openai import OpenAI
    client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="x")
    with client.audio.speech.with_streaming_response.create(
        model="vieneu-v3-turbo", voice="Mai Anh", input="Xin chào! Đây là chế độ streaming của VieNeu, phát tới đâu nghe tới đó.",
        response_format="pcm",              # 48 kHz s16le mono (see `sample_rate` below)
    ) as r:
        for chunk in r.iter_bytes(4096):
            play(chunk)

Request body (OpenAI fields + a few extras, all optional but ``input``):
    model            any string; reported back as-is
    input            text, chunked internally at ``max_chars`` (256)
    voice            preset name (GET /v1/voices) or one added with POST /v1/voices
    response_format  "pcm" (s16le, no header) | "wav" (header with unknown length,
                     plays as it streams). mp3/opus/aac/flac → 400.
    stream_format    "audio" (default: raw chunked body) | "sse" (Server-Sent
                     Events: {"type":"speech.audio.delta","audio":"<base64>"} ...
                     {"type":"speech.audio.done","usage":{...}})
    speed            accepted for compatibility, ignored (header X-VieNeu-Ignored)
    sample_rate      48000 (native) | 24000 (OpenAI's pcm rate) | 16000 | 8000 —
                     resampled on the fly (soxr), per chunk, no extra latency
    temperature, top_k, top_p, repetition_penalty, max_chars   sampling extras,
                     range-checked (out of range → 400): 0-2 / 1-1024 / (0, 1] / 1-2 / 64-512
    preprocess       false (default: ``input`` reaches the engine unchanged) | true:
                     run the story preprocessor (docs/tts-specs/tts-specs-v1.md) with
                     every enabled pronunciation dictionary and stream its single-voice
                     text with ``[x.xx]`` pause tags (header X-VieNeu-Preprocess: 1).
                     Fail-open: a preprocessor error is logged and the raw input is
                     spoken. Per-chunk speed is not applied (X-VieNeu-Ignored: speed).

Admin web app (``/admin``, on unless VIENEU_ADMIN=0): users manage their own API
keys, admins manage users and dictionaries; Script Lab renders story previews.
With the admin app on, every /v1/* call needs a key — a DB key (``vn_...``) or
VIENEU_API_KEY — even before any key exists. A fresh database without an admin
account refuses to start unless VIENEU_ADMIN_USER/VIENEU_ADMIN_PASSWORD are set
(or ``python -m vieneu_admin create-admin`` ran first). VIENEU_ADMIN=0 restores
the keyless behavior below; DB keys still work then if the database file exists.

POST /v1/voices refuses (409) the name of a built-in voice or alias, so a client
cannot swap out a voice other clients rely on (e.g. the default one).

Concurrency: GPU serves ``VIENEU_MAX_STREAMS`` streams at once (continuous
batching, default 16); CPU serves one (fp32) or two (int8) — the ONNX engine
interleaves them frame by frame but they share the cores.
Extra requests wait up to ``VIENEU_QUEUE_TIMEOUT`` s in a queue of at most
``VIENEU_QUEUE`` entries, then get 429 with Retry-After.

Environment:
    VIENEU_BACKEND=auto|onnx|pytorch   VIENEU_DEVICE=auto|cuda|cpu
    VIENEU_PRECISION=fp32|int8 (CPU)   VIENEU_ONNX_DIR=... (local ONNX export)
    VIENEU_MAX_STREAMS=16 (GPU)        VIENEU_QUEUE=16   VIENEU_QUEUE_TIMEOUT=10
    VIENEU_API_KEY=...  (Bearer auth; with VIENEU_ADMIN=0 unset = open — logged as
                        a warning when HOST is not a loopback address)
    VIENEU_ADMIN=1|0    VIENEU_ADMIN_DB=vieneu_data/admin.sqlite3
    VIENEU_ADMIN_USER / VIENEU_ADMIN_PASSWORD   first admin on a fresh DB (the
                        password is never logged; ignored once an admin exists)
    VIENEU_COOKIE_SECURE=1 (admin behind HTTPS)  VIENEU_DOCS_DIR=docs (Help page)
    FORWARDED_ALLOW_IPS=127.0.0.1  proxies whose X-Forwarded-For is trusted (the
                        admin login lockout is per client IP)
    VIENEU_WATERMARK=1                 HOST=127.0.0.1  PORT=8000
                                       (HOST=0.0.0.0 to serve other machines; the
                                       Docker profiles set it)
"""
from __future__ import annotations

import base64
import hmac
import io
import json
import logging
import os
import re
import struct
import threading
import time
import uuid
import wave
import weakref
from typing import Any, Iterator, NamedTuple, Optional

import numpy as np
import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

import vieneu_preprocess
from vieneu import Vieneu
from vieneu_admin import AdminStore, create_admin_router, verify_api_key
from vieneu_admin.db import default_db_path
from vieneu_admin.models import StoreError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("vieneu.api")

SAMPLE_RATE = 48_000
MODEL_ID = "vieneu-v3-turbo"
RATES = (48_000, 24_000, 16_000, 8_000)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# ── engine + admission ───────────────────────────────────────────────────────

class Engine:
    """The model plus the admission gate (how many streams run at once)."""

    def __init__(self):
        backend = os.environ.get("VIENEU_BACKEND", "auto")
        device = os.environ.get("VIENEU_DEVICE", "auto")
        kw: dict = dict(backend=backend, device=device,
                        precision=os.environ.get("VIENEU_PRECISION", "fp32"),
                        onnx_dir=os.environ.get("VIENEU_ONNX_DIR") or None,
                        max_streams=_env_int("VIENEU_MAX_STREAMS", 16))
        log.info("⏳ loading VieNeu-TTS v3 Turbo (backend=%s device=%s)", backend, device)
        t = time.perf_counter()
        self.tts = Vieneu(mode="v3turbo", **kw)
        self.backend = self.tts.backend
        # The voices and aliases that exist before any client enrolls one;
        # POST /v1/voices may not replace them.
        self.builtin_voices = frozenset(self.tts._preset_voices) | frozenset(self.tts._voice_aliases)
        self.watermark = os.environ.get("VIENEU_WATERMARK", "1") != "0"
        # GPU: the scheduler batches every stream. CPU: the ONNX engine interleaves
        # calls frame by frame, but they share the cores — measured on a 6-core
        # desktop, fp32 keeps one stream real-time (RTF 0.58; two → 1.19), int8
        # two (RTF 0.35; two → 0.67). VIENEU_MAX_STREAMS overrides either.
        self.sched = self.tts._get_stream_scheduler() if self.backend == "pytorch" else None
        if self.sched is not None:
            self.max_streams = self.sched.B
        else:
            cpu_default = 2 if kw["precision"] == "int8" else 1
            self.max_streams = _env_int("VIENEU_MAX_STREAMS", cpu_default) if "VIENEU_MAX_STREAMS" in os.environ else cpu_default
        self.max_queue = _env_int("VIENEU_QUEUE", self.max_streams)
        self.queue_timeout = float(os.environ.get("VIENEU_QUEUE_TIMEOUT", "10"))
        self._gate = threading.BoundedSemaphore(self.max_streams)
        self._lock = threading.Lock()
        self.active = 0
        self.waiting = 0
        # Warm-up: capture the CUDA graphs / load the ONNX graphs before the
        # first client pays for it.
        for _ in self.tts.infer_stream("Xin chào.", apply_watermark=False):
            pass
        log.info("✅ ready in %.1fs: backend=%s max_streams=%d queue=%d", time.perf_counter() - t,
                 self.backend, self.max_streams, self.max_queue)

    def acquire(self) -> None:
        with self._lock:
            if self.waiting >= self.max_queue:
                raise HTTPException(429, "server busy: queue full", headers={"Retry-After": "1"})
            self.waiting += 1
        try:
            if not self._gate.acquire(timeout=self.queue_timeout):
                raise HTTPException(429, "server busy: timed out waiting for a stream slot",
                                    headers={"Retry-After": "2"})
        finally:
            with self._lock:
                self.waiting -= 1
        with self._lock:
            self.active += 1

    def release(self) -> None:
        with self._lock:
            self.active -= 1
        self._gate.release()

    def stream_error(self) -> Optional[BaseException]:
        """Why the GPU stream scheduler died, or None. A dead scheduler refuses
        every request until the process restarts."""
        return getattr(self.sched, "error", None) if self.sched is not None else None

    def voices(self) -> list:
        out = []
        for name, v in self.tts._preset_voices.items():
            out.append({"id": name, "name": name, "description": v.get("description", ""),
                        "gender": v.get("gender", ""), "featured": v.get("featured"),
                        "aliases": list(v.get("aliases") or [])})
        return out


class _Slot:
    """One ``Engine`` stream slot, released exactly once: by the stream's own
    ``finally``, or — when the body is never iterated because the client left
    while queued — when the dropped body is garbage-collected."""

    def __init__(self, eng: Engine):
        self._eng = eng
        self._lock = threading.Lock()
        self._held = True

    def release(self) -> None:
        with self._lock:
            held, self._held = self._held, False
        if held:
            self._eng.release()


ENGINE: Optional[Engine] = None


def engine() -> Engine:
    global ENGINE
    if ENGINE is None:
        ENGINE = Engine()
    return ENGINE


# ── Script Lab engine provider ───────────────────────────────────────────────

class _StreamedInfer:
    """The ``tts.infer(text, voice=, temperature=)`` the story runner calls, served
    by ``infer_stream``.

    On GPU, ``infer`` drives the batch engine's CUDA graph directly, the same graph
    the stream scheduler's worker thread replays for every API stream; running both
    at once corrupts it. ``infer_stream`` submits to that one scheduler instead, so
    Script Lab renders and API streams share the engine safely (and on CPU they share
    the admission gate like any stream).
    """

    sample_rate = SAMPLE_RATE

    def __init__(self, eng: Engine):
        self._eng = eng

    def infer(self, text: str, voice: Optional[str] = None, temperature: Optional[float] = None,
              **_unused: Any) -> np.ndarray:
        kw: dict = {"voice": voice or None, "apply_watermark": self._eng.watermark}
        if temperature is not None:
            kw["temperature"] = float(temperature)
        gen = self._eng.tts.infer_stream(text, **kw)
        try:
            parts = [np.asarray(c, dtype=np.float32) for c in gen if c is not None and len(c)]
        finally:
            gen.close()
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


def _encode_audio(wav: np.ndarray, fmt: str) -> bytes:
    """A complete 16-bit WAV or FLAC file at the native rate."""
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, np.asarray(wav, dtype=np.float32), SAMPLE_RATE, format=fmt.upper(), subtype="PCM_16")
    return buf.getvalue()


class _EngineProvider:
    """``tts_provider`` for the admin app's Script Lab. The engine loads after the
    router is built, so every call looks the engine up lazily."""

    def available(self) -> bool:
        eng = ENGINE
        return eng is not None and eng.stream_error() is None

    def voices(self) -> list:
        eng = ENGINE
        return list(eng.tts._preset_voices) if eng is not None else []

    def render(self, result: Any, voices: Any, fmt: str) -> bytes:
        # ``voices`` (speaker -> voice) is already applied: Script Lab passes it to the
        # preprocessor, which stores it on each chunk's ``voice_preset``.
        del voices
        if fmt not in ("wav", "flac"):
            raise ValueError(f"unsupported format {fmt!r}")
        eng = ENGINE
        if eng is None or eng.stream_error() is not None:
            raise HTTPException(503, "speech engine is not available")
        eng.acquire()   # one stream slot, same queue / 429 semantics as the API
        try:
            wav = vieneu_preprocess.render(result, _StreamedInfer(eng))
        finally:
            eng.release()
        return _encode_audio(wav, fmt)


# ── admin app + API keys ─────────────────────────────────────────────────────

class AdminConfigError(RuntimeError):
    """The admin app cannot start safely with the current configuration."""


def _admin_enabled() -> bool:
    return os.environ.get("VIENEU_ADMIN", "1").strip() != "0"


# The admin store (None when the admin app is off and no DB file exists), whether
# the admin router is mounted (then every /v1/* call needs a key), and the routes
# it added, so a restart of the app (tests, reload) does not mount them twice.
STORE: Optional[AdminStore] = None
ADMIN_ON = False
_ADMIN_ROUTES: list = []


def _close_admin() -> None:
    global STORE, ADMIN_ON
    for route in _ADMIN_ROUTES:
        if route in app.router.routes:
            app.router.routes.remove(route)
    _ADMIN_ROUTES.clear()
    ADMIN_ON = False
    if STORE is not None:
        STORE.close()
        STORE = None


def _bootstrap_admin(store: AdminStore) -> None:
    """Make sure an active admin exists, or refuse to start (no unconfigured public admin)."""
    store.seed_if_empty()
    if store.has_active_admin():
        return
    user = (os.environ.get("VIENEU_ADMIN_USER") or "").strip()
    password = os.environ.get("VIENEU_ADMIN_PASSWORD") or ""
    if not user or not password:
        raise AdminConfigError(
            f"the admin database {store.path} has no active admin account. Set VIENEU_ADMIN_USER and "
            "VIENEU_ADMIN_PASSWORD for the first start, or run `python -m vieneu_admin create-admin "
            "<user>`, or set VIENEU_ADMIN=0 to run the speech API without the admin app.")
    try:
        store.bootstrap_admin(user, password)
    except StoreError as e:
        raise AdminConfigError(f"VIENEU_ADMIN_USER/VIENEU_ADMIN_PASSWORD rejected: {e}") from None
    log.info("👤 admin account %r created from VIENEU_ADMIN_USER", user)


def _setup_admin() -> None:
    """Open the admin DB and mount ``/admin`` (or, with VIENEU_ADMIN=0, only accept DB keys)."""
    global STORE, ADMIN_ON
    _close_admin()
    env_key = bool(os.environ.get("VIENEU_API_KEY"))
    if not _admin_enabled():
        path = default_db_path()
        if path.is_file():
            STORE = AdminStore(path)
        log.info("🔓 admin app off (VIENEU_ADMIN=0): /v1/* %s%s",
                 "requires VIENEU_API_KEY" if env_key else "is open (no VIENEU_API_KEY)",
                 f"; API keys from {path} are also accepted" if STORE is not None else "")
        return
    store = AdminStore()
    try:
        _bootstrap_admin(store)
        before = len(app.router.routes)
        app.include_router(create_admin_router(store, tts_provider=_EngineProvider()), prefix="/admin")
        _ADMIN_ROUTES.extend(app.router.routes[before:])
        keys = store.count_keys()
    except BaseException:
        store.close()
        raise
    STORE, ADMIN_ON = store, True
    log.info("🔐 admin app at /admin (db=%s); every /v1/* call requires an API key (%d active%s)",
             store.path, keys, ", plus VIENEU_API_KEY" if env_key else "")
    if keys == 0 and not env_key:
        log.warning("⚠️ no API keys exist yet: every /v1/* call gets 401 until a key is created at /admin/keys")


# ── auth / errors in OpenAI's shape ───────────────────────────────────────────

def _auth(authorization: Optional[str] = Header(default=None)) -> None:
    """VIENEU_API_KEY (constant-time compare) or an active DB key. With the admin app
    on, a key is always required; with VIENEU_ADMIN=0 only when VIENEU_API_KEY is set."""
    env_key = os.environ.get("VIENEU_API_KEY")
    if env_key and hmac.compare_digest((authorization or "").encode(), f"Bearer {env_key}".encode()):
        return
    store = STORE
    if store is not None and authorization:
        try:
            if verify_api_key(store, authorization) is not None:
                return
        except Exception:   # noqa: BLE001 - fail closed, but say why in the log
            log.exception("API key lookup failed")
            raise HTTPException(503, "api key verification unavailable", headers={"Retry-After": "5"})
    if env_key or ADMIN_ON:
        raise HTTPException(401, "invalid api key")


def _error(status: int, message: str, code: Optional[str] = None, headers=None) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": "invalid_request_error",
                                   "code": code or status}}, status_code=status, headers=headers)


app = FastAPI(title="VieNeu-TTS speech API", version="1.0")


def _is_admin_path(req: Request) -> bool:
    path = req.url.path
    return path == "/admin" or path.startswith("/admin/")


@app.exception_handler(HTTPException)
async def _http_exc(req: Request, exc: HTTPException):
    if _is_admin_path(req):   # the admin app keeps FastAPI's own error handling
        return await http_exception_handler(req, exc)
    return _error(exc.status_code, str(exc.detail), headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def _invalid_request(req: Request, exc: RequestValidationError):
    if _is_admin_path(req):
        return await request_validation_exception_handler(req, exc)
    # Field and reason only: FastAPI's default echoes the rejected value, and a
    # NaN (which json.loads accepts) cannot be encoded back — the 422 became a 500.
    errs = exc.errors()
    first = errs[0] if errs else {}
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query", "header"))
    msg = first.get("msg", "invalid request")
    return _error(400, f"{field}: {msg}" if field else msg)


@app.on_event("startup")
def _startup() -> None:
    # Admin first: a configuration error aborts before the model spends time loading.
    _setup_admin()
    try:
        engine()
    except BaseException:
        _close_admin()
        raise


@app.on_event("shutdown")
def _shutdown() -> None:
    _close_admin()


@app.get("/", include_in_schema=False)
def root():
    if not ADMIN_ON:
        raise HTTPException(404, "not found; the API lives under /v1")
    return RedirectResponse("/admin/", status_code=303)


# ── audio helpers ────────────────────────────────────────────────────────────

def _pcm16(x: np.ndarray) -> bytes:
    return (np.asarray(x, dtype=np.float32) * 32767).clip(-32768, 32767).astype("<i2").tobytes()


def _wav_header(rate: int) -> bytes:
    """A WAV header claiming an unknown (huge) length, so players start at once."""
    h = io.BytesIO()
    with wave.open(h, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.setnframes(0)
    b = bytearray(h.getvalue())
    struct.pack_into("<I", b, 4, 0xFFFFFFFF)      # RIFF size
    struct.pack_into("<I", b, len(b) - 4, 0xFFFFFFFF)   # data size
    return bytes(b)


class _Resampler:
    """48 kHz → ``rate`` chunk by chunk with carried state (soxr), no added latency."""

    def __init__(self, rate: int):
        self.rate = rate
        self._rs = None
        if rate != SAMPLE_RATE:
            import soxr
            self._rs = soxr.ResampleStream(SAMPLE_RATE, rate, 1, dtype="float32", quality="HQ")

    def __call__(self, x: np.ndarray, last: bool = False) -> np.ndarray:
        if self._rs is None:
            return x
        return self._rs.resample_chunk(np.asarray(x, dtype=np.float32), last=last)


# ── /v1/audio/speech ─────────────────────────────────────────────────────────

class SpeechRequest(BaseModel):
    model: str = MODEL_ID
    input: str = Field(min_length=1, max_length=20_000)
    voice: Optional[str] = None
    response_format: str = "wav"
    stream_format: str = "audio"
    speed: Optional[float] = None
    instructions: Optional[str] = None
    sample_rate: int = SAMPLE_RATE
    # Bounded so one request cannot break the GPU scheduler every stream shares:
    # e.g. a huge top_k overflowed its int64 slot and NaN reached multinomial.
    temperature: float = Field(0.8, ge=0.0, le=2.0, allow_inf_nan=False)
    top_k: int = Field(25, ge=1, le=1024)   # 1024 = the codec's vocabulary
    top_p: float = Field(0.95, gt=0.0, le=1.0, allow_inf_nan=False)
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, allow_inf_nan=False)
    max_chars: int = Field(256, ge=64, le=512)
    # Opt-in story preprocessing (tts-specs-v1) with every enabled dictionary.
    preprocess: bool = False


class _Preprocessed(NamedTuple):
    text: str
    speed_ignored: bool   # some chunk asked for a speed the streaming path cannot apply


def _preprocess_input(raw: str, rid: str) -> Optional[_Preprocessed]:
    """Story-preprocess ``raw`` into single-voice text with ``[x.xx]`` pause tags.

    Fail-open: any error (dictionaries unreadable, preprocessor anomaly, empty
    output) is logged and returns None, so the caller speaks the raw input.
    """
    try:
        lexicon = STORE.enabled_lexicon() if STORE is not None else ()
        outcome = vieneu_preprocess.preprocess_safely(raw, lexicon)
        if not outcome.ok:
            log.warning("%s preprocess failed (%s); speaking the raw input", rid, outcome.error)
            return None
        text = outcome.result.to_tagged_text()
        if not text.strip():
            log.warning("%s preprocess produced no text; speaking the raw input", rid)
            return None
        ignored = any(abs(c.speed - 1.0) > 1e-6 for c in outcome.result.chunks)
        return _Preprocessed(text, ignored)
    except Exception as e:   # noqa: BLE001 - fail-open contract
        log.warning("%s preprocess unavailable (%s: %s); speaking the raw input", rid, type(e).__name__, e)
        return None


def _speech_chunks(eng: Engine, req: SpeechRequest, rid: str, slot: _Slot,
                   text: str) -> Iterator[np.ndarray]:
    """float32 chunks at ``req.sample_rate``; logs TTFA / RTF; holds one stream slot."""
    t0 = time.perf_counter()
    first = None
    emitted = 0
    rs = _Resampler(req.sample_rate)
    try:
        for chunk in eng.tts.infer_stream(
            text, voice=req.voice or None, apply_watermark=eng.watermark,
            temperature=req.temperature, top_k=req.top_k, top_p=req.top_p,
            repetition_penalty=req.repetition_penalty, max_chars=req.max_chars,
        ):
            if chunk is None or len(chunk) == 0:
                continue
            if first is None:
                first = time.perf_counter() - t0
            emitted += len(chunk)
            out = rs(chunk)
            if len(out):
                yield out
        tail = rs(np.zeros(0, np.float32), last=True)
        if len(tail):
            yield tail
    finally:
        slot.release()
        total = time.perf_counter() - t0
        audio_s = emitted / SAMPLE_RATE
        log.info("%s done: ttfa=%s total=%.2fs audio=%.2fs rtf=%s active=%d", rid,
                 f"{first*1000:.0f}ms" if first is not None else "-", total, audio_s,
                 f"{total/audio_s:.2f}" if audio_s else "-", eng.active)


def _audio_body(chunks: Iterator[np.ndarray], fmt: str, rate: int) -> Iterator[bytes]:
    if fmt == "wav":
        yield _wav_header(rate)
    for c in chunks:
        yield _pcm16(c)


def _sse_body(chunks: Iterator[np.ndarray], fmt: str, rate: int) -> Iterator[bytes]:
    def ev(obj: dict) -> bytes:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")
    n = 0
    if fmt == "wav":
        yield ev({"type": "speech.audio.delta", "audio": base64.b64encode(_wav_header(rate)).decode()})
    for c in chunks:
        n += len(c)
        yield ev({"type": "speech.audio.delta", "audio": base64.b64encode(_pcm16(c)).decode()})
    yield ev({"type": "speech.audio.done",
              "usage": {"output_samples": n, "sample_rate": rate, "seconds": round(n / rate, 3)}})


@app.post("/v1/audio/speech", dependencies=[Depends(_auth)])
def speech(req: SpeechRequest):
    eng = engine()
    fmt = req.response_format.lower()
    if fmt not in ("pcm", "wav"):
        raise HTTPException(400, f"response_format '{fmt}' not supported; use 'pcm' or 'wav'")
    if req.stream_format not in ("audio", "sse"):
        raise HTTPException(400, "stream_format must be 'audio' or 'sse'")
    if req.sample_rate not in RATES:
        raise HTTPException(400, f"sample_rate must be one of {RATES}")
    if req.voice and eng.tts.resolve_voice_name(req.voice) is None:
        raise HTTPException(400, f"unknown voice '{req.voice}'; see GET /v1/voices")
    if eng.stream_error() is not None:
        # Say so now: once the 200 headers are out, a failure only truncates the body.
        raise HTTPException(503, "speech engine is down; restart the server (see /health)")
    rid = f"spk-{uuid.uuid4().hex[:8]}"
    # Plain requests reach the engine byte-identical; preprocessing runs before a
    # stream slot is taken so a slow parse never holds one.
    pre = _preprocess_input(req.input, rid) if req.preprocess else None
    text = pre.text if pre is not None else req.input
    eng.acquire()   # 429 if the server is full; released when the stream ends
    slot = _Slot(eng)
    chunks = _speech_chunks(eng, req, rid, slot, text)
    # A generator that never starts never runs its finally: if the client is gone
    # before the body is read, the slot is freed when the body is dropped.
    weakref.finalize(chunks, slot.release)
    headers = {"X-Request-Id": rid, "X-Sample-Rate": str(req.sample_rate), "Cache-Control": "no-store"}
    if pre is not None:
        headers["X-VieNeu-Preprocess"] = "1"
    ignored = [k for k in ("speed", "instructions") if getattr(req, k) is not None]
    if pre is not None and pre.speed_ignored and "speed" not in ignored:
        ignored.insert(0, "speed")
    if ignored:
        headers["X-VieNeu-Ignored"] = ",".join(ignored)
    if req.stream_format == "sse":
        return StreamingResponse(_sse_body(chunks, fmt, req.sample_rate),
                                 media_type="text/event-stream", headers=headers)
    media = "audio/wav" if fmt == "wav" else "audio/pcm"
    return StreamingResponse(_audio_body(chunks, fmt, req.sample_rate), media_type=media, headers=headers)


# ── discovery ────────────────────────────────────────────────────────────────

@app.get("/v1/models", dependencies=[Depends(_auth)])
def models():
    eng = engine()
    return {"object": "list", "data": [{
        "id": MODEL_ID, "object": "model", "created": 0, "owned_by": "vieneu",
        "sample_rate": SAMPLE_RATE, "backend": eng.backend,
        "max_streams": eng.max_streams, "response_formats": ["pcm", "wav"],
        "stream_formats": ["audio", "sse"], "sample_rates": list(RATES),
    }]}


@app.get("/v1/voices", dependencies=[Depends(_auth)])
def voices():
    return {"object": "list", "data": engine().voices()}


# A voice name is a label: letters/digits (any script), spaces, dots, dashes,
# underscores; 1-64 chars, no control characters. It ends up in logs and in the
# voices file, so anything else is rejected at the boundary.
_VOICE_NAME = re.compile(r"[^\W_][\w .\-]{0,63}")
_CLIP_EXTS = {".wav": ".wav", ".mp3": ".mp3", ".flac": ".flac", ".ogg": ".ogg", ".m4a": ".m4a"}
_MAX_CLIP_BYTES = 20 * 1024 * 1024


@app.post("/v1/voices", dependencies=[Depends(_auth)])
def add_voice(name: str = Form(...), file: UploadFile = File(...), denoise: bool = Form(True),
              description: str = Form("")):
    """Enroll a 3-8 s reference clip as ``voice=name`` (in memory, for this process).

    Plain ``def``: FastAPI runs it in a thread, so the blocking upload read,
    temp file and enrolment do not stall the event loop.
    """
    import tempfile
    eng = engine()
    if not _VOICE_NAME.fullmatch(name):
        raise HTTPException(400, "voice name: 1-64 letters, digits, spaces, '.', '-' or '_'")
    if not _VOICE_NAME.fullmatch(description or "x"):
        raise HTTPException(400, "description: 1-64 letters, digits, spaces, '.', '-' or '_'")
    if name in eng.builtin_voices:
        # add_voice would replace it for every client, including the default voice.
        raise HTTPException(409, f"'{name}' is a built-in voice; choose another name")
    # The suffix only picks the decoder; it is mapped to a constant, never taken from the client.
    ext = _CLIP_EXTS.get(os.path.splitext(file.filename or "")[1].lower(), ".wav")
    data = file.file.read(_MAX_CLIP_BYTES + 1)
    if len(data) > _MAX_CLIP_BYTES:
        raise HTTPException(413, "reference clip larger than 20 MB")
    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        eng.tts.add_voice(name, path, denoise=denoise, description=description)
    except HTTPException:
        raise
    except Exception as e:   # noqa: BLE001
        raise HTTPException(400, f"could not enroll voice: {e}")
    finally:
        os.unlink(path)
    return {"id": name, "name": name, "description": description}


@app.get("/health")
def health():
    eng = engine()
    body = {"status": "ok", "backend": eng.backend, "max_streams": eng.max_streams,
            "active": eng.active, "waiting": eng.waiting, "sample_rate": SAMPLE_RATE}
    err = eng.stream_error()
    if err is not None:
        # 503 so a container healthcheck restarts us: the scheduler does not recover.
        return JSONResponse({**body, "status": "error", "error": f"stream scheduler is down: {err!r}"},
                            status_code=503)
    return body


def main() -> None:
    # Loopback unless told otherwise: with VIENEU_ADMIN=0 the API is open when
    # VIENEU_API_KEY is unset.
    host = os.environ.get("HOST", "127.0.0.1")
    port = _env_int("PORT", 8000)
    if host not in ("127.0.0.1", "localhost", "::1"):
        if not _admin_enabled() and not os.environ.get("VIENEU_API_KEY"):
            log.warning("⚠️ listening on %s:%d without VIENEU_API_KEY: anyone who can reach this port "
                        "can use the API and enroll voices", host, port)
        elif _admin_enabled() and os.environ.get("VIENEU_COOKIE_SECURE") != "1":
            log.info("serve /admin over HTTPS and set VIENEU_COOKIE_SECURE=1 when it is reachable from "
                     "other machines")
    # One worker: the model (and on GPU the scheduler) is process-local. Behind a
    # reverse proxy, FORWARDED_ALLOW_IPS lists the proxies whose X-Forwarded-For is
    # trusted, so the admin login lockout sees real client addresses.
    uvicorn.run(app, host=host, port=port, workers=1, log_level="info", proxy_headers=True,
                forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS") or "127.0.0.1")


if __name__ == "__main__":
    main()
