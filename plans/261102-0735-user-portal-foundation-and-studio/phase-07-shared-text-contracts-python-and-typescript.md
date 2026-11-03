# Phase 07: Shared text contracts in Python and TypeScript, pinned by JSON vectors

## Context
- Algorithm reference: `07_pronunciation_dictionary_and_nlp.md:93-177` (single-pass longest match), parser `:179-186`; master `vieneu_tts_user_specs.md:540-556` (separator priority `=`, `→`, tab, `,`; 2000 cap).
- Acceptance: TC-12, TC-13, TC-14 in `09_qa_acceptance_criteria.md:23-25`. Counter rule: master `:177-180` says `text.length` (UTF-16 units); this plan deliberately overrides it with NFC code points (plan.md spec-conflict table).
- Existing protected-span idea: `src/vieneu_preprocess/lexicon_mapper.py:21` (`<en>`, `[...]`, `<|...|>` untouched).

## Overview
Priority P1. Three pure functions implemented twice (Python for server, TS for browser) and validated by the same JSON vectors: character count + token estimate, dictionary matcher, import parser + merge. Runs in parallel with phases 2 and 4.

## Key insights
- JS `string.length` counts UTF-16 units and Python `len` counts code points; NFD vs NFC Vietnamese doubles counts. Both sides count code points of the NFC string, and the matcher walks code points (`Array.from`) instead of the spec sample's UTF-16 indexing. Results equal the spec sample for every BMP input.
- `toLowerCase`/`lower()` can change length (`İ`, `ß`); compare the candidate slice only when both lowercased forms are equal, never rely on length after folding. Vectors include these.
- Protected spans (`[...]`, `<en>...</en>`, `<|...|>`) are copied verbatim, so a rule `cười` cannot break the emotion tag `[cười]` and targets like `<en>Apple</en>` are not rescanned.
- Separator: master-spec priority order (first `=` if any, else first `→`, else tab, else `,`), so `Hà Nội, Việt Nam = Ha Noi` splits at `=`.

## Requirements
- `count_chars(text) = len(NFC(text))`; `estimate_tokens(chars, rate_milli) = (chars * rate_milli + 999) // 1000` (integers only on both sides).
- Rule type carries `layer`: `ACCOUNT` (rank 0), `SYSTEM` (rank 1), `ENGLISH_FALLBACK` (rank 2; system rows with `rule_kind = ENGLISH_FALLBACK`).
- `compile_rules(rules) -> CompiledRuleSet`: sorted list plus an index keyed by the case-folded first code point (required, not optional), and `source_terms` for the phase 8 normalizer; immutable so callers can cache it. <!-- Updated: Red Team 2026-11-02 - index required, compiled set cacheable -->
- `apply_pronunciation_rules(text, compiled)`: input NFC; enabled rules with non-empty trimmed source; stable sort by (source length in code points desc, layer rank asc, list order asc); at each position outside protected spans take the first matching rule (case and whole-word checks per spec, word char = Unicode `L*`, `N*` or `_`); emit target (`ENGLISH_FALLBACK` emits `<en>` + the matched text with its original casing + `</en>`), jump, no rescan.
- Precedence (user decision): longest match wins across the combined set; on equal length the account rule beats the system rule, which beats the English fallback; then list order (account table order, system pack order then entry order). This supersedes the earlier "system first" ordering.
- `<en>` interpretation (confirmed, Validation Session 1): an English term with a dictionary rule (account or system `REPLACE`) is read by that rule; otherwise a fallback-list term is wrapped in `<en>...</en>`; anything else is left for the engine.
- `parse_dictionary_import(text) -> (rules, errors)`: strip BOM, split `\r?\n`, trim, skip blank and `#` lines; split by priority separator; trim parts; empty side or length > 255 -> error with line number; defaults whole_word=true, case_sensitive=false, enabled=true; duplicate sources inside the file: last line wins.
- `merge_imported_rules(existing, imported)`: imported block first (file order), then existing minus conflicts. Conflict: equal ignoring case when either rule is case-insensitive, else exact equal. Result > 2000 -> `DICTIONARY_LIMIT_EXCEEDED` (no truncation).
- `validate_rule`: no newline/tab in either side; source must not contain `=` (export round-trip); lengths 1-255.
- `export_dictionary_txt(rules)`: `source = target` per line, UTF-8, `# exported` header; re-import round-trips exactly.

## Related code files
Create:
- Python: `src/vieneu_portal/text/character_count_and_token_estimate.py`, `text/pronunciation_rule_types.py`, `text/pronunciation_dictionary_single_pass_matcher.py`, `text/dictionary_import_export_and_merge.py`, `tests/portal/test_text_contract_vectors.py` (no DB needed).
- TS: `portal-web/package.json` (vitest + typescript only; phase 11 adds Next), `portal-web/tsconfig.json`, `portal-web/vitest.config.ts`, `portal-web/src/lib/text/character-count-and-token-estimate.ts`, `pronunciation-rule-types.ts`, `pronunciation-dictionary-single-pass-matcher.ts`, `dictionary-import-export-and-merge.ts`, `portal-web/src/lib/text/text-contract-vectors.test.ts`.
- Vectors: `tests/fixtures/text_contract_vectors/token_estimate_vectors.json`, `dictionary_matcher_vectors.json`, `dictionary_import_vectors.json`.

## Implementation steps
1. Write vectors first: TC-12 (`km`, `km/h`, `Tốc độ 5 km/h` -> `Tốc độ 5 ki lô mét trên giờ`), TC-13 (`A=AB`, `B=C`, `A` -> `AB`), TC-14 (`# comment`, `GPU = Gờ Pê U`, existing `VieNeu = Vi Nơi` + imported `VieNeu = Vi Nêu Mới` -> new rules on top, old removed), plus: whole-word inside longer word, case-sensitive miss, disabled rule, Vietnamese diacritics boundary (`Hà Nội` inside `Hà Nộii`), NFD input, emoji/astral chars, `[cười]` protected, `<en>` target not rescanned, `C++` and `.NET` sources, `İ`/`ß`, CRLF and BOM files, comma vs `=` priority, 2001-rule overflow, precedence vectors (account `VieNeu = Vi Nêu` beats system `VieNeu = Vi Nơi`; system `Apple = Ép-pồ` beats fallback `Apple`; fallback-only `Google` -> `<en>Google</en>`, `GOOGLE` keeps casing inside the tag; longer system `km/h` still beats shorter account `km`), token estimate rounding (0, 1, 999, 1000, 1001 chars with rates 1000/1500/333).
2. Python implementation until vectors pass; then TS until the same vectors pass.
3. Add `portal-web` vitest run to `make portal-test`.

## Todo
- [ ] vectors  - [ ] Python funcs  - [ ] TS funcs  - [ ] both test runners green  - [ ] Make target

## Success criteria
- Same vector files drive `pytest tests/portal/test_text_contract_vectors.py` and `vitest run`; both green; no vector is skipped on either side.
- Matcher checks only rules indexed under the current folded code point; benchmark: 20 000-char text with 2 000 account + 848 seed + 10 000 synthetic system rules completes < 200 ms in Python (generous bound), and `compile_rules` for that set < 500 ms.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Python/TS drift later | M x H | Vectors are the contract; any change requires a vector first |
| Performance with 2000 account + large system packs | M x M | Required first-code-point index; system layer compiled once and cached (phase 9); `SYSTEM_RULES_MAX` cap (phase 5); benchmark test |
| Fallback `<en>` wrapping of common words that are also Vietnamese-readable | M x M | Fallback only from curated system packs; admins edit/disable entries (phase 14); `<en>` interpretation confirmed |

## Rollback
Pure additive modules; delete them.

## Security
Parsing caps: max file 1 MB, max 5 000 lines before merge; no regex built from user input (literal comparison only), so no ReDoS.

## Next
Phase 8 (pipeline), phase 9 (dictionary API), phase 11/12 (web counter, C2 preview).
