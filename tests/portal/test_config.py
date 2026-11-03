"""Unit coverage for config.py validation — no DB needed."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
os.environ.setdefault("VIENEU_PORTAL_DATABASE_URL", "postgresql://u:p@localhost/db")


def _reload_settings():
    from vieneu_portal import config

    config.get_settings.cache_clear()
    try:
        return config.get_settings()
    finally:
        config.get_settings.cache_clear()


def test_job_lease_sec_must_exceed_the_largest_render_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from vieneu_portal.config import ConfigError

    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_TIMEOUT_SEC", "60")
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_MAX_INPUT_CHARS", "20000")
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SEC_PER_CHAR", "0.05")
    monkeypatch.setenv("VIENEU_PORTAL_JOB_LEASE_SEC", "180")  # 60 + 20000*0.05 = 1060s
    with pytest.raises(ConfigError, match="JOB_LEASE_SEC"):
        _reload_settings()


def test_job_lease_sec_default_satisfies_its_own_constraint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIENEU_PORTAL_JOB_LEASE_SEC", raising=False)
    settings = _reload_settings()
    max_render = settings.ENGINE_TIMEOUT_SEC + settings.ENGINE_MAX_INPUT_CHARS * settings.ENGINE_SEC_PER_CHAR
    assert settings.JOB_LEASE_SEC > max_render


def test_cookie_secure_defaults_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIENEU_PORTAL_COOKIE_SECURE", raising=False)
    assert _reload_settings().COOKIE_SECURE is True


def test_env_bool_rejects_unrecognized_values(monkeypatch: pytest.MonkeyPatch) -> None:
    from vieneu_portal.config import ConfigError

    monkeypatch.setenv("VIENEU_PORTAL_COOKIE_SECURE", "ture")
    with pytest.raises(ConfigError):
        _reload_settings()


def test_moderation_provider_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    from vieneu_portal.config import ConfigError

    monkeypatch.setenv("VIENEU_PORTAL_MODERATION_PROVIDER", "openai")
    with pytest.raises(ConfigError):
        _reload_settings()


def test_quota_timezone_rejects_unknown_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    from vieneu_portal.config import ConfigError

    monkeypatch.setenv("VIENEU_PORTAL_QUOTA_TIMEZONE", "Not/AZone")
    with pytest.raises(ConfigError):
        _reload_settings()


@pytest.mark.parametrize(
    "given,expected",
    [
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_to_sqlalchemy_url_normalizes_scheme(given: str, expected: str) -> None:
    from vieneu_portal.config import to_sqlalchemy_url

    assert to_sqlalchemy_url(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        ("postgresql+psycopg://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
    ],
)
def test_to_libpq_url_normalizes_scheme(given: str, expected: str) -> None:
    from vieneu_portal.config import to_libpq_url

    assert to_libpq_url(given) == expected
