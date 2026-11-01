"""apps/openai_speech.py with a stand-in model: request limits, voice enrolment,
stream slots, health, auth (env key, DB keys, admin on/off), the opt-in story
preprocessor, the mounted admin app and the listening address. ``Engine.__init__``
and the admin store run for real, on a temporary database."""
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
from test_admin_routes import login, post

ADMIN_PW = "admin-password-1"


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
def eng(monkeypatch, tmp_path):
    for var in ("VIENEU_API_KEY", "VIENEU_MAX_STREAMS", "VIENEU_QUEUE", "VIENEU_ADMIN_USER",
                "VIENEU_ADMIN_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    # The pre-admin behavior by default; admin tests switch it on. Never the repo DB.
    monkeypatch.setenv("VIENEU_ADMIN", "0")
    monkeypatch.setenv("VIENEU_ADMIN_DB", str(tmp_path / "admin.sqlite3"))
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


def test_open_public_bind_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kw: None)
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("VIENEU_ADMIN", "0")
    monkeypatch.delenv("VIENEU_API_KEY", raising=False)
    with caplog.at_level(logging.WARNING, logger="vieneu.api"):
        api.main()
    assert "without VIENEU_API_KEY" in caplog.text


def test_public_bind_with_admin_on_is_not_open(monkeypatch, caplog):
    seen = {}
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kw: seen.update(kw))
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    monkeypatch.delenv("VIENEU_API_KEY", raising=False)
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.2")
    with caplog.at_level(logging.WARNING, logger="vieneu.api"):
        api.main()
    assert "without VIENEU_API_KEY" not in caplog.text   # every /v1/* call needs a key
    assert seen["proxy_headers"] is True and seen["forwarded_allow_ips"] == "10.0.0.2"


# ── VIENEU_ADMIN=0: today's behavior, plus DB keys when the DB file exists ──────

def test_admin_off_without_env_key_stays_open(client, eng):
    assert client.get("/v1/voices").status_code == 200
    assert _speech(client).status_code == 200
    assert api.STORE is None and not api.ADMIN_ON
    assert client.get("/admin/login").status_code == 404     # router not mounted
    assert client.get("/", follow_redirects=False).status_code == 404


def test_admin_off_still_accepts_db_keys_when_the_db_exists(eng, tmp_path, monkeypatch):
    store = api.AdminStore(tmp_path / "admin.sqlite3")
    user = store.create_user("carol", "password123")
    plaintext, _ = store.create_key(user.id, "ci")
    store.close()
    monkeypatch.setenv("VIENEU_API_KEY", "s3cret")
    with TestClient(api.app) as c:
        assert c.get("/v1/voices").status_code == 401
        assert c.get("/v1/voices", headers={"Authorization": "Bearer s3cret"}).status_code == 200
        assert c.get("/v1/voices", headers={"Authorization": f"Bearer {plaintext}"}).status_code == 200


# ── VIENEU_ADMIN=1 (default) ───────────────────────────────────────────────────

@pytest.fixture
def admin(eng, monkeypatch):
    """Admin app on, fresh DB bootstrapped from env credentials; yields (client, store)."""
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    monkeypatch.setenv("VIENEU_ADMIN_USER", "root")
    monkeypatch.setenv("VIENEU_ADMIN_PASSWORD", ADMIN_PW)
    with TestClient(api.app) as c:
        yield c, api.STORE
    assert api.STORE is None and not api.ADMIN_ON   # shutdown closed and unmounted


def _key_for(store, username="bob"):
    user = store.create_user(username, "password123")
    plaintext, key = store.create_key(user.id, "laptop")
    return user, key, {"Authorization": f"Bearer {plaintext}"}


def test_fresh_db_without_admin_credentials_refuses_to_start(eng, monkeypatch):
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    with pytest.raises(api.AdminConfigError, match="VIENEU_ADMIN_USER"):
        with TestClient(api.app):
            pass
    assert api.STORE is None and not api.ADMIN_ON


def test_invalid_bootstrap_credentials_refuse_to_start(eng, monkeypatch):
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    monkeypatch.setenv("VIENEU_ADMIN_USER", "x")   # too short a username
    monkeypatch.setenv("VIENEU_ADMIN_PASSWORD", ADMIN_PW)
    with pytest.raises(api.AdminConfigError, match="rejected"):
        with TestClient(api.app):
            pass


def test_startup_bootstraps_admin_seeds_and_never_logs_the_password(eng, monkeypatch, caplog):
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    monkeypatch.setenv("VIENEU_ADMIN_USER", "root")
    monkeypatch.setenv("VIENEU_ADMIN_PASSWORD", ADMIN_PW)
    with caplog.at_level(logging.INFO):
        with TestClient(api.app):
            store = api.STORE
            assert store.has_active_admin() and store.list_dictionaries()
    assert "root" in caplog.text and ADMIN_PW not in caplog.text
    assert "every /v1/* call gets 401" in caplog.text


def test_existing_admin_starts_without_env_credentials(eng, tmp_path, monkeypatch):
    store = api.AdminStore(tmp_path / "admin.sqlite3")
    store.create_user("root", ADMIN_PW, "admin")       # e.g. `python -m vieneu_admin create-admin`
    store.close()
    monkeypatch.delenv("VIENEU_ADMIN", raising=False)
    with TestClient(api.app) as c:
        assert c.get("/admin/login").status_code == 200


def test_admin_on_with_zero_keys_rejects_every_call(admin):
    c, store = admin
    assert store.count_keys() == 0
    assert c.get("/v1/voices").status_code == 401
    assert _speech(c).status_code == 401
    assert c.get("/v1/models", headers={"Authorization": "Bearer vn_made-up"}).status_code == 401
    assert c.get("/health").status_code == 200        # health stays open for probes


def test_db_key_accepted_then_revoked(admin):
    c, store = admin
    _, key, headers = _key_for(store)
    r = _speech(c, headers=headers)
    assert r.status_code == 200 and r.content[:4] == b"RIFF"
    store.revoke_key(key.id, store.get_user_by_name("root"))
    assert _speech(c, headers=headers).status_code == 401


def test_disabled_user_key_rejected(admin):
    c, store = admin
    user, _, headers = _key_for(store)
    assert c.get("/v1/voices", headers=headers).status_code == 200
    store.set_active(user.id, False)
    assert c.get("/v1/voices", headers=headers).status_code == 401


def test_env_key_still_accepted_with_admin_on(admin, monkeypatch):
    c, _ = admin
    monkeypatch.setenv("VIENEU_API_KEY", "s3cret")
    assert c.get("/v1/voices", headers={"Authorization": "Bearer s3cret"}).status_code == 200
    assert c.get("/v1/voices", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_preprocess_sends_tagged_text_with_lexicon_to_the_engine(admin, eng):
    c, store = admin
    _, _, headers = _key_for(store)
    text = 'Harry nhìn lâu đài Hogwarts. "Đi thôi!" Ron hét lên. [1.0] Xong.'
    r = c.post("/v1/audio/speech", json={"input": text, "preprocess": True}, headers=headers)
    assert r.status_code == 200 and r.headers["X-VieNeu-Preprocess"] == "1"
    sent = eng.tts.stream_texts[-1]
    assert "Hốc-goát" in sent and "Hogwarts" not in sent          # seed dictionary applied
    assert "[0.35]" in sent and "[1.0]" in sent                    # pause tags for the engine
    assert eng.tts.stream_calls[-1]["max_chars"] == 256            # request max_chars still applies


def test_plain_request_reaches_the_engine_unchanged(admin, eng):
    c, store = admin
    _, _, headers = _key_for(store)
    text = 'Harry nhìn lâu đài Hogwarts. "Đi thôi!"'
    r = c.post("/v1/audio/speech", json={"input": text}, headers=headers)
    assert r.status_code == 200 and "X-VieNeu-Preprocess" not in r.headers
    assert eng.tts.stream_texts[-1] == text


def test_preprocess_failure_falls_back_to_raw_input(admin, eng, monkeypatch, caplog):
    c, store = admin
    _, _, headers = _key_for(store)

    def broken(*a, **kw):
        raise ValueError("unbalanced quote")
    monkeypatch.setattr(vieneu_preprocess, "preprocess", broken)
    with caplog.at_level(logging.WARNING):
        r = c.post("/v1/audio/speech", json={"input": "Xin chào.", "preprocess": True}, headers=headers)
    assert r.status_code == 200 and "X-VieNeu-Preprocess" not in r.headers
    assert eng.tts.stream_texts[-1] == "Xin chào."
    assert "unbalanced quote" in caplog.text


def test_preprocess_chunk_speed_is_reported_as_ignored(admin, monkeypatch):
    c, store = admin
    _, _, headers = _key_for(store)
    from vieneu_preprocess.types import Chunk, PreprocessResult
    monkeypatch.setattr(vieneu_preprocess, "preprocess", lambda text, lexicon=(), **kw: PreprocessResult(
        [Chunk("c1", "Narrator", "narration_countdown", "Ba.", speed=0.9, pause_after_sec=0.6)], ""))
    r = c.post("/v1/audio/speech", json={"input": "Ba.", "preprocess": True}, headers=headers)
    assert r.status_code == 200 and r.headers["X-VieNeu-Ignored"] == "speed"


def test_admin_router_is_mounted_and_root_redirects(admin):
    c, _ = admin
    r = c.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/"
    assert c.get("/admin/login").status_code == 200
    r = c.get("/admin/", follow_redirects=False)                 # admin keeps its own error handling
    assert r.status_code == 303 and "/admin/login" in r.headers["location"]
    assert c.get("/admin/static/app.css").status_code == 200


def test_script_lab_render_returns_wav_and_flac_through_the_stream_slot(admin, eng):
    c, _ = admin
    ui = login(api.app, "root", ADMIN_PW)
    for fmt, magic in (("wav", b"RIFF"), ("flac", b"fLaC")):
        r = post(ui, "/admin/script-lab/render", text="Harry nhìn Hogwarts. [0.5] Xong.", fmt=fmt)
        assert r.status_code == 200, r.text
        audio = ui.get("/admin/script-lab/audio")
        assert audio.status_code == 200 and audio.content[:4] == magic
        data, rate = sf.read(io.BytesIO(audio.content))
        assert rate == api.SAMPLE_RATE and len(data) > 0
    assert any("Hốc-goát" in t for t in eng.tts.stream_texts)     # rendered through infer_stream
    assert eng.active == 0                                          # the slot was given back


def test_script_lab_render_gets_429_when_the_engine_is_full(admin, eng):
    ui = login(api.app, "root", ADMIN_PW)
    eng.queue_timeout = 0.01
    for _ in range(eng.max_streams):
        eng.acquire()
    try:
        r = post(ui, "/admin/script-lab/render", text="Xin chào.", fmt="wav")
        assert r.status_code == 429
    finally:
        for _ in range(eng.max_streams):
            eng.release()
