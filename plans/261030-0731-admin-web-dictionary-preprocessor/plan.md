---
title: "Admin web app, pronunciation dictionaries and spec-based story preprocessor"
description: "Add a user and API-key admin web app, global JSON-portable dictionaries with a ready seed set, the tts-specs-v1 story preprocessor with engine pause tags, and bilingual docs served in-app."
status: pending
priority: P1
effort: 48h
branch: main-bkt
tags: [feature, backend, frontend, api, auth, database, docs]
blockedBy: []
blocks: []
created: 2026-10-30
---

# Admin web app, dictionaries and story preprocessor

## Overview

One FastAPI process (`apps/openai_speech.py`) keeps serving the OpenAI-compatible speech API and also mounts an admin web app at `/admin`. Users log in to manage their own API keys. Admins manage users and global pronunciation dictionaries, and everyone can try the new spec-based story preprocessor in a Script Lab page. The engine learns numeric pause tags such as `[0.35]` so preprocessed scripts are playable anywhere. Two docs (app functions, user guide) ship in English and Vietnamese and are rendered by the in-app Help page.

Source contract: [brainstorm report](../reports/brainstorm-261030-1409-admin-web-dictionary-preprocessor.md). Spec: [tts-specs-v1](../../docs/tts-specs/tts-specs-v1.md).

## Locked decisions

- Access: admin + self-service users. Only admins edit users and dictionaries.
- Preprocessor: opt-in `preprocess` field on `/v1/audio/speech`, Script Lab page, and a `vieneu-preprocess` CLI.
- Dictionaries: global, named, toggleable. Every enabled one applies to every preprocessed request.
- Stack: FastAPI + Jinja2 + HTMX (vendored), SQLite, server-side sessions. No Node, no new third-party runtime dependency (Jinja2 and markdown-it-py already ship with Gradio and get declared explicitly).
- Docs: English + Vietnamese pairs. Help page has an EN/VI switch.
- Seed dictionaries: written in full by the implementer, verified by ear by the user after delivery.

## Architecture

```mermaid
flowchart LR
    C[API client] -->|Bearer key| S["/v1/audio/speech"]
    B[Browser] -->|session cookie| A["/admin (Jinja2 + HTMX)"]
    S --> K{key check}
    K --> DB[(SQLite: users, keys, sessions, dictionaries)]
    A --> DB
    S -->|preprocess=true| P[vieneu_preprocess.preprocess]
    A -->|Script Lab| P
    P --> L[enabled dictionaries -> lexicon]
    L --> DB
    P -->|tagged text with [x.xx]| E[VieNeuV3Turbo.infer_stream]
    A -->|render JSON chunks| R[runner: per-chunk voice, speed, exact pauses]
    R --> E
    H["/admin/help"] --> D[docs/*.md, *.vi.md]
```

## Phases

| # | Phase | Depends on | Parallel group | Effort | Status |
|---|-------|-----------|----------------|--------|--------|
| 1 | [Foundation: packaging and shared contracts](./phase-01-foundation-contracts.md) | none | A (alone) | 3h | Complete |
| 2 | [Engine numeric pause tags](./phase-02-engine-pause-tags.md) | 1 | B | 5h | Complete |
| 3 | [Story preprocessor, runner and CLI](./phase-03-story-preprocessor.md) | 1 | B | 13h | Complete |
| 4 | [Seed dictionaries](./phase-04-seed-dictionaries.md) | 1 | B | 4h | Complete |
| 5 | [Admin web app](./phase-05-admin-web-app.md) | 1 | B | 12h | Complete |
| 6 | [Speech API integration and deploy](./phase-06-api-integration.md) | 2, 3, 4, 5 | C | 6h | Complete |
| 7 | [Bilingual docs and final verification](./phase-07-docs-and-verification.md) | 6 | D | 5h | Complete |

Phases 2–5 run in parallel with disjoint file ownership. Each phase file lists the files it owns; no other phase edits them.

## File ownership map

| Phase | Owns |
|---|---|
| 1 | `pyproject.toml`, `.gitignore`, `src/vieneu_preprocess/__init__.py`, `src/vieneu_preprocess/types.py`, `src/vieneu_preprocess/dictionary_schema.py`, `tests/test_dictionary_schema.py` |
| 2 | `src/vieneu_utils/phonemize_text.py`, `src/vieneu_utils/core_utils.py`, `src/vieneu/v3turbo.py`, `tests/test_pause_tags.py` |
| 3 | every other file under `src/vieneu_preprocess/`, `tests/test_preprocess_*.py`, `tests/fixtures/preprocess/` |
| 4 | `src/vieneu_admin/seed/*.json`, `tests/test_seed_dictionaries.py` |
| 5 | everything else under `src/vieneu_admin/`, `tests/test_admin_*.py` |
| 6 | `apps/openai_speech.py`, `tests/test_openai_speech.py`, `docker/*`, `.env.example`, `Makefile` |
| 7 | `docs/web-admin-functions.md`, `docs/web-admin-functions.vi.md`, `docs/user-guide.md`, `docs/user-guide.vi.md`, `README.md`, `README.vi.md` |

## Success criteria

- [x] Fresh DB + `VIENEU_ADMIN_USER`/`VIENEU_ADMIN_PASSWORD`: the admin logs in, creates a user; that user logs in, creates a key; `curl` with the key gets audio; after revoking, the same call gets 401. `VIENEU_API_KEY` still works. With the admin app on and no keys, API calls get 401; with `VIENEU_ADMIN=0`, behavior matches today.
- [x] The DB holds only hashes of passwords, keys and session tokens. A non-admin gets 403 on `/admin/users*` and dictionary write routes. A POST without a valid CSRF token gets 403.
- [x] Dictionary JSON export, then import into an empty DB, round-trips entries exactly. Malformed JSON shows the line and column of the error.
- [x] Seed dictionaries exist after first start; preprocessing the spec §5.1 input yields `Hốc-goát`, `Sờ-li-thơ-rin`, `Đờ-ra-xê-na`.
- [x] Unit tests prove the spec §5.2/§5.3 structure: speaker turns, inner-voice split, countdown pauses `0.6 → 0.85 → 1.1 → 1.4`, shout normalization, drop-cap recovery, embedded-quote guard.
- [ ] `[0.5]` in API input yields about 0.5 s of silence and is never spoken; input without tags produces the same chunks and gaps as before.
- [x] `/admin/help` renders all four docs with an EN/VI switch; `docs/` is the only copy.
- [x] `uv run pytest` passes in full.

## Red-team review (applied)

| Persona | Finding | Resolution in plan |
|---|---|---|
| Assumptions | `itsdangerous` is not installed, so Starlette `SessionMiddleware` would add a dependency. | Server-side session rows (random token, SHA-256 stored) in SQLite. Phase 5. |
| Assumptions | Docker images do not copy `docs/`, so Help would be empty in containers. | Phase 6 adds `COPY docs/ docs/`; Help reads `VIENEU_DOCS_DIR` (default repo `docs/`) and shows a clear message when missing. |
| Failure | Gradio uses `normalize_to_chunks_v3` (no gaps); a `[0.5]` tag there would be spoken. | Phase 2 strips numeric tags on every chunker entry point; only the gaps path turns them into silence. |
| Failure | `_merge_short_chunks` could merge across an explicit pause and drop it. | Phase 2: explicit-pause boundaries are never merged; test case included. |
| Failure | An implicit open-to-closed switch on the first key would surprise operators. | Replaced by the user's choice: the API always requires a key when the admin app is on; `VIENEU_ADMIN=0` restores today's behavior. Breaking for keyless setups, documented in both docs and the startup log. |
| Scope | Per-key quotas, OAuth, password-reset email, MP3, per-user dictionaries. | Non-goals, unchanged. |
| Security | Login brute force; key enumeration; XSS via dictionary entries or Markdown docs. | Per-username + per-IP failure lockout (in memory); constant-time hash lookup; Jinja2 autoescape on; markdown-it-py with `html=False`. |
| Security | Lexicon replacement text could inject `<|emotion_k|>` or `[x]` control tags. | Phase 1 schema rejects `[`, `]`, `<|`, `|>` and any tag other than `<en>` in `replacement`. |

## Validation answers (2026-10-30)

1. **API lock:** always require a key when the admin app is enabled, even with zero keys. This intentionally changes the public contract for keyless setups; `VIENEU_ADMIN=0` keeps the old behavior. Phases 6 and 7 updated.
2. **Dictionaries on plain API requests:** only when `preprocess=true`; plain requests stay byte-identical.
3. **DB location:** `./vieneu_data/admin.sqlite3`, overridable with `VIENEU_ADMIN_DB`, git-ignored.
4. **Script Lab limit:** 50 000 characters for script/JSON analysis; interactive in-app audio render capped at ≤ 3 000 characters to prevent engine starvation and proxy timeouts (full-chapter batch render uses the CLI).

## Red Team Review

### Session — 2026-11-01
**Findings:** 15 (14 accepted, 1 rejected)  
**Severity breakdown:** 4 Critical, 7 High, 4 Medium

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | Path traversal & arbitrary file read in `/admin/help` via unvalidated `doc`/`lang` | Critical | Accept | Phase 5, Phase 7 |
| 2 | Leading & trailing pause tag off-by-one misalignment in chunker contract | Critical | Accept | Phase 2 |
| 3 | GPU CUDA graph memory corruption from concurrent Script Lab `tts.infer()` | Critical | Accept | Phase 6 |
| 4 | Synchronous 50k-char Script Lab render causes engine starvation & HTTP 504 timeouts | Critical | Accept | Phase 5, plan.md |
| 5 | Uncheckpointed SQLite data loss & corruption via raw file copy in WAL mode | High | Accept | Phase 5 |
| 6 | Thread-safety violation on shared SQLite connection with `check_same_thread=False` | High | Accept | Phase 5 |
| 7 | Unescaped regex characters in lexicon mapping cause ReDoS & crash on symbols (`C++`, `C#`) | High | Accept | Phase 1, Phase 3 |
| 8 | Insecure Direct Object Reference (IDOR) on API key revocation `POST /keys/{id}/revoke` | High | Accept | Phase 5 |
| 9 | Unrecoverable headless lockout when admin environment credentials are missing | High | Accept | Phase 6 |
| 10 | In-memory lockout DoS on `admin` username & reverse proxy `127.0.0.1` collateral lockout | High | Accept | Phase 5 |
| 11 | Decouple CSRF protection from SQLite `sessions` table to secure `/login` without DB DoS | High | Accept | Phase 5 |
| 12 | Preprocessor multi-speaker & speed discarded by streaming API (YAGNI challenge) | Medium | Reject | N/A (Required by tts-specs-v1 for Script Lab & CLI) |
| 13 | Fictional character names in seed dictionaries enabled by default for general users | Medium | Accept | Phase 4 |
| 14 | Time-stretching via `librosa.effects.time_stretch` in runner introduces latency & artifacts | Medium | Accept | Phase 3 |
| 15 | Session token retention across user deactivation and password reset | Medium | Accept | Phase 5 |

## Validation Log

### Session 2 — 2026-11-01
**Trigger:** Pre-implementation critical questions interview via `/ck-plan validate`  
**Questions asked:** 4

#### Questions & Answers

1. **[Architecture / Failure Handling]** When an API client sends 'preprocess: true' on '/v1/audio/speech' and an unexpected parsing anomaly or syntax issue occurs, how should the API handle it?
   - Options: (Recommended) Fail-open: log warning and synthesize raw text without failing the TTS request | Fail-closed: return HTTP 400 Bad Request with preprocessor error details | Sanitize aggressively: strip invalid tags/structures and proceed with partial preprocessing
   - **Answer:** Fail-open: log warning and synthesize raw text without failing the TTS request
   - **Rationale:** Prevents audio synthesis disruptions for downstream API consumers while ensuring diagnostic warnings are recorded for preprocessor fixes.

2. **[Operations / Security]** On a fresh installation with 'VIENEU_ADMIN=1', if neither VIENEU_ADMIN_USER nor VIENEU_ADMIN_PASSWORD are provided in the environment, what should happen?
   - Options: (Recommended) Require explicit env vars: fail startup with an informative error if admin DB has no users and no env credentials are provided | Generate random one-time admin credentials logged to stdout/stderr, requiring password change on first login | Run speech API only and keep /admin routes disabled until CLI bootstrap or env vars are supplied
   - **Answer:** Require explicit env vars: fail startup with an informative error if admin DB has no users and no env credentials are provided
   - **Rationale:** Eliminates accidental headless/unconfigured public deployments; forces deliberate operator setup via environment variables or explicit CLI initialization.

3. **[Architecture / UI UX]** What audio output format should the Script Lab in-app preview render (/admin/script-lab/render) generate?
   - Options: (Recommended) WAV 48kHz (native uncompressed, zero encoding latency, instant browser playback) | FLAC (lossless compressed, lower network payload for 3,000-char scripts) | Selectable WAV or FLAC via toggle in the Script Lab UI (default WAV)
   - **Answer:** Selectable WAV or FLAC via toggle in the Script Lab UI (default WAV)
   - **Rationale:** Provides both zero-overhead instant preview via default WAV and smaller bandwidth-friendly downloads via FLAC when working with longer preview passages.

4. **[Scope / Dictionaries]** Which activation state should seeded pronunciation dictionaries have on initial database creation?
   - Options: (Recommended) Standard general dictionaries enabled by default, domain-specific/fictional (e.g. Harry Potter) disabled by default | All seed dictionaries enabled by default (ready out-of-the-box for story demos) | All seed dictionaries disabled by default (strict opt-in)
   - **Answer:** All seed dictionaries enabled by default (ready out-of-the-box for story demos)
   - **Rationale:** Ensures immediate out-of-the-box functionality for story preprocessing benchmarks and demo scripts without manual admin activation.

#### Confirmed Decisions
- **Preprocessor API Error Strategy**: Fail-open with warning and raw text synthesis fallback.
- **Fresh DB Admin Bootstrap**: Hard fail at startup with an informative error if no admin user and no env vars exist.
- **Script Lab Audio Render Format**: Format selector toggle in UI supporting both WAV (default) and FLAC.
- **Seed Dictionaries Initial State**: All seed dictionaries enabled by default upon fresh DB initialization.

#### Action Items
- [x] Phase 3: Add safe execution contract for fail-open fallback support.
- [x] Phase 4: Set `enabled: true` for all seed dictionary files.
- [x] Phase 5: Add format toggle (WAV/FLAC, default WAV) to Script Lab preview UI and rendering endpoint.
- [x] Phase 6: Implement explicit env credential requirement on fresh start and fail-open preprocessor API wrapper.

#### Impact on Phases
- Phase 3: Preprocessor wrapper designed to catch syntax exceptions safely.
- Phase 4: `fantasy-ash-land.json` and `fantasy-hogwarts.json` configured with `enabled: true`.
- Phase 5: Script Lab render route and template updated with format choice.
- Phase 6: Startup validation enforced and API preprocessor try/except fallback wired.

<!-- slug: admin-web-dictionary-preprocessor -->
