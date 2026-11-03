"""`POST /tts/generate` against the *real* speech engine (not the double) —
runs only via `make portal-test-e2e`, which starts the engine profile first.
Skips cleanly when no real engine is configured, same pattern as the MinIO
integration test.
"""
from __future__ import annotations

import os

import pytest

from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import Voice

pytestmark = pytest.mark.engine

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


@pytest.fixture
def real_engine(monkeypatch):
    engine_url = os.environ.get("VIENEU_PORTAL_REAL_ENGINE_URL")
    service_key = os.environ.get("VIENEU_PORTAL_REAL_ENGINE_SERVICE_KEY")
    if not engine_url or not service_key:
        pytest.skip(
            "VIENEU_PORTAL_REAL_ENGINE_URL/VIENEU_PORTAL_REAL_ENGINE_SERVICE_KEY are not set; "
            "run via `make portal-test-e2e` with the engine profile up"
        )
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", engine_url)
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", service_key)
    monkeypatch.setenv("VIENEU_PORTAL_S3_ENDPOINT", os.environ.get("VIENEU_PORTAL_S3_ENDPOINT", ""))
    get_settings.cache_clear()
    yield engine_url
    get_settings.cache_clear()


def test_sync_generate_against_the_real_engine(client, db_session, real_engine) -> None:
    from sqlalchemy import select

    resp = client.post("/api/v1/auth/signup", json={"email": "real-engine@example.com", "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201
    settings = get_settings()
    client.post("/api/v1/user/terms/accept", json={"terms_version": settings.TERMS_VERSION}, headers={"X-CSRF-Token": _csrf(client)})

    voice = db_session.execute(select(Voice).where(Voice.is_active.is_(True))).scalars().first()
    assert voice is not None, "sync a voice from the real engine first (python -m vieneu_portal voices sync)"

    resp2 = client.post(
        "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "Xin chào, đây là bài kiểm tra engine thật."},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp2.status_code == 200
    assert resp2.json()["recording"]["status"] == "SUCCESS"
