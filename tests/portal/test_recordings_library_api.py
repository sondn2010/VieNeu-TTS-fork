"""`GET /tts/recordings`, `GET /tts/recordings/{id}`, `DELETE
/tts/recordings/{id}`: TC-07-style filter/search/totals, polling shape,
delete guards, and that another user's recordings are invisible.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from tests.portal.in_memory_object_storage import InMemoryObjectStorage
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import TTSRecording, Voice
from vieneu_portal.storage.s3_object_storage import get_object_storage

_PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def _fake_storage(client):
    storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: storage
    yield storage
    client.app.dependency_overrides.pop(get_object_storage, None)


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup(client, email: str) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": email, "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201


def _voice(db_session, voice_id: str, name: str) -> Voice:
    voice = Voice(
        id=voice_id, name=name, initials=name[0].upper(), gender="NAM", region="MIEN_BAC",
        engine_voice_name=name, sample_audio_url=f"voices/samples/{voice_id}.mp3",
        sample_object_key=f"voices/samples/{voice_id}.mp3", sort_order=0,
    )
    db_session.add(voice)
    db_session.flush()
    return voice


def _recording(db_session, user_id, voice_id: str, *, text: str, duration: float, status: str = "SUCCESS") -> TTSRecording:
    row = TTSRecording(
        user_id=user_id, voice_id=voice_id, original_text=text, processed_text=text, char_count=len(text),
        tokens_consumed=len(text), duration_seconds=Decimal(str(duration)), status=status,
        audio_object_key=f"recordings/{user_id}/{voice_id}.mp3" if status == "SUCCESS" else None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_tc07_filter_search_and_totals(client, db_session) -> None:
    _signup(client, "library@example.com")
    user = db_session.execute(select(User).where(User.email == "library@example.com")).scalar_one()
    voice_a = _voice(db_session, "voice-a", "Mai Anh")
    voice_b = _voice(db_session, "voice-b", "Hải Đăng")
    _recording(db_session, user.id, voice_a.id, text="Xin chào buổi sáng", duration=2.0)
    _recording(db_session, user.id, voice_a.id, text="Một câu khác hẳn", duration=3.0)
    _recording(db_session, user.id, voice_b.id, text="Chào buổi sáng Hải Đăng", duration=4.0)
    db_session.commit()

    resp_all = client.get("/api/v1/tts/recordings")
    assert resp_all.status_code == 200
    body_all = resp_all.json()
    assert body_all["overall_count"] == 3
    assert body_all["total_count"] == 3
    assert body_all["total_duration_seconds"] == 9.0
    assert {v["id"] for v in body_all["voices_used"]} == {"voice-a", "voice-b"}

    resp_voice = client.get("/api/v1/tts/recordings", params={"voice_id": voice_a.id})
    body_voice = resp_voice.json()
    assert body_voice["total_count"] == 2 and body_voice["total_duration_seconds"] == 5.0

    resp_search = client.get("/api/v1/tts/recordings", params={"search": "buổi sáng"})
    body_search = resp_search.json()
    assert body_search["total_count"] == 2   # two recordings' text contains "buổi sáng"
    assert body_search["overall_count"] == 3   # unaffected by the filter


def test_get_recording_includes_estimated_seconds_while_pending(client, db_session) -> None:
    _signup(client, "poll@example.com")
    user = db_session.execute(select(User).where(User.email == "poll@example.com")).scalar_one()
    voice = _voice(db_session, "voice-poll", "Poll Voice")
    recording = _recording(db_session, user.id, voice.id, text="x" * 10, duration=0.0, status="PENDING")
    db_session.commit()

    resp = client.get(f"/api/v1/tts/recordings/{recording.id}")
    assert resp.status_code == 200
    body = resp.json()["recording"]
    assert body["status"] == "PENDING" and "estimated_seconds" in body


def test_delete_pending_with_live_lease_returns_409(client, db_session) -> None:
    _signup(client, "delete-live@example.com")
    user = db_session.execute(select(User).where(User.email == "delete-live@example.com")).scalar_one()
    voice = _voice(db_session, "voice-delete-live", "Delete Live")
    recording = _recording(db_session, user.id, voice.id, text="x", duration=0.0, status="PENDING")
    user.synthesis_lock_until = datetime(2099, 1, 1, tzinfo=timezone.utc)
    db_session.commit()

    resp = client.delete(f"/api/v1/tts/recordings/{recording.id}", headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "RECORDING_IN_PROGRESS"


def test_delete_abandoned_pending_succeeds(client, db_session) -> None:
    _signup(client, "delete-abandoned@example.com")
    user = db_session.execute(select(User).where(User.email == "delete-abandoned@example.com")).scalar_one()
    voice = _voice(db_session, "voice-delete-abandoned", "Delete Abandoned")
    recording = _recording(db_session, user.id, voice.id, text="x", duration=0.0, status="PENDING")
    db_session.commit()   # no lease set -> treated as abandoned

    resp = client.delete(f"/api/v1/tts/recordings/{recording.id}", headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 204


def test_delete_success_removes_the_row(client, db_session) -> None:
    _signup(client, "delete-success@example.com")
    user = db_session.execute(select(User).where(User.email == "delete-success@example.com")).scalar_one()
    voice = _voice(db_session, "voice-delete-success", "Delete Success")
    recording = _recording(db_session, user.id, voice.id, text="x", duration=1.0)
    db_session.commit()

    resp = client.delete(f"/api/v1/tts/recordings/{recording.id}", headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 204
    # Not `.get()`: this instance is already identity-mapped in `db_session`,
    # so `.get()` would try to *refresh* it and raise `ObjectDeletedError`
    # instead of reporting absence; a plain SELECT has no such special case.
    assert db_session.execute(select(TTSRecording).where(TTSRecording.id == recording.id)).first() is None


def test_another_users_recordings_are_invisible(client, db_session) -> None:
    _signup(client, "owner-recordings@example.com")
    owner = db_session.execute(select(User).where(User.email == "owner-recordings@example.com")).scalar_one()
    voice = _voice(db_session, "voice-owner", "Owner Voice")
    recording = _recording(db_session, owner.id, voice.id, text="secret", duration=1.0)
    db_session.commit()

    _signup(client, "other-recordings@example.com")
    assert client.get("/api/v1/tts/recordings").json()["total_count"] == 0
    assert client.get(f"/api/v1/tts/recordings/{recording.id}").status_code == 404
    assert client.delete(f"/api/v1/tts/recordings/{recording.id}", headers={"X-CSRF-Token": _csrf(client)}).status_code == 404
