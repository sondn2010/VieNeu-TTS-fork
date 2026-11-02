---
title: "User portal C0+C1: Postgres foundation, Studio, library and admin"
description: "Replace the SQLite admin with a Postgres FastAPI /api/v1 portal plus a Next.js SPA: signup, terms gate, moderation, math/chem normalization, per-account dictionary, metered generate/stream, recordings, My Voices, and a role-guarded admin area with audit log."
status: pending
priority: P1
effort: 104h
branch: main-bkt
tags: [feature, backend, frontend, database, auth, migration, api, admin]
blockedBy: [261030-0731-admin-web-dictionary-preprocessor]
blocks: []
created: 2026-11-02
---

# User portal C0 (Foundation) + C1 (Studio, recordings, library, admin)

Source of truth: [brainstorm report](../reports/brainstorm-261102-0735-user-portal-postgres-rewrite.md) plus the user's answers of 2026-11-02 (admin in C1, account rules win dictionary ties, quota defaults, fail-closed moderation, `<en>` fallback). Specs: `docs/vieneu_tts_docs_specs/docs/specs/` (master, 01, 02, 04, 07, 08, 09). Specs define no admin screens; phases 13-14 design them.

## Architecture

```text
Browser (Next.js static export, same origin) --cookie+CSRF--> portal: FastAPI /api/v1 (+ /api/v1/admin, role-guarded)
portal --SQLAlchemy 2--> Postgres (Alembic)        portal --boto3--> S3 (MinIO dev, any S3 prod, 15-min signed URLs)
portal --httpx + service key--> engine: apps/openai_speech.py (/v1/audio/speech stream, /internal/v1/render)
worker (python -m vieneu_portal worker) --> same DB/S3/engine; async generate jobs (SKIP LOCKED)
Text path: original_text -> moderation -> math/chem normalize -> [account + system rules + English fallback, one pass] -> engine
```

## Phases

| # | Phase | Depends on | Group | Effort | Status |
|---|---|---|---|---|---|
| 1 | [Portal skeleton and Postgres schema](./phase-01-portal-skeleton-and-postgres-schema.md) | none | A | 8h | Pending |
| 2 | [Auth: signup, sessions, roles, profile](./phase-02-auth-signup-sessions-and-profile.md) | 1 | B | 6h | Pending |
| 3 | [Storage interface and voice catalog](./phase-03-storage-interface-and-voice-catalog.md) | 2 | C | 4h | Pending |
| 4 | [Engine service trim](./phase-04-engine-service-trim.md) | none | B | 5h | Pending |
| 5 | [SQLite migrator and admin CLI](./phase-05-sqlite-migrator-and-admin-cli.md) | 3, 4, 7 | D | 7h | Pending |
| 6 | [Remove SQLite admin, compose, packaging](./phase-06-remove-sqlite-admin-compose-and-packaging.md) | 4, 5 | E | 5h | Pending |
| 7 | [Shared text contracts (Py + TS + vectors)](./phase-07-shared-text-contracts-python-and-typescript.md) | 1 | B | 7h | Pending |
| 8 | [Moderation and normalization pipeline](./phase-08-moderation-and-math-chem-normalization-pipeline.md) | 7 | C | 8h | Pending |
| 9 | [Account dictionary API](./phase-09-account-dictionary-api.md) | 3, 7 | D | 4h | Pending |
| 10 | [TTS generate/stream, metering, recordings, library](./phase-10-tts-generate-stream-metering-recordings-library.md) | 4, 6, 9 | F | 10h | Pending |
| 11 | [Next.js shell, auth pages, Terms modal](./phase-11-nextjs-shell-auth-pages-and-terms-modal.md) | 2, 7 | C | 8h | Pending |
| 12 | [Studio and My Voices pages](./phase-12-studio-and-my-voices-pages.md) | 10, 11 | G | 8h | Pending |
| 13 | [Admin API and audit log](./phase-13-admin-api-and-audit-log.md) | 5, 10 | G | 10h | Pending |
| 14 | [Admin web pages](./phase-14-admin-web-pages.md) | 11, 13 | H | 10h | Pending |
| 15 | [Acceptance verification and docs](./phase-15-acceptance-verification-and-docs.md) | 12, 14 | I | 4h | Pending |

Same-group phases run in parallel only with disjoint files (each phase lists what it owns). `config.py` is written once in phase 1. Shared files, edited only in dependency order: `app.py` (2, 3, 9, 10, 13), `__main__.py` (5, 10), `Makefile` (1, 6, 7, 10, 11, 12), `pyproject.toml` (1, 5, 6), `docker/Dockerfile.portal` (6, 12), `docker/docker-compose.portal.yml` (1, 6, 10). Phases 12 and 14 share no files: admin pages, admin i18n catalogs (stubbed in 11) and `e2e/admin-pages.spec.ts` belong to 14.

## Cross-cutting decisions

- Schema = spec 08 DDL plus documented additions (auth/sessions, roles `USER/ADMIN/SUPERADMIN`, system dictionary layer with `rule_kind`, jobs, object keys, daily-reset date, `admin_audit_log`).
- Characters = code points of NFC original text, identical in Python and TS; tokens = `ceil(chars * rate_milli / 1000)`. Defaults (env-configurable): 150 000 tokens, 50 000 chars/day, 1 token/char, 14-day trial.
- Charge after success via conditional `UPDATE` in the transaction that records success. Moderation reject, moderation outage (503, fail-closed), engine/storage failure and lost races charge nothing. Stream charges only on completion. Admin token adjustments are the only other counter writer, always audited.
- Dictionary: longest match first over the combined set; equal-length ties: account rule > system replace rule > English fallback, then list order. Protected spans (`[...]`, `<en>...</en>`, `<|...|>`) never rewritten.
- `<en>` interpretation: an English term that matches any dictionary rule uses that rule's replacement; otherwise known English terms (fallback list) are wrapped in `<en>...</en>` for the engine's English handling; unknown words are left to the engine.
- Admin parity: web user management restored (phases 13-14) with last-active-superadmin and self-demotion guards. Script Lab stays dropped; `vieneu-preprocess` CLI covers it.
- Deferred UI shown as disabled "coming soon": background music, onboarding checklist expansion (progress from existing onboarding fields), support chat. No email verification or reset-by-email.

## Success criteria

- [ ] TC-01, 02, 03, 04, 07, 09 (Studio/library numbers), 12, 13, 14 automated and green, plus the account-beats-system tie vector and admin acceptance tests (phase 15 list).
- [ ] Failure-injection tests: moderation reject/outage, engine 5xx, storage error, concurrent overspend never change `token_balance` or `daily_char_remaining`.
- [ ] `original_text` stored byte-identical; migrator dry-run on a copy of `vieneu_data/admin.sqlite3` reports 0 lost rows; re-apply is a no-op.
- [ ] Every admin mutation writes one audit row; guards block removing the last active superadmin and self-demotion.
- [ ] `uv run pytest` and `make portal-test` pass; no import of `vieneu_admin` remains.

## Unresolved questions

1. Confirm the `<en>` interpretation above (dictionary value wins, else `<en>` wrap for known English terms, else engine default).
2. Audit log retention (default: keep forever, no purge job) and whether admin viewing/playing user recordings must be audited (default: only mutations audited).
