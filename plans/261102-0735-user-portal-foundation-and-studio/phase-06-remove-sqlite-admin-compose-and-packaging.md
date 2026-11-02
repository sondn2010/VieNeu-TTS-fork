# Phase 06: Remove the SQLite admin, full dev compose, packaging cleanup

## Context
- Package to delete: `src/vieneu_admin/` (28 modules, templates, static; seed already moved in phase 5).
- Remaining references (re-grep before deleting): `pyproject.toml` (`packages.find include` `vieneu_admin*`, package-data `vieneu_admin = [...]`, deps comments for `jinja2`/`markdown-it-py`), `docker/Dockerfile.cpu:18,34`, `docker/Dockerfile.gpu:20,51`, `Makefile:13,123` (engine compose files and `.env.example` admin block are cleaned in phase 4), `tests/test_admin_*.py` (6 files).
- `jinja2` and `markdown-it-py` have no importer outside `vieneu_admin` (grep of `src/` and `apps/`, 2026-11-02).

## Overview
Priority P1. Deletes the replaced admin app and its tests (coverage now lives in `tests/portal/`), adds the full portal dev stack to compose, and builds a torch-free portal image.

## Requirements
- No file imports `vieneu_admin`; `uv run pytest` (engine suite) green.
- Deleted test -> replacement map (no lost behavior coverage):
| Deleted | Replaced by |
|---|---|
| `test_admin_security.py` | `tests/portal/test_security_primitives.py` (phase 2) |
| `test_admin_migrations.py` | `tests/portal/test_schema_baseline.py` (phase 1) |
| `test_admin_cli.py` | `tests/portal/test_portal_admin_cli.py` (phase 5) |
| `test_admin_store.py` | `test_system_dictionary_store.py`, `test_role_change_guards.py`, `test_auth_signup_login_logout.py` |
| `test_admin_routes.py`, `test_admin_routes_content.py` | `tests/portal/test_admin_api_*.py` (phase 13) and admin page tests (phase 14); Script Lab is dropped, `vieneu-preprocess` CLI remains the tool |
- Between this phase and phase 14, web user management is CLI-only (same services the admin API will use).
- `docker/docker-compose.portal.yml` services: `postgres` (16, volume, healthcheck), `minio` + `minio-init` (bucket, private), `engine` (build `Dockerfile.cpu`, profile `cpu`; `engine-gpu` with `Dockerfile.gpu`, profile `gpu`; internal network only; `VIENEU_API_KEY=${VIENEU_ENGINE_SERVICE_KEY}`), `portal` (build `Dockerfile.portal`, runs `db upgrade` then `serve`, port 8100 published).
- `docker/Dockerfile.portal`: python:3.12-slim, `postgresql-client-16` (for `pg_dump`), installs `.[portal]` without torch/onnx; non-root user.

## Related code files
Delete: `src/vieneu_admin/**`, `tests/test_admin_cli.py`, `tests/test_admin_migrations.py`, `tests/test_admin_routes.py`, `tests/test_admin_routes_content.py`, `tests/test_admin_security.py`, `tests/test_admin_store.py`.
Modify: `pyproject.toml` (drop `vieneu_admin*`, its package-data, `jinja2` and `markdown-it-py` explicit deps), `docker/Dockerfile.cpu`, `docker/Dockerfile.gpu` (drop `VIENEU_ADMIN_DB`, Help docs COPY comment), `docker/docker-compose.portal.yml`, `Makefile` (`api` help text, add `portal-up`, `portal-down`, `portal-migrate-sqlite`), `.env.example` (portal section: DB URL, S3, engine URL/service key, quotas).
Create: `docker/Dockerfile.portal`.

## Implementation steps
1. Re-grep `vieneu_admin|VIENEU_ADMIN` across repo (excluding `plans/`, `docs/` handled in phase 15); fix every hit listed above.
2. Delete package and tests; run `uv run pytest` and `make portal-test`.
3. Write `Dockerfile.portal` and extend compose; `make portal-up` brings the stack up; portal health 200; engine reachable from portal container only.
4. `uv lock` after dependency removals; confirm `pip install vieneu` core still installs Gradio fine (jinja2 is a Gradio transitive dep).

## Todo
- [ ] re-grep refs  - [ ] delete package/tests  - [ ] pyproject/Dockerfiles/Makefile/env  - [ ] Dockerfile.portal  - [ ] compose stack  - [ ] full test runs

## Success criteria
- `git grep -n "vieneu_admin\|VIENEU_ADMIN" -- ':!plans' ':!docs'` empty.
- `make portal-up` -> `curl :8100/api/v1/health` 200; `docker compose exec portal python -m vieneu_portal voices sync` inserts 25 voices.
- Both test suites green.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Admins lose Script Lab; web user management gap until phase 14 | M x M | Script Lab dropped by decision (`vieneu-preprocess` CLI covers it); web user management restored in phases 13-14, CLI meanwhile; docs in phase 15 |
| Existing deployments with SQLite data upgrade blindly | M x H | Engine no longer reads SQLite; docs give the order: back up volume -> `migrate-sqlite --dry-run` -> `--apply` |
| Removing jinja2 explicit dep breaks Gradio | L x M | Gradio declares it; verify with fresh venv install |

## Rollback
`git revert` this phase's commit restores the package and tests; data untouched (SQLite file stays in `vieneu_data`).

## Security
Engine port not published in portal compose; MinIO console bound to localhost; secrets only via `.env`.

## Next
Phase 10 builds on the running stack.
