# Phase 14: Admin web pages (Next.js)

## Context
- API: phase 13 (`/api/v1/admin/*`). Shell, API client, design tokens, admin nav group and empty admin i18n catalogs: phase 11.
- Static export (no dynamic route segments): detail pages use query strings, e.g. `/admin/users/detail/?id=<uuid>`.
- Visual language: reuse spec tokens and components (cards, pills, tables) from `vieneu_tts_user_specs.md:29-77`; specs define no admin screens, so layouts below are the design.

## Overview
Priority P1. Admin area for `ADMIN`/`SUPERADMIN`: users, quotas, keys, recordings, system dictionaries, voices and audit log. Owns only `portal-web/src/app/(admin)/**`, `src/components/admin/**`, the admin i18n catalogs and `e2e/admin-pages.spec.ts`, so it can overlap phase 12.

## Requirements
- `(admin)/layout.tsx`: requires profile role `ADMIN`/`SUPERADMIN`, else redirect to `/studio/`; reuses the app sidebar.
- Users `/admin/users/`: search box, role/status filters, paginated table (email, username, role badge, active, plan, `balance / quota`, expiry, last login), `+ Tạo người dùng` dialog (email, username, password, role select shown only to SUPERADMIN).
- User detail `/admin/users/detail/?id=`: profile card with edit (email, username), enable/disable toggle, reset password dialog (new password twice), role select (SUPERADMIN only; disabled for self), delete (type email to confirm); quota card: token adjust (signed delta + required reason, shows resulting balance), plan form (tier, quota total, daily limit, expiry date, reset-daily checkbox); API keys table with revoke confirm; recordings table (search, voice, status incl. FAILED + error code, play, delete confirm).
- System dictionaries `/admin/dictionaries/`: pack list (name, kind, enabled toggle, rule count, order), create/rename/delete pack, import (`.json` new pack or into pack with merge/replace; `.txt/.csv` into pack), export (`json`/`txt`). Pack detail `/admin/dictionaries/detail/?id=`: editable rules table (source, replacement, kind `REPLACE`/`ENGLISH_FALLBACK`, whole word, case sensitive, enabled, note), add/delete rows, save with etag conflict message, local preview box using the phase 7 TS matcher on this pack's rules.
- Voices `/admin/voices/`: table incl. inactive; edit drawer (name, gender NAM/NU, region, tags chips, language label, sort order, active), avatar upload/remove with initials fallback preview, sample upload or `Tạo mẫu bằng engine` (render) with player.
- Audit log `/admin/audit-log/`: filters (actor, action, target type/id, date range), table with expandable before/after JSON (rendered as text, never HTML).
- All server errors shown via the shared `ApiError` mapping; guard errors (`LAST_SUPERADMIN`, `SELF_MODIFICATION`, `FORBIDDEN_ROLE`) get explicit Vietnamese/English messages.

## Related code files
Create (under `portal-web/`): `src/app/(admin)/layout.tsx`, `src/app/(admin)/admin/users/page.tsx`, `admin/users/detail/page.tsx`, `admin/dictionaries/page.tsx`, `admin/dictionaries/detail/page.tsx`, `admin/voices/page.tsx`, `admin/audit-log/page.tsx`; `src/components/admin/admin-api-hooks.ts`, `admin-users-table.tsx`, `create-user-dialog.tsx`, `user-profile-admin-card.tsx`, `reset-password-dialog.tsx`, `role-select-with-guards.tsx`, `delete-user-confirm-dialog.tsx`, `token-adjust-form.tsx`, `plan-edit-form.tsx`, `user-api-keys-table.tsx`, `user-recordings-admin-table.tsx`, `system-dictionary-pack-list.tsx`, `system-dictionary-rules-editor.tsx`, `system-dictionary-import-export-controls.tsx`, `voice-edit-drawer.tsx`, `voice-media-upload-controls.tsx`, `audit-log-table.tsx`; tests `role-select-with-guards.test.tsx`, `token-adjust-form.test.tsx`, `system-dictionary-rules-editor.test.tsx`, `admin-layout-guard.test.tsx`; `e2e/admin-pages.spec.ts`.
Modify: `portal-web/src/lib/i18n/messages-admin-vi.ts`, `messages-admin-en.ts`.

## Implementation steps
1. Admin layout guard + hooks over the phase 13 endpoints (React Query, invalidation per mutation).
2. Users list/detail with all dialogs and forms.
3. System dictionary list/detail with editor, import/export, preview.
4. Voices page with media uploads and render.
5. Audit log page.
6. Component tests: USER redirected away; role select disabled for self and hidden for ADMIN; token form requires reason and non-zero delta; rules editor marks etag conflict.
7. Playwright `admin-pages.spec.ts`: superadmin (created by CLI in test setup) creates a user, disables/enables, resets password (user logs in with new one), grants 1 000 tokens (user sidebar shows it), changes role, sees audit rows for each step; ADMIN cannot open role select and its create dialog has no role field (API also rejects a forged `role`); last-superadmin demotion shows the guard message; edits a voice name and the Studio voice list shows it; imports a txt into a system pack and exports it.

## Todo
- [ ] layout guard + hooks  - [ ] users  - [ ] dictionaries  - [ ] voices  - [ ] audit log  - [ ] component tests  - [ ] E2E

## Success criteria
- Component tests and `admin-pages.spec.ts` green; lint/typecheck clean; every admin API capability reachable from the UI.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| UI hides an action the API still allows (or vice versa) | M x M | API is the authority (phase 13 matrix tests); UI hiding is convenience only |
| Large rule tables (2 000+) sluggish | M x L | Paginated/virtualized table; save sends full list once |
| Destructive clicks | M x H | Typed-email confirm for delete; confirm dialogs for revoke/delete recording |

## Rollback
Remove `(admin)` routes and admin components; API and CLI remain.

## Security
No secrets rendered; before/after JSON shown as text; uploads validated server-side regardless of client checks.

## Next
Phase 15 acceptance and docs.
