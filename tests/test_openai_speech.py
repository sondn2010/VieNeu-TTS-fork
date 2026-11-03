"""apps/openai_speech.py with a stand-in model: request limits, voice enrolment,
stream slots, health, auth (env key only), the opt-in prosody/pause-tag
preprocessor, and the listening address. ``Engine.__init__`` runs for real."""
import gc
import io
import logging
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import vieneu_preprocess
from apps import openai_speech as api


class FakeTTS:
    backend = "onnx"

    def __init__(self):
        self._preset_voices = {"Hải Đăng": {}, "Mai Anh": {}}
        self._voice_aliases = {"Minh Quân": "Hải Đăng"}
        self.stream_calls = []
        self.stream_texts = []
        self.enrolled = []

    def resolve_voice_name(self, name):
        if name in self._preset_voices:
            return name
        target = self._voice_aliases.get(name)
        return target if target in self._preset_voices else None

    def infer_stream(self, text, **kw):
        self.stream_texts.append(text)
        self.stream_calls.append(kw)
        yield np.zeros(4800, dtype=np.float32)

    def add_voice(self, name, path, **kw):
        self.enrolled.append(name)
        self._preset_voices[name] = {}


@pytest.fixture
def eng(monkeypatch):
    for var in ("VIENEU_API_KEY", "VIENEU_MAX_STREAMS", "VIENEU_QUEUE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(api, "Vieneu", lambda **kw: FakeTTS())
    e = api.Engine()
    monkeypatch.setattr(api, "ENGINE", e)
    return e


@pytest.fixture
def client(eng):
    with TestClient(api.app) as c:
        yield c


def _speech(client, headers=None, **body):
    return client.post("/v1/audio/speech", json={"input": "Xin chào.", **body}, headers=headers)


def test_valid_request_streams_wav(client, eng):
    r = _speech(client, voice="Mai Anh", temperature=0.5, top_k=50)
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF" and len(r.content) == 44 + 4800 * 2
    assert eng.tts.stream_calls[-1]["temperature"] == 0.5
    assert eng.tts.stream_calls[-1]["top_k"] == 50
    gc.collect()                               # the drop-time release must be a no-op now
    assert eng.active == 0                     # the stream slot was given back, once


def test_unread_response_still_frees_its_slot(eng):
    # The client left while its request was queued: the body is never iterated,
    # so the stream's own finally never runs. On CPU there is a single slot, and
    # losing it meant 429 for every later request.
    resp = api.speech(api.SpeechRequest(input="Xin chào."))
    assert eng.active == 1
    del resp
    gc.collect()
    assert eng.active == 0
    assert eng._gate.acquire(blocking=False)
    eng._gate.release()


@pytest.mark.parametrize("field, value", [
    ("top_k", 10 ** 30),          # overflowed the GPU scheduler's int64 slot and killed it
    ("top_k", 0),
    ("temperature", 5.0),
    ("top_p", 0.0),
    ("repetition_penalty", 0.0),
    ("max_chars", 0),             # ZeroDivisionError in the chunker, after the 200 was sent
])
def test_out_of_range_sampling_is_rejected_up_front(client, eng, field, value):
    r = _speech(client, **{field: value})
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith(f"{field}:")   # OpenAI's error shape
    assert eng.tts.stream_calls == [{"apply_watermark": False}]   # only Engine's warm-up ran


def test_nan_temperature_is_rejected(client, eng):
    # json.loads accepts NaN; it used to reach torch.multinomial. Echoing it back
    # in the error body is what turned FastAPI's default 422 into a 500.
    r = client.post("/v1/audio/speech", content=b'{"input": "x", "temperature": NaN}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and "temperature" in r.json()["error"]["message"]


@pytest.mark.parametrize("name", ["Hải Đăng", "Minh Quân"])   # the default voice, an alias of it
def test_builtin_voice_cannot_be_replaced(client, eng, name):
    r = client.post("/v1/voices", data={"name": name}, files={"file": ("a.wav", b"RIFF", "audio/wav")})
    assert r.status_code == 409
    assert eng.tts.enrolled == []


def test_new_voice_is_enrolled(client, eng):
    r = client.post("/v1/voices", data={"name": "Giọng của tôi"},
                    files={"file": ("me.wav", b"RIFF", "audio/wav")})
    assert r.status_code == 200
    assert eng.tts.enrolled == ["Giọng của tôi"]


def test_dead_scheduler_fails_health_and_new_requests(client, eng):
    assert client.get("/health").status_code == 200
    eng.sched = SimpleNamespace(error=RuntimeError("worker died"))
    r = client.get("/health")
    assert r.status_code == 503 and r.json()["status"] == "error"
    assert _speech(client).status_code == 503
    assert eng.active == 0 and eng.waiting == 0


def test_open_without_env_key_when_unset(client, eng):
    assert client.get("/v1/voices").status_code == 200
    assert _speech(client).status_code == 200
    assert client.get("/", follow_redirects=False).status_code == 404


def test_api_key_is_enforced_when_set(client, monkeypatch):
    monkeypatch.setenv("VIENEU_API_KEY", "s3cret")
    assert client.get("/v1/voices").status_code == 401
    assert client.get("/v1/voices", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/v1/voices", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_listens_on_loopback_by_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kw: seen.update(kw))
    monkeypatch.delenv("HOST", raising=False)
    api.main()
    assert seen["host"] == "127.0.0.1"


def test_public_bind_without_key_refuses_to_start(monkeypatch):
    run_calls = []
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kw: run_calls.append(kw))
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.delenv("VIENEU_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        api.main()
    assert "VIENEU_API_KEY" in str(exc_info.value)
    assert run_calls == []   # never reaches uvicorn.run


def test_public_bind_with_key_is_allowed(monkeypatch):
    seen = {}
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kw: seen.update(kw))
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("VIENEU_API_KEY", "s3cret")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.2")
    api.main()
    assert seen["host"] == "0.0.0.0"
    assert seen["proxy_headers"] is True and seen["forwarded_allow_ips"] == "10.0.0.2"


# ── opt-in prosody/pause-tag preprocessing ──────────────────────────────────

def test_preprocess_sends_tagged_text_to_the_engine(client, eng):
    text = 'Harry nhìn lâu đài Hogwarts. "Đi thôi!" Ron hét lên. [1.0] Xong.'
    r = client.post("/v1/audio/speech", json={"input": text, "preprocess": True})
    assert r.status_code == 200 and r.headers["X-VieNeu-Preprocess"] == "1"
    sent = eng.tts.stream_texts[-1]
    assert "Hogwarts" in sent                      # no dictionary substitution at the engine anymore
    assert "[0.35]" in sent and "[1.0]" in sent     # pause tags for the engine
    assert eng.tts.stream_calls[-1]["max_chars"] == 256   # request max_chars still applies


def test_plain_request_reaches_the_engine_unchanged(client, eng):
    text = 'Harry nhìn lâu đài Hogwarts. "Đi thôi!"'
    r = client.post("/v1/audio/speech", json={"input": text})
    assert r.status_code == 200 and "X-VieNeu-Preprocess" not in r.headers
    assert eng.tts.stream_texts[-1] == text


def test_preprocess_failure_falls_back_to_raw_input(client, eng, monkeypatch, caplog):
    def broken(*a, **kw):
        raise ValueError("unbalanced quote")
    monkeypatch.setattr(vieneu_preprocess, "preprocess", broken)
    with caplog.at_level(logging.WARNING):
        r = client.post("/v1/audio/speech", json={"input": "Xin chào.", "preprocess": True})
    assert r.status_code == 200 and "X-VieNeu-Preprocess" not in r.headers
    assert eng.tts.stream_texts[-1] == "Xin chào."
    assert "unbalanced quote" in caplog.text


def test_preprocess_chunk_speed_is_reported_as_ignored(client, monkeypatch):
    from vieneu_preprocess.types import Chunk, PreprocessResult
    monkeypatch.setattr(vieneu_preprocess, "preprocess", lambda text, lexicon=(), **kw: PreprocessResult(
        [Chunk("c1", "Narrator", "narration_countdown", "Ba.", speed=0.9, pause_after_sec=0.6)], ""))
    r = client.post("/v1/audio/speech", json={"input": "Ba.", "preprocess": True})
    assert r.status_code == 200 and r.headers["X-VieNeu-Ignored"] == "speed"


# ── POST /internal/v1/render ─────────────────────────────────────────────────

def _render(client, headers=None, **body):
    return client.post("/internal/v1/render", json={"text": "Xin chào.", **body}, headers=headers)


def test_render_returns_wav_with_duration_header(client, eng):
    r = _render(client, format="wav")
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF"
    data, rate = sf.read(io.BytesIO(r.content))
    decoded_s = len(data) / rate
    header_s = float(r.headers["X-Audio-Duration-Seconds"])
    assert decoded_s == 0 or abs(header_s - decoded_s) / decoded_s < 0.05
    assert r.headers["X-Sample-Rate"] == str(rate)
    assert "X-Request-Id" in r.headers
    assert eng.active == 0


def test_render_mp3_when_available(client, eng):
    if not api._mp3_available():
        pytest.skip("this libsndfile build has no MP3 encoder")
    r = _render(client, format="mp3")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"


def test_render_mp3_falls_back_to_415_when_unavailable(client, eng, monkeypatch):
    monkeypatch.setattr(api, "_mp3_available", lambda: False)
    r = _render(client, format="mp3")
    assert r.status_code == 415


def test_render_speed_shortens_duration(client, eng, monkeypatch):
    # A full second of silence (not FakeTTS's default 0.1 s chunk) gives
    # `librosa.effects.time_stretch` enough STFT frames for an accurate ratio.
    monkeypatch.setattr(eng.tts, "infer_stream",
                         lambda text, **kw: iter([np.zeros(48_000, dtype=np.float32)]))
    d1 = float(_render(client, speed=1.0).headers["X-Audio-Duration-Seconds"])
    d2 = float(_render(client, speed=1.5).headers["X-Audio-Duration-Seconds"])
    assert d2 < d1
    assert abs(d2 - d1 / 1.5) / (d1 / 1.5) < 0.1


def test_render_runs_within_a_stream_slot(client, eng):
    seen_active = []
    orig = eng.tts.infer_stream

    def wrapped(text, **kw):
        for chunk in orig(text, **kw):
            seen_active.append(eng.active)
            yield chunk
    eng.tts.infer_stream = wrapped
    assert _render(client).status_code == 200
    assert seen_active and all(a == 1 for a in seen_active)
    assert eng.active == 0


def test_render_server_full_returns_429(client, eng):
    eng.queue_timeout = 0.01
    for _ in range(eng.max_streams):
        eng.acquire()
    try:
        assert _render(client).status_code == 429
    finally:
        for _ in range(eng.max_streams):
            eng.release()


def test_render_unknown_voice_returns_400(client, eng):
    assert _render(client, voice="nope").status_code == 400


def test_render_text_over_limit_returns_400(client, eng):
    assert _render(client, text="x" * 20_001).status_code == 400


def test_render_requires_auth(eng, monkeypatch):
    monkeypatch.setenv("VIENEU_API_KEY", "s3cret")
    with TestClient(api.app) as c:
        assert c.post("/internal/v1/render", json={"text": "Xin chào."}).status_code == 401
        r = c.post("/internal/v1/render", json={"text": "Xin chào."},
                    headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200
