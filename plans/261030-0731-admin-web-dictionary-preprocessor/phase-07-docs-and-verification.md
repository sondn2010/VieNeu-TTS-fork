---
phase: 7
title: "Bilingual docs and final verification"
status: pending
priority: P2
effort: "5h"
dependencies: [6]
---

# Phase 7: Bilingual docs and final verification

## Goal

Write the app-functions reference and the user guide in English and Vietnamese, link them from the READMEs, and confirm every plan success criterion against the running app.

## Files to Create / Modify

- Create: `docs/web-admin-functions.md`, `docs/web-admin-functions.vi.md` — reference for maintainers and operators: architecture (one diagram), every page and route with role requirements, environment variables, DB location and backup behavior, API changes (`preprocess`, key auth modes with a prominent "breaking change" note that the API requires a key whenever the admin app is on and how `VIENEU_ADMIN=0` restores the old behavior, `[x.xx]` pause tags with range and clamping), dictionary JSON format with a full example and validation rules, preprocessor stages and rule table pointing to `src/vieneu_preprocess/config/pause_rules.yaml` (link, do not copy numbers), CLI commands (`vieneu-preprocess`, `python -m vieneu_admin ...`), security notes.
- Create: `docs/user-guide.md`, `docs/user-guide.vi.md` — task-oriented guide: first login, change password, create and revoke an API key, call the API with `curl` and the OpenAI SDK (with and without `preprocess`), use Script Lab (paste, read the script, map voices, listen, download), admin tasks (users, dictionaries, import/export, testing a sentence, fixing a seed pronunciation), troubleshooting (401, 429, engine not loaded, Help says docs missing).
- Modify: `README.md`, `README.vi.md` — a short "Admin web app" section linking both docs.

## Tasks & Steps

- [ ] Write from the implemented code, not from the plan; verify every route, env var and default by grepping source.
- [ ] Keep each file under 800 lines; Vietnamese files mirror English structure section by section.
- [ ] Open `/admin/help` in both languages for both docs; check tables, code blocks and links render.
- [ ] Walk the plan success criteria one by one against the running app and the test suite; record results in `plans/reports/verification-<timestamp>-admin-web-dictionary-preprocessor.md`.
- [ ] List seed dictionary files and the spec sample commands in the report so the user can verify pronunciation by ear.

## Verification

- `uv run pytest -q` (full suite green).
- Manual Help page check in EN and VI.
- Every success criterion in `plan.md` ticked with evidence.

## Risk / rollback

Docs only plus a verification report. Rollback: revert the phase commit.
