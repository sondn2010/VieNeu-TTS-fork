# Phase 15: Acceptance verification and docs

## Context
- Acceptance matrix: `09_qa_acceptance_criteria.md` (TC-01..04, TC-07, TC-09 Studio/library parts, TC-12..14), plan success criteria, user decisions of 2026-11-02 (admin in C1, account-wins ties, `<en>` fallback, fail-closed moderation, stream charge on completion).
- Docs describing the removed admin (re-grep before editing): `docs/web-admin-functions.md`, `docs/web-admin-functions.vi.md`, `docs/user-guide.md`, `docs/user-guide.vi.md`, `README.md` (section "Admin web app", ~line 386), `README.vi.md`. Repo convention: English + Vietnamese pairs.

## Overview
Priority P1. Prove every acceptance item with an automated test reference, rehearse the real-data migration, and replace the admin docs with portal operations, admin and user docs.

## Requirements
Traceability table in the completion report (TC/requirement -> test -> result):
| Item | Automated by |
|---|---|
| TC-01 | `terms-consent-modal.test.tsx`, Playwright step |
| TC-02 | `test_tts_generate_sync_and_async.py` (blocklist reject and provider-down 503; counters unchanged) |
| TC-03 | `insert-text-at-caret.test.ts`, `emotion-tag-buttons.test.tsx`, Playwright step |
| TC-04 | `test_math_chem_normalization_golden.py` (+ by-ear check) |
| TC-07 | `test_recordings_library_api.py`, `library-summary-footer.test.tsx`, Playwright step |
| TC-09 (subset) | quota/profile equality in `test_recordings_library_api.py`, Playwright sidebar check |
| TC-12, TC-13 | `dictionary_matcher_vectors.json` via pytest + vitest |
| TC-14 | `dictionary_import_vectors.json` via pytest + vitest, `test_account_dictionary_api.py` |
| Account rule wins equal-length tie over system rule; fallback `<en>` wrap | precedence vectors (phase 7), `test_rules_for_synthesis_loader.py` |
| Stream charges only on completion | `test_tts_stream_metering.py` |
| Admin role matrix (USER 403 everywhere, ADMIN limited to USER targets) | `test_admin_api_role_matrix.py` |
| Last-superadmin and self-demotion guards (API + CLI) | `test_role_change_guards.py`, `test_admin_api_users.py`, `role-select-with-guards.test.tsx` |
| Admin user lifecycle, token/plan adjust, key revoke, recording delete, sysdict and voice edits | `test_admin_api_*.py`, `e2e/admin-pages.spec.ts` |
| Admin access to another user's recordings audited (`user.recordings_view`) | `test_admin_api_audit_log.py` |
| One audit row per admin mutation, no secrets | `test_admin_api_audit_log.py`, `test_portal_admin_cli.py` |
| Voice sync never overwrites admin edits | `test_voice_catalog_from_engine.py`, `test_admin_api_voices.py` |
| One in-flight synthesis per user; no overspend from parallel streams/jobs | `test_user_synthesis_lease.py`, `test_quota_atomic_charge.py` |
| Worker lease expiry: one charge, no deleted paid audio; abandoned sync rows swept | `test_worker_recording_claiming.py`, `test_tts_generate_sync_and_async.py` |
| Dictionary rule cannot smuggle blocked text; processed-length cap | `test_engine_text_pipeline.py`, `test_account_dictionary_api.py` |
| `B2B`/`F0` keep seed readings | `test_math_chem_normalization_golden.py`, `test_engine_text_pipeline.py` |
| ADMIN cannot create privileged accounts | `test_admin_api_role_matrix.py`, `test_role_change_guards.py` |
| Signup/login throttles shared across processes; signup switch; password change; absolute session expiry | `test_auth_throttle_and_signup_switch.py`, `test_auth_signup_login_logout.py` |
| Migration provenance and conflict abort | `test_sqlite_to_postgres_migration.py` |
| Engine refuses public bind without key; portal image engine-free | `tests/test_openai_speech.py`, Dockerfile.portal build check |
<!-- Updated: Red Team 2026-11-02 - traceability rows for accepted findings -->

- Invariants: counters unchanged on every failure path; `original_text` byte equality; migrator dry-run on a copy of the real `vieneu_data/admin.sqlite3` with `lost_rows: 0` (or fixture if none exists, stated explicitly).
- By-ear verification (user): TC-04 sentence, 5 seed-dictionary terms, 3 English fallback terms (`<en>` wrap) through Studio.
- Docs:
  - Replace `docs/web-admin-functions{,.vi}.md` with `docs/portal-operations{,.vi}.md`: architecture (portal, worker, engine, Postgres, S3), env settings (link to `src/vieneu_portal/config.py`; required `SECRET_KEY`, `FORWARDED_ALLOW_IPS` behind a proxy, `SIGNUP_ENABLED`), compose quick start, first superadmin via CLI, admin area tour (users, quotas, keys, recordings, system dictionaries incl. `ENGLISH_FALLBACK`, voices, audit log), roles and guards (only SUPERADMIN creates privileged accounts), one synthesis at a time per user, dictionary precedence, SQLite migration runbook (keep `SIGNUP_ENABLED=false` -> back up -> `migrate-sqlite --dry-run` -> `--apply` -> verify -> `system-dict seed` only when there was no SQLite -> enable signup; migrated users sign in with `<username>@migrated.invalid`), backup/restore, breaking changes (engine has no `/admin`; engine refuses a public bind without `VIENEU_API_KEY` and compose requires it; DB-issued `vn_...` keys stop working until the C2 developer API; direct engine API users no longer get global dictionaries; Script Lab replaced by `python -m vieneu_portal text preview`, while `vieneu-preprocess` remains a standalone tool with the old matcher).
  - `docs/user-guide{,.vi}.md`: signup, terms, Studio (stream vs generate charging, disabled "coming soon" controls), My Voices, quotas.
  - `README{,.vi}.md`: replace "Admin web app" with a short "User portal" section linking the docs.
- Plan status updated through the plan CLI after verification.

## Related code files
Delete: `docs/web-admin-functions.md`, `docs/web-admin-functions.vi.md`.
Create: `docs/portal-operations.md`, `docs/portal-operations.vi.md`.
Modify: `docs/user-guide.md`, `docs/user-guide.vi.md`, `README.md`, `README.vi.md`.

## Implementation steps
1. Run `uv run pytest`, `make portal-test`, `make portal-test-e2e`; fix regressions in the owning phase's files.
2. Migration rehearsal on a copied DB; keep the JSON report under `plans/reports/`.
3. Write/replace docs; verify commands, env names and routes against source (`git grep`).
4. Completion report: traceability table, remaining open questions, docs impact.

## Todo
- [ ] full test runs  - [ ] migration rehearsal  - [ ] by-ear session request  - [ ] docs EN/VI  - [ ] traceability report

## Success criteria
- Every traceability row green; docs mention `vieneu_admin`/`VIENEU_ADMIN` only in the breaking-change note; `/admin` in docs refers to the portal admin area.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Docs drift from config | M x L | Link to `config.py` and CLI `--help` |
| By-ear rejects readings late | M x M | Readings and fallback lists are data (golden table, system packs editable by admins) |

## Rollback
Docs are text; revert commit.

## Security
Migration report holds counts and usernames only; never commit real DB copies.

## Next
C2 (dictionary UI + live preview, Live/Test keys, MCP).
