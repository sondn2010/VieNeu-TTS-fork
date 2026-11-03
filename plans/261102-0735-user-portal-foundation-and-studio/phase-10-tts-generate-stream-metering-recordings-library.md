# Phase 10: TTS generate/stream, atomic metering, recordings and library API, portal compose

<!-- Updated: Red Team 2026-11-02 - per-user synthesis lease; recording row is the queue (no background_jobs); finalize locks the recording first, per-attempt object keys, lease + heartbeat; no DB session across engine calls; orphaned sync rows swept; engine 429/400 handling; portal compose and engine-free image moved here from phase 6 -->

## Context
- Contracts: master `vieneu_tts_user_specs.md:726-729` (`/tts/stream`, `/tts/generate`, `GET /tts/recordings?search&voice_id&page&limit` with `total_count`, `total_duration_seconds`, `DELETE /tts/recordings/:id`); response shape spec 08 `:236-268`; library UI rules master `:299-302`; TC-02, TC-07, TC-09.
- Building blocks: engine client, engine double + storage (phase 3), engine render/stream + portal compose engine services (phase 4), `build_engine_text` (phase 8), `load_rules_for_synthesis` (phase 9), profile serializer (phase 2).
- Engine admission: CPU default one slot, queue one, 10 s queue timeout (`apps/openai_speech.py:149-152`, `:173-184`); GPU compose default 16 streams (`docker/docker-compose.yml:78-79`). CPU RTF ~0.58 (`apps/openai_speech.py:143`).
- Core package deps include onnxruntime, gradio, librosa (`pyproject.toml:69-83`), so the portal image cannot install `.` with deps.

## Overview
Priority P1. The money path. Charge only after audio is safely stored, in the same transaction that records success. One in-flight synthesis per user makes the precheck exact. Long texts are rendered by a worker that claims `ASYNC` `PENDING` recordings directly and reuses the exact same finalize function. Also delivers the runnable portal stack (portal + worker services, engine-free image).

## Key insights
- Charge-after-success with a conditional UPDATE means failures never touch counters. With the per-user synthesis lease, the read-only precheck cannot be outrun by the same user's parallel requests, so the conditional UPDATE failing becomes a true edge case (admin adjustment or expiry in between).
- The recording row is both queue item and idempotency guard. Finalize first locks it (`SELECT ... FOR UPDATE` where `status = 'PENDING'`); if it is no longer PENDING, finalize returns without charging or touching objects. Only then does it charge and mark SUCCESS, in that one transaction.
- Every attempt writes its own object key, so a losing attempt can only delete what it wrote.
- Never hold a DB connection across an engine or storage call (phase 1 discipline): commit, call out, open a new short session.
- Daily reset is lazy, inside the same UPDATE, using the `QUOTA_TIMEZONE` date.

## Requirements
Per-user synthesis lease (`tts/user_synthesis_lease.py`):
```sql
UPDATE users SET synthesis_lock_until = now() + make_interval(secs => :lease)
WHERE id = :uid AND (synthesis_lock_until IS NULL OR synthesis_lock_until < now())
RETURNING id;
```
0 rows -> `409 SYNTHESIS_IN_PROGRESS`. Renewed every `JOB_LEASE_SEC / 3` while a stream/render is active; released (`synthesis_lock_until = NULL`) when the stream ends, the sync generate finishes, or the async recording reaches a terminal state. A crash simply lets the lease expire.

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
3. `build_engine_text` in a threadpool (moderation 422 on original or processed text, 503 `MODERATION_UNAVAILABLE` when the provider is down since moderation fails closed, `422 TEXT_TOO_LONG_AFTER_PROCESSING`: no row, no charge).
4. Read-only precheck -> `402 INSUFFICIENT_TOKENS` / `402 DAILY_CHAR_LIMIT_REACHED` / `402 PLAN_EXPIRED`.
5. Acquire the user synthesis lease (409 if held).
6. Insert recording `PENDING` (tokens 0, original_text verbatim, processed_text, char_count, `render_mode` = `ASYNC` when `processed_char_count > TTS_SYNC_CHAR_CAP` else `SYNC`, `locked_until = now() + JOB_LEASE_SEC` for SYNC) and commit.
7. `ASYNC` -> `202 {recording: {id, status: "PENDING", estimated_seconds}}`; the lease stays held until the worker finishes.
8. `SYNC` -> `finalize_recording(recording_id, attempt=1)` with no open DB session during the engine/storage calls: engine render (mp3, timeout from processed length) -> storage put `recordings/<user>/<recording>-<attempt>.mp3` -> new transaction {lock recording FOR UPDATE where PENDING (else stop and delete own object); charge UPDATE; recording -> SUCCESS with tokens, duration, object key}. Charge returns 0 rows -> mark FAILED `QUOTA_RACE`, delete own object, 402. Engine/storage error -> recording FAILED (`ENGINE_UNAVAILABLE`/`ENGINE_REJECTED`/`STORAGE_ERROR`, tokens 0) -> 503/422/502; `EngineBusy` on sync -> FAILED `ENGINE_UNAVAILABLE`, 503 with `retry_after`. Release lease. Success -> `200 {recording, quota}` (spec shape, presigned `audio_url`, `download_url`).
- Worker `python -m vieneu_portal worker` (`jobs/recording_render_worker_loop.py`): claims `UPDATE tts_recordings SET locked_until = now() + lease, attempts = attempts + 1 WHERE id = (SELECT id ... WHERE status = 'PENDING' AND render_mode = 'ASYNC' AND (locked_until IS NULL OR locked_until < now()) ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING ...`; renews `locked_until` (and the user lease) every lease/3 while rendering; calls the same `finalize_recording()`. `EngineBusy` (429) -> release claim with backoff, attempt not consumed; `EngineUnavailable` -> retry up to `WORKER_MAX_ATTEMPTS`, then FAILED; `EngineRejected` -> FAILED at once. Sweeps: `SYNC` PENDING rows with expired `locked_until` (process died mid-request) -> FAILED `ABANDONED` and lease released, never re-rendered (the user may already have retried); expired sessions and throttle rows purged (phase 2). Graceful SIGTERM (finish or release the claim).
- `POST /tts/stream` `{voice_id, text}`: steps 1-5, then proxy engine PCM16 (24 kHz, `X-Sample-Rate`) as `audio/pcm` streaming with no DB session held; after the last chunk open a short session and run the charge UPDATE (no recording row); client disconnect, engine error or a truncated engine body mid-stream: no charge. Lease released in a `finally`. Speed not applied on stream (engine limitation; UI says so).
- `GET /tts/recordings?search=&voice_id=&page=1&limit=20` (limit <= 100): items with status SUCCESS or PENDING, newest first; `total_count` (filtered), `overall_count` (all SUCCESS, the "Y"), `total_duration_seconds` (filtered SUCCESS), `voices_used [{id, name}]`. Search = NFC, `ILIKE` with escaped `%`/`_` over `original_text` or voice name.
- `GET /tts/recordings/{id}` (polling; includes FAILED with `error_code`; PENDING includes `estimated_seconds` from processed length); `DELETE /tts/recordings/{id}` -> 204, 404 for others' ids, 409 while PENDING with a live lease (abandoned rows become FAILED and deletable); object delete after commit, failures logged.

Portal stack (moved from phase 6):
- `docker/Dockerfile.portal`: python:3.12-slim, `postgresql-client-16` (for `pg_dump`), `uv export --frozen --only-group portal --no-hashes > /tmp/req.txt && pip install -r /tmp/req.txt && pip install --no-deps .`; non-root user; build-time check fails if `onnxruntime`, `torch` or `gradio` is importable.
- `docker/docker-compose.portal.yml`: `portal` (build `Dockerfile.portal`, runs `db upgrade` then `serve`, port 8100 published, `VIENEU_PORTAL_SECRET_KEY=${VIENEU_PORTAL_SECRET_KEY:?}`, `VIENEU_PORTAL_ENGINE_SERVICE_KEY=${VIENEU_ENGINE_SERVICE_KEY:?}`), `worker` (same image, `python -m vieneu_portal worker`); MinIO console bound to localhost.
- `.env.example` portal section: DB URL, secret key, S3, engine URL/service key, quotas, signup switch.

## Related code files
Create: `src/vieneu_portal/tts/request_models_and_validation.py`, `tts/user_synthesis_lease.py`, `tts/quota_precheck_and_atomic_charge.py`, `tts/recording_finalize_service.py`, `tts/routes_tts_generate.py`, `tts/routes_tts_stream.py`, `tts/routes_recordings_library.py`, `tts/recording_serializer.py` (reused by the admin recordings browser), `tts/recordings_query.py` (filter/search/totals, reused by admin), `jobs/recording_render_queue.py` (claim, renew, sweep), `jobs/recording_render_worker_loop.py`, `tests/portal/test_quota_atomic_charge.py`, `tests/portal/test_user_synthesis_lease.py`, `tests/portal/test_tts_generate_sync_and_async.py`, `tests/portal/test_tts_stream_metering.py`, `tests/portal/test_recordings_library_api.py`, `tests/portal/test_worker_recording_claiming.py`, `tests/portal/test_generate_against_real_engine.py` (marker `engine`, runs in `make portal-test-e2e`), `docker/Dockerfile.portal`.
Modify: `src/vieneu_portal/app.py`, `src/vieneu_portal/__main__.py` (`worker`), `docker/docker-compose.portal.yml` (`portal`, `worker`), `.env.example` (portal section), `Makefile` (`portal-up`, `portal-down`, `portal-migrate-sqlite`, `portal-test-e2e`).

## Implementation steps
1. Lease + charge modules + tests: 10 parallel streams or generates from one user -> 1 accepted, 9 get 409; concurrent generates from 20 users each with balance for one -> all charged exactly once; daily reset across date boundary; expired plan.
2. Finalize service shared by route and worker; failure tests: moderation reject (original and rule-introduced), moderation provider down (503), processed text over cap, engine 503/429/400, storage error, commit failure -> counters byte-equal before/after (TC-02 included).
3. Generate route (sync/async) and worker loop; lease expiry mid-render (second claim) -> exactly one charge, winner's object intact, loser deletes only its own key; worker crash after commit -> no re-render; abandoned SYNC row swept to FAILED and deletable; 429 does not consume attempts.
4. Stream route with disconnect, mid-stream error and truncated-body tests; no DB connection checked out while streaming (pool assertion).
5. Library routes; TC-07 API test: 3 recordings, two voices, `voice_id` filter and `search` give correct `X`/`Y` and summed duration; TC-09 subset: quota in generate response equals subsequent `GET /user/profile`.
6. `original_text` byte-equality test (NFD input, emoji, CRLF preserved as sent).
7. Dockerfile.portal + compose services; `make portal-up` -> `curl :8100/api/v1/health` 200; `docker compose exec portal python -m vieneu_portal voices sync` inserts the engine's voices; image check passes.

## Todo
- [ ] lease  - [ ] charge  - [ ] finalize + failures  - [ ] generate sync/async  - [ ] worker + sweeps  - [ ] stream  - [ ] library  - [ ] TC tests  - [ ] portal image + compose

## Success criteria
- All listed tests green on real Postgres + MinIO with the engine double; real-engine test green in `portal-test-e2e`.
- No code path writes `token_balance`/`daily_char_remaining` outside `quota_precheck_and_atomic_charge.py` and the audited admin adjustment module of phase 13 (grep check in test; phase 13 extends its allow-list by exactly that one file).
- Portal image contains no onnxruntime/torch/gradio.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Orphan objects when commit fails after upload | M x L | Best-effort delete of own key + `recordings/` prefix sweeper later (C3) |
| Free audio via aborted streams | M x M | Accepted by user (charge only on completion); one in-flight synthesis per user and precheck bound abuse to one stream at a time |
| Worker starvation / engine overload | M x M | One worker concurrency 1 by default; 429 -> backoff without consuming attempts; per-user lease prevents one account filling the queue |
| User wants to stream while a long job renders | M x L | 409 explains it; UI disables actions while a synthesis is in flight (phase 12) |

## Rollback
Remove routers, worker and portal services; recordings rows stay valid (SUCCESS ones playable).

## Security
Every query scoped by session user; presigned URLs short TTL; text never logged; the worker reads text from the recording row only.

## Next
Phase 12 (Studio, My Voices), phase 13 (admin API).
