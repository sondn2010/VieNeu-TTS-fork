# Phase 03: Object storage interface, engine client and voice catalog

## Context
- Voices source: `src/vieneu/assets/voices_v3_turbo.json` (`presets` dict of 25; fields `description`, `featured`, `gender` male/female, `region` Bắc/Trung/Nam, `style`, optional `aliases`; `default_voice` "Hải Đăng").
- `voices` DDL: spec 08 `:39-54` (`gender` NAM/NU, `region` MIEN_BAC/MIEN_TRUNG/MIEN_NAM, `sample_audio_url NOT NULL`).
- Engine contract to call: phase 4 (`/internal/v1/render`, `/v1/audio/speech`).

## Overview
Priority P1. A storage interface with S3 (MinIO dev) and local-disk backends, the HTTP engine client used by later phases, the voice catalog sync from the preset JSON, and `GET /api/v1/voices`.

## Key insights
- Store object keys, never URLs; presign per response so TTL and bucket moves never break rows.
- User decision: seed a best guess from the preset JSON (gender/region fields, or parsed from the description such as `Nữ · Bắc`, the same data as sample names like `(nữ miền Bắc)`), initials avatars (`avatar_url` null), empty tags. Admins edit everything later in the admin UI (phases 13-14), so sync must never overwrite admin-edited fields.
- `sample_audio_url NOT NULL`: fill with the deterministic key `voices/samples/<id>.mp3`; phase 5 CLI renders the audio into that key.

## Requirements
- `ObjectStorage` protocol: `put_bytes(key, data, content_type)`, `presigned_get(key, ttl, download_name=None)`, `delete(key)`, `exists(key)`. Backends: `S3ObjectStorage` (boto3, path-style for MinIO), `LocalDiskObjectStorage` (dev/tests; serves via `GET /api/v1/files/{signed}` with HMAC-signed expiring path).
- `EngineClient`: `render(text, engine_voice_name, speed, fmt="mp3") -> RenderedAudio(bytes, duration_seconds, sample_rate)`; `open_stream(text, engine_voice_name) -> async iterator of PCM16 bytes + sample_rate`; typed errors `EngineUnavailable`, `EngineRejected`. Bearer service key; timeouts from settings.
- Voice id = slug of preset name (strip diacritics, `đ`->`d`, spaces->`-`), e.g. `Hải Đăng` -> `hai-dang`. `initials` = first letters of first and last word, upper. `gender`: male->NAM, female->NU. `region`: Bắc->MIEN_BAC, Trung->MIEN_TRUNG, Nam->MIEN_NAM. Missing `gender`/`region` fields fall back to parsing `description` (`Nam|Nữ · Bắc|Trung|Nam`); still unknown -> sync error naming the preset. `tags = '{}'`; `avatar_url` null (UI renders initials); `supported_styles = ['Tự nhiên']`; `sort_order` = `featured` then name; `model_version` = settings label.
- Sync semantics: insert presets not yet in the table; deactivate rows whose preset disappeared; never update name, gender, region, tags, avatar, sample or `is_active` of existing rows (admin-owned after first insert).
- `voices.avatar_url` stores an object key (`voices/avatars/<id>.<ext>`) when an admin uploads one; responses presign it.
- `GET /api/v1/voices` (auth required): active voices ordered by `sort_order`, with presigned `sample_audio_url`.

## Related code files
Create: `src/vieneu_portal/storage/object_storage_interface.py`, `storage/s3_object_storage.py`, `storage/local_disk_object_storage.py`, `storage/routes_local_signed_files.py`, `storage/object_storage_factory.py`, `engine/engine_http_client.py`, `voices/voice_catalog_from_presets.py`, `voices/voice_serializer.py`, `voices/routes_voices.py`, `tests/portal/test_object_storage_backends.py`, `tests/portal/test_voice_catalog_from_presets.py`, `tests/portal/test_routes_voices.py`.
Modify: `src/vieneu_portal/app.py` (register voices + local files routes).

## Implementation steps
1. Protocol + local backend (atomic write via temp + rename; reject keys with `..` or absolute paths).
2. S3 backend; integration test against compose MinIO (put, presign, GET via httpx, delete).
3. Engine client with httpx (sync for worker, async for stream route); map 429/503 to `EngineUnavailable`, 400 to `EngineRejected`.
4. Catalog derivation as a pure function (preset JSON -> list of rows) + sync function (insert new, deactivate removed ids, leave existing rows untouched; never delete because recordings reference voices).
5. Voices route and tests (slug uniqueness across all 25, NAM/NU and region mapping, description fallback parse, an admin-edited row survives a re-sync).

## Todo
- [ ] storage protocol + 2 backends  - [ ] engine client  - [ ] catalog derivation + upsert  - [ ] voices route  - [ ] tests

## Success criteria
- MinIO round-trip test green; local backend rejects traversal keys.
- Catalog sync on empty DB inserts 25 active voices with unique ids; second run is a no-op; removing a preset deactivates it.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Slug collisions (e.g. `Adam` vs `Adam bựa`) | L x M | Test asserts uniqueness; collision fails sync loudly |
| Presigned URL host unreachable from browser (internal MinIO hostname) | M x M | `S3_PUBLIC_ENDPOINT` setting used only for presigning |
| Best-guess metadata wrong (region/gender) | M x L | Editable in admin UI; sync never overwrites edits |

## Rollback
Remove routers; storage objects are additive; catalog rows can be deactivated.

## Security
Presigned URLs short-lived; local signed path uses HMAC with server secret and expiry; bucket private.

## Next
Phase 5 (CLI sync + sample rendering), phase 10 (generate uses storage + engine client).
