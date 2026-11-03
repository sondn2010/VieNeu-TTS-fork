# Phase 06: Remove the SQLite admin and the engine's admin wiring

<!-- Updated: Red Team 2026-11-02 - runs at the end (after phases 12 and 14) instead of before the portal works; absorbs the engine admin stripping formerly in phase 4; compose stack and portal image moved to phase 10; consumer list completed -->

## Context
- Runs only after the portal user pages (phase 12) and admin pages (phase 14) exist, so the old admin is never removed before its replacement works.
- Package to delete: `src/vieneu_admin/` (27 `.py` modules plus `seed/`, `static/`, `templates/`; the seed packs were copied to the portal in phase 5).
- Engine admin coupling to remove (line refs as of 2026-11-02; re-grep, phase 4 added lines): imports `apps/openai_speech.py:102-104`; Script Lab provider `:265-289`; admin setup/bootstrap/close `:293-372`; DB-key branch in `_auth` `:374-389`; `_is_admin_path` + its use in handlers `:400-422`; startup/shutdown admin calls `:425-438`; `/` redirect to `/admin/` `:441-445`; `STORE.enabled_lexicon()` in `_preprocess_input` `:518`; admin hints in `main()` `:703-723`; module docstring `:42-70`.
- Remaining references (re-grep before deleting): `pyproject.toml` (`packages.find include` `vieneu_admin*` `:174`, package-data `vieneu_admin = [...]` `:179`, explicit `jinja2`/`markdown-it-py` deps), `docker/Dockerfile.cpu:17-18,34-35`, `docker/Dockerfile.gpu:19-20,51` (`VIENEU_ADMIN_DB`, `VIENEU_DOCS_DIR`, help-only `COPY docs/`), `Makefile:13,123`, `docker/docker-compose.yml:83-88,131-136` and `docker/docker-compose.prod.yml:43-48` (`VIENEU_ADMIN*`, `VIENEU_COOKIE_SECURE`), `.env.example:36-50` (admin block, `VIENEU_COOKIE_SECURE`, `VIENEU_DOCS_DIR`), `tests/test_openai_speech.py` (admin fixtures `:17-19`, `:53-55`, DB-key cases `:166-260`, `from test_admin_routes import login, post` `:17`), `tests/test_admin_*.py` (6 files). Admin-only env consumers: `VIENEU_COOKIE_SECURE` (`src/vieneu_admin/auth.py:29`), `VIENEU_DOCS_DIR` (`src/vieneu_admin/web_paths.py:16`).
- README admin lines (`README.md:386-393`, `README.vi.md:393-396`) belong to phase 15; `.claude/agent-memory/**` is tooling state, not product code.
- `jinja2` and `markdown-it-py` have no importer outside `vieneu_admin` (grep of `src/` and `apps/`, 2026-11-02); Gradio declares jinja2 (`uv.lock:949-965`).

## Overview
Priority P1. The engine becomes an internal service with one service key and no DB or admin; the replaced admin app, its tests and its config are deleted. Behavior coverage already lives in `tests/portal/`.

## Requirements
- Engine: remove every `vieneu_admin` import, the `VIENEU_ADMIN*` handling, Script Lab provider, `/admin` mount and DB-key branch. `_auth` = constant-time compare against `VIENEU_API_KEY`. Startup guard tightened: non-loopback bind without `VIENEU_API_KEY` exits non-zero. `/` returns 404 JSON. `_preprocess_input` calls `vieneu_preprocess.preprocess_safely(raw, ())` (prosody + pause tags only; global dictionaries now apply only through the portal).
- Engine compose files (`docker-compose.yml`, `docker-compose.prod.yml`): drop `VIENEU_ADMIN*` and `VIENEU_COOKIE_SECURE`; `VIENEU_API_KEY=${VIENEU_API_KEY:?set VIENEU_API_KEY}` wherever `HOST=0.0.0.0`.
- No file imports `vieneu_admin`; `uv run pytest` (engine suite) green.
- Deleted test -> replacement map (no lost behavior coverage):
| Deleted | Replaced by |
|---|---|
| `test_admin_security.py` | `tests/portal/test_security_primitives.py`, `test_auth_throttle_and_signup_switch.py` (phase 2) |
| `test_admin_migrations.py` | `tests/portal/test_schema_baseline.py` (phase 1) |
| `test_admin_cli.py` | `tests/portal/test_portal_admin_cli.py` (phase 5) |
| `test_admin_store.py` | `test_system_dictionary_store.py`, `test_role_change_guards.py`, `test_auth_signup_login_logout.py` |
| `test_admin_routes.py`, `test_admin_routes_content.py` | `tests/portal/test_admin_api_*.py` (phase 13) and admin page tests (phase 14); Script Lab replaced by `python -m vieneu_portal text preview` (phase 5) |
| DB-key cases in `tests/test_openai_speech.py` | env-key auth tests kept; refuse-to-start test (phase 4) tightened to key-required |

## Related code files
Delete: `src/vieneu_admin/**`, `tests/test_admin_cli.py`, `tests/test_admin_migrations.py`, `tests/test_admin_routes.py`, `tests/test_admin_routes_content.py`, `tests/test_admin_security.py`, `tests/test_admin_store.py`.
Modify: `apps/openai_speech.py`, `tests/test_openai_speech.py`, `pyproject.toml` (drop `vieneu_admin*`, its package-data, `jinja2` and `markdown-it-py` explicit deps), `docker/Dockerfile.cpu`, `docker/Dockerfile.gpu` (drop `VIENEU_ADMIN_DB`, `VIENEU_DOCS_DIR`, help-only `COPY docs/`), `docker/docker-compose.yml`, `docker/docker-compose.prod.yml`, `Makefile` (`api` help text), `.env.example` (drop admin block, `VIENEU_COOKIE_SECURE`, `VIENEU_DOCS_DIR`).

## Implementation steps
1. Re-grep `vieneu_admin|VIENEU_ADMIN|VIENEU_COOKIE_SECURE|VIENEU_DOCS_DIR|test_admin_routes` across the repo (excluding `plans/`, `docs/`, `README*.md`, `.claude/`); fix every hit listed above.
2. Strip the engine admin wiring; simplify `_auth` and error handlers (no admin path exception); tighten the startup guard; update engine tests.
3. Delete package and tests; `uv lock` after dependency removals; confirm a fresh `pip install vieneu` still installs Gradio fine.
4. Run `uv run pytest`, `make portal-test`, `make portal-test-e2e`.

## Todo
- [ ] re-grep refs  - [ ] strip engine admin  - [ ] delete package/tests  - [ ] pyproject/Dockerfiles/compose/Makefile/env  - [ ] full test runs

## Success criteria
- `git grep -n "vieneu_admin\|VIENEU_ADMIN\|VIENEU_COOKIE_SECURE\|VIENEU_DOCS_DIR" -- ':!plans' ':!docs' ':!README*.md' ':!.claude'` empty (phase 15 cleans docs and READMEs).
- Engine on `HOST=0.0.0.0` without `VIENEU_API_KEY` refuses to start; `docker compose -f docker/docker-compose.yml config` fails without the key.
- All test suites green.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Admins lose Script Lab | L x M | `text preview` CLI gives the exact portal output; docs in phase 15 |
| Existing deployments with SQLite data upgrade blindly | M x H | Engine no longer reads SQLite; docs give the order: back up volume -> `migrate-sqlite --dry-run` -> `--apply` -> `system-dict seed` only if no SQLite existed |
| DB-issued `vn_...` keys stop working at the engine | M x M | Accepted breaking change (keys move to the C2 developer API); `VIENEU_API_KEY` remains; documented in phase 15 |
| Removing jinja2 explicit dep breaks Gradio | L x M | Gradio declares it; verify with fresh venv install |

## Rollback
`git revert` this phase's commit restores the package, engine wiring and tests; data untouched (SQLite file stays in `vieneu_data`).

## Security
Engine port not published in the portal compose; the engine cannot start publicly without a key; secrets only via `.env`.

## Next
Phase 15 acceptance and docs.
