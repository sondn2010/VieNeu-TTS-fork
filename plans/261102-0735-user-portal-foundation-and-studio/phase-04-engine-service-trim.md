# Phase 04: Engine internal render endpoint and startup key guard (`apps/openai_speech.py`)

<!-- Updated: Red Team 2026-11-02 - admin removal moved to phase 6 (end of plan) so the working admin and DB keys survive until the portal replaces them; fail-closed key guard added (the current code only warns); portal compose engine services added here -->

## Context
- Current guard only warns: `main()` logs "listening on ... without VIENEU_API_KEY" and keeps serving (`apps/openai_speech.py:703-712`); `_auth` rejects keyless calls only when `env_key or ADMIN_ON` (`:388-390`); admin defaults on (`:299-300`). Existing compose files bind `0.0.0.0`, publish 8000 and default `VIENEU_API_KEY` to empty (`docker/docker-compose.yml:71-85`, `docker/docker-compose.prod.yml:35-45`). Tests pinning the warn-only behavior: `tests/test_openai_speech.py:156-163` (`test_open_public_bind_is_logged`), `:181-186` (`test_admin_off_without_env_key_stays_open`).
- Slot discipline (one stream slot per synthesis, never a parallel `tts.infer`): `speech()` `:587-625`, `_speech_chunks` `:534-564`. Earlier red-team finding: concurrent `tts.infer()` corrupts CUDA graphs. Admission: `acquire()` raises 429 when the queue is full or after `queue_timeout` (`:173-184`; CPU defaults `:149-152`).
- Existing encoder: `_encode_audio` writes WAV/FLAC with `subtype="PCM_16"` (`:256-261`); that subtype is invalid for MP3, so MP3 needs its own branch.
- Speed: v3 Turbo `infer`/`infer_stream` have no speed parameter (`src/vieneu/v3turbo.py:600-672`); `X-VieNeu-Ignored: speed` today.
- Engine Dockerfiles default to Gradio (`docker/Dockerfile.cpu:39`, `docker/Dockerfile.gpu:55`); the existing compose overrides with `command: ["python", "-m", "apps.openai_speech"]` and `HOST=0.0.0.0` (`docker/docker-compose.yml:117,123`).

## Overview
Priority P1. Additive engine work the portal needs: a full-render endpoint and a fail-closed startup guard, plus the engine services in the portal compose. The SQLite admin, its `/admin` mount and DB-key auth stay untouched here and are removed in phase 6. Runs in parallel with phases 2 and 7 (disjoint files).

## Requirements
- Startup guard: on a non-loopback `HOST`, `main()` exits non-zero with a clear message when neither `VIENEU_API_KEY` is set nor the admin is enabled (admin mode already requires a key per request). Phase 6 tightens this to "`VIENEU_API_KEY` required" when the admin branch goes away.
- `/v1/audio/speech`, `/v1/models`, `/v1/voices`, `/health` unchanged in shape.
- New `POST /internal/v1/render` (auth required): body `{text (1..20000), voice, speed (0.5..2.0, default 1.0), format: "mp3"|"wav", sample_rate}`; response audio bytes with headers `X-Audio-Duration-Seconds`, `X-Sample-Rate`, `X-Request-Id`. Errors in the existing OpenAI error shape: 400 unknown voice or invalid input, 429 server full, 503 engine down.
- Render reuses the streaming path: `eng.acquire()` + `_Slot` + `_speech_chunks` (no new scheduler), concatenates chunks, applies `librosa.effects.time_stretch` when `speed != 1.0`, encodes WAV through the existing `_encode_audio` and MP3 through a new branch of the same helper (`format="MP3"`, `subtype="MPEG_LAYER_III"`). If `soundfile.available_formats()` lacks `MP3`, return `415 format_unavailable` and the portal falls back to WAV.
- Portal compose (`docker/docker-compose.portal.yml`): `engine` (build `Dockerfile.cpu`, profile `cpu`) and `engine-gpu` (`Dockerfile.gpu`, profile `gpu`), both with `command: ["python", "-m", "apps.openai_speech"]`, `HOST=0.0.0.0`, `VIENEU_ADMIN=0`, `VIENEU_API_KEY=${VIENEU_ENGINE_SERVICE_KEY:?set VIENEU_ENGINE_SERVICE_KEY}`, explicit `VIENEU_MAX_STREAMS`, `VIENEU_QUEUE`, `VIENEU_QUEUE_TIMEOUT`, internal network only, no `ports:`.

## Related code files
Modify: `apps/openai_speech.py` (startup guard, register render router, MP3 branch in `_encode_audio`), `tests/test_openai_speech.py` (replace `test_open_public_bind_is_logged` and `test_admin_off_without_env_key_stays_open` with "public bind without key and admin off refuses to start"; add render tests), `docker/docker-compose.portal.yml` (engine services), `.env.example` (document `VIENEU_ENGINE_SERVICE_KEY` for the portal stack).
Create: `apps/openai_speech_internal_render.py` (render route; keeps `openai_speech.py` from growing).

## Implementation steps
1. Startup guard + replacement tests.
2. Render module: request model, slot acquire, collect, time-stretch, encode via `_encode_audio`, headers; register router from `openai_speech.py`.
3. Verify `soundfile.available_formats()` contains `MP3` in the engine images (CPU + GPU Dockerfiles); add a startup log line with the result.
4. Tests: render returns playable MP3/WAV with duration header within 5% of decoded length, speed 1.5 shortens duration ~1/1.5, render while server full -> 429, unknown voice -> 400, text over 20 000 chars -> 400, render never runs outside a slot (`eng.active` accounting).
5. Portal compose engine services; `docker compose -f docker/docker-compose.portal.yml --profile cpu up engine` starts the speech API (not Gradio) and refuses to start when the key is unset.

## Todo
- [ ] startup guard + tests  - [ ] render endpoint  - [ ] MP3 capability check  - [ ] render tests  - [ ] portal compose engine  - [ ] env docs

## Success criteria
- `pytest tests/test_openai_speech.py` green, including the refuse-to-start test.
- Render endpoint never runs outside a stream slot (test asserts `eng.active` accounting).
- Portal compose engine has no published port and fails fast without `VIENEU_ENGINE_SERVICE_KEY`.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Existing keyless public deployments stop starting | M x M | Intentional: they were open to the internet; message names the fix; breaking change documented in phase 15 |
| Time-stretch artifacts/latency at extreme speeds | M x L | Bounded 0.5-2.0; only on full render; stream path keeps ignoring speed (header) |
| Long renders hold a slot and HTTP connection | M x M | Portal routes processed texts above `TTS_SYNC_CHAR_CAP` to the worker; per-user single in-flight synthesis (phase 10); render timeout sized from text length |
| Orphaned render after portal timeout keeps the slot | M x M | Portal timeout = base + chars x rate; worker treats 429 as busy (backoff, no attempt consumed); lease longer than timeout (phase 10) |

## Rollback
`git revert` of this phase; the admin was never touched here.

## Security
Service key required for every route except `/health`; engine port not published in the portal compose (internal network only); a public bind without any key cannot start.

## Next
Phase 5 (sample rendering), phase 10 (portal generate/stream), phase 6 (admin wiring removal at the end).
