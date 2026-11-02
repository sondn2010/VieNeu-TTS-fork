---
name: project-plan-location-and-portal-rewrite
description: VieNeu-TTS-fork keeps plans in ./plans (not docs/plans) and is mid-rewrite from SQLite admin to a Postgres user portal in cycles C0-C5
metadata:
  type: project
---

Plans for this repo live in `plans/<yymmdd-hhmm>-<slug>/` with reports in `plans/reports/`, even though the user's global CLAUDE.md says `docs/plans/`. The orchestrator passes the plan dir explicitly.

The user approved (2026-11-02) replacing the SQLite admin (`src/vieneu_admin`) with a Postgres FastAPI portal (`src/vieneu_portal`) + Next.js SPA, delivered in cycles C0..C5. Decision source: `plans/reports/brainstorm-261102-0735-user-portal-postgres-rewrite.md`. C0+C1 plan: `plans/261102-0735-user-portal-foundation-and-studio/`.

**Why:** user chose the rewrite against the assistant's advice; decisions must not be silently reversed.
**How to apply:** for C2+ planning, read the brainstorm report and the C0+C1 plan first; set `blockedBy` on the previous cycle's plan.
