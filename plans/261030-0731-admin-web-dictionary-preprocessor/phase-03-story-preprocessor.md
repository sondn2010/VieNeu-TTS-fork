---
phase: 3
title: "Story preprocessor, runner and CLI"
status: pending
priority: P1
effort: "13h"
dependencies: [1]
---

# Phase 3: Story preprocessor, runner and CLI

## Goal

Implement the five-stage, rule-based pipeline from `docs/tts-specs/tts-specs-v1.md` behind the phase 1 contract, plus a runner that turns JSON chunks into audio and a batch CLI.

## Files to Create / Modify

All under `src/vieneu_preprocess/` except tests. Do not edit `__init__.py` signatures or `types.py` fields (phase 1); only replace the stub bodies in `__init__.py`.

- Create: `config/pause_rules.yaml` — every duration from spec §4.2 (P-01…P-14), the countdown ladder, §4.3 emotion/speed table, thresholds (12/18/35 words, 4-word short sentence, 3-run countdown), trigger keyword lists, and the drop-cap opener list.
- Create: `rules.py` — load and validate the YAML into a frozen dataclass; cached per path.
- Create: `sanitizer.py` — stage 1: strip chapter metadata lines (word count, reading time, CSV-ish rows), Unicode NFC, unify quotes `“ ” « »` → `"`, dashes `–`/`--` → `—`, ellipsis `…` → `...`, drop-cap recovery (spec §2 row 1: lowercase or onset-less first word of a chapter is repaired from the opener list, e.g. `ặt nước` → `Mặt nước`, `hi ông` → `Khi ông`; also re-joins a lone capital letter line with the next word).
- Create: `dialogue_parser.py` — stage 2: classify segments into narration, dialogue, shout, inner_voice, embedded_quote; handle Vietnamese–French `"…" — Tên` and English–American `"…," tag. "…"` (split-dialogue linker, spec §2 row 5); telepathy detector (§2 row 2: colon after `trong tâm trí`/`trong đầu` cue, interjected `, chiếc nón thì thầm.`, first/second-person openers `Tôi`, `Con`, `Chà,`, `Đúng vậy,`); embedded-quote guard (§2 row 6); speaker attribution from the dialogue tag (name or title before the verb), falling back to the last known speaker for split dialogue.
- Create: `prosody_annotator.py` — stage 3: rules P-01…P-14 (soft `...` vs hard `[x]` per §4.1), progressive countdown ladder (§2 row 3), §4.3 emotion tags and speed, shout handling (§2 row 4: pause before/after, `"Họ, Tên!"` → `Họ... [0.25] Tên!`).
- Create: `lexicon_mapper.py` — stage 4: apply `LexiconEntry` list (longest term first, whole-word with Unicode-aware boundaries, case rules, skip inside existing `<en>…</en>` and `[…]`); `mode="en"` wraps in `<en>`; ALL-CAPS words of 4+ letters not in the lexicon → Title Case before G2P.
- Create: `exporters.py` — stage 5: mode 1 script text (speaker labels, `// Phân cảnh N` comments on `***`) and mode 2 JSON (spec §5.3 keys); `to_tagged_text` joins chunk texts with `[pause]` tags and drops speaker labels.
- Create: `runner.py` — `render()`: group consecutive chunks by voice and speed, call `tts.infer(text, voice=…)`, apply `librosa.effects.time_stretch(rate=speed)` only when `speed != 1.0` and `apply_speed`, join with exact `pause_after_sec`/`pause_before_sec` using `pause_pad_samples` semantics; returns 48 kHz float32.
- Create: `cli.py` — `vieneu-preprocess INPUT [--out DIR] [--format script|json|both] [--dict FILE ...] [--render --voice NAME]`; INPUT may be a `.md`/`.txt`/`.html` file or a directory (batch, one output per chapter). `.html` input goes through a tag stripper that keeps the drop-cap span text.
- Modify: `__init__.py` — replace stubs with calls into the stages.
- Create: `tests/fixtures/preprocess/dracaena_input.md` (spec §5.1 verbatim) and `tests/fixtures/preprocess/ash_land_sample.md` (a short dash-heavy passage written for the test, not copied from the external site).
- Create: `tests/test_preprocess_sanitizer.py`, `tests/test_preprocess_dialogue.py`, `tests/test_preprocess_prosody.py`, `tests/test_preprocess_lexicon.py`, `tests/test_preprocess_end_to_end.py`, `tests/test_preprocess_runner.py` (fake TTS returning fixed-length tones).

## Tasks & Steps

- [ ] YAML + loader; every number in spec §4.2/§4.3 comes from YAML, none hard-coded.
- [ ] Stage 1 with tests for each normalization and both drop-cap cases.
- [ ] Stage 2 with tests for the six spec §2 edge cases.
- [ ] Stage 3 with one test per rule code P-01…P-14 and the countdown ladder.
- [ ] Stage 4 with tests for longest-match, case, `<en>`, guard regions, caps-to-title.
- [ ] Stage 5 + `to_tagged_text`; end-to-end test on the §5.1 fixture asserts the §5.2 structure: speakers in order (Người dẫn, Nón Phân Loại, …, McGonagall, Nón Phân Loại), countdown pauses `0.6, 0.85, 1.1, 1.4`, `GRYFFINDOR` → `Gryffindor` (or seeded phonetic) with `[0.5]` before and `[0.9]` after, drop-cap `Mặt nước`.
- [ ] Performance test: a 5 000-word chapter preprocesses in under 20 ms median on CI hardware (assert < 100 ms to avoid flakiness; log the real number).
- [ ] Runner with fake TTS: total length equals audio plus pauses within 1 frame; speed 1.0 skips stretching.
- [ ] CLI on a temp directory of two chapters produces both outputs.

## Verification

- `uv run pytest tests/test_preprocess_*.py -q`
- `uv run vieneu-preprocess tests/fixtures/preprocess/dracaena_input.md --format both --out <scratch>` and read the script output.

## Risk / rollback

Medium: heuristics will misfire on unseen prose. Keep every threshold in YAML so tuning needs no code change. The API path is opt-in, so existing clients are unaffected. Rollback: revert the phase commit.
