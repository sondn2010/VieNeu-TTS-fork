"""User and session persistence for AdminStore (mixed into the store class)."""
from __future__ import annotations

import re
import sqlite3
import time
from typing import Optional

from .db import Database
from .models import ROLES, NotFoundError, Session, StoreError, User
from .security import (MAX_PASSWORD_LEN, SESSION_TTL_SEC, CsrfSigner, hash_password,
                       new_session_token, sha256_hex, verify_password, burn_password_check)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
MIN_PASSWORD_LEN = 8
_SLIDE_EVERY_SEC = 60  # extend a session's expiry at most once a minute


def _user(row: sqlite3.Row) -> User:
    return User(row["id"], row["username"], row["role"], bool(row["active"]), row["created_at"])


def validate_password(password: str) -> None:
    if not isinstance(password, str) or not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
        raise StoreError(f"Password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters.")


class AccountStoreMixin:
    db: Database

    # -- users ------------------------------------------------------------------
    def get_user(self, user_id: int) -> Optional[User]:
        row = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return _user(row) if row else None

    def get_user_by_name(self, username: str) -> Optional[User]:
        row = self.db.query_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
        return _user(row) if row else None

    def list_users(self) -> list[User]:
        return [_user(r) for r in self.db.query("SELECT * FROM users ORDER BY username COLLATE NOCASE")]

    def has_active_admin(self) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM users WHERE role = 'admin' AND active = 1 LIMIT 1") is not None

    def create_user(self, username: str, password: str, role: str = "user") -> User:
        username = (username or "").strip()
        if not USERNAME_RE.match(username):
            raise StoreError("Username must be 3-40 characters: letters, digits, '.', '_' or '-'.")
        if role not in ROLES:
            raise StoreError("Unknown role.")
        validate_password(password)
        pw_hash = hash_password(password)
        try:
            with self.db.write() as c:
                cur = c.execute(
                    "INSERT INTO users (username, password_hash, role, active, created_at) "
                    "VALUES (?, ?, ?, 1, ?)", (username, pw_hash, role, int(time.time())))
        except sqlite3.IntegrityError as e:
            raise StoreError(f"User {username!r} already exists.") from e
        return self.get_user(int(cur.lastrowid))  # type: ignore[return-value]

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Return the active user for valid credentials; equal timing for unknown names."""
        row = self.db.query_one("SELECT * FROM users WHERE username = ?", ((username or "").strip(),))
        if row is None:
            burn_password_check(password or "")
            return None
        if not verify_password(password or "", row["password_hash"]) or not row["active"]:
            return None
        return _user(row)

    @staticmethod
    def _guard_last_admin(c: sqlite3.Connection, user_id: int) -> None:
        """Refuse to remove the last active admin (call inside the write transaction)."""
        row = c.execute("SELECT role, active FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError("User not found.")
        if row["role"] == "admin" and row["active"]:
            others = c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1 "
                               "AND id != ?", (user_id,)).fetchone()[0]
            if others == 0:
                raise StoreError("This is the last active admin; promote another admin first.")

    def set_role(self, user_id: int, role: str) -> None:
        if role not in ROLES:
            raise StoreError("Unknown role.")
        with self.db.write() as c:
            if role != "admin":
                self._guard_last_admin(c, user_id)
            if c.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id)).rowcount == 0:
                raise NotFoundError("User not found.")

    def set_active(self, user_id: int, active: bool) -> None:
        """Enable or disable a user; disabling also ends every session of that user."""
        with self.db.write() as c:
            if not active:
                self._guard_last_admin(c, user_id)
            if c.execute("UPDATE users SET active = ? WHERE id = ?",
                         (1 if active else 0, user_id)).rowcount == 0:
                raise NotFoundError("User not found.")
            if not active:
                c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def reset_password(self, user_id: int, password: str) -> None:
        """Set a new password and end every session of that user."""
        validate_password(password)
        pw_hash = hash_password(password)
        with self.db.write() as c:
            if c.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (pw_hash, user_id)).rowcount == 0:
                raise NotFoundError("User not found.")
            c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def delete_user(self, user_id: int) -> None:
        with self.db.write() as c:
            self._guard_last_admin(c, user_id)
            c.execute("DELETE FROM users WHERE id = ?", (user_id,))

    # -- sessions ---------------------------------------------------------------
    def create_session(self, user_id: int) -> tuple[str, Session]:
        """Return (cookie token, session). Only the token's SHA-256 is stored."""
        token, token_hash = new_session_token()
        now = int(time.time())
        csrf = CsrfSigner.new_nonce()
        with self.db.write() as c:
            c.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            c.execute("INSERT INTO sessions (token_hash, user_id, csrf, expires_at) VALUES (?, ?, ?, ?)",
                      (token_hash, user_id, csrf, now + SESSION_TTL_SEC))
        session = self.get_session(token)
        if session is None:
            raise StoreError("Account is disabled.")
        return token, session

    def get_session(self, token: Optional[str]) -> Optional[Session]:
        """Resolve a cookie token to a live session of an active user (sliding expiry)."""
        if not token or len(token) > 128:
            return None
        token_hash = sha256_hex(token)
        now = int(time.time())
        row = self.db.query_one(
            "SELECT s.token_hash, s.csrf, s.expires_at, u.* FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?", (token_hash,))
        if row is None or row["expires_at"] <= now or not row["active"]:
            return None
        expires = row["expires_at"]
        if now + SESSION_TTL_SEC - expires >= _SLIDE_EVERY_SEC:
            expires = now + SESSION_TTL_SEC
            with self.db.write() as c:
                c.execute("UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (expires, token_hash))
        return Session(token_hash, _user(row), row["csrf"], expires)

    def delete_session(self, token_hash: str) -> None:
        with self.db.write() as c:
            c.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def delete_sessions_for_user(self, user_id: int) -> None:
        with self.db.write() as c:
            c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def purge_expired_sessions(self) -> int:
        with self.db.write() as c:
            return c.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),)).rowcount
