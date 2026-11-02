# Phase 12: Studio page and My Voices library page

## Context
- Studio UI/rules: master `vieneu_tts_user_specs.md:127-181`; spec `02_tts_studio_single_voice.md`; TC-03, TC-04 (banner text), TC-02 (violation message).
- Library UI: master `:274-302`; spec `04_voice_library_and_leaderboard.md` (My Voices part); TC-07.
- APIs: phase 10 (`/tts/generate`, `/tts/stream`, `/tts/recordings*`), phase 3 (`/voices`), phase 2 (profile `client_config`).
- PCM streaming playback reference: `client/client.html:91-102` (AudioContext + `resp.body.getReader()`).
- Shared counter functions: `portal-web/src/lib/text/character-count-and-token-estimate.ts` (phase 7, read-only here).

## Overview
Priority P1. The two user-visible C1 pages, plus the portal image's web build stage and the browser end-to-end suite.

## Requirements
Studio (`/studio/`, `?voice=<id>` preselects):
- Toolbar: voice selector pill (initials avatar, name, list from `/voices` with sample play), speed selector `0.5x 0.75x 1x 1.25x 1.5x 2.0x`, emotion pills `[Cười] [Thở dài] [Hắng giọng]` inserting `[cười]`, `[thở dài]`, `[hắng giọng]` at the caret (end of text when unfocused) and restoring caret after the tag, background-music dropdown disabled with "Sắp có" (C1 has no music catalog), `Tải tệp` (`.txt`, `.srt` cues stripped of index/timing, `.docx` via `mammoth` browser build), `Từ điển` link (C2 page; disabled until then), `?` help popover.
- Onboarding bar (master `:79-82`): `Bắt đầu` + `Đã xong N/4` from `onboarding_completed_steps`; expand arrow disabled with "Sắp có" (steps undefined, user decision); `Ẩn` sends `PATCH /user/profile {onboarding_hidden: true}`; hidden when `onboarding_hidden`.
- Dismissible math/chem banner (spec text; `localStorage`).
- Editor: textarea, placeholder per spec, `Chèn câu mẫu` (random from a list that includes the TC-04 sentence), drag-and-drop `.txt`.
- Counter pill `N ký tự · ~T token · còn D` from shared functions and profile (`daily_char_remaining`, `token_balance`, `client_config`); red + disabled `Tạo giọng nói` when `T > token_balance`, `N > daily_char_remaining`, or `N > tts_max_chars`.
- `Phát ngay`: POST `/tts/stream`, schedule PCM16 chunks on WebAudio; stop button; note that speed applies only to `Tạo giọng nói`.
- `Tạo giọng nói`: POST `/tts/generate`; 200 -> prepend recording, update quota cache from response; 202 -> poll `GET /tts/recordings/{id}` every 2 s (max 10 min) showing progress; errors mapped: `CONTENT_POLICY_VIOLATION` (red banner with category text), `402 *` (quota message), `TERMS_NOT_ACCEPTED` (reopen modal), `503` (retry later).
- Recent recordings: `GET /tts/recordings?limit=5`, count badge, refresh, cards (play/pause, one-line snippet, voice name + `V4` badge, `146.0s`, `HH:mm DD/MM/YYYY`), download button, `♪` button disabled (music mixing not in C1).

My Voices (`/voices/`):
- Header/subtitle per spec; search input (debounced 250 ms, server search), voice filter from `voices_used` (`Tất cả giọng` default), `+ Tạo mới` -> `/studio/`.
- Cards: play/pause, original text line, voice, language label, duration, date; download (`download_url`), delete with confirm dialog then refetch.
- Sticky footer `X trong số Y giọng nói` (`total_count`, `overall_count`) and `Tổng thời lượng: 293.3s` (`total_duration_seconds`, one decimal); "load more" pagination (20).
- Empty and error states.

Build/E2E:
- `docker/Dockerfile.portal` gains a `node:22` stage running `npm ci && npm run build`, copying `out/` to `WEB_DIST_DIR`.
- Playwright suite against the compose stack (CPU engine): signup -> TC-01 modal -> TC-03 tag insert + counter -> generate short text -> TC-07 search/filter footer numbers -> TC-09 subset (sidebar balance equals generate response quota and profile).

## Related code files
Create (under `portal-web/`): `src/app/(app)/studio/page.tsx` (replace placeholder), `src/components/studio/voice-selector-pill.tsx`, `speed-selector.tsx`, `emotion-tag-buttons.tsx`, `insert-text-at-caret.ts`, `text-file-import.ts`, `studio-text-editor.tsx`, `studio-counter-pill.tsx`, `studio-action-buttons.tsx`, `onboarding-progress-bar.tsx`, `pcm-stream-player.ts`, `recent-recordings-list.tsx`, `math-chem-feature-banner.tsx`, `use-generate-recording-mutation.ts`; `src/app/(app)/voices/page.tsx` (replace placeholder), `src/components/library/library-filter-bar.tsx`, `library-recording-card.tsx`, `library-summary-footer.tsx`, `use-recordings-library-query.ts`, `delete-recording-confirm-dialog.tsx`, `src/components/audio/single-active-audio-player.ts`; tests `insert-text-at-caret.test.ts`, `emotion-tag-buttons.test.tsx`, `studio-counter-pill.test.tsx`, `text-file-import.test.ts`, `library-summary-footer.test.tsx`; `e2e/playwright.config.ts`, `e2e/studio-and-library.spec.ts`.
Modify: `portal-web/package.json` (mammoth, @playwright/test), `portal-web/src/lib/i18n/messages-vi.ts`, `messages-en.ts`, `docker/Dockerfile.portal`, `Makefile` (`portal-test-e2e` runs Playwright too).

## Implementation steps
1. Caret insertion util + TC-03 tests (middle of sentence, no focus -> end, selection replaced, counter updates synchronously).
2. Counter pill with shared functions; tests for warning thresholds.
3. Voice/speed/toolbar, file import (txt/srt/docx), banner, sample text.
4. Stream player (port from `client/client.html`), generate mutation with polling and error mapping.
5. Recent list; My Voices page, filters, footer, delete; footer tests with API fixtures recorded from phase 10 response shapes (typed).
6. Dockerfile web stage; Playwright E2E; run lint/typecheck/vitest/E2E.

## Todo
- [ ] caret + TC-03  - [ ] counter  - [ ] toolbar/import/banner  - [ ] stream + generate  - [ ] recent list  - [ ] My Voices  - [ ] Dockerfile stage  - [ ] E2E

## Success criteria
- TC-03 component test and the Playwright flow (TC-01, TC-03, TC-07, TC-09 subset) green against the compose stack.
- One audio element plays at a time across lists.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| WebAudio autoplay policy blocks stream start | M x M | Create/resume `AudioContext` inside the click handler |
| Client counter differs from server charge | L x H | Shared vectors (phase 7); server is authority, response quota overwrites cache |
| E2E slow/flaky on CPU engine | M x M | Short texts; generous timeouts; E2E outside the fast test target |

## Rollback
Restore placeholders; backend unaffected.

## Security
Uploaded files parsed in-browser only (size cap 2 MB); presigned URLs never persisted in storage.

## Next
Phase 15 acceptance and docs. Runs in parallel with phase 13 (backend admin) and may overlap phase 14 (disjoint files; admin specs live in `e2e/admin-pages.spec.ts`, picked up by this phase's Playwright config without edits).
