---
title: "Plan: admin web app, dictionaries and story preprocessor"
date: 2026-10-30
summary: "Planned a 7-phase delivery of a user/API-key admin app, JSON dictionaries with seeds, the tts-specs-v1 preprocessor and bilingual docs"
---

# Plan: admin web app, dictionaries and story preprocessor

## What happened
Brainstormed and planned the admin web app, global pronunciation dictionaries and the story preprocessor from docs/tts-specs/tts-specs-v1.md. Plan: plans/261030-0731-admin-web-dictionary-preprocessor/ (7 phases; phases 2-5 parallel with disjoint file ownership).

## Findings that shaped the plan
- The v3 Turbo engine has no numeric pause-tag support. Only [cười], [thở dài] and [hắng giọng] are recognized, so `[0.35]` would be spoken as text. Phase 2 adds tags as explicit gaps in normalize_to_chunks_v3_with_gaps and strips them on the other chunker entry points (Gradio uses normalize_to_chunks_v3).
- itsdangerous is not installed, so sessions are server-side SQLite rows rather than Starlette SessionMiddleware. Jinja2 and markdown-it-py already arrive via Gradio.
- The Docker images do not copy docs/, so the Help page needs `COPY docs/` (phase 6).
- The API ignores `speed`. The runner applies it with librosa time-stretch, in Script Lab and the CLI only.

## Decisions (user)
- Admin plus self-service users. Global, toggleable dictionaries edited by admins only. FastAPI + Jinja2/HTMX + SQLite.
- The API always requires a key when the admin app is on, even with zero keys. This breaks keyless setups; VIENEU_ADMIN=0 restores the old behavior.
- Dictionaries apply only with preprocess=true. DB at ./vieneu_data/admin.sqlite3. Script Lab is capped at 50k chars.
- Docs are written in English and Vietnamese. The seed dictionaries are written in full and the user verifies them by ear.

## Next steps
/ak-cook plans/261030-0731-admin-web-dictionary-preprocessor/plan.md

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
