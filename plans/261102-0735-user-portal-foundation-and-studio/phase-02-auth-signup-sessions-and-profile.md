# Phase 02: Auth (self-signup, sessions, CSRF) and user profile

## Context
- Reuse (copy now, original deleted in phase 6 at the end of the plan): scrypt hashing, timing equalizer, session token, CSRF signer in `src/vieneu_admin/security.py:17-117`. The in-memory login limiter (`:119-169`) is replaced, not moved. The old admin keeps working until phase 6.
- Profile contract: master spec `vieneu_tts_user_specs.md:716-717` (`GET /api/v1/user/profile`, `POST /api/v1/user/terms/accept`); terms persistence fields `01_terms_and_ai_moderation.md:61-64`.

## Overview
Priority P1. Email + password self-signup, server-side sessions in Postgres, CSRF for the SPA, profile read/update, terms acceptance.

## Key insights
- Same-origin SPA: HttpOnly `SameSite=Lax` cookie + double-submit CSRF header (`X-CSRF-Token`) on every non-GET. No JWT, no CORS.
- Migrated SQLite password hashes use the same `scrypt$n$r$p$salt$hash` format, so moving the module keeps them verifiable (phase 5 relies on this).
- Limiter state lives in Postgres (`auth_throttle_events`), not process memory, so limits hold across uvicorn workers and restarts. The old in-memory `LoginLimiter` (`src/vieneu_admin/security.py:119-165`, failures only, keyed `(username, ip)`) is not moved.
- `CsrfSigner` keeps its algorithm but its secret comes from `SECRET_KEY` (derived key, label `csrf`) instead of the SQLite `meta` table (`src/vieneu_admin/store.py:52-57`), so tokens validate on every worker and survive restarts.
- Login identifier is a plain normalized string (strip + lower) looked up against `lower(email)`; no `EmailStr` on login, because migrated accounts use `@migrated.invalid` addresses that strict validators reject. Signup uses a simple syntax check (one `@`, non-empty parts, no whitespace) and rejects the `MIGRATION_EMAIL_DOMAIN`.
<!-- Updated: Red Team 2026-11-02 - shared limiter, stable secret, login lookup without strict email validation -->


## Requirements
Endpoints (all JSON, `/api/v1`):
| Method path | Behavior |
|---|---|
| `POST /auth/signup` `{email, password, username?}` | 201; `403 SIGNUP_DISABLED` when `SIGNUP_ENABLED=false`; normalizes email (strip, lower); rejects `MIGRATION_EMAIL_DOMAIN` (`422 EMAIL_DOMAIN_RESERVED`); password 10-256 chars; username defaults to email local part; trial quotas from settings; `plan_expires_at = now + TRIAL_DAYS`; `avatar_initials` from username; starts session. `409 EMAIL_TAKEN`; `429 SIGNUP_RATE_LIMITED` when successful signups exceed `SIGNUP_MAX_PER_IP_PER_HOUR` for the IP or `SIGNUP_MAX_GLOBAL_PER_HOUR` overall |
| `POST /auth/login` `{email, password}` | 200 + session; `401 INVALID_CREDENTIALS` (same message for unknown email); `429 LOGIN_LOCKED` with `retry_after` when failures exceed `LOGIN_MAX_FAILURES` per (email, IP) or `LOGIN_MAX_FAILURES_PER_IP` per IP across emails (stops password spraying); inactive user -> 401 |
| `POST /user/password` `{current_password, new_password}` | verifies current; 10-256 chars; revokes every other session of the user; wrong current -> `401 INVALID_CREDENTIALS` and counts as a login failure |
| `POST /auth/logout` | deletes session row, clears cookie |
| `GET /auth/csrf` | returns CSRF token bound to session (or anonymous nonce cookie for signup/login) |
| `GET /user/profile` | id, email, username, avatar_initials, plan_tier, token_balance, token_quota_total, daily_char_limit, daily_char_remaining (lazily reset view), plan_expires_at, has_accepted_tts_terms, terms_version, onboarding fields, ui_theme, ui_language, role, plus `client_config {tokens_per_char_milli, tts_max_chars, tts_sync_char_cap, terms_version}` |
| `PATCH /user/profile` `{username?, ui_theme?, ui_language?, onboarding_hidden?}` | validated enums (`dark`/`light`, `vi`/`en`); `onboarding_completed_steps` is read-only here |
| `POST /user/terms/accept` `{terms_version}` | sets flag, `terms_accepted_at`, `terms_version`, `terms_accepted_ip`; version must equal settings `TERMS_VERSION` else 409 |

`has_accepted_tts_terms` is reported false when the stored `terms_version` differs from the current one (policy update re-prompts).

## Architecture
`require_user` dependency: cookie -> sha256 -> `user_sessions` join `users` where `expires_at > now()`, `absolute_expires_at > now()` and `is_active`; sliding renewal at most once per hour, never past `absolute_expires_at` (`SESSION_ABSOLUTE_TTL_SEC`); ADMIN/SUPERADMIN sessions use `ADMIN_SESSION_IDLE_TTL_SEC` as the idle window. Expired sessions are purged on login and by the worker loop (phase 10). `require_csrf` on mutating routes. Role dependencies `require_admin` (ADMIN or SUPERADMIN) and `require_superadmin` live here; phase 13 uses them. Login updates `last_login_at`. Session lookup re-reads `role` and `is_active` on every request, so demotion or disable takes effect immediately.

## Related code files
Create: `src/vieneu_portal/security/password_hashing.py`, `security/session_tokens_and_csrf.py`, `security/postgres_auth_throttle.py`, `security/derived_secret_keys.py`, `user/routes_user_password_change.py`, `tests/portal/test_auth_throttle_and_signup_switch.py`, `auth/session_dependencies.py`, `auth/routes_auth_signup_login_logout.py`, `user/routes_user_profile_and_terms.py`, `user/user_profile_serializer.py`, `tests/portal/test_auth_signup_login_logout.py`, `tests/portal/test_user_profile_and_terms.py`, `tests/portal/test_security_primitives.py` (ported from `tests/test_admin_security.py` cases).
Modify: `src/vieneu_portal/app.py` (register routers).

## Implementation steps
1. Move scrypt hashing, timing equalizer, session token and CSRF signer into `security/*` with identical algorithms (CSRF secret from `SECRET_KEY` via `derived_secret_keys.py`); port their unit tests. Replace the in-memory login limiter with `postgres_auth_throttle.py`.
2. Session service: create (random token, store hash, csrf nonce, idle + absolute expiry), resolve, renew, delete, delete-all-for-user, delete-others-for-user (password change), purge-expired (reused by admin disable/reset/delete).
2b. Role dependencies + tests: USER gets 403 `FORBIDDEN_ROLE` on an admin-guarded probe route; demoted admin loses access on the next request.
3. Signup/login/logout and password-change routes with the Postgres throttle (keys `(email, client_ip)`, `client_ip`, global); client IP from uvicorn proxy headers only when the peer is in `FORWARDED_ALLOW_IPS`.
4. Profile serializer shared by profile route and later quota responses (phase 10 reuses `quota` subset).
5. Terms accept with IP capture.
6. Tests: signup happy path, duplicate email (case-insensitive), weak password, reserved migration domain, signup disabled, signup per-IP and global caps, login lockout per (email, IP) and per IP across emails (limits shared by two app instances on one DB), CSRF missing -> 403, CSRF token minted by one app instance accepted by another with the same `SECRET_KEY`, logout invalidates cookie, password change revokes other sessions, absolute expiry ends a renewed session, migrated-style `x@migrated.invalid` account logs in, profile shows trial defaults, terms accept + version bump re-prompt.

## Todo
- [ ] security move + derived keys  - [ ] Postgres throttle  - [ ] sessions (idle/absolute/purge)  - [ ] signup/login/logout  - [ ] password change  - [ ] profile GET/PATCH  - [ ] terms accept  - [ ] tests

## Success criteria
- All tests above green against real Postgres. DB contains only hashes of passwords and session tokens (test greps the row).
- Mutating request without CSRF header returns `403 CSRF_FAILED`.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Account enumeration via signup 409 | M x L | Accepted for self-signup UX; login stays uniform; limiter on signup too |
| Session fixation | L x H | New token on every login; old cookie ignored |
| Bot signups drain free trial tokens | M x M | Postgres-backed per-IP and global signup caps, `SIGNUP_ENABLED` switch, one in-flight synthesis per user (phase 10); admins can disable accounts (phase 13). No email verification or reset-by-email (user decision); users change their own password, admins reset forgotten ones |
| Wrong client IP behind a proxy (all clients share one IP) | M x M | Proxy headers honored only from `FORWARDED_ALLOW_IPS`; global caps bound damage either way; documented in phase 15 |

## Rollback
Remove the routers from `app.py`; tables stay (baseline). No data migration involved.

## Security
scrypt N=2^14; constant-time compares; cookie `Secure` when `COOKIE_SECURE=1`; no password or token in logs; `username` length 1-100, stripped of control chars.

## Next
Phase 3 (storage, voices), phase 11 (web auth pages).
