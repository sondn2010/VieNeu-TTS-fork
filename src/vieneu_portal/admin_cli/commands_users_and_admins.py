"""`admin create EMAIL --role admin|superadmin` and `user reset-password|
set-active|set-role`: same services and guards as the future phase 13 API.
A CLI call passes `actor=None` (counts as SUPERADMIN; audited as
`cli:<os-user>`) — the CLI itself is already an operator-only surface.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import func, select

from ..admin_services.user_account_admin_service import create_user_by_admin, reset_password, set_user_active, set_user_role
from ..db.models_users_and_sessions import User
from ..errors import PortalError
from .cli_parser_and_dispatch import current_settings, open_session


def _find_user_or_die(db, email: str) -> User:
    user = db.execute(select(User).where(func.lower(User.email) == email.strip().lower())).scalar_one_or_none()
    if user is None:
        print(f"no user with email {email!r}", file=sys.stderr)
        raise SystemExit(1)
    return user


def _prompt_password(label: str) -> str:
    password = getpass.getpass(f"{label}: ")
    if password != getpass.getpass(f"Confirm {label.lower()}: "):
        print("passwords do not match", file=sys.stderr)
        raise SystemExit(1)
    return password


def _handle_admin_create(args: argparse.Namespace) -> int:
    password = _prompt_password("Password")
    db = open_session()
    settings = current_settings()
    try:
        user = create_user_by_admin(
            db, settings, actor=None, email=args.email, username=args.email.split("@", 1)[0],
            password=password, role=args.role.upper(),
        )
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"created {user.email} ({user.role})")
    return 0


def _handle_user_reset_password(args: argparse.Namespace) -> int:
    password = _prompt_password("New password")
    db = open_session()
    try:
        target = _find_user_or_die(db, args.email)
        reset_password(db, actor=None, target=target, new_password=password)
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"password reset for {args.email}; every session was revoked")
    return 0


def _handle_user_set_active(args: argparse.Namespace) -> int:
    db = open_session()
    try:
        target = _find_user_or_die(db, args.email)
        set_user_active(db, actor=None, target=target, active=args.on)
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"{args.email} is now {'active' if args.on else 'inactive'}")
    return 0


def _handle_user_set_role(args: argparse.Namespace) -> int:
    db = open_session()
    try:
        target = _find_user_or_die(db, args.email)
        set_user_role(db, actor=None, target=target, role=args.role)
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"{args.email} role is now {args.role}")
    return 0


def add_parsers(top_sub) -> None:
    admin_parser = top_sub.add_parser("admin")
    admin_sub = admin_parser.add_subparsers(dest="command", required=True)
    create_parser = admin_sub.add_parser("create")
    create_parser.add_argument("email")
    create_parser.add_argument("--role", choices=["admin", "superadmin"], required=True)
    create_parser.set_defaults(handler=_handle_admin_create)

    user_parser = top_sub.add_parser("user")
    user_sub = user_parser.add_subparsers(dest="command", required=True)

    reset_parser = user_sub.add_parser("reset-password")
    reset_parser.add_argument("email")
    reset_parser.set_defaults(handler=_handle_user_reset_password)

    set_active_parser = user_sub.add_parser("set-active")
    set_active_parser.add_argument("email")
    active_group = set_active_parser.add_mutually_exclusive_group(required=True)
    active_group.add_argument("--on", dest="on", action="store_true")
    active_group.add_argument("--off", dest="on", action="store_false")
    set_active_parser.set_defaults(handler=_handle_user_set_active)

    set_role_parser = user_sub.add_parser("set-role")
    set_role_parser.add_argument("email")
    set_role_parser.add_argument("role", choices=["USER", "ADMIN", "SUPERADMIN"])
    set_role_parser.set_defaults(handler=_handle_user_set_role)
