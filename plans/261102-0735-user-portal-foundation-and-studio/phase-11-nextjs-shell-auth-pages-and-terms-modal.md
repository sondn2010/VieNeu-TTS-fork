# Phase 11: Next.js shell, auth pages, design tokens, theme/language, Terms modal

## Context
- Design tokens and sidebar: master `vieneu_tts_user_specs.md:29-77`; `00_system_overview_and_ui_system.md`.
- Terms modal UI/logic: `01_terms_and_ai_moderation.md:13-64` (no close on backdrop/ESC, button disabled until checked, `localStorage` key `vieneu_tts_terms_v1_accepted`); TC-01.
- API: phase 2 (`/auth/*`, `/user/profile`, `/user/terms/accept`, CSRF header). `portal-web/` scaffold + `src/lib/text/*` from phase 7 (do not edit those files here).
- Static export is served by the portal (phase 1), same origin.

## Overview
Priority P1. Next.js (App Router, TypeScript, `output: "export"`, `trailingSlash: true`) SPA shell: login/signup, authenticated layout with sidebar, dark/light theme and VI/EN language, token balance widget, Terms modal. Runs in parallel with backend phases 3 and 8.

## Key insights
- Static export means no server components that fetch at request time and no Next middleware; auth guard is a client layout that calls `GET /user/profile` and redirects to `/login/` on 401.
- Server flag is authoritative for terms (version bump re-prompts); `localStorage` only prevents a flash before the profile loads.
- Dev: `next dev` with `rewrites` proxying `/api/*` to `http://localhost:8100` (rewrites are dev-only under export; prod is same origin anyway).

## Requirements
- Routes: `/login/`, `/signup/`, `/studio/` (placeholder until phase 12), `/voices/` (placeholder), `/` redirects to `/studio/`.
- Sidebar per spec groups (TẠO, THƯ VIỆN, TÀI KHOẢN) with icons; only `Phòng thu` and `Giọng nói` are live in C1, others rendered disabled with a "Sắp có"/"Soon" badge; footer: token widget `140.574 / 150.000` (vi-VN grouping, monospace), theme toggle, `VI`/`EN` selector, profile card (initials avatar, truncated email, plan label, logout).
- Sidebar shows a fourth group `QUẢN TRỊ` / `ADMIN` only for `ADMIN`/`SUPERADMIN` (links: Người dùng, Từ điển hệ thống, Giọng đọc, Nhật ký quản trị -> `/admin/users/`, `/admin/dictionaries/`, `/admin/voices/`, `/admin/audit-log/`; pages built in phase 14). Hiding is cosmetic; the API enforces roles.
- Floating support button (bottom-right) rendered disabled with a "Sắp có" tooltip (user decision: deferred).
- i18n provider also loads `messages-admin-vi.ts` / `messages-admin-en.ts`, created here as empty typed catalogs and owned by phase 14 afterwards (lets phases 12 and 14 run in parallel without touching the same catalog).
- Design tokens as CSS variables (dark default per spec colors; light theme counterpart); theme and language persisted via `PATCH /user/profile` and `localStorage` for first paint.
- i18n: typed message catalogs `vi`, `en`; no hard-coded UI strings in components.
- API client: `fetch` wrapper adding `X-CSRF-Token` (from `GET /auth/csrf`), `credentials: "same-origin"`, parsing the error envelope into a typed `ApiError(code, message, extra)`; React Query for profile cache.
- Terms modal: blocks interaction on `/studio/` while `has_accepted_tts_terms` is false; checkbox gates the button; accept -> `POST /user/terms/accept {terms_version}` -> set `localStorage` -> invalidate profile -> close. Failure keeps modal open with error text.

## Related code files
Create (all under `portal-web/`): `next.config.ts`, `eslint.config.mjs`, `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/(auth)/login/page.tsx`, `src/app/(auth)/signup/page.tsx`, `src/app/(app)/layout.tsx`, `src/app/(app)/studio/page.tsx` (placeholder), `src/app/(app)/voices/page.tsx` (placeholder), `src/styles/design-tokens.css`, `src/styles/globals.css`, `src/lib/api/api-client-with-csrf.ts`, `src/lib/api/api-error.ts`, `src/lib/api/use-user-profile-query.ts`, `src/lib/i18n/messages-vi.ts`, `src/lib/i18n/messages-en.ts`, `src/lib/i18n/messages-admin-vi.ts` (empty stub), `src/lib/i18n/messages-admin-en.ts` (empty stub), `src/lib/i18n/i18n-provider.tsx`, `src/components/support/disabled-support-chat-button.tsx`, `src/lib/theme/theme-provider.tsx`, `src/lib/format/vietnamese-number-and-date-format.ts`, `src/components/sidebar/app-sidebar.tsx`, `src/components/sidebar/sidebar-nav-groups.ts`, `src/components/sidebar/token-balance-widget.tsx`, `src/components/sidebar/user-profile-card.tsx`, `src/components/terms/terms-consent-modal.tsx`, `src/components/terms/terms-consent-modal.test.tsx`, `src/components/sidebar/token-balance-widget.test.tsx`, `src/lib/api/api-client-with-csrf.test.ts`, `vitest.setup.ts`.
Modify: `portal-web/package.json` (next, react, react-dom, @tanstack/react-query, lucide-react, testing-library, jsdom, eslint), `portal-web/vitest.config.ts` (jsdom env), `.gitignore` (`portal-web/node_modules`, `portal-web/out`, `.next`).

## Implementation steps
1. Add Next + deps; `npm run build` produces `out/`; set `WEB_DIST_DIR` to it in dev docs.
2. Tokens, globals, theme provider (class on `<html>`), i18n provider.
3. API client + profile query + auth pages (signup validation mirrors server: email, password >= 10).
4. Authenticated layout + sidebar + widgets.
5. Terms modal + tests: TC-01 (unchecked -> disabled; checked -> enabled; ESC/backdrop do nothing; accept posts version and stores key); widget formats `140574/150000` as `140.574 / 150.000`; admin nav group hidden for `USER`, shown for `ADMIN`/`SUPERADMIN`.
6. `npm run lint`, `tsc --noEmit`, `vitest run` wired into `make portal-test`.

## Todo
- [ ] deps/config  - [ ] tokens/theme/i18n  - [ ] api client  - [ ] auth pages  - [ ] layout + sidebar  - [ ] terms modal  - [ ] tests + Make wiring

## Success criteria
- TC-01 component test green; build output served by portal at `http://localhost:8100/studio/` after login.
- Lint, typecheck and tests clean.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Static export limits (dynamic routes, images) | L x M | No dynamic segments in C1; `images.unoptimized` |
| Flash of wrong theme/lang | M x L | Inline pre-hydration script reads `localStorage` |
| Next major-version API drift | M x M | Pin exact versions in `package.json`; lockfile committed |

## Rollback
Delete `portal-web/` app files (keep phase 7 `src/lib/text`); portal still serves the API.

## Security
No tokens in `localStorage` (cookie is HttpOnly); React escaping only, no `dangerouslySetInnerHTML`; CSRF header on all mutations.

## Next
Phase 12 fills Studio and My Voices.
