# Phase 13: Admin API (`/api/v1/admin`) and audit log

## Context
- User decision 2026-11-02: admin/super-user area in C1. Specs define no admin screens; this phase designs the API.
- Parity source (old admin): user list/create/disable/reset-password/role and global dictionaries in `src/vieneu_admin/routes_users.py`, `routes_dictionaries.py`, `routes_dictionary_entries.py`, `routes_dictionary_transfer.py`, `store_accounts.py` (deleted in phase 6; read via `git show` of commit `5c930ac`). Guards kept: last active superadmin, no self-demotion.
- Building blocks: role dependencies (phase 2), admin services + audit writer + system dictionary store (phase 5), storage/engine client/voice serializer (phase 3), recordings query/serializer (phase 10), import/export functions (phase 7).

## Overview
Priority P1. Role-guarded JSON API for user, quota, key, system dictionary, voice catalog and recording administration. Every mutation writes exactly one `admin_audit_log` row in the same transaction. Runs in parallel with phase 12.

## Key insights
- Permission matrix lives in one module and is tested by enumerating every `/api/v1/admin` route from the app, so a new route cannot ship unguarded.
- ADMIN manages `USER` accounts only; SUPERADMIN manages everyone and is the only role that changes roles. Prevents an ADMIN from disabling or resetting a SUPERADMIN.
- Admin token adjustment is the only counter writer besides metering: atomic `UPDATE ... SET token_balance = token_balance + :delta WHERE id = :id AND token_balance + :delta >= 0`, with a mandatory reason.

## Requirements
All under `/api/v1/admin`, `require_admin`, CSRF on mutations, errors in the standard envelope (`403 FORBIDDEN_ROLE`, `409 LAST_SUPERADMIN`, `409 SELF_MODIFICATION`).
| Area | Endpoints |
|---|---|
| Users | `GET /users?search=&role=&status=&page=&limit=` (email/username ILIKE; returns role, active, plan, balances, expiry, created, last login, recording count); `POST /users {email, username?, password, role?}`; `GET /users/{id}`; `PATCH /users/{id} {email?, username?, is_active?}` (disable revokes sessions); `PUT /users/{id}/role {role}` (SUPERADMIN only); `POST /users/{id}/password {new_password}` (revokes sessions); `DELETE /users/{id}` body `{confirm_email}` |
| Quota/plan | `POST /users/{id}/tokens {delta, reason}`; `PATCH /users/{id}/plan {plan_tier?, token_quota_total?, daily_char_limit?, plan_expires_at?, reset_daily_remaining?}` |
| API keys | `GET /users/{id}/api-keys` (prefix, name, env, created, last used, revoked; never hashes); `POST /users/{id}/api-keys/{key_id}/revoke` |
| Recordings (read-only + delete) | `GET /users/{id}/recordings?search=&voice_id=&status=&page=` (incl. FAILED with `error_code`, presigned audio); `DELETE /recordings/{id}` |
| System dictionaries | `GET /system-dictionaries`; `POST /system-dictionaries` (create, or JSON body upload of `vieneu-dictionary/1`); `PATCH /system-dictionaries/{id} {name?, kind?, is_enabled?, description?, sort_order?}`; `DELETE /system-dictionaries/{id}`; `GET /{id}/rules?search=&page=`; `PUT /{id}/rules` (replace-all, `If-Match` etag, fields incl. `rule_kind`, `note`); `POST /{id}/import?format=json\|txt&mode=merge\|replace` (multipart, 1 MB); `GET /{id}/export?format=json\|txt` |
| Voices | `GET /voices` (incl. inactive); `PATCH /voices/{id} {name?, gender?, region?, tags?, language_label?, is_active?, sort_order?}`; `PUT /voices/{id}/avatar` (png/jpg/webp <= 1 MB) and `DELETE`; `PUT /voices/{id}/sample` (mp3/wav <= 5 MB); `POST /voices/{id}/sample/render {text?}` (engine render, same function as the CLI) |
| Audit | `GET /audit-log?actor=&action=&target_type=&target_id=&from=&to=&page=` (read-only; no update/delete endpoint exists) |

- Audit row: action (`user.create`, `user.disable`, `user.role_change`, `user.password_reset`, `user.delete`, `user.tokens_adjust`, `user.plan_update`, `api_key.revoke`, `recording.delete`, `sysdict.*`, `voice.*`), actor, target, `before`/`after` with changed fields only; never passwords or hashes; token adjustments record delta, reason, resulting balance.
- User delete: collect the user's object keys, delete the row (FK cascades recordings, rules, keys, sessions), commit, then delete objects best effort; audit keeps email in `target_label`.
- Uploads: size cap before full read; type by magic bytes, not filename; stored under `voices/avatars/<id>.<ext>`, `voices/samples/<id>.mp3|wav`.

## Related code files
Create: `src/vieneu_portal/admin_api/admin_permission_matrix.py`, `admin_api/routes_admin_users.py`, `admin_api/routes_admin_user_quota_and_plan.py`, `admin_api/routes_admin_user_keys_and_recordings.py`, `admin_api/routes_admin_system_dictionaries.py`, `admin_api/routes_admin_voices.py`, `admin_api/routes_admin_audit_log.py`, `admin_services/token_and_plan_adjustment_service.py`, `admin_services/user_deletion_service.py`, `admin_services/voice_catalog_admin_service.py`, `admin_services/upload_type_sniffing.py`; tests `tests/portal/test_admin_api_role_matrix.py`, `test_admin_api_users.py`, `test_admin_api_tokens_and_plan.py`, `test_admin_api_keys_and_recordings.py`, `test_admin_api_system_dictionaries.py`, `test_admin_api_voices.py`, `test_admin_api_audit_log.py`.
Modify: `src/vieneu_portal/app.py` (register admin routers), `tests/portal/test_quota_atomic_charge.py` (allow-list adds `token_and_plan_adjustment_service.py`).

## Implementation steps
1. Permission matrix + route-enumeration test (USER -> 403 on every admin route; ADMIN -> 403 on SUPERADMIN-only routes and on non-USER targets).
2. Users routes on phase 5 services; guards tests over HTTP (last superadmin, self-demotion, self-delete).
3. Token/plan service + concurrency test (adjust racing with generate never yields negative balance).
4. Keys and recordings routes reusing phase 10 query/serializer.
5. System dictionary routes on phase 5 store; JSON and txt import/export round-trip; `ENGLISH_FALLBACK` rules round-trip as `mode: "en"`.
6. Voice routes: edit, avatar/sample upload with sniffing, render sample; edited row survives `voices sync`.
7. Audit log route; test every mutation endpoint writes exactly one row with no secret fields.

## Todo
- [ ] matrix  - [ ] users  - [ ] tokens/plan  - [ ] keys/recordings  - [ ] system dicts  - [ ] voices  - [ ] audit  - [ ] tests

## Success criteria
- All admin API tests green on real Postgres + MinIO; route-enumeration test covers 100% of `/api/v1/admin` routes.
- Old-admin parity checklist (list/create/disable/reset/role, dictionary CRUD/import/export) satisfied.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Privilege escalation via role edits | L x H | SUPERADMIN-only role route; target-role check; guards lock rows |
| Audit gaps | M x M | One writer function in the same transaction; per-endpoint test |
| Malicious uploads (SVG/HTML as avatar) | M x M | Magic-byte allow-list (png/jpg/webp, mp3/wav); served via presigned URL with fixed content type |

## Rollback
Unregister admin routers; CLI keeps working on the same services; audit rows remain.

## Security
Admin routes require session + role + CSRF; no impersonation feature; passwords and hashes never returned or audited; admin listening/viewing is not audited (open question 2).

## Next
Phase 14 builds the admin pages on this API.
