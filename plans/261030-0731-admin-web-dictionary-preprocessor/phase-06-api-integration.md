---
phase: 6
title: "Speech API integration and deploy"
status: pending
priority: P1
effort: "6h"
dependencies: [2, 3, 4, 5]
---

# Phase 6: Speech API integration and deploy

## Goal

Wire the admin app, DB-backed keys and the opt-in preprocessor into `apps/openai_speech.py` without changing behavior for existing clients.

## Files to Create / Modify

- Modify: `apps/openai_speech.py`
- Modify: `tests/test_openai_speech.py`
- Modify: `docker/Dockerfile.cpu`, `docker/Dockerfile.gpu` (add `COPY docs/ docs/`), `docker/docker-compose*.yml` (an `api` service or profile running `python -m apps.openai_speech`, port 8000, volume for `vieneu_data/`).
- Modify: `.env.example` — `VIENEU_ADMIN_DB`, `VIENEU_ADMIN_USER`, `VIENEU_ADMIN_PASSWORD`, `VIENEU_COOKIE_SECURE`, `VIENEU_DOCS_DIR`, `VIENEU_ADMIN=0|1`.
- Modify: `Makefile` — `api` target if the Makefile lists app targets.

## Tasks & Steps

- [ ] Startup: open `AdminStore`, run migrations, `seed_if_empty`, `bootstrap_admin` from env when no admin exists (log the username only, never the password); `VIENEU_ADMIN=0` skips mounting the router (keys in DB still checked if the DB exists).
- [ ] Auth dependency `_auth`: accept `VIENEU_API_KEY` (unchanged `hmac` compare) or a valid DB key. When the admin app is enabled (default), **every** `/v1/*` request requires a key, even when no keys exist yet (user decision, validation Q1). With `VIENEU_ADMIN=0`, keep today's behavior exactly (env key or open with the existing warning). Log at startup which mode is active, and when the admin app is on with zero keys, log that all API calls will get 401 until a key is created.
- [ ] `SpeechRequest.preprocess: bool = False`. When true: `result = preprocess(req.input, store.enabled_lexicon())`, then stream `result.to_tagged_text()` through the existing path; chunk speed is not applied on the streaming path (header `X-VieNeu-Ignored: speed` already exists — reuse it). When false: byte-identical request to the engine as today.
- [ ] Response header `X-VieNeu-Preprocess: 1` when applied; request `max_chars` still applies.
- [ ] Mount router: `app.include_router(create_admin_router(store, tts_provider=_EngineProvider()), prefix="/admin")` and `app.mount("/admin/static", StaticFiles(...))`; `_EngineProvider.render` acquires a stream slot (same queue/429 semantics) and runs `vieneu_preprocess.render` in a worker thread; returns WAV via `soundfile` or FLAC.
- [ ] `GET /` redirects to `/admin/` when the admin app is mounted.
- [ ] Tests (extend the existing FakeTTS fixture): DB key accepted, revoked key 401, disabled user 401, env key still accepted, admin app on with zero keys returns 401, `VIENEU_ADMIN=0` with no env key stays open, `preprocess=true` sends tagged text with `[x]` tags and lexicon replacements to `infer_stream`, `preprocess=false` sends input unchanged, admin router reachable, Script Lab render returns a WAV with the fake engine.

## Verification

- `uv run pytest tests/test_openai_speech.py -q`
- Full suite: `uv run pytest -q`
- Manual end to end (CPU): `VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD=<pw> uv run python -m apps.openai_speech`, log in at `http://127.0.0.1:8000/admin`, create a user and key, then `curl -H "Authorization: Bearer <key>" -d '{"input":"Xin chào. [1.0] Hogwarts.","preprocess":true,"response_format":"wav"}' ... -o out.wav`, listen, revoke, repeat → 401.
- `docker compose -f docker/docker-compose.yml config` validates.

## Risk / rollback

Touches the public API module. Backward compatibility is covered by the `preprocess=false` and env-key tests. Rollback: revert the phase commit; set `VIENEU_ADMIN=0` as an operational kill switch.
