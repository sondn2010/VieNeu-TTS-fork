---
phase: 5
title: "Admin web app"
status: pending
priority: P1
effort: "12h"
dependencies: [1]
---

# Phase 5: Admin web app

## Goal

A self-contained `vieneu_admin` package exposing one FastAPI `APIRouter` (mounted at `/admin` in phase 6) plus a store and an API-key verifier, with no import of `apps.*` or the TTS engine.

## Files to Create / Modify

All under `src/vieneu_admin/` (except `seed/`, owned by phase 4) and `tests/test_admin_*.py`.

- `__init__.py` — exports `create_admin_router(store, *, tts_provider)`, `AdminStore`, `verify_api_key`.
- `db.py` — SQLite connection (WAL, `check_same_thread=False`, one lock for writes), schema + numbered migrations in a `schema_version` table; **copies the DB file to `<db>.bak-<UTC timestamp>` before applying any migration to an existing file**. Path from `VIENEU_ADMIN_DB` (default `vieneu_data/admin.sqlite3`).
- `store.py` — `AdminStore` methods: users (create, list, set role, enable/disable, reset password, delete), keys (create → returns plaintext once, list for user or all, revoke, `lookup(plaintext)`), sessions (create, get, delete, purge expired), dictionaries (list, get, create, rename, toggle, delete, replace entries, merge entries, upsert/delete entry, search), `enabled_lexicon()` cached and invalidated by a `dict_version` counter bumped on every dictionary write, `seed_if_empty(seed_dir)`, `bootstrap_admin(username, password)`.
- `security.py` — `hash_password` / `verify_password` with `hashlib.scrypt` (n=2**14, r=8, p=1, 16-byte salt, encoded `scrypt$n$r$p$salt$hash`); API keys `vn_` + `secrets.token_urlsafe(32)`, stored as SHA-256 hex + 8-char display prefix; session tokens `secrets.token_urlsafe(32)` stored hashed, 12 h sliding expiry; per-session CSRF token; login lockout after 5 failures per username or IP for 5 min (in memory).
- `auth.py` — FastAPI dependencies `current_user`, `require_admin`, `csrf_protect`; cookie `vieneu_session`, `HttpOnly`, `SameSite=Lax`, `Secure` when `VIENEU_COOKIE_SECURE=1`.
- `routes.py` — pages and HTMX partials:
  - `GET/POST /login`, `POST /logout`, `GET/POST /account/password`.
  - `GET /` dashboard: own key count, enabled dictionaries, links.
  - `GET /keys`, `POST /keys` (name → shows plaintext once in a dismissible panel with copy button), `POST /keys/{id}/revoke`; admins see every user's keys with an owner column and may revoke any.
  - Admin only: `GET /users`, `POST /users`, `POST /users/{id}/role`, `POST /users/{id}/active`, `POST /users/{id}/password`, `POST /users/{id}/delete` (cannot delete or demote the last active admin, nor yourself).
  - `GET /dictionaries` (all users can view), admin only: create, rename, toggle, delete, entry add/edit/delete inline (HTMX), `POST /dictionaries/import` (file upload ≤ 5 MB; choose new dictionary, merge into, or replace), `GET /dictionaries/{id}/export` (download `<slug>.json`), `GET /dictionaries/{id}?q=` search with pagination (50/page), `POST /dictionaries/preview` (sentence in → lexicon-applied text out).
  - `GET /script-lab`, `POST /script-lab/preprocess` (text ≤ 50 000 chars → script, JSON, tagged text tabs; speaker → voice mapping table filled from the voices list), `POST /script-lab/render` (calls `tts_provider` hook; returns WAV or FLAC download and an inline `<audio>`), `GET /script-lab/download.json`.
  - `GET /help?doc=functions|guide&lang=en|vi` renders `VIENEU_DOCS_DIR` (default `<repo>/docs`) files `web-admin-functions[.vi].md` and `user-guide[.vi].md` with markdown-it-py (`html=False`, tables on); missing files show a clear notice with the expected path.
- `tts_provider` contract: an object with `voices() -> list[str]`, `render(result, voices, fmt) -> bytes` and `available() -> bool`; phase 6 supplies the real one. Script Lab shows "engine not loaded" when unavailable; tests pass a fake.
- `templates/` — `base.html` (nav: Dashboard, API keys, Dictionaries, Script Lab, Users [admin], Help, language EN/VI for Help, logout), one template per page, `partials/` for HTMX fragments. Autoescape on. Every form includes the CSRF hidden field; HTMX sends it via `hx-headers`.
- `static/` — `htmx.min.js` (vendored, pinned 1.9.12, license header kept), `app.css` (small, no framework, readable on mobile, light/dark via `prefers-color-scheme`).
- `cli.py` — `python -m vieneu_admin create-admin USER` (prompts password twice), `reset-password USER`, `export-dicts DIR`, `import-dict FILE`.
- Tests: `tests/test_admin_security.py`, `tests/test_admin_store.py`, `tests/test_admin_routes.py` (TestClient on a bare FastAPI app with the router and a temp DB), `tests/test_admin_migrations.py`.

## Tasks & Steps

- [ ] Schema v1: `users(id, username UNIQUE COLLATE NOCASE, password_hash, role CHECK IN ('admin','user'), active, created_at)`, `api_keys(id, user_id FK CASCADE, name, prefix, key_hash UNIQUE, created_at, last_used_at, revoked_at)`, `sessions(token_hash PK, user_id FK CASCADE, csrf, expires_at)`, `dictionaries(id, name UNIQUE, kind, enabled, description, updated_at)`, `dictionary_entries(id, dictionary_id FK CASCADE, term, term_key, replacement, mode, case_sensitive, note, UNIQUE(dictionary_id, term_key))`.
- [ ] Store + security + auth with unit tests.
- [ ] `verify_api_key(store, header) -> Optional[KeyOwner]`: constant-time compare against the stored hash row found by hash; rejects revoked keys and disabled users; updates `last_used_at` at most once per minute per key.
- [ ] Routes and templates; import/export use `dictionary_schema` from phase 1 only.
- [ ] Route tests: login/logout, lockout, CSRF rejection, role checks (403 for non-admin on users and dictionary writes), key create shows plaintext once and list never shows it, revoke, last-admin guard, dictionary import (new/merge/replace) and export round-trip, malformed JSON shows line/column, preview applies lexicon, help renders a temp docs dir in both languages and escapes raw HTML.
- [ ] Migration test: an existing v1 file gets a `.bak-*` copy before a fake v2 migration runs.

## Verification

- `uv run pytest tests/test_admin_*.py -q`

## Risk / rollback

SQLite on local disk assumes one API instance (recorded trade-off). Rollback: revert the phase commit; the DB file is separate and backed up before migrations.
