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

## Requirements
- `ModerationProvider.check(text) -> ModerationVerdict(allowed, category, message_vi)`; categories `PROFANITY_SEVERE`, `SEXUAL_EXPLICIT`, `HATE_HARASSMENT`, `POLITICAL_SOVEREIGNTY`, `VIOLENCE_ILLEGAL`.
- Providers: `off` (allow, debug log), `blocklist` (UTF-8 file `CATEGORY<TAB>term`, NFC + lowercase whole-word literal match). Factory by `MODERATION_PROVIDER`.
- Provider exception: `MODERATION_FAIL_MODE=closed` -> `ModerationUnavailable` (route maps to `503 MODERATION_UNAVAILABLE`); `open` -> allow + warning log.
- `POLITICAL_SOVEREIGNTY` hits log a security warning (user id, category, text length; never the text).
- `ContentPolicyViolation(category, message)` exception -> route maps to 422 with `{"error": {"code": "CONTENT_POLICY_VIOLATION", "category", "message"}}`.
- `normalize_math_and_chemistry(text) -> str`: readings `²` bình phương, `³` lập phương, other `ⁿ`/`^k` mũ k, `+` cộng, `-`/`−` trừ (inside math spans), `×`/`·` nhân, `÷` chia, `=` bằng, `≥` lớn hơn hoặc bằng, `≤` nhỏ hơn hoặc bằng, `≠` khác, `≈` xấp xỉ, `<` nhỏ hơn, `>` lớn hơn, `∈` thuộc, `∉` không thuộc, `ℝ` tập số thực, `ℕ` tập số tự nhiên, `ℤ` tập số nguyên, `ℚ` tập số hữu tỉ, `Δ` đen ta, `π` pi, `√` căn bậc hai của, `∞` vô cực, `±` cộng trừ; variable runs split (`ax²` -> `a x bình phương`); chem `→` tạo thành, `⇌` thuận nghịch, coefficients/subscripts as words.
- `build_engine_text(original, system_rules, account_rules, moderation) -> EngineText(processed_text, char_count, estimated_tokens)`: NFC, strip `<|...|>`, moderation on the cleaned original, normalize, apply combined rules (phase 7 precedence: longest, then account > system > English fallback), compute counts from the original (not processed) text.

## Related code files
Create: `src/vieneu_portal/moderation/moderation_provider_interface.py`, `moderation/blocklist_moderation_provider.py`, `moderation/moderation_provider_factory.py`, `text/vietnamese_small_integer_reader.py`, `text/math_expression_normalizer.py`, `text/chemical_equation_normalizer.py`, `text/chemical_element_symbols.py`, `text/engine_text_pipeline.py`, `tests/fixtures/normalization_golden/math_chem_vi.json`, `tests/portal/test_math_chem_normalization_golden.py`, `tests/portal/test_moderation_providers.py`, `tests/portal/test_engine_text_pipeline.py`, `tests/fixtures/moderation_blocklist_sample.tsv`.

## Implementation steps
1. Golden file first. Must include TC-04 verbatim: `Giải phương trình ax² + bx + c = 0 với Δ ≥ 0, x ∈ ℝ và phản ứng 2H2 + O2 → 2H2O` -> `Giải phương trình a x bình phương cộng b x cộng c bằng không với đen ta lớn hơn hoặc bằng không, x thuộc tập số thực và phản ứng hai H hai cộng O hai tạo thành hai H hai O`. Negatives unchanged: `5 km/h`, `2020-2021`, `A4`, `MP3`, `COVID-19`, `A/B`, `[cười]`, `<en>H2O</en>`.
2. Integer reader (`0`..`999 999`, Vietnamese `mươi/mốt/lăm/linh` rules), unit-tested.
3. Math span detector + reader; chem tokenizer + reader; protected spans skipped as in phase 7.
4. Moderation interface, providers, factory, fail-mode handling.
5. Pipeline composition and tests (order proven: rule targeting a normalized word applies; rule never sees `<|...|>`; counts from original).

## Todo
- [ ] golden  - [ ] integer reader  - [ ] math  - [ ] chem  - [ ] moderation  - [ ] pipeline  - [ ] tests

## Success criteria
- Golden test green including TC-04 and all negatives; blocklist provider rejects a listed term in each category; fail-closed raises, fail-open allows.
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
