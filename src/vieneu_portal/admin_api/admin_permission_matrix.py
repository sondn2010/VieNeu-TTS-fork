"""Single source of truth for every `/api/v1/admin` route's minimum role.

`test_admin_api_role_matrix.py` enumerates `app.routes`, asserts every
registered `/api/v1/admin` route has an entry here (method + exact path as
FastAPI registers it, with `{param}` placeholders), and then actually calls
each one — unauthenticated expects `401`, as a plain `USER` expects `403`,
and as `ADMIN` expects `403` for every `SUPERADMIN`-only entry. A new route
that forgets to add itself here fails the enumeration half of that test
immediately, so it can never ship silently unguarded.

This matrix only covers the *actor's own role* floor. The separate
"an ADMIN may only manage USER accounts" target-role rule is a service/route
-level check (`admin_shared_helpers.require_actor_can_manage_target`), not
expressible as a static per-route minimum, and is covered by its own tests.
"""
from __future__ import annotations

ADMIN = "ADMIN"
SUPERADMIN = "SUPERADMIN"

# (method, path exactly as registered with FastAPI, minimum role to pass `require_*`)
ADMIN_ROUTE_MIN_ROLE: tuple[tuple[str, str, str], ...] = (
    ("GET", "/api/v1/admin/users", ADMIN),
    ("POST", "/api/v1/admin/users", ADMIN),
    ("GET", "/api/v1/admin/users/{user_id}", ADMIN),
    ("PATCH", "/api/v1/admin/users/{user_id}", ADMIN),
    ("PUT", "/api/v1/admin/users/{user_id}/role", SUPERADMIN),
    ("POST", "/api/v1/admin/users/{user_id}/password", ADMIN),
    ("DELETE", "/api/v1/admin/users/{user_id}", ADMIN),
    ("POST", "/api/v1/admin/users/{user_id}/tokens", ADMIN),
    ("PATCH", "/api/v1/admin/users/{user_id}/plan", ADMIN),
    ("GET", "/api/v1/admin/users/{user_id}/api-keys", ADMIN),
    ("POST", "/api/v1/admin/users/{user_id}/api-keys/{key_id}/revoke", ADMIN),
    ("GET", "/api/v1/admin/users/{user_id}/recordings", ADMIN),
    ("DELETE", "/api/v1/admin/recordings/{recording_id}", ADMIN),
    ("GET", "/api/v1/admin/system-dictionaries", ADMIN),
    ("POST", "/api/v1/admin/system-dictionaries", ADMIN),
    ("PATCH", "/api/v1/admin/system-dictionaries/{dictionary_id}", ADMIN),
    ("DELETE", "/api/v1/admin/system-dictionaries/{dictionary_id}", ADMIN),
    ("GET", "/api/v1/admin/system-dictionaries/{dictionary_id}/rules", ADMIN),
    ("PUT", "/api/v1/admin/system-dictionaries/{dictionary_id}/rules", ADMIN),
    ("POST", "/api/v1/admin/system-dictionaries/{dictionary_id}/import", ADMIN),
    ("GET", "/api/v1/admin/system-dictionaries/{dictionary_id}/export", ADMIN),
    ("GET", "/api/v1/admin/voices", ADMIN),
    ("PATCH", "/api/v1/admin/voices/{voice_id}", ADMIN),
    ("PUT", "/api/v1/admin/voices/{voice_id}/avatar", ADMIN),
    ("DELETE", "/api/v1/admin/voices/{voice_id}/avatar", ADMIN),
    ("PUT", "/api/v1/admin/voices/{voice_id}/sample", ADMIN),
    ("POST", "/api/v1/admin/voices/{voice_id}/sample/render", ADMIN),
    ("GET", "/api/v1/admin/audit-log", ADMIN),
)
