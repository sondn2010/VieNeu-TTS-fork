# Phase 08: Moderation interface and math/chem normalization pipeline

## Context
- Moderation contract: `01_terms_and_ai_moderation.md:66-77` (5 categories, `422 CONTENT_POLICY_VIOLATION`, no token or daily-char charge, not counted as technical failure).
- Pipeline order: `07_pronunciation_dictionary_and_nlp.md:73-91` (raw -> moderation -> normalization -> dictionary -> engine); TC-04 `09_qa_acceptance_criteria.md:15`; examples master `:181`.
- Engine already normalizes plain numbers, dates and units (sea-g2p front-end), so the portal normalizer touches only math/chem spans.
- Matcher from phase 7; settings `MODERATION_*` from phase 1.

## Overview
Priority P1. Pluggable moderation (stubbed off by default, real blocklist provider for admins and tests), a deterministic rule-based math/chem normalizer, and `build_engine_text()` that composes the whole text path. No routes; phase 10 consumes it.

## Key insights
- ASCII `+ - * / < >` alone are ambiguous in prose (`2020-2021`, `km/h`, `A/B testing`). A span is math only with a strong marker: Unicode math symbol (`≥ ≤ ≠ ≈ ∈ ∉ ⊂ ∞ √ ± × ÷ Δ π ℝ ℕ ℤ ℚ`), a superscript, `^`, or `=` with operands on both sides.
- Chem: only formulas whose every symbol is a real element (periodic table list), inside an equation (`→`, `⇌`, or `=` between formulas) or a standalone token containing a digit (`H2O`, `CO2`). `A4`, `MP3` are untouched (no element `A`/`M`).
- The spec example reads digits inside spans as words (`= 0` -> `bằng không`, `2H2` -> `hai H hai`), so spans use a small Vietnamese integer reader (0-999 999); outside spans digits are left to the engine.
- Raw control tokens `<|...|>` in user input are stripped before anything else (the engine treats them as control codes).
- Element-symbol tokens collide with dictionary terms: `B2B`, `B2C` (`src/vieneu_admin/seed/business-finance.json:99,105`) and `F0`, `F1` (`src/vieneu_admin/seed/medical.json:393,400`) are all "formulas" by the element rule. Any token that equals an enabled dictionary source (account or system, case rules as in the matcher) is left for the dictionary and never normalized.
- Moderating only the original lets a user rule smuggle blocked text (`hoa = <blocked sentence>`). Moderation therefore runs on the original and again on the processed text; rule targets are also moderated when saved (phases 5, 9).
- Processed text can grow (math readings, phonetic replacements, `<en>` wraps) past the engine's 20 000-char input limit (`apps/openai_speech.py:488`) or amplify cost; it is capped here.
<!-- Updated: Red Team 2026-11-02 - dictionary sources protected from chem normalization; moderation of processed text; processed-length cap -->

## Requirements
- `ModerationProvider.check(text) -> ModerationVerdict(allowed, category, message_vi)`; categories `PROFANITY_SEVERE`, `SEXUAL_EXPLICIT`, `HATE_HARASSMENT`, `POLITICAL_SOVEREIGNTY`, `VIOLENCE_ILLEGAL`. The same `check` is used for dictionary rule targets on save/import (phases 5, 9), with the same fail mode.
- Providers: `off` (allow, debug log), `blocklist` (UTF-8 file `CATEGORY<TAB>term`, NFC + lowercase whole-word literal match). Factory by `MODERATION_PROVIDER`.
- Provider exception: `MODERATION_FAIL_MODE=closed` -> `ModerationUnavailable` (route maps to `503 MODERATION_UNAVAILABLE`); `open` -> allow + warning log.
- `POLITICAL_SOVEREIGNTY` hits log a security warning (user id, category, text length; never the text).
- `ContentPolicyViolation(category, message)` exception -> route maps to 422 with `{"error": {"code": "CONTENT_POLICY_VIOLATION", "category", "message"}}`.
- `normalize_math_and_chemistry(text) -> str`: readings `²` bình phương, `³` lập phương, other `ⁿ`/`^k` mũ k, `+` cộng, `-`/`−` trừ (inside math spans), `×`/`·` nhân, `÷` chia, `=` bằng, `≥` lớn hơn hoặc bằng, `≤` nhỏ hơn hoặc bằng, `≠` khác, `≈` xấp xỉ, `<` nhỏ hơn, `>` lớn hơn, `∈` thuộc, `∉` không thuộc, `ℝ` tập số thực, `ℕ` tập số tự nhiên, `ℤ` tập số nguyên, `ℚ` tập số hữu tỉ, `Δ` đen ta, `π` pi, `√` căn bậc hai của, `∞` vô cực, `±` cộng trừ; variable runs split (`ax²` -> `a x bình phương`); chem `→` tạo thành, `⇌` thuận nghịch, coefficients/subscripts as words.
- `normalize_math_and_chemistry(text, protected_terms)`: tokens in `protected_terms` (the compiled rule set's `source_terms`) are skipped.
- `build_engine_text(original, compiled_rules, moderation, settings) -> EngineText(processed_text, char_count, processed_char_count, estimated_tokens)`: NFC, strip `<|...|>`, moderation on the cleaned original, normalize (dictionary sources protected), apply combined rules (phase 7 precedence: longest, then account > system > English fallback), moderation on the processed text (same categories, same 422/503 mapping), then cap: `processed_char_count <= ENGINE_MAX_INPUT_CHARS` and `<= max(2 x char_count, char_count + 2000)`, else `TextTooLongAfterProcessing` (route maps to `422 TEXT_TOO_LONG_AFTER_PROCESSING`). Billing counts come from the original (not processed) text.

## Related code files
Create: `src/vieneu_portal/moderation/moderation_provider_interface.py`, `moderation/blocklist_moderation_provider.py`, `moderation/moderation_provider_factory.py`, `text/vietnamese_small_integer_reader.py`, `text/math_expression_normalizer.py`, `text/chemical_equation_normalizer.py`, `text/chemical_element_symbols.py`, `text/engine_text_pipeline.py`, `tests/fixtures/normalization_golden/math_chem_vi.json`, `tests/portal/test_math_chem_normalization_golden.py`, `tests/portal/test_moderation_providers.py`, `tests/portal/test_engine_text_pipeline.py`, `tests/fixtures/moderation_blocklist_sample.tsv`.

## Implementation steps
1. Golden file first. Must include TC-04 verbatim: `Giải phương trình ax² + bx + c = 0 với Δ ≥ 0, x ∈ ℝ và phản ứng 2H2 + O2 → 2H2O` -> `Giải phương trình a x bình phương cộng b x cộng c bằng không với đen ta lớn hơn hoặc bằng không, x thuộc tập số thực và phản ứng hai H hai cộng O hai tạo thành hai H hai O`. Negatives unchanged: `5 km/h`, `2020-2021`, `A4`, `MP3`, `COVID-19`, `A/B`, `[cười]`, `<en>H2O</en>`; with the seed packs loaded as protected terms: `B2B`, `B2C`, `F0`, `F1` (then read by their seed rules in the pipeline test).
2. Integer reader (`0`..`999 999`, Vietnamese `mươi/mốt/lăm/linh` rules), unit-tested.
3. Math span detector + reader; chem tokenizer + reader; protected spans skipped as in phase 7.
4. Moderation interface, providers, factory, fail-mode handling.
5. Pipeline composition and tests (order proven: rule targeting a normalized word applies; rule never sees `<|...|>`; counts from original; `B2B`/`F0` read by seed rules, not the chem reader; benign original + malicious account rule target -> `ContentPolicyViolation`; expansion over the cap -> `TextTooLongAfterProcessing`).

## Todo
- [ ] golden  - [ ] integer reader  - [ ] math  - [ ] chem  - [ ] moderation  - [ ] pipeline  - [ ] tests

## Success criteria
- Golden test green including TC-04 and all negatives; blocklist provider rejects a listed term in each category (in the original and when introduced by a rule); fail-closed raises, fail-open allows.
- `build_engine_text` is pure and DB-free (unit tests run without Postgres).

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| False positives in prose rewrite meaning | M x H | Strong-marker rule + negative goldens; any new pattern needs a golden pair |
| Spoken readings disputed by native listeners | M x M | Readings centralized in one table; user verifies by ear in phase 15 |
| Blocklist is weak moderation | H x M | Approved: provider stubbed off; interface ready for a real provider. Provider outage fails closed (user decision): 503, no charge |

## Rollback
Pure modules; pipeline can be bypassed by setting moderation `off` (normalizer has no flag; revert commit if needed).

## Security
Never log text bodies; strip control tokens; blocklist file path from deployment config only.

## Next
Phase 10 wires pipeline into generate/stream.
