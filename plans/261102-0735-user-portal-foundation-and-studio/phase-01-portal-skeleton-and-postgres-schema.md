# Phase 01: Portal skeleton and Postgres schema

## Context
- Brainstorm: `plans/reports/brainstorm-261102-0735-user-portal-postgres-rewrite.md` (C0 row, architecture call 1).
- DDL: `docs/vieneu_tts_docs_specs/docs/specs/08_database_schema_and_api_contracts.md:10-205`.
- Pattern to reuse: backup-before-migrate in `src/vieneu_admin/db.py:144-184`.
- Packaging: `pyproject.toml` (`[project.optional-dependencies]`, `[tool.setuptools.packages.find]`, pytest `pythonpath = ["src"]`).

## Overview
Priority P1. Status pending. Creates `src/vieneu_portal/` (torch-free FastAPI app, `/api/v1`), the full settings object for C0+C1, SQLAlchemy 2 models, the Alembic baseline, the JSON error envelope, and a Postgres-backed test harness. No user-visible feature yet.

## Key insights
- Python module names must be snake_case to be importable; use long descriptive snake_case names (kebab-case only for TS/config files).
- `config.py` defines every C0+C1 setting now, so later phases never edit it in parallel.
- Spec 08 and master DDL disagree on column names; 08 is the DDL authority (`processed_text`, `tokens_consumed`, `error_code`).

## Requirements
- `python -m vieneu_portal serve` starts uvicorn on `PORTAL_HOST:PORTAL_PORT` (default 127.0.0.1:8100).
- `GET /api/v1/health` returns `{status, db}`; DB down gives 503.
- When `WEB_DIST_DIR` exists, `app.py` serves the Next.js static export at `/` (exact file, then `<path>/index.html`, then `404.html`); `/api/*` never falls through to the SPA. Done here so web phases never edit `app.py`.
- Errors always `{"error": {"code": "UPPER_SNAKE", "message": str, ...extra}}`; FastAPI validation errors map to `422 VALIDATION_ERROR`.
- `python -m vieneu_portal db upgrade` runs `pg_dump` to `PORTAL_BACKUP_DIR` first when the target DB has tables, then `alembic upgrade head`. Missing `pg_dump` on a non-empty DB aborts unless `--no-backup` is passed explicitly.

## Architecture
Settings (env, prefix `VIENEU_PORTAL_`): `DATABASE_URL`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `STORAGE_BACKEND` (`s3`|`local`), `LOCAL_STORAGE_DIR`, `PRESIGN_TTL_SEC` (900), `ENGINE_URL`, `ENGINE_SERVICE_KEY`, `ENGINE_TIMEOUT_SEC`, `SESSION_TTL_SEC` (14 d), `COOKIE_SECURE`, `TOKENS_PER_CHAR_MILLI` (1000), `TRIAL_TOKENS` (150000), `TRIAL_DAILY_CHARS` (50000), `TRIAL_DAYS` (14), `TTS_MAX_CHARS` (20000), `TTS_SYNC_CHAR_CAP` (3000), `MODERATION_PROVIDER` (`off`|`blocklist`), `MODERATION_BLOCKLIST_PATH`, `MODERATION_FAIL_MODE` (`closed`), `TERMS_VERSION` ("1.0"), `QUOTA_TIMEZONE` (`Asia/Saigon`), `S3_PUBLIC_ENDPOINT` (presign host), `ADMIN_UPLOAD_MAX_BYTES` (5 MB samples, 1 MB avatars), `WEB_DIST_DIR`, `BACKUP_DIR`, `MODEL_VERSION_LABEL` ("V4").

Baseline migration = every table of spec 08 plus these additions:
| Table | Addition |
|---|---|
| users | `password_hash`, `role` CHECK (`USER`,`ADMIN`,`SUPERADMIN`) default `USER`, `is_active`, `last_login_at`, `terms_version`, `terms_accepted_ip`, `daily_chars_reset_on DATE`, unique index on `lower(email)` |
| user_sessions (new) | `token_hash` PK, `user_id` FK cascade, `csrf_nonce`, `expires_at`, `created_at`, `ip`, `user_agent` |
| voices | `engine_voice_name` (preset key sent to engine), `sort_order`, `sample_object_key` |
| tts_recordings | `audio_object_key`; `source_module` CHECK widened to `STUDIO,PODCAST,STORY,API,MCP`; pg_trgm GIN on `original_text` |
| story_segments | status CHECK `DRAFT,GENERATING,READY,MODIFIED_NEEDS_REGEN` |
| system_dictionaries (new) | `id`, `name` unique, `kind`, `is_enabled`, `description`, `sort_order`, `updated_at` |
| system_pronunciation_rules (new) | rule columns of `pronunciation_rules` with `dictionary_id` FK instead of `user_id`, plus `note TEXT NOT NULL DEFAULT ''` (lossless legacy import) and `rule_kind` CHECK (`REPLACE`,`ENGLISH_FALLBACK`) default `REPLACE` (fallback rows keep `phonetic_replacement = ''`; CHECK: `REPLACE` requires non-empty replacement) |
| admin_audit_log (new) | `id BIGSERIAL`, `actor_user_id` FK `ON DELETE SET NULL`, `actor_label` (email or `cli:<os-user>`), `action VARCHAR(64)`, `target_type VARCHAR(32)`, `target_id TEXT`, `target_label TEXT`, `before JSONB`, `after JSONB`, `ip`, `created_at`; indexes `(created_at DESC)`, `(target_type, target_id)`; no FK on target so rows survive deletes |
| background_jobs (new) | `id`, `kind`, `user_id`, `payload JSONB`, `status` (`QUEUED,RUNNING,SUCCEEDED,FAILED`), `attempts`, `locked_until`, `error_code`, `result_ref`, `created_at`, `updated_at`; index `(status, created_at)` |

Extensions: `pgcrypto` (gen_random_uuid), `pg_trgm`.

## Related code files
Create (all under `src/vieneu_portal/` unless noted):
- `__init__.py`, `__main__.py` (argparse dispatch: `serve`, `db upgrade|current`)
- `config.py`, `errors.py`, `app.py` (`create_app()`, error handlers, router list), `routes_health.py`
- `db/session_factory.py`, `db/base.py`, `db/models_users_and_sessions.py`, `db/models_voices_and_recordings.py`, `db/models_dictionaries.py`, `db/models_podcasts_and_stories.py`, `db/models_developer_and_billing.py`, `db/models_background_jobs.py`, `db/models_admin_audit_log.py`
- `db/database_backup_before_migrate.py`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_baseline_spec_schema.py`, `alembic.ini`
- `tests/portal/conftest.py` (creates a throwaway database per session from `VIENEU_PORTAL_TEST_DATABASE_URL`, runs `alembic upgrade head`, truncates per test), `tests/portal/test_schema_baseline.py`, `tests/portal/test_health_and_error_envelope.py`
- `docker/docker-compose.portal.yml` (postgres:16 + minio + bucket-init only; phase 6 adds services)

Modify: `pyproject.toml` (extra `portal = [fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary]>=3, boto3, httpx]`, package find include `vieneu_portal*`, package-data for `alembic.ini`, `migrations/**`), `Makefile` (`portal-db-up`, `portal-test`).

## Implementation steps
1. Add the `portal` extra and package registration; `uv lock`.
2. Write `config.py` as a frozen dataclass loaded once from env with validation (fail fast on missing `DATABASE_URL`).
3. Write models mirroring DDL exactly (types, defaults, CHECKs, indexes); `server_default` for DB defaults.
4. Hand-write `0001_baseline_spec_schema.py` (not autogenerate) so CHECKs/extensions/indexes are explicit; run autogenerate diff afterwards and require it empty.
5. `db upgrade`: detect non-empty schema, run `pg_dump -Fc` to `BACKUP_DIR/portal-<utc>.dump`, then upgrade.
6. App factory, error envelope, health route; `__main__ serve`.
7. Test harness and Makefile targets (`portal-test` = compose up postgres/minio, export test URL, `pytest tests/portal`).

## Todo
- [ ] extra + packaging  - [ ] config  - [ ] models  - [ ] baseline migration  - [ ] backup-before-upgrade  - [ ] app/health/errors  - [ ] test harness + Make targets

## Success criteria
- `alembic upgrade head` on empty Postgres creates all spec tables + additions; autogenerate diff is empty; `downgrade base` drops cleanly.
- Health test green; validation error returns the envelope.
- `db upgrade` on a DB with data writes a dump file before migrating (test asserts file exists).

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Model/DDL drift | M x H | Empty-autogenerate test in CI |
| Tests silently skipped without Postgres | M x M | Portal tests error (not skip) when the URL is set but unreachable; `make portal-test` always sets it |
| `pg_dump` version mismatch with server | L x M | Compose pins postgres:16; portal image installs postgresql-client-16 (phase 6) |

## Rollback
Additive only: delete `src/vieneu_portal/`, `tests/portal/`, the compose file and the extra. Engine and admin untouched in this phase.

## Security
`DATABASE_URL` and S3 secrets only from env; never logged (settings `__repr__` masks secrets).

## Next
Phases 2, 4, 7 can start.
