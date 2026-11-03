# Phase 09: Per-account pronunciation dictionary API

## Context
- Endpoints: master `vieneu_tts_user_specs.md:757-758` (`GET/PUT /api/v1/dictionary`, `POST /dictionary/import`, `GET /dictionary/export`); table `pronunciation_rules` spec 08 `:152-165`.
- Pure functions from phase 7 (`dictionary_import_export_and_merge.py`, matcher, `compile_rules`); system layer store from phase 5 (`dictionaries/system_dictionary_store.py`); moderation provider and `build_engine_text` from phase 8.
- Dictionary UI and live preview are C2; this phase is backend only.

## Overview
Priority P1. CRUD-by-replacement for one account's rule table (max 2000), file import with TC-14 merge semantics, export, and the rule loader used by synthesis.

## Requirements
| Method path | Behavior |
|---|---|
| `GET /dictionary` | `{rules: [...ordered], max_rules: 2000, etag}`; rule fields `id, source_term, phonetic_replacement, match_whole_word, case_sensitive, is_enabled, sort_order` |
| `PUT /dictionary` + `If-Match: <etag>` | body `{rules: [...]}` replaces the whole table in one transaction; `sort_order` = list index; validation per phase 7; every changed target moderated (phase 8 provider) -> `422 CONTENT_POLICY_VIOLATION` with index + category, `503 MODERATION_UNAVAILABLE` when fail-closed provider is down; `412 DICTIONARY_CHANGED` on etag mismatch; `422 DICTIONARY_LIMIT_EXCEEDED` / `422 INVALID_RULE` (with index + reason) / `422 DUPLICATE_SOURCE` |
| `POST /dictionary/import?dry_run=bool` multipart `file` (.txt/.csv, <= 1 MB, UTF-8) | parse + merge onto stored rules; `dry_run=true` returns merged list without saving (for unsaved-table UI in C2); response `{rules, imported_count, replaced_count, errors: [{line, reason}], etag}` |
| `GET /dictionary/export?format=txt\|csv` | attachment `vieneu-dictionary.<ext>`, `source = target` lines (both extensions use the spec line format) |

- `load_rules_for_synthesis(session, user_id) -> CompiledRuleSet`: the account's enabled rules (layer `ACCOUNT`, table order), then enabled rules of enabled system packs by pack `sort_order` (layer `SYSTEM` or `ENGLISH_FALLBACK` from `rule_kind`); the matcher applies precedence (longest, then account > system > fallback). The system layer is loaded and compiled once per process and cached by a version key (`count(*)`, `max(updated_at)` over `system_dictionaries`), so admin edits take effect on the next request without reloading ~850+ rules each time. Used by phase 10 and the phase 5 `text preview` CLI.
- Routes run `build_engine_text` / matching through `run_in_threadpool` so large inputs never block the event loop.
<!-- Updated: Red Team 2026-11-02 - rule targets moderated; system layer cache; threadpool -->
- Note: the moderation provider and compiled rule set come from phases 8 and 5, hence the dependency on both.
- All queries filter by `user_id` from the session (no id in URL, so no IDOR surface).

## Architecture
`etag = sha256(json of ordered rule tuples)`. Import = read stored rules -> `parse_dictionary_import` -> `merge_imported_rules` -> same save path as PUT (single code path for validation and limits).

## Related code files
Create: `src/vieneu_portal/dictionaries/account_dictionary_store.py`, `dictionaries/routes_account_dictionary.py`, `dictionaries/rules_for_synthesis_loader.py`, `dictionaries/system_rule_layer_cache.py`, `tests/portal/test_account_dictionary_api.py`, `tests/portal/test_rules_for_synthesis_loader.py`.
Modify: `src/vieneu_portal/app.py` (register router).

## Implementation steps
1. Store: list, replace-all (DELETE + bulk INSERT in a transaction), etag.
2. Routes with CSRF on PUT/POST; multipart size guard before reading fully.
3. Loader combining layers with the cached system layer; test layer tagging, disabled pack/rule exclusion, cache invalidation after a pack edit, and end-to-end tie: account `VieNeu` overrides system `VieNeu` in `build_engine_text`.
3b. Target moderation on PUT and import (blocklisted target -> 422 with index; provider down -> 503; nothing saved).
4. API tests: TC-14 end to end (seed `VieNeu = Vi Nơi`, import file with `# comment`, `GPU = Gờ Pê U`, `VieNeu = Vi Nêu Mới` -> new rules top, old `VieNeu` gone, comment ignored); 2001 rules -> 422; stale etag -> 412; another user's rules invisible; export -> import round-trip identical.

## Todo
- [ ] store  - [ ] routes  - [ ] loader  - [ ] tests incl. TC-14 API

## Success criteria
- TC-14 API test green; round-trip export/import equal; loader tags layers correctly and account rules win equal-length ties.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Lost update across two tabs | M x M | `If-Match` etag, 412 |
| Large import blocks a worker | L x M | 1 MB / 5 000-line cap before parse |
| Non-UTF-8 files (Windows-1258 exports) | M x L | Reject with `422 FILE_NOT_UTF8` and a clear message |

## Rollback
Remove router; table remains empty for unaffected users.

## Security
Session + CSRF required; content-type and size checked; rule text stored as data, rendered escaped by React.

## Next
Phase 10 (synthesis uses loader); C2 builds the dictionary page on this API.
