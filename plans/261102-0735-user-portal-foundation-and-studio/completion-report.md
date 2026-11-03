# Completion report — User portal C0+C1

Plan: `plan.md` (this directory). All 15 phases are Done. This report covers
phase 15's own acceptance pass: traceability, the migration rehearsal, docs,
and what is explicitly still open.

## Traceability

Every row in the plan's own acceptance table (copied from `phase-15-...md`),
with the result column filled in from this session's test runs: Python
`pytest tests/portal -m "not engine"` → 308 passed, 5 skipped, 1 deselected;
`pytest tests/ --ignore=tests/portal` → 365 passed, 4 skipped; TypeScript
`npx vitest run` (portal-web) → 115 passed. All three suites are green as of
this report; `git status`/`git log` are authoritative for what each file now
contains.

| Item | Automated by | Result |
|---|---|---|
| TC-01 | `terms-consent-modal.test.tsx` | PASS (component). Playwright step written (`admin-pages.spec.ts`'s login helper exercises the modal path indirectly; no dedicated `studio-and-library.spec.ts` run — see Not verified). |
| TC-02 | `test_tts_generate_sync_and_async.py` | PASS |
| TC-03 | `insert-text-at-caret.test.ts`, `emotion-tag-buttons.test.tsx` | PASS |
| TC-04 | `test_math_chem_normalization_golden.py` | PASS (automated). By-ear check: **open**, see below. |
| TC-07 | `test_recordings_library_api.py`, `library-summary-footer.test.tsx` | PASS |
| TC-09 (subset) | `test_recordings_library_api.py` (quota/profile equality) | PASS |
| TC-12, TC-13 | `dictionary_matcher_vectors.json` via pytest + vitest | PASS (`text-contract-vectors.test.ts` and the Python mirror) |
| TC-14 | `dictionary_import_vectors.json` via pytest + vitest, `test_account_dictionary_api.py` | PASS |
| Account rule wins equal-length tie; `<en>` fallback | phase 7 precedence vectors, `test_rules_for_synthesis_loader.py` | PASS |
| Stream charges only on completion | `test_tts_stream_metering.py` | PASS |
| Admin role matrix | `test_admin_api_role_matrix.py` | PASS — enumerates all 28 `/api/v1/admin` routes against the matrix and calls every one unauthenticated/USER/ADMIN |
| Last-superadmin and self-demotion guards | `test_role_change_guards.py`, `test_admin_api_users.py`, `role-select-with-guards.test.tsx` | PASS |
| Admin user lifecycle, token/plan, key revoke, recording delete, sysdict/voice edits | `test_admin_api_*.py` | PASS. `e2e/admin-pages.spec.ts` written, not run — see Not verified. |
| Admin access to another user's recordings audited | `test_admin_api_audit_log.py` | PASS |
| One audit row per mutation, no secrets | `test_admin_api_audit_log.py`, `test_portal_admin_cli.py` | PASS |
| Voice sync never overwrites admin edits | `test_voice_catalog_from_engine.py`, `test_admin_api_voices.py` | PASS |
| One in-flight synthesis per user | `test_user_synthesis_lease.py`, `test_quota_atomic_charge.py` | PASS |
| Worker lease expiry, abandoned sync rows swept | `test_worker_recording_claiming.py`, `test_tts_generate_sync_and_async.py` | PASS |
| Dictionary rule cannot smuggle blocked text; processed-length cap | `test_engine_text_pipeline.py`, `test_account_dictionary_api.py` | PASS |
| `B2B`/`F0` keep seed readings | `test_math_chem_normalization_golden.py`, `test_engine_text_pipeline.py` | PASS |
| ADMIN cannot create privileged accounts | `test_admin_api_role_matrix.py`, `test_role_change_guards.py` | PASS |
| Signup/login throttles, signup switch, password change, absolute session expiry | `test_auth_throttle_and_signup_switch.py`, `test_auth_signup_login_logout.py` | PASS |
| Migration provenance and conflict abort | `test_sqlite_to_postgres_migration.py` | PASS (automated). Real-CLI rehearsal also run this session — see below. |
| Engine refuses public bind without key; portal image engine-free | `tests/test_openai_speech.py` | PASS (`test_public_bind_without_key_refuses_to_start`, `test_public_bind_with_key_is_allowed`, both rewritten in phase 6). Dockerfile build-time check not run — see Not verified. |

## Migration rehearsal

Run for real this session (not merely unit-tested): `python -m
vieneu_portal migrate-sqlite` against the fixture built by
`tests/fixtures/legacy_admin_sqlite_builder.py` (2 users incl. one disabled,
2 API keys incl. one revoked, 1 dictionary pack with 4 edge-case rules —
a case-sensitive duplicate, an `en`-mode entry with a replacement, a
unicode `en`-mode entry with none). No real `vieneu_data/admin.sqlite3`
exists in this repository or environment, so the fixture stood in, exactly
as the phase's own instructions allow when stated explicitly.

- `--dry-run`: `lost_rows: 0`, `conflicts: []`, counts matched the fixture
  exactly. Report: `plans/reports/261103-migration-rehearsal-dry-run.json`.
- `--apply` against a disposable Postgres database, then verified with
  direct SQL: `role` mapped `admin→SUPERADMIN`/`user→USER`, `is_active`
  preserved, emails synthesized as `<username>@migrated.invalid`,
  `legacy_source_id` set, and the two `en`-mode entries split correctly
  into `REPLACE` (had a replacement) vs `ENGLISH_FALLBACK` (none) by
  `rule_kind` — the exact distinction the mode-mapping logic exists to get
  right.

## Docs

- Deleted `docs/web-admin-functions.md` / `.vi.md` (described a package that
  no longer exists).
- Created `docs/portal-operations.md` / `.vi.md`: architecture, environment
  settings (linking to `config.py` rather than duplicating it), compose
  quick start, first superadmin via CLI, the admin area tour, roles/guards,
  one-synthesis-per-user, dictionary precedence, the SQLite migration
  runbook (§8, pointing at the rehearsal report above), backup/restore, and
  the breaking-changes list.
- Rewrote `docs/user-guide.md` / `.vi.md` for the actual portal: signup, the
  terms modal, Studio (stream vs generate, disabled "coming soon"
  controls), My Voices, quotas, troubleshooting.
- `README.md` / `README.vi.md`: replaced "Admin web app" with "User portal",
  linking the two docs above.
- `git grep -n "vieneu_admin|VIENEU_ADMIN|web-admin-functions|VIENEU_COOKIE_SECURE|VIENEU_DOCS_DIR" -- ':!plans' ':!.claude'`
  now returns exactly two lines, both inside the README breaking-change
  notes — matching this phase's own success criterion verbatim.

## Not verified here (sandbox limitations, consistent with every earlier phase this session)

- **By-ear verification (TC-04 sentence, 5 seed-dictionary terms, 3 English
  fallback terms through Studio).** This genuinely requires a human to
  listen to rendered audio; it is explicitly a user action in the plan, not
  something this session could perform. **Open — needs you.**
- `make portal-test-e2e`'s Playwright suites (`studio-and-library.spec.ts`,
  `admin-pages.spec.ts`): written and lint/type-checked, but need the full
  `docker compose up` stack plus a real CPU engine — no Docker daemon in
  this sandbox.
- `docker/Dockerfile.portal`'s own build (torch/onnx/gradio-free check) and
  `docker compose -f docker/docker-compose.yml config` failing without
  `VIENEU_API_KEY`: same reason, no Docker daemon here.
- `uv lock` after phase 6's dependency removal (`jinja2`, `markdown-it-py`):
  `uv` itself is not installed in this sandbox. The lockfile still lists
  both as direct dependencies until this is run somewhere with `uv`
  available — flagged explicitly in phase 6's plan.md note too.

## Remaining open questions

None beyond the by-ear check and the Docker/`uv` items above — every other
acceptance item in the plan's own matrix has an automated test that ran
green this session.
