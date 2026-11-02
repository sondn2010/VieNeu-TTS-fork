# Phase 10: TTS generate/stream, atomic metering, recordings and library API

## Context
- Contracts: master `vieneu_tts_user_specs.md:726-729` (`/tts/stream`, `/tts/generate`, `GET /tts/recordings?search&voice_id&page&limit` with `total_count`, `total_duration_seconds`, `DELETE /tts/recordings/:id`); response shape spec 08 `:236-268`; library UI rules master `:299-302`; TC-02, TC-07, TC-09.
- Building blocks: engine client + storage (phase 3), engine render/stream (phase 4), `build_engine_text` (phase 8), `load_rules_for_synthesis` (phase 9), profile serializer (phase 2).

## Overview
Priority P1. The money path. Charge only after audio is safely stored, in the same transaction that records success. Long texts go to a Postgres-backed worker that reuses the exact same finalize function.

## Key insights
- Charge-after-success with a conditional UPDATE means failures never touch counters, and a lost race returns 402 instead of overdrawing. Cost: a lost race wastes one render (rare; precheck first).
- The recording row is the idempotency guard: finalize does `UPDATE tts_recordings ... WHERE id = :id AND status = 'PENDING'` in the charging transaction, so a retried job can never charge twice.
- Daily reset is lazy, inside the same UPDATE, using the `QUOTA_TIMEZONE` date.

## Requirements
Charge statement (one round trip, `RETURNING` new quota):
```sql
UPDATE users SET token_balance = token_balance - :t,
  daily_char_remaining = (CASE WHEN daily_chars_reset_on IS DISTINCT FROM :today THEN daily_char_limit ELSE daily_char_remaining END) - :c,
  daily_chars_reset_on = :today, updated_at = now()
WHERE id = :uid AND is_active AND token_balance >= :t
  AND (CASE WHEN daily_chars_reset_on IS DISTINCT FROM :today THEN daily_char_limit ELSE daily_char_remaining END) >= :c
  AND (plan_expires_at IS NULL OR plan_expires_at > now())
RETURNING token_balance, token_quota_total, daily_char_remaining;
```
`POST /tts/generate` `{voice_id, text, speed, bg_music_id}`:
1. Session + CSRF; terms accepted for current version else `403 TERMS_NOT_ACCEPTED`.
2. Validate: active voice (`422 UNKNOWN_VOICE`), speed in {0.5, 0.75, 1, 1.25, 1.5, 2}, `1 <= count_chars <= TTS_MAX_CHARS` (`422 TEXT_TOO_LONG`), `bg_music_id` must be null in C1 (`422 BG_MUSIC_UNAVAILABLE`).
3. `build_engine_text` (moderation 422, or 503 `MODERATION_UNAVAILABLE` when the provider is down since moderation fails closed: no row, no charge).
4. Read-only precheck -> `402 INSUFFICIENT_TOKENS` / `402 DAILY_CHAR_LIMIT_REACHED` / `402 PLAN_EXPIRED`.
5. Insert recording `PENDING` (tokens 0, original_text verbatim, processed_text, char_count).
6. `chars > TTS_SYNC_CHAR_CAP`: insert `background_jobs` row in the same transaction -> `202 {recording: {id, status: "PENDING"}, job: {id}}`.
7. Else `finalize_recording()`: engine render (mp3) -> storage put `recordings/<user>/<recording>.mp3` -> transaction {charge UPDATE; recording -> SUCCESS with tokens, duration, object key}. Charge returns 0 rows -> mark FAILED `QUOTA_RACE`, delete object, 402. Engine/storage error -> recording FAILED (`ENGINE_UNAVAILABLE`/`STORAGE_ERROR`, tokens 0) -> 503/502. Success -> `200 {recording, quota}` (spec shape, presigned `audio_url`, `download_url`).
- Worker `python -m vieneu_portal worker`: claims with `FOR UPDATE SKIP LOCKED` (`QUEUED` or `RUNNING` with expired `locked_until`), calls the same `finalize_recording()`, up to 3 attempts on `EngineUnavailable`, then FAILED. Graceful SIGTERM.
- `POST /tts/stream` `{voice_id, text}`: steps 1-4, then proxy engine PCM16 (24 kHz, `X-Sample-Rate`) as `audio/pcm` streaming; after the last chunk run the charge UPDATE (no recording row); client disconnect or engine error mid-stream: no charge. Speed not applied on stream (engine limitation; UI says so).
- `GET /tts/recordings?search=&voice_id=&page=1&limit=20` (limit <= 100): items with status SUCCESS or PENDING, newest first; `total_count` (filtered), `overall_count` (all SUCCESS, the "Y"), `total_duration_seconds` (filtered SUCCESS), `voices_used [{id, name}]`. Search = NFC, `ILIKE` with escaped `%`/`_` over `original_text` or voice name.
- `GET /tts/recordings/{id}` (polling; includes FAILED with `error_code`); `DELETE /tts/recordings/{id}` -> 204, 404 for others' ids, 409 while PENDING; object delete after commit, failures logged.

## Related code files
Create: `src/vieneu_portal/tts/request_models_and_validation.py`, `tts/quota_precheck_and_atomic_charge.py`, `tts/recording_finalize_service.py`, `tts/routes_tts_generate.py`, `tts/routes_tts_stream.py`, `tts/routes_recordings_library.py`, `tts/recording_serializer.py` (reused by the admin recordings browser), `tts/recordings_query.py` (filter/search/totals, reused by admin), `jobs/background_job_queue.py`, `jobs/tts_generate_worker_loop.py`, `tests/portal/engine_double_asgi_app.py` (deterministic test double of the phase 4 contract with failure switches; used only for failure injection), `tests/portal/test_quota_atomic_charge.py`, `tests/portal/test_tts_generate_sync_and_async.py`, `tests/portal/test_tts_stream_metering.py`, `tests/portal/test_recordings_library_api.py`, `tests/portal/test_worker_job_claiming.py`, `tests/portal/test_generate_against_real_engine.py` (marker `engine`, runs in `make portal-test-e2e`).
Modify: `src/vieneu_portal/app.py`, `src/vieneu_portal/__main__.py` (`worker`), `docker/docker-compose.portal.yml` (`worker` service), `Makefile` (`portal-test-e2e`).

## Implementation steps
1. Charge module + tests: concurrent 20 x generate with balance for 5 -> exactly 5 SUCCESS, balance >= 0; daily reset across date boundary; expired plan.
2. Finalize service shared by route and worker; failure tests: moderation reject, moderation provider down (503), engine 503, storage error, commit failure -> counters byte-equal before/after (TC-02 included).
3. Generate route (sync/async), worker loop, job reclaim after crash (expired lock) without double charge.
4. Stream route with disconnect and mid-stream error tests.
5. Library routes; TC-07 API test: 3 recordings, two voices, `voice_id` filter and `search` give correct `X`/`Y` and summed duration; TC-09 subset: quota in generate response equals subsequent `GET /user/profile`.
6. `original_text` byte-equality test (NFD input, emoji, CRLF preserved as sent).

## Todo
- [ ] charge  - [ ] finalize + failures  - [ ] generate sync/async  - [ ] worker  - [ ] stream  - [ ] library  - [ ] TC tests  - [ ] compose worker

## Success criteria
- All listed tests green on real Postgres + MinIO; real-engine test green in `portal-test-e2e`.
- No code path writes `token_balance`/`daily_char_remaining` outside `quota_precheck_and_atomic_charge.py` and the audited admin adjustment module of phase 13 (grep check in test; phase 13 extends its allow-list by exactly that one file).

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Orphan objects when commit fails after upload | M x L | Best-effort delete + `recordings/` prefix sweeper later (C3) |
| Free audio via aborted streams | M x M | Accepted by user (charge only on completion); precheck of tokens and daily chars on start bounds abuse |
| Worker starvation / engine overload | M x M | One worker concurrency 1 by default; engine 429 -> retry with backoff |

## Rollback
Remove routers and worker service; recordings rows stay valid (SUCCESS ones playable).

## Security
Every query scoped by session user; presigned URLs short TTL; text never logged; job payload holds ids only (text read from the recording row).

## Next
Phase 12 (Studio, My Voices).
