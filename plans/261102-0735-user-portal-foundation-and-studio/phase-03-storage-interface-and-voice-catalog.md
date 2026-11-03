# Phase 03: Object storage interface, engine client and voice catalog

<!-- Updated: Red Team 2026-11-02 - S3 only (local backend and signed-files route dropped); voice sync reads the engine's /v1/voices instead of the bundled preset JSON; engine double moved here; engine 400/422 mapped -->

## Context
- Engine voice list: `GET /v1/voices` returns `{id, name, description, gender, featured, aliases}` per voice (`apps/openai_speech.py:189-195`, `:641-643`). The engine's voice set comes from the model repo or a fine-tune, not necessarily the bundled `src/vieneu/assets/voices_v3_turbo.json` (`src/vieneu/v3turbo.py:268-283`), so the engine is the authority on which voices exist. Bundled file today: 25 presets, all with `gender` male/female and `description` like `Nữ · Bắc`; `default_voice` "Hải Đăng".
- `voices` DDL: spec 08 `:39-54` (`gender` NAM/NU, `region` MIEN_BAC/MIEN_TRUNG/MIEN_NAM, `sample_audio_url NOT NULL`).
- Engine contract to call: phase 4 (`/internal/v1/render`, `/v1/audio/speech`, `/v1/voices`).
- Brainstorm decision: S3-compatible storage from day one (`plans/reports/brainstorm-261102-0735-user-portal-postgres-rewrite.md:19`); MinIO is in the phase 1 compose and every integration test uses it.

## Overview
Priority P1. One S3 storage implementation behind a thin protocol (kept for test doubles), the HTTP engine client and its deterministic test double, the voice catalog sync from the engine's voice list, and `GET /api/v1/voices`.

## Key insights
- Store object keys, never URLs; presign per response so TTL and bucket moves never break rows.
- User decision: seed a best guess (gender from the engine field, region parsed from the description such as `Nữ · Bắc`), initials avatars (`avatar_url` null), empty tags. Admins edit everything later in the admin UI (phases 13-14), so sync must never overwrite admin-edited fields.
- `sample_audio_url NOT NULL`: fill with the deterministic key `voices/samples/<id>.mp3`; phase 5 CLI renders the audio into that key.
- The portal never reads `src/vieneu/assets/*` or imports `vieneu`, so the portal image stays engine-free (phase 10).

## Requirements
- `ObjectStorage` protocol: `put_bytes(key, data, content_type)`, `presigned_get(key, ttl, download_name=None)`, `delete(key)`, `delete_prefix(prefix)`, `exists(key)`. One backend: `S3ObjectStorage` (boto3, path-style for MinIO, `S3_PUBLIC_ENDPOINT` for presign host, `ResponseContentDisposition` for downloads, fixed `ContentType` on put). Unit tests that need no MinIO use an in-memory fake implementing the protocol (test code only).
- `EngineClient`: `render(text, engine_voice_name, speed, fmt="mp3", timeout) -> RenderedAudio(bytes, duration_seconds, sample_rate)`; `open_stream(text, engine_voice_name) -> async iterator of PCM16 bytes + sample_rate`; `list_voices() -> list[EngineVoice]`; typed errors `EngineBusy` (429), `EngineUnavailable` (503, connect/timeout errors), `EngineRejected` (400 and 422, including input over the engine's 20 000-char limit, `apps/openai_speech.py:488`). Bearer service key; timeouts from settings (render timeout = `ENGINE_TIMEOUT_SEC + chars x ENGINE_SEC_PER_CHAR`). A stream that ends without its full body (httpx protocol error, early close) raises `EngineUnavailable` so callers never charge a truncated stream.
- `tests/portal/engine_double_asgi_app.py`: deterministic ASGI double of the phase 4 contract (render, stream, voices) with switches for 429, 503, 400/422, truncated stream and slow render; used by phases 3, 5, 10, 13.
- Voice id = slug of engine voice id (strip diacritics, `đ`->`d`, spaces->`-`), e.g. `Hải Đăng` -> `hai-dang`; `engine_voice_name` = engine id verbatim. `initials` = first letters of first and last word, upper. `gender`: male->NAM, female->NU. `region` parsed from `description` (`Nam|Nữ · Bắc|Trung|Nam`): Bắc->MIEN_BAC, Trung->MIEN_TRUNG, Nam->MIEN_NAM; gender also falls back to the description. Still unknown -> sync error naming the voice. `tags = '{}'`; `avatar_url` null (UI renders initials); `supported_styles = ['Tự nhiên']`; `sort_order` = `featured` then name; `model_version` = settings label.
- Sync semantics: insert engine voices not yet in the table; deactivate rows whose engine voice disappeared; never update name, gender, region, tags, avatar, sample or `is_active` of existing rows (admin-owned after first insert); engine unreachable -> sync fails without touching rows.
- `voices.avatar_url` stores an object key (`voices/avatars/<id>.<ext>`) when an admin uploads one; responses presign it.
- `GET /api/v1/voices` (auth required): active voices ordered by `sort_order`, with presigned `sample_audio_url`.

## Related code files
Create: `src/vieneu_portal/storage/object_storage_interface.py`, `storage/s3_object_storage.py`, `engine/engine_http_client.py`, `voices/voice_catalog_from_engine.py`, `voices/voice_serializer.py`, `voices/routes_voices.py`, `tests/portal/engine_double_asgi_app.py`, `tests/portal/in_memory_object_storage.py`, `tests/portal/test_s3_object_storage.py`, `tests/portal/test_engine_http_client.py`, `tests/portal/test_voice_catalog_from_engine.py`, `tests/portal/test_routes_voices.py`.
Modify: `src/vieneu_portal/app.py` (register voices route).

## Implementation steps
1. Protocol + S3 backend; integration test against compose MinIO (put, presign, GET via httpx, download disposition, delete, delete_prefix).
2. Engine client with httpx (sync for worker, async for stream route) and the engine double; error mapping tests for 429, 503, 400, 422, timeout and truncated stream.
3. Catalog derivation as a pure function (engine voice list -> rows) + sync function (insert new, deactivate removed ids, leave existing rows untouched; never delete because recordings reference voices).
4. Voices route and tests (slug uniqueness over the bundled 25 names as a fixture, NAM/NU and region mapping, description parse, an admin-edited row survives a re-sync, engine down leaves rows unchanged).

## Todo
- [ ] storage protocol + S3 backend  - [ ] engine client + double  - [ ] catalog derivation + sync  - [ ] voices route  - [ ] tests

## Success criteria
- MinIO round-trip test green.
- Catalog sync against the engine double (25 voices) on an empty DB inserts 25 active voices with unique ids; second run is a no-op; removing a voice from the double deactivates it.
- Every engine error class maps to the typed error above.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Slug collisions (e.g. `Adam` vs `Adam bựa`) | L x M | Test asserts uniqueness; collision fails sync loudly |
| Presigned URL host unreachable from browser (internal MinIO hostname) | M x M | `S3_PUBLIC_ENDPOINT` setting used only for presigning |
| Best-guess metadata wrong (region/gender) | M x L | Editable in admin UI; sync never overwrites edits |
| Engine runs a fine-tune with different voices | M x M | Sync reads the engine list, so the catalog follows the deployed model |

## Rollback
Remove routers; storage objects are additive; catalog rows can be deactivated.

## Security
Presigned URLs short-lived; bucket private; no unauthenticated file route exists in the portal.

## Next
Phase 5 (CLI sync + sample rendering), phase 10 (generate uses storage + engine client).
