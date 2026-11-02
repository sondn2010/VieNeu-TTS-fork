# Brainstorm: VieNeu user portal per `docs/vieneu_tts_docs_specs/docs/specs`

Date: 2026-11-02 | Branch: main-bkt | Status: design approved by user

## Problem
Specs describe a full end-user TTS SaaS (11 modules: terms/moderation, Studio, Podcast, Story, My Voices, Leaderboard, Dashboard, Billing, Developer/MCP, per-account Pronunciation Dictionary). `src/` today is operator-oriented: FastAPI + Jinja2/HTMX + SQLite admin (`vieneu_admin`: users/role, keys, global dictionaries, Script Lab), `vieneu_preprocess` (story preprocessor, lexicon), `vieneu` engine, OpenAI-compat `/v1/audio/speech` in `apps/openai_speech.py`.

## Gap summary
- Per-account dictionary: current is global, kinds english/term/name, modes phonetic/en, JSON import. Spec: per-user, `whole_word`/`case_sensitive`/`enabled`, 2000 cap, `.txt/.csv` import (`=`, `→`, tab, `,`, `#` comments).
- Missing entirely: tokens/quota/plans/vouchers, terms gate, moderation, recordings, library, leaderboard, dashboard, podcast/story persistence, Live/Test keys, MCP.
- Spec inconsistencies (master spec vs 08): `/user/profile` vs `/user/me`; `/tts/stream` vs `/tts/preview-stream`; `/ai-generate-script` vs `/ai-script`; `vouchers/validate` vs `apply`; segment status `MODIFIED_NEEDS_REGEN`/`STALE`/`MODIFIED`; `source_module` values.
- "V4" model is proprietary, not in repo; repo ships v3 Turbo.

## User decisions (do not reverse silently)
- Scope: full portal, delivered in cycles.
- Backend rewrite on Postgres per spec DDL (assistant advised against; user chose it).
- Replace existing SQLite admin entirely.
- Frontend: Next.js/React SPA on JSON `/api/v1`.
- Accounts: self-signup; storage: S3-compatible from day one.
- Assumptions: v3 Turbo stands in for V4, tokens = chars-based configurable rate; master-spec endpoint names win; moderation = pluggable provider, stubbed off; billing checkout out of scope (plans/quota/voucher logic in).
- First slice: Studio + recordings + library.
- Seed dictionaries: operator-managed system layer applied before account rules.

## Decomposition
| Cycle | Scope |
|---|---|
| C0 Foundation | Postgres (SQLAlchemy 2 + Alembic), `src/vieneu_portal/` FastAPI `/api/v1`, self-signup auth, S3 storage interface (MinIO dev), voices catalog from `voices_v3_turbo.json`, SQLite→Postgres migrator, minimal operator CLI |
| C1 Studio/recordings/library | Terms gate, moderation interface + 422 contract, normalize math/chem → system+account dictionary → engine, atomic token/quota metering, `tts/generate` + `tts/stream`, recordings, library list/search/filter/delete + totals, Next.js shell, Terms modal, Studio, My Voices |
| C2 | Dictionary UI + live preview, Live/Test keys, MCP |
| C3 | Dashboard, Leaderboard |
| C4 | Podcast + Story (async jobs, ffmpeg export) |
| C5 | Billing logic (checkout stubbed) |

## Architecture calls
1. Portal (stateless, multi-worker) and GPU engine are separate processes; portal calls trimmed `apps/openai_speech.py` internally with a service key.
2. Metering: shared `estimate_tokens(chars)` for client counter and server; charge via conditional `UPDATE ... WHERE balance >= n AND daily_remaining >= c`; moderation reject/failure charges nothing.
3. One single-pass longest-match dictionary algorithm in Python and TypeScript, validated by shared JSON vectors (TC-12/13/14). System layer runs before account rules, single pass over combined ordered rules.
4. Math/chem normalization rule-based (deterministic, testable); TC-04 is acceptance bar.
5. Generate sync up to char cap, async job polling above it; reused by C4.
6. `vieneu_preprocess` stays as library/CLI (dialogue parsing, pause tags).

## Risks
- Replacing admin drops working tested code (Script Lab, operator user mgmt, ~10 admin test files); C0 has no user-visible feature.
- S3 day-one adds MinIO to dev/compose.
- Voice metadata (gender, region, tags, leaderboard names) not in repo; needs curation vs 25 v3 Turbo presets.
- Existing lexicon features (`<en>` mode, ALL-CAPS title-casing) vs spec's plain replacement: define interaction in single pass.
- Multi-month total scope.

## Success criteria (C0+C1)
- TC-01..04, TC-07, TC-09 (Studio/library parts), TC-12..14 automated and passing.
- Failed/rejected generation never changes `token_balance` or `daily_char_remaining`.
- `original_text` preserved untouched.
- SQLite→Postgres migration dry-run on a copy of admin DB is lossless.

## Unresolved questions
- Token rate (per char vs per second) and trial/plan quota values.
- Which S3 provider in prod; signed-URL TTL.
- Who curates voice metadata for the 25 presets.
- Moderation provider choice and fallback when provider is down (fail-open vs fail-closed).
- Interaction of existing `<en>` lexicon mode with spec rules.
