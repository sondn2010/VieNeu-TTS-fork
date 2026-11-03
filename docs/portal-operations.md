# Portal operations

Reference for operators of the VieNeu **user portal** (`src/vieneu_portal/`): a
FastAPI + PostgreSQL service backing a Next.js SPA, plus a worker process and
the speech engine. For day-to-day user tasks (signup, Studio, My Voices), read
the **User guide** (`docs/user-guide.md`). Vietnamese version:
`docs/portal-operations.vi.md`.

> This replaces the old SQLite admin app that used to live inside the speech
> engine (`src/vieneu_admin/`, mounted at `/admin` on `apps/openai_speech.py`).
> That package no longer exists. See **Breaking changes** at the end of this
> document if you are upgrading a server that used it.

## 1. Architecture

```text
 Browser ──session cookie──▶ Next.js static export (served by the portal itself)
                                 │
                                 ▼
                       portal (FastAPI, src/vieneu_portal/)
                         │                              │
                         │ SQLAlchemy                   │ presigned URLs
                         ▼                              ▼
                     PostgreSQL                     S3-compatible storage
                  (users, voices, recordings,            (MinIO in dev)
                   dictionaries, audit log)
                         ▲
                         │ claims PENDING/ASYNC rows
                     worker (same image, `python -m vieneu_portal worker`)
                         │
                         ▼
                  speech engine (apps/openai_speech.py)
                    one VIENEU_API_KEY, no admin app, no database
```

- **portal**: serves `/api/v1/*` and, when `VIENEU_PORTAL_WEB_DIST_DIR` points
  at the Next.js `out/` build, the SPA itself at `/`. One process handles both
  the sync `POST /tts/generate` path (short text) and every other route; it
  never holds a database connection across a call to the engine or to storage.
- **worker**: the same image, `python -m vieneu_portal worker`. Claims
  `ASYNC`/`PENDING` recording rows with `SELECT ... FOR UPDATE SKIP LOCKED` —
  the recording row *is* the queue, there is no separate jobs table.
- **engine**: `apps/openai_speech.py`, reachable only by the portal and
  worker over `POST /internal/v1/render` and `POST /v1/audio/speech`, guarded
  by one shared `VIENEU_API_KEY` (compose calls it
  `VIENEU_ENGINE_SERVICE_KEY` on the portal side, same value). It has no
  database and no admin app of its own.
- **PostgreSQL**: the single source of truth for users, sessions, voices,
  recordings, dictionaries (account + system packs) and the admin audit log.
- **S3-compatible storage**: rendered audio and voice avatars/samples. The
  database stores object *keys*, never URLs — every read presigns a fresh,
  short-lived URL (`PRESIGN_TTL_SEC`).

## 2. Environment settings

Every setting is a `VIENEU_PORTAL_*` environment variable, loaded once at
startup by [`src/vieneu_portal/config.py`](../src/vieneu_portal/config.py) —
that file is the authoritative list of names, defaults and validation; this
section only calls out the ones that most affect a deployment:

| Variable | Required? | Notes |
|---|---|---|
| `VIENEU_PORTAL_SECRET_KEY` | **Yes** | Signs sessions and CSRF tokens; must be at least 32 bytes. No production default — startup fails fast without it. |
| `VIENEU_PORTAL_DATABASE_URL` | **Yes** | `postgresql://user:pass@host:port/db`. |
| `VIENEU_PORTAL_ENGINE_URL`, `VIENEU_PORTAL_ENGINE_SERVICE_KEY` | Yes (for TTS) | Where the engine lives and the key both sides share. |
| `VIENEU_PORTAL_S3_*` | Yes (for TTS) | Endpoint, bucket, credentials for recordings/voice media. |
| `VIENEU_PORTAL_FORWARDED_ALLOW_IPS` | Behind a reverse proxy | Proxy addresses trusted for `X-Forwarded-For`. Without this, every client behind the proxy shares its IP for login-throttle purposes. Empty (the default) trusts no proxy. |
| `VIENEU_PORTAL_SIGNUP_ENABLED` | No (default `true`) | Set `false` to close public signup (e.g. during a migration — see §6). |
| `VIENEU_PORTAL_COOKIE_SECURE` | No (default `true`) | Session/CSRF cookies get `Secure`; turn off only for a plain-HTTP dev setup. |
| `VIENEU_PORTAL_WEB_DIST_DIR` | No | Path to the Next.js static export (`portal-web/out/`); when set and the directory exists, the portal serves the SPA itself. |

## 3. Quick start (Docker Compose)

```bash
cp .env.example .env   # set VIENEU_PORTAL_SECRET_KEY, VIENEU_ENGINE_SERVICE_KEY
make portal-up         # postgres, minio, portal, worker (docker/docker-compose.portal.yml)
docker compose -f docker/docker-compose.portal.yml --profile cpu up -d engine
```

The portal listens on `http://localhost:8100` (`PORTAL_PORT`); the Next.js SPA
is served at `/` once the image's build stage has produced `out/` (see
`docker/Dockerfile.portal`). `make portal-down` stops the stack.

## 4. The first superadmin

Signup always creates a plain `USER` account — there is no "first admin"
bootstrap on startup the way the old admin app had one. Create the first
superadmin from the CLI, inside the running container:

```bash
docker compose -f docker/docker-compose.portal.yml exec portal \
  python -m vieneu_portal admin create you@example.com --role superadmin
```

This prompts for a password (entered twice) and never logs it. From there,
that account manages everything else through the admin web pages
(`/admin/users/`) or the `/api/v1/admin/*` API directly.

## 5. Admin area tour

Everything under `/admin/*` requires the `ADMIN` or `SUPERADMIN` role (the
`(admin)` layout itself redirects a plain `USER` to `/studio/`; the API
independently enforces the same matrix — the UI hiding an action is
convenience only, never the real guard).

| Area | Route | What it does |
|---|---|---|
| Users | `/admin/users/`, `/admin/users/detail/?id=` | List/search/filter accounts; create a user (role field shown only to `SUPERADMIN`); edit email/username; enable/disable; reset password; delete (typed-email confirm); adjust token balance (signed delta + required reason); edit plan (tier, quota, daily limit, expiry, reset-today). |
| API keys | (on the user detail page) | List and revoke a user's developer API keys. Never shows a key's hash. |
| Recordings | (on the user detail page) | Search/filter a user's recordings, including `FAILED` ones with their error code; delete. |
| System dictionaries | `/admin/dictionaries/`, `/admin/dictionaries/detail/?id=` | Create/rename/enable/delete a shared pronunciation pack; import `.json` (new pack, or merge/replace into one) or `.txt`; export `.json`/`.txt`; edit rules (source, replacement, `REPLACE` vs `ENGLISH_FALLBACK`, whole-word, case-sensitive, note) with an `If-Match` etag conflict check and an in-browser preview. |
| Voices | `/admin/voices/` | Edit the catalog (name, gender, region, tags, language label, sort order, active); upload/remove an avatar; upload a sample or render one through the engine. |
| Audit log | `/admin/audit-log/` | Read-only. Filters by actor, action, target type/id, date range; expandable before/after JSON (rendered as text, never HTML). |

### Roles and guards

- `USER`: no admin access.
- `ADMIN`: manages `USER` accounts only — cannot view, edit, disable or
  delete an `ADMIN`/`SUPERADMIN` account, and `POST /admin/users` with a
  `role` other than `USER` from an `ADMIN` actor gets `403 FORBIDDEN_ROLE`.
- `SUPERADMIN`: manages everyone; the only role that changes roles or
  creates `ADMIN`/`SUPERADMIN` accounts.
- The last active `SUPERADMIN` can never be demoted or disabled
  (`409 LAST_SUPERADMIN`), and nobody can disable, reset, re-role or delete
  their own account from the admin pages (`409 SELF_MODIFICATION`) — use the
  regular self-service password-change instead.
- Every mutation writes exactly one row to the audit log, in the same
  database transaction as the change; listing another user's recordings
  writes a `user.recordings_view` row (one per request, not per presigned
  URL). No route ever returns a password or a key hash.

## 6. One synthesis at a time, per user

Before a render starts, the portal takes a per-user lease
(`users.synthesis_lock_until`); a second `POST /tts/generate` or
`POST /tts/stream` from the same account while one is in flight gets
`409 SYNTHESIS_IN_PROGRESS`. Token/character quota is enforced by a single
atomic conditional `UPDATE` at the moment of charging — not by the earlier
precheck — so a concurrent admin token adjustment and a user's own generate
can never together push a balance negative.

## 7. Dictionary precedence

Three layers compile into one rule set for a given synthesis: the account's
own rules win over system packs, which win over the English-fallback list
(ties at equal match length go to the earliest layer). A system pack's
`ENGLISH_FALLBACK` entries wrap the matched term in `<en>...</en>` instead of
substituting text, so the engine reads it with its English pronunciation.
`python -m vieneu_portal text preview "<text>" [--user EMAIL]` prints exactly
the text the engine would receive, with or without an account's own rules —
this is the direct replacement for the old admin app's Script Lab preview.

## 8. SQLite migration runbook

If you are upgrading a server that ran the old `src/vieneu_admin/` SQLite
admin app, its users, API keys and dictionaries can be migrated into the
portal's Postgres database. The migrator is idempotent by provenance
(`legacy_source_id`), so re-running it is safe, and it aborts on a natural-key
conflict (e.g. a username already taken by a different account) rather than
guessing.

1. Keep `VIENEU_PORTAL_SIGNUP_ENABLED=false` until the migration is verified,
   so no new account can collide with one still to be migrated.
2. Back up first: the command itself takes a SQLite online backup of the
   source file and a `pg_dump` of the target before touching anything
   (`VIENEU_PORTAL_BACKUP_DIR`, default `vieneu_data/portal_backups`).
3. Rehearse with `--dry-run`, read the JSON report (counts, conflicts,
   `lost_rows`), fix anything it flags, then run the same command with
   `--apply`:

   ```bash
   docker compose -f docker/docker-compose.portal.yml exec portal \
     python -m vieneu_portal migrate-sqlite --sqlite /path/to/admin.sqlite3 --dry-run
   docker compose -f docker/docker-compose.portal.yml exec portal \
     python -m vieneu_portal migrate-sqlite --sqlite /path/to/admin.sqlite3 --apply
   ```

4. Migrated accounts sign in with `<username>@migrated.invalid` — give each
   person their own account's username so they know what to use, and tell
   them to change their email from the portal once signed in.
5. Run `python -m vieneu_portal system-dict seed` **only if the target had no
   SQLite admin database to migrate from** — seeding after a migration would
   create name-duplicate packs with no provenance, and the command refuses to
   run once any system dictionary already exists.
6. Re-enable `VIENEU_PORTAL_SIGNUP_ENABLED=true` once the report's counts
   match expectations.

A rehearsal of this exact runbook (against a fixture database, since no real
`vieneu_data/admin.sqlite3` existed in this environment) is recorded at
`plans/reports/261103-migration-rehearsal-dry-run.json`.

## 9. Backup and restore

- **PostgreSQL**: `python -m vieneu_portal db upgrade` takes a `pg_dump`
  before applying new migrations (`--no-backup` skips it only when `pg_dump`
  itself is unavailable). Restore with the matching `pg_restore`/`psql`
  against that dump.
- **Object storage**: back up the S3/MinIO bucket independently; the database
  only stores object keys, so a storage-only restore needs the bucket's
  contents to match the keys already in the database.

## 10. Breaking changes from the old admin app

- The speech engine has no `/admin` route, no database, and no Script Lab.
  `/` on the engine returns a plain `404`.
- The engine refuses to start on a non-loopback `HOST` unless
  `VIENEU_API_KEY` is set; the engine's own Docker Compose services now
  require that variable with no default (`${VIENEU_API_KEY:?set VIENEU_API_KEY}`).
- API keys issued by the old SQLite database (`vn_...`) no longer work
  against the engine directly. A C2 developer API (not yet built) will reissue
  equivalent keys scoped to the portal.
- A client calling the engine's `POST /v1/audio/speech` directly (bypassing
  the portal) no longer gets any pronunciation dictionary applied — global
  dictionaries are portal-only now; `preprocess: true` on that route still
  adds prosody/pause tags, nothing else.
- Script Lab is replaced by `python -m vieneu_portal text preview` (§7);
  `vieneu-preprocess` remains a standalone CLI tool with its own matcher,
  unrelated to the portal's dictionaries.
