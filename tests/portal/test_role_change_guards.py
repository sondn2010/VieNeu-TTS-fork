"""Last-active-superadmin and self-modification guards, exercised through
`user_account_admin_service` (the guards are only ever called from there)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from vieneu_portal.admin_services.role_change_guards import guard_not_last_active_superadmin, guard_not_self
from vieneu_portal.admin_services.user_account_admin_service import create_user_by_admin, set_user_active, set_user_role
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.errors import PortalError


def _create(db_session, email: str, role: str = "USER") -> User:
    return create_user_by_admin(
        db_session, get_settings(), actor=None, email=email, username=email.split("@")[0],
        password="correct horse battery", role=role,
    )


def test_cannot_demote_the_last_active_superadmin(db_session) -> None:
    root = _create(db_session, "root@example.com", "SUPERADMIN")
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        set_user_role(db_session, actor=None, target=root, role="ADMIN")
    assert exc_info.value.code == "LAST_SUPERADMIN"


def test_cannot_disable_the_last_active_superadmin(db_session) -> None:
    root = _create(db_session, "root2@example.com", "SUPERADMIN")
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        set_user_active(db_session, actor=None, target=root, active=False)
    assert exc_info.value.code == "LAST_SUPERADMIN"


def test_demoting_one_of_two_superadmins_is_allowed(db_session) -> None:
    first = _create(db_session, "first@example.com", "SUPERADMIN")
    second = _create(db_session, "second@example.com", "SUPERADMIN")
    db_session.commit()

    set_user_role(db_session, actor=None, target=first, role="ADMIN")
    db_session.commit()

    assert first.role == "ADMIN"
    assert db_session.get(User, second.id).role == "SUPERADMIN"


def test_second_demotion_after_the_first_commits_hits_last_superadmin_guard(db_session) -> None:
    """Simulates two concurrent demotions serialized by the row lock: after
    the first demotion commits, a second attempt against the *other* former
    co-superadmin must now see itself as the last one and refuse.
    """
    first = _create(db_session, "third@example.com", "SUPERADMIN")
    second = _create(db_session, "fourth@example.com", "SUPERADMIN")
    db_session.commit()

    set_user_role(db_session, actor=None, target=first, role="ADMIN")
    db_session.commit()

    with pytest.raises(PortalError) as exc_info:
        set_user_role(db_session, actor=None, target=second, role="ADMIN")
    assert exc_info.value.code == "LAST_SUPERADMIN"


def test_cannot_change_own_role(db_session) -> None:
    root = _create(db_session, "self-role@example.com", "SUPERADMIN")
    other = _create(db_session, "other-role@example.com", "SUPERADMIN")
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        set_user_role(db_session, actor=root, target=root, role="ADMIN")
    assert exc_info.value.code == "SELF_MODIFICATION"


def test_cannot_disable_self(db_session) -> None:
    root = _create(db_session, "self-disable@example.com", "SUPERADMIN")
    other = _create(db_session, "other-disable@example.com", "SUPERADMIN")
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        set_user_active(db_session, actor=root, target=root, active=False)
    assert exc_info.value.code == "SELF_MODIFICATION"


def test_admin_actor_cannot_create_privileged_account(db_session) -> None:
    admin = _create(db_session, "plain-admin@example.com", "ADMIN")
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        create_user_by_admin(
            db_session, get_settings(), actor=admin, email="new-admin@example.com", username="new-admin",
            password="correct horse battery", role="ADMIN",
        )
    assert exc_info.value.code == "FORBIDDEN_ROLE"


def test_cli_actor_none_counts_as_superadmin(db_session) -> None:
    user = create_user_by_admin(
        db_session, get_settings(), actor=None, email="cli-created@example.com", username="cli-created",
        password="correct horse battery", role="SUPERADMIN",
    )
    assert user.role == "SUPERADMIN"


def test_guard_helpers_are_reusable_directly(db_session) -> None:
    root = _create(db_session, "direct-guard@example.com", "SUPERADMIN")
    db_session.commit()
    with pytest.raises(PortalError):
        guard_not_last_active_superadmin(db_session, root)
    with pytest.raises(PortalError):
        guard_not_self(root, root, "do anything to")
