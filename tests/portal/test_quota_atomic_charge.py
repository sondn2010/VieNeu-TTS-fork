"""The read-only precheck and the single atomic charge statement: charges
exactly once, never on a failing condition, resets the daily counter lazily
across the date boundary, and 20 concurrent per-user charges each succeed
exactly once without cross-user interference.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.errors import PortalError
from vieneu_portal.tts.quota_precheck_and_atomic_charge import charge_or_none, precheck_quota
from vieneu_portal.user.user_profile_serializer import quota_today


def _make_user(db_session, email: str, **overrides) -> User:
    defaults = dict(
        email=email, username=email.split("@")[0], password_hash="scrypt$16384$8$1$x$y",
        token_balance=1000, token_quota_total=1000, daily_char_limit=1000, daily_char_remaining=1000,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    return user


def test_precheck_insufficient_tokens(db_session) -> None:
    user = _make_user(db_session, "precheck1@example.com", token_balance=5)
    with pytest.raises(PortalError) as exc_info:
        precheck_quota(user, get_settings(), chars=1, tokens=10)
    assert exc_info.value.code == "INSUFFICIENT_TOKENS"


def test_precheck_daily_char_limit(db_session) -> None:
    user = _make_user(db_session, "precheck2@example.com", daily_char_remaining=5, daily_chars_reset_on=quota_today(get_settings()))
    with pytest.raises(PortalError) as exc_info:
        precheck_quota(user, get_settings(), chars=10, tokens=1)
    assert exc_info.value.code == "DAILY_CHAR_LIMIT_REACHED"


def test_precheck_plan_expired(db_session) -> None:
    user = _make_user(db_session, "precheck3@example.com", plan_expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    with pytest.raises(PortalError) as exc_info:
        precheck_quota(user, get_settings(), chars=1, tokens=1)
    assert exc_info.value.code == "PLAN_EXPIRED"


def test_precheck_passes_when_within_limits(db_session) -> None:
    user = _make_user(db_session, "precheck4@example.com")
    precheck_quota(user, get_settings(), chars=10, tokens=10)   # does not raise


def test_charge_deducts_tokens_and_chars(db_session) -> None:
    user = _make_user(db_session, "charge1@example.com")
    row = charge_or_none(db_session, user.id, get_settings(), chars=50, tokens=20)
    db_session.commit()
    assert row is not None
    token_balance, token_quota_total, daily_char_remaining = row
    assert token_balance == 980 and daily_char_remaining == 950


def test_charge_returns_none_when_tokens_insufficient(db_session) -> None:
    user = _make_user(db_session, "charge2@example.com", token_balance=5)
    row = charge_or_none(db_session, user.id, get_settings(), chars=1, tokens=10)
    db_session.commit()
    assert row is None
    assert db_session.get(User, user.id).token_balance == 5   # untouched


def test_charge_returns_none_for_inactive_user(db_session) -> None:
    user = _make_user(db_session, "charge3@example.com", is_active=False)
    row = charge_or_none(db_session, user.id, get_settings(), chars=1, tokens=1)
    db_session.commit()
    assert row is None


def test_daily_reset_happens_lazily_on_charge(db_session) -> None:
    settings = get_settings()
    yesterday = quota_today(settings) - timedelta(days=1)
    user = _make_user(
        db_session, "charge4@example.com", daily_char_limit=100, daily_char_remaining=1, daily_chars_reset_on=yesterday,
    )
    row = charge_or_none(db_session, user.id, settings, chars=30, tokens=1)
    db_session.commit()
    assert row is not None
    _, _, daily_char_remaining = row
    assert daily_char_remaining == 70   # reset to 100 then charged 30, not 1 - 30


def test_twenty_users_each_charged_exactly_once_with_no_cross_user_interference(db_session, portal_database_url) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vieneu_portal.config import to_sqlalchemy_url

    settings = get_settings()
    user_ids = [_make_user(db_session, f"concurrent{i}@example.com", token_balance=10, token_quota_total=10).id for i in range(20)]

    engine = create_engine(to_sqlalchemy_url(portal_database_url))
    Session_ = sessionmaker(bind=engine)
    results: dict = {}
    lock = threading.Lock()

    def charge_one(uid):
        session = Session_()
        try:
            row = charge_or_none(session, uid, settings, chars=1, tokens=10)
            session.commit()
            with lock:
                results[uid] = row is not None
        finally:
            session.close()

    threads = [threading.Thread(target=charge_one, args=(uid,)) for uid in user_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    engine.dispose()

    assert all(results.values())   # every user had exactly enough for one charge
    db_session.expire_all()
    for uid in user_ids:
        assert db_session.get(User, uid).token_balance == 0


# Files allowed to contain a `token_balance =`/`daily_char_remaining =`
# *source* match at all — the regex can't tell a column write from a
# `Column(...)` declaration or a tuple-unpack of the charge statement's own
# `RETURNING` row, so each is enumerated here with its reason, not waved
# through as a write:
_ALLOWED_FILES = {
    "models_users_and_sessions.py",               # the Column(...) declarations themselves
    "quota_precheck_and_atomic_charge.py",         # the one audited charge statement
    "recording_finalize_service.py",               # unpacks `charge_or_none`'s own RETURNING row
    "routes_auth_signup_login_logout.py",          # sets the *initial* trial grant on a brand-new row
    "user_account_admin_service.py",               # same, for an admin-created account
    "run_sqlite_to_postgres_migration.py",         # same, for a migrated account
    "token_and_plan_adjustment_service.py",        # phase 13's own audited admin token/plan writer
}
_ASSIGNMENT_RE = re.compile(r"\b(token_balance|daily_char_remaining)\s*=(?!=)")


def test_only_the_charge_module_and_initial_grants_assign_quota_columns() -> None:
    """Heuristic grep guard: `token_balance`/`daily_char_remaining` must
    never be assigned outside `quota_precheck_and_atomic_charge.py` (the one
    audited charge statement) and the two call sites that set a brand-new
    user's starting trial grant. Phase 13 extends this set by exactly its
    own audited admin token-adjustment module.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "vieneu_portal"
    offenders = []
    for path in src_root.rglob("*.py"):
        if path.name in _ALLOWED_FILES:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _ASSIGNMENT_RE.search(line):
                offenders.append(f"{path.relative_to(src_root)}:{lineno}: {line.strip()}")
    assert offenders == []
