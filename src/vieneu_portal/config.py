"""Portal runtime configuration, loaded once from `VIENEU_PORTAL_*` env vars.

A missing `DATABASE_URL` or a `SECRET_KEY` shorter than 32 bytes fails fast at
startup instead of drifting into a half-configured process. Test mode sets a
fixed 32-byte `SECRET_KEY` in `tests/portal/conftest.py`; no production
default exists.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_PREFIX = "VIENEU_PORTAL_"

_MODERATION_PROVIDERS = ("off", "blocklist")
_MODERATION_FAIL_MODES = ("closed",)
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class ConfigError(RuntimeError):
    """Raised when required settings are missing or invalid."""


def to_sqlalchemy_url(database_url: str) -> str:
    """Add the `psycopg` (v3) driver SQLAlchemy/Alembic need."""
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


def to_libpq_url(database_url: str) -> str:
    """Strip the SQLAlchemy `+psycopg` driver suffix; `pg_dump`/`psycopg`
    connect directly and need a plain `postgresql://` URI.
    """
    prefix = "postgresql+psycopg://"
    if database_url.startswith(prefix):
        return "postgresql://" + database_url[len(prefix) :]
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def _env(name: str) -> Optional[str]:
    return os.environ.get(_PREFIX + name)


def _env_str(name: str, default: str) -> str:
    return _env(name) or default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{_PREFIX}{name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{_PREFIX}{name} must be a number, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if not raw:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigError(f"{_PREFIX}{name} must be one of {sorted(_TRUE_VALUES | _FALSE_VALUES)}, got {raw!r}")


def _env_optional(name: str) -> Optional[str]:
    return _env(name) or None


def _env_choice(name: str, default: str, choices: tuple[str, ...]) -> str:
    value = _env_str(name, default)
    if value not in choices:
        raise ConfigError(f"{_PREFIX}{name} must be one of {choices}, got {value!r}")
    return value


@dataclass(frozen=True)
class Settings:
    HOST: str
    PORT: int
    SECRET_KEY: str
    FORWARDED_ALLOW_IPS: str
    DATABASE_URL: str
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT_SEC: int
    DB_STATEMENT_TIMEOUT_MS: int
    DB_IDLE_IN_TX_TIMEOUT_MS: int
    S3_ENDPOINT: Optional[str]
    S3_PUBLIC_ENDPOINT: Optional[str]
    S3_BUCKET: Optional[str]
    S3_ACCESS_KEY: Optional[str]
    S3_SECRET_KEY: Optional[str]
    S3_REGION: str
    PRESIGN_TTL_SEC: int
    ENGINE_URL: Optional[str]
    ENGINE_SERVICE_KEY: Optional[str]
    ENGINE_TIMEOUT_SEC: int
    ENGINE_SEC_PER_CHAR: float
    ENGINE_MAX_INPUT_CHARS: int
    JOB_LEASE_SEC: int
    WORKER_MAX_ATTEMPTS: int
    SESSION_TTL_SEC: int
    SESSION_ABSOLUTE_TTL_SEC: int
    ADMIN_SESSION_IDLE_TTL_SEC: int
    COOKIE_SECURE: bool
    SIGNUP_ENABLED: bool
    SIGNUP_MAX_PER_IP_PER_HOUR: int
    SIGNUP_MAX_GLOBAL_PER_HOUR: int
    LOGIN_MAX_FAILURES: int
    LOGIN_MAX_FAILURES_PER_IP: int
    MIGRATION_EMAIL_DOMAIN: str
    TOKENS_PER_CHAR_MILLI: int
    TRIAL_TOKENS: int
    TRIAL_DAILY_CHARS: int
    TRIAL_DAYS: int
    TTS_MAX_CHARS: int
    TTS_SYNC_CHAR_CAP: int
    MODERATION_PROVIDER: str
    MODERATION_BLOCKLIST_PATH: Optional[str]
    MODERATION_FAIL_MODE: str
    TERMS_VERSION: str
    QUOTA_TIMEZONE: str
    SYSTEM_RULES_MAX: int
    ADMIN_UPLOAD_MAX_BYTES_SAMPLE: int
    ADMIN_UPLOAD_MAX_BYTES_AVATAR: int
    WEB_DIST_DIR: Optional[str]
    BACKUP_DIR: str
    MODEL_VERSION_LABEL: str

    @property
    def sqlalchemy_database_url(self) -> str:
        return to_sqlalchemy_url(self.DATABASE_URL)

    def __repr__(self) -> str:  # secrets never get logged via repr/str
        return "Settings(...)"


def _load() -> Settings:
    secret_key = _env("SECRET_KEY")
    if not secret_key:
        raise ConfigError(f"{_PREFIX}SECRET_KEY is required")
    if len(secret_key.encode("utf-8")) < 32:
        raise ConfigError(f"{_PREFIX}SECRET_KEY must be at least 32 bytes")

    database_url = _env("DATABASE_URL")
    if not database_url:
        raise ConfigError(f"{_PREFIX}DATABASE_URL is required")

    engine_timeout_sec = _env_int("ENGINE_TIMEOUT_SEC", 60)
    engine_sec_per_char = _env_float("ENGINE_SEC_PER_CHAR", 0.05)
    engine_max_input_chars = _env_int("ENGINE_MAX_INPUT_CHARS", 20000)
    # The lease must outlive the longest possible render, with margin for the
    # lease-renewal cadence (every lease/3) to land before it expires.
    max_render_timeout_sec = engine_timeout_sec + engine_max_input_chars * engine_sec_per_char
    default_job_lease_sec = int(max_render_timeout_sec * 1.5) + 60
    job_lease_sec = _env_int("JOB_LEASE_SEC", default_job_lease_sec)
    if job_lease_sec <= max_render_timeout_sec:
        raise ConfigError(
            f"{_PREFIX}JOB_LEASE_SEC ({job_lease_sec}) must exceed the largest possible "
            f"render timeout ({max_render_timeout_sec:.0f}s, from ENGINE_TIMEOUT_SEC + "
            "ENGINE_MAX_INPUT_CHARS * ENGINE_SEC_PER_CHAR)"
        )

    quota_timezone = _env_str("QUOTA_TIMEZONE", "Asia/Saigon")
    try:
        ZoneInfo(quota_timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"{_PREFIX}QUOTA_TIMEZONE is not a known timezone: {quota_timezone!r}") from exc

    return Settings(
        HOST=_env_str("HOST", "127.0.0.1"),
        PORT=_env_int("PORT", 8100),
        SECRET_KEY=secret_key,
        FORWARDED_ALLOW_IPS=_env_str("FORWARDED_ALLOW_IPS", ""),
        DATABASE_URL=database_url,
        DB_POOL_SIZE=_env_int("DB_POOL_SIZE", 10),
        DB_MAX_OVERFLOW=_env_int("DB_MAX_OVERFLOW", 10),
        DB_POOL_TIMEOUT_SEC=_env_int("DB_POOL_TIMEOUT_SEC", 10),
        DB_STATEMENT_TIMEOUT_MS=_env_int("DB_STATEMENT_TIMEOUT_MS", 15000),
        DB_IDLE_IN_TX_TIMEOUT_MS=_env_int("DB_IDLE_IN_TX_TIMEOUT_MS", 30000),
        S3_ENDPOINT=_env_optional("S3_ENDPOINT"),
        S3_PUBLIC_ENDPOINT=_env_optional("S3_PUBLIC_ENDPOINT"),
        S3_BUCKET=_env_optional("S3_BUCKET"),
        S3_ACCESS_KEY=_env_optional("S3_ACCESS_KEY"),
        S3_SECRET_KEY=_env_optional("S3_SECRET_KEY"),
        S3_REGION=_env_str("S3_REGION", "us-east-1"),
        PRESIGN_TTL_SEC=_env_int("PRESIGN_TTL_SEC", 900),
        ENGINE_URL=_env_optional("ENGINE_URL"),
        ENGINE_SERVICE_KEY=_env_optional("ENGINE_SERVICE_KEY"),
        ENGINE_TIMEOUT_SEC=engine_timeout_sec,
        ENGINE_SEC_PER_CHAR=engine_sec_per_char,
        ENGINE_MAX_INPUT_CHARS=engine_max_input_chars,
        JOB_LEASE_SEC=job_lease_sec,
        WORKER_MAX_ATTEMPTS=_env_int("WORKER_MAX_ATTEMPTS", 3),
        SESSION_TTL_SEC=_env_int("SESSION_TTL_SEC", 14 * 86400),
        SESSION_ABSOLUTE_TTL_SEC=_env_int("SESSION_ABSOLUTE_TTL_SEC", 30 * 86400),
        ADMIN_SESSION_IDLE_TTL_SEC=_env_int("ADMIN_SESSION_IDLE_TTL_SEC", 12 * 3600),
        COOKIE_SECURE=_env_bool("COOKIE_SECURE", True),
        SIGNUP_ENABLED=_env_bool("SIGNUP_ENABLED", True),
        SIGNUP_MAX_PER_IP_PER_HOUR=_env_int("SIGNUP_MAX_PER_IP_PER_HOUR", 5),
        SIGNUP_MAX_GLOBAL_PER_HOUR=_env_int("SIGNUP_MAX_GLOBAL_PER_HOUR", 200),
        LOGIN_MAX_FAILURES=_env_int("LOGIN_MAX_FAILURES", 5),
        LOGIN_MAX_FAILURES_PER_IP=_env_int("LOGIN_MAX_FAILURES_PER_IP", 30),
        MIGRATION_EMAIL_DOMAIN=_env_str("MIGRATION_EMAIL_DOMAIN", "migrated.invalid"),
        TOKENS_PER_CHAR_MILLI=_env_int("TOKENS_PER_CHAR_MILLI", 1000),
        TRIAL_TOKENS=_env_int("TRIAL_TOKENS", 150000),
        TRIAL_DAILY_CHARS=_env_int("TRIAL_DAILY_CHARS", 50000),
        TRIAL_DAYS=_env_int("TRIAL_DAYS", 14),
        TTS_MAX_CHARS=_env_int("TTS_MAX_CHARS", 20000),
        TTS_SYNC_CHAR_CAP=_env_int("TTS_SYNC_CHAR_CAP", 3000),
        MODERATION_PROVIDER=_env_choice("MODERATION_PROVIDER", "off", _MODERATION_PROVIDERS),
        MODERATION_BLOCKLIST_PATH=_env_optional("MODERATION_BLOCKLIST_PATH"),
        MODERATION_FAIL_MODE=_env_choice("MODERATION_FAIL_MODE", "closed", _MODERATION_FAIL_MODES),
        TERMS_VERSION=_env_str("TERMS_VERSION", "1.0"),
        QUOTA_TIMEZONE=quota_timezone,
        SYSTEM_RULES_MAX=_env_int("SYSTEM_RULES_MAX", 20000),
        ADMIN_UPLOAD_MAX_BYTES_SAMPLE=_env_int("ADMIN_UPLOAD_MAX_BYTES_SAMPLE", 5 * 1024 * 1024),
        ADMIN_UPLOAD_MAX_BYTES_AVATAR=_env_int("ADMIN_UPLOAD_MAX_BYTES_AVATAR", 1 * 1024 * 1024),
        WEB_DIST_DIR=_env_optional("WEB_DIST_DIR"),
        BACKUP_DIR=_env_str("BACKUP_DIR", "vieneu_data/portal_backups"),
        MODEL_VERSION_LABEL=_env_str("MODEL_VERSION_LABEL", "V4"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _load()
