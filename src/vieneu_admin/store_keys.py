"""API-key persistence and verification for AdminStore (mixed into the store class)."""
from __future__ import annotations

import hmac
import sqlite3
import time
from typing import Optional

from .db import Database
from .models import ApiKey, ForbiddenError, KeyOwner, NotFoundError, StoreError, User
from .security import API_KEY_PREFIX, new_api_key, sha256_hex

MAX_KEY_NAME_LEN = 80
_MAX_KEY_LEN = 128
_TOUCH_EVERY_SEC = 60  # update last_used_at at most once a minute per key

_KEY_SELECT = ("SELECT k.id, k.user_id, u.username, k.name, k.prefix, k.created_at, "
               "k.last_used_at, k.revoked_at FROM api_keys k JOIN users u ON u.id = k.user_id")


def _key(row: sqlite3.Row) -> ApiKey:
    return ApiKey(row["id"], row["user_id"], row["username"], row["name"], row["prefix"],
                  row["created_at"], row["last_used_at"], row["revoked_at"])


class KeyStoreMixin:
    db: Database

    def create_key(self, user_id: int, name: str) -> tuple[str, ApiKey]:
        """Create a key and return (plaintext, record). The plaintext is never stored."""
        name = (name or "").strip()
        if not (1 <= len(name) <= MAX_KEY_NAME_LEN):
            raise StoreError(f"Key name must be 1-{MAX_KEY_NAME_LEN} characters.")
        plaintext, prefix, key_hash = new_api_key()
        try:
            with self.db.write() as c:
                cur = c.execute(
                    "INSERT INTO api_keys (user_id, name, prefix, key_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?)", (user_id, name, prefix, key_hash, int(time.time())))
        except sqlite3.IntegrityError as e:
            raise NotFoundError("User not found.") from e
        return plaintext, self.get_key(int(cur.lastrowid))  # type: ignore[return-value]

    def get_key(self, key_id: int) -> Optional[ApiKey]:
        row = self.db.query_one(_KEY_SELECT + " WHERE k.id = ?", (key_id,))
        return _key(row) if row else None

    def list_keys(self, user_id: Optional[int] = None) -> list[ApiKey]:
        """Keys of one user, or of every user when ``user_id`` is None (admin view)."""
        order = " ORDER BY k.revoked_at IS NOT NULL, k.created_at DESC, k.id DESC"
        if user_id is None:
            rows = self.db.query(_KEY_SELECT + order)
        else:
            rows = self.db.query(_KEY_SELECT + " WHERE k.user_id = ?" + order, (user_id,))
        return [_key(r) for r in rows]

    def count_keys(self, user_id: Optional[int] = None, *, active_only: bool = True) -> int:
        sql = "SELECT COUNT(*) FROM api_keys k JOIN users u ON u.id = k.user_id WHERE 1 = 1"
        params: list = []
        if active_only:
            sql += " AND k.revoked_at IS NULL AND u.active = 1"
        if user_id is not None:
            sql += " AND k.user_id = ?"
            params.append(user_id)
        return int(self.db.query_one(sql, params)[0])

    def revoke_key(self, key_id: int, actor: User) -> ApiKey:
        """Revoke a key. Non-admins may only revoke their own keys (IDOR guard)."""
        key = self.get_key(key_id)
        if key is None:
            raise NotFoundError("Key not found.")
        if key.user_id != actor.id and not actor.is_admin:
            raise ForbiddenError("You can only revoke your own keys.")
        if key.revoked_at is None:
            with self.db.write() as c:
                c.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                          (int(time.time()), key_id))
        return self.get_key(key_id)  # type: ignore[return-value]

    def lookup(self, plaintext: str) -> Optional[KeyOwner]:
        """Resolve a plaintext key to its owner; None when unknown, revoked or user disabled."""
        if (not isinstance(plaintext, str) or not plaintext.startswith(API_KEY_PREFIX)
                or len(plaintext) > _MAX_KEY_LEN):
            return None
        key_hash = sha256_hex(plaintext)
        row = self.db.query_one(
            "SELECT k.id, k.name, k.key_hash, k.last_used_at, k.revoked_at, u.id AS uid, "
            "u.username, u.role, u.active FROM api_keys k JOIN users u ON u.id = k.user_id "
            "WHERE k.key_hash = ?", (key_hash,))
        if row is None or not hmac.compare_digest(row["key_hash"], key_hash):
            return None
        if row["revoked_at"] is not None or not row["active"]:
            return None
        now = int(time.time())
        if row["last_used_at"] is None or now - row["last_used_at"] >= _TOUCH_EVERY_SEC:
            with self.db.write() as c:
                c.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row["id"]))
        return KeyOwner(row["uid"], row["username"], row["role"], row["id"], row["name"])
