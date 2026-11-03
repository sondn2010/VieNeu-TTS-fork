"""`GET /api/v1/voices`: auth required, active voices ordered by `sort_order`,
presigned `sample_audio_url`.
"""
from __future__ import annotations

from vieneu_portal.db.models_voices_and_recordings import Voice
from vieneu_portal.storage.s3_object_storage import get_object_storage

from tests.portal.in_memory_object_storage import InMemoryObjectStorage

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup(client, email: str = "voices@example.com") -> None:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201


def _seed_voice(db_session, voice_id: str, *, name: str, sort_order: int, is_active: bool = True) -> None:
    db_session.add(Voice(
        id=voice_id, name=name, initials=name[0].upper(), gender="NAM", region="MIEN_BAC",
        engine_voice_name=name, sample_audio_url=f"voices/samples/{voice_id}.mp3",
        sample_object_key=f"voices/samples/{voice_id}.mp3", sort_order=sort_order, is_active=is_active,
    ))
    db_session.commit()


def test_voices_requires_auth(client) -> None:
    assert client.get("/api/v1/voices").status_code == 401


def test_voices_returns_active_rows_sorted_with_presigned_sample_url(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        _seed_voice(db_session, "b-voice", name="B Voice", sort_order=1)
        _seed_voice(db_session, "a-voice", name="A Voice", sort_order=0)
        _seed_voice(db_session, "inactive-voice", name="Inactive", sort_order=2, is_active=False)

        _signup(client)
        resp = client.get("/api/v1/voices")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [v["id"] for v in data] == ["a-voice", "b-voice"]
        assert data[0]["sample_audio_url"].startswith("https://fake-storage.test/voices/samples/a-voice.mp3")
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)
