"""`GET`/`PATCH /user/profile` and `POST /user/terms/accept`."""
from __future__ import annotations

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    resp = client.get("/api/v1/auth/csrf")
    assert resp.status_code == 200
    return resp.json()["csrf_token"]


def _signup(client, email: str = "profile@example.com") -> None:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 201


def test_profile_shows_trial_defaults_and_client_config(client) -> None:
    from vieneu_portal.config import get_settings

    _signup(client)
    settings = get_settings()

    resp = client.get("/api/v1/user/profile")
    assert resp.status_code == 200
    body = resp.json()

    assert body["token_balance"] == settings.TRIAL_TOKENS
    assert body["token_quota_total"] == settings.TRIAL_TOKENS
    assert body["daily_char_limit"] == settings.TRIAL_DAILY_CHARS
    assert body["daily_char_remaining"] == settings.TRIAL_DAILY_CHARS
    assert body["has_accepted_tts_terms"] is False
    assert body["role"] == "USER"
    assert body["client_config"] == {
        "tokens_per_char_milli": settings.TOKENS_PER_CHAR_MILLI,
        "tts_max_chars": settings.TTS_MAX_CHARS,
        "tts_sync_char_cap": settings.TTS_SYNC_CHAR_CAP,
        "terms_version": settings.TERMS_VERSION,
    }


def test_patch_profile_updates_fields(client) -> None:
    _signup(client)
    resp = client.patch(
        "/api/v1/user/profile",
        json={"username": "New Name", "ui_theme": "light", "ui_language": "en", "onboarding_hidden": True},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "New Name"
    assert body["ui_theme"] == "light"
    assert body["ui_language"] == "en"
    assert body["onboarding_hidden"] is True


def test_patch_profile_rejects_invalid_theme(client) -> None:
    _signup(client)
    resp = client.patch(
        "/api/v1/user/profile", json={"ui_theme": "neon"}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_profile_rejects_invalid_language(client) -> None:
    _signup(client)
    resp = client.patch(
        "/api/v1/user/profile", json={"ui_language": "fr"}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_profile_requires_csrf(client) -> None:
    _signup(client)
    resp = client.patch("/api/v1/user/profile", json={"ui_theme": "light"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_FAILED"


def test_terms_accept_sets_flag_and_ip(client) -> None:
    from vieneu_portal.config import get_settings

    _signup(client)
    settings = get_settings()

    resp = client.post(
        "/api/v1/user/terms/accept",
        json={"terms_version": settings.TERMS_VERSION},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_accepted_tts_terms"] is True
    assert body["terms_version"] == settings.TERMS_VERSION


def test_terms_accept_wrong_version_returns_409(client) -> None:
    _signup(client)
    resp = client.post(
        "/api/v1/user/terms/accept", json={"terms_version": "not-the-current-version"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TERMS_VERSION_MISMATCH"


def test_terms_version_bump_re_prompts(client, monkeypatch) -> None:
    """A policy update changes `TERMS_VERSION`; a user who accepted the old
    version must show `has_accepted_tts_terms: false` again.
    """
    from vieneu_portal.config import get_settings

    _signup(client)
    old_version = get_settings().TERMS_VERSION

    accept = client.post(
        "/api/v1/user/terms/accept", json={"terms_version": old_version}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert accept.status_code == 200
    assert accept.json()["has_accepted_tts_terms"] is True

    monkeypatch.setenv("VIENEU_PORTAL_TERMS_VERSION", old_version + "-v2")
    get_settings.cache_clear()
    try:
        resp = client.get("/api/v1/user/profile")
        assert resp.status_code == 200
        assert resp.json()["has_accepted_tts_terms"] is False
    finally:
        get_settings.cache_clear()
