# Phase 02: Auth (self-signup, sessions, CSRF) and user profile

## Context
- Reuse (move, not copy): scrypt hashing, timing equalizer, session token, CSRF signer, login limiter in `src/vieneu_admin/security.py:17-169`. Phase 6 deletes the original.
- Profile contract: master spec `vieneu_tts_user_specs.md:716-717` (`GET /api/v1/user/profile`, `POST /api/v1/user/terms/accept`); terms persistence fields `01_terms_and_ai_moderation.md:61-64`.

## Overview
Priority P1. Email + password self-signup, server-side sessions in Postgres, CSRF for the SPA, profile read/update, terms acceptance.

## Key insights
- Same-origin SPA: HttpOnly `SameSite=Lax` cookie + double-submit CSRF header (`X-CSRF-Token`) on every non-GET. No JWT, no CORS.
- Migrated SQLite password hashes use the same `scrypt$n$r$p$salt$hash` format, so moving the module keeps them verifiable (phase 5 relies on this).
- Login limiter is per process (in memory); with N workers the effective limit is N x 5. Acceptable for C0; documented.

## Requirements
Endpoints (all JSON, `/api/v1`):
| Method path | Behavior |
|---|---|
| `POST /auth/signup` `{email, password, username?}` | 201; normalizes email (strip, lower); password 10-256 chars; username defaults to email local part; trial quotas from settings; `plan_expires_at = now + TRIAL_DAYS`; `avatar_initials` from username; starts session. `409 EMAIL_TAKEN` |
| `POST /auth/login` `{email, password}` | 200 + session; `401 INVALID_CREDENTIALS` (same message for unknown email); `429 LOGIN_LOCKED` with `retry_after`; inactive user -> 401 |
| `POST /auth/logout` | deletes session row, clears cookie |
| `GET /auth/csrf` | returns CSRF token bound to session (or anonymous nonce cookie for signup/login) |
| `GET /user/profile` | id, email, username, avatar_initials, plan_tier, token_balance, token_quota_total, daily_char_limit, daily_char_remaining (lazily reset view), plan_expires_at, has_accepted_tts_terms, terms_version, onboarding fields, ui_theme, ui_language, role, plus `client_config {tokens_per_char_milli, tts_max_chars, tts_sync_char_cap, terms_version}` |
| `PATCH /user/profile` `{username?, ui_theme?, ui_language?, onboarding_hidden?}` | validated enums (`dark`/`light`, `vi`/`en`); `onboarding_completed_steps` is read-only here |
| `POST /user/terms/accept` `{terms_version}` | sets flag, `terms_accepted_at`, `terms_version`, `terms_accepted_ip`; version must equal settings `TERMS_VERSION` else 409 |

`has_accepted_tts_terms` is reported false when the stored `terms_version` differs from the current one (policy update re-prompts).

## Architecture
`require_user` dependency: cookie -> sha256 -> `user_sessions` join `users` where `expires_at > now()` and `is_active`; sliding renewal at most once per hour. `require_csrf` on mutating routes. Role dependencies `require_admin` (ADMIN or SUPERADMIN) and `require_superadmin` live here; phase 13 uses them. Login updates `last_login_at`. Session lookup re-reads `role` and `is_active` on every request, so demotion or disable takes effect immediately.

## Related code files
Create: `src/vieneu_portal/security/password_hashing.py`, `security/session_tokens_and_csrf.py`, `security/login_failure_limiter.py`, `auth/session_dependencies.py`, `auth/routes_auth_signup_login_logout.py`, `user/routes_user_profile_and_terms.py`, `user/user_profile_serializer.py`, `tests/portal/test_auth_signup_login_logout.py`, `tests/portal/test_user_profile_and_terms.py`, `tests/portal/test_security_primitives.py` (ported from `tests/test_admin_security.py` cases).
Modify: `src/vieneu_portal/app.py` (register routers).

## Implementation steps
1. Move security primitives into `security/*` with identical algorithms; port their unit tests.
2. Session service: create (random token, store hash, csrf nonce), resolve, renew, delete, delete-all-for-user (reused by admin disable/reset/delete).
2b. Role dependencies + tests: USER gets 403 `FORBIDDEN_ROLE` on an admin-guarded probe route; demoted admin loses access on the next request.
3. Signup/login/logout routes with limiter keyed `(email, client_ip)`; respect `FORWARDED_ALLOW_IPS` via uvicorn proxy headers.
4. Profile serializer shared by profile route and later quota responses (phase 10 reuses `quota` subset).
5. Terms accept with IP capture.
6. Tests: signup happy path, duplicate email (case-insensitive), weak password, login lockout, CSRF missing -> 403, logout invalidates cookie, profile shows trial defaults, terms accept + version bump re-prompt.

## Todo
- [ ] security move  - [ ] sessions  - [ ] signup/login/logout  - [ ] profile GET/PATCH  - [ ] terms accept  - [ ] tests

## Success criteria
- All tests above green against real Postgres. DB contains only hashes of passwords and session tokens (test greps the row).
- Mutating request without CSRF header returns `403 CSRF_FAILED`.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Account enumeration via signup 409 | M x L | Accepted for self-signup UX; login stays uniform; limiter on signup too |
| Session fixation | L x H | New token on every login; old cookie ignored |
| Bot signups drain free trial tokens | M x M | Signup rate limit per IP; admins can disable accounts (phase 13). No email verification or reset-by-email (user decision); admins reset passwords |

## Rollback
Remove the routers from `app.py`; tables stay (baseline). No data migration involved.

## Security
scrypt N=2^14; constant-time compares; cookie `Secure` when `COOKIE_SECURE=1`; no password or token in logs; `username` length 1-100, stripped of control chars.

## Next
Phase 3 (storage, voices), phase 11 (web auth pages).
