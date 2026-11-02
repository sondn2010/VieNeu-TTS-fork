# Phase 04: Engine service trim (`apps/openai_speech.py`)

## Context
- Admin coupling to remove: imports `apps/openai_speech.py:102-104`; Script Lab provider `:265`; admin setup/bootstrap/close `:293-372`; DB-key branch in `_auth` `:374-389`; `_is_admin_path` + its use in handlers `:400-422`; startup/shutdown admin calls `:425-438`; `/` redirect to `/admin/` `:441-445`; `STORE.enabled_lexicon()` in `_preprocess_input` `:518`; admin hints in `main()` `:703-723`; module docstring `:42-70`.
- Slot discipline (one stream slot per synthesis, never a parallel `tts.infer`): `speech()` `:587-625`, `_speech_chunks` `:534-564`. Earlier red-team finding: concurrent `tts.infer()` corrupts CUDA graphs.
- Speed: v3 Turbo `infer`/`infer_stream` have no speed parameter (`src/vieneu/v3turbo.py:600-672`); `X-VieNeu-Ignored: speed` today.

## Overview
Priority P1. The engine becomes an internal service: one service key (`VIENEU_API_KEY`), no DB, no admin. Adds a full-render endpoint for the portal's generate path. Runs in parallel with phases 2 and 7 (disjoint files).

## Requirements
- Remove every `vieneu_admin` import and the `VIENEU_ADMIN*` env handling. `_auth` = constant-time compare against `VIENEU_API_KEY`; non-loopback bind without a key refuses to start (keep current guard semantics, minus admin branch).
- `/v1/audio/speech`, `/v1/models`, `/v1/voices`, `/health` unchanged in shape. `preprocess=true` keeps working with an empty lexicon (prosody + pause tags only).
- New `POST /internal/v1/render` (auth required): body `{text (1..20000), voice, speed (0.5..2.0, default 1.0), format: "mp3"|"wav", sample_rate}`; response audio bytes with headers `X-Audio-Duration-Seconds`, `X-Sample-Rate`, `X-Request-Id`. Errors in the existing OpenAI error shape: 400 unknown voice, 429 server full, 503 engine down.
- Render runs through `eng.acquire()` + `_Slot` + `_speech_chunks` (same scheduler as streaming), concatenates chunks, applies `librosa.effects.time_stretch` when `speed != 1.0`, encodes with `soundfile` (MP3 needs libsndfile >= 1.1; verify, else return `415 format_unavailable` and the portal falls back to WAV).
- `/` returns 404 JSON (no admin redirect).

## Related code files
Modify: `apps/openai_speech.py`, `tests/test_openai_speech.py` (drop admin fixtures `:17-19`, `:53-55`, `:166-260` cases; keep env-key, slots, health, preprocess tests; add render tests), `docker/docker-compose.yml` (remove `VIENEU_ADMIN*` env from `api-gpu`/`api-cpu`), `docker/docker-compose.prod.yml` (same), `.env.example` (drop admin block; document service key).
Create: `apps/openai_speech_internal_render.py` (render route + encoder helper, keeps `openai_speech.py` from growing).

## Implementation steps
1. Delete admin wiring listed above; simplify `_auth` and error handlers (no admin path exception).
2. `_preprocess_input`: call `vieneu_preprocess.preprocess_safely(raw, ())`.
3. Implement render module: request model, slot acquire, collect, time-stretch, encode, headers; register router from `openai_speech.py`.
4. Verify `soundfile.available_formats()` contains `MP3` in the engine images (CPU + GPU Dockerfiles); add a startup log line with the result.
5. Update tests: auth with/without key, render returns playable MP3/WAV with duration header within 5% of decoded length, speed 1.5 shortens duration ~1/1.5, render while server full -> 429, unknown voice -> 400.
6. Update compose/env docs for the engine services.

## Todo
- [ ] strip admin  - [ ] auth simplify  - [ ] render endpoint  - [ ] MP3 capability check  - [ ] tests  - [ ] compose/env

## Success criteria
- `grep -n vieneu_admin apps/` returns nothing; `pytest tests/test_openai_speech.py` green.
- Render endpoint never runs outside a stream slot (test asserts `eng.active` accounting).

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Breaking existing keyless/admin-key API users | M x M | Documented breaking change; `VIENEU_API_KEY` remains the single key; DB keys move to portal developer API in C2 |
| Time-stretch artifacts/latency at extreme speeds | M x L | Bounded 0.5-2.0; only on full render; stream path keeps ignoring speed (header) |
| Long renders hold a slot and HTTP connection | M x M | Portal routes texts above `TTS_SYNC_CHAR_CAP` to the async worker; engine timeout configured |

## Rollback
`git revert` of this phase restores admin mounting (requires `vieneu_admin` still present, so revert before phase 6 or revert together).

## Security
Service key required for every route except `/health`; engine port not published publicly in portal compose (internal network only).

## Next
Phase 6 (admin package removal), phase 10 (portal generate/stream).
