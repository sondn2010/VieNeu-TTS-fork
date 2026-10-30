---
phase: 2
title: "Engine numeric pause tags"
status: pending
priority: P1
effort: "5h"
dependencies: [1]
---

# Phase 2: Engine numeric pause tags

## Goal

Make `[x.xx]` in input text produce exactly that much silence on the v3 Turbo path (batch and stream), and never be spoken on any other path.

## Context

- `normalize_to_chunks_v3_with_gaps` (`src/vieneu_utils/phonemize_text.py:354`) returns `gaps` as strings `para|sentence|minor`; `gaps_to_silence` (`src/vieneu_utils/core_utils.py:171`) maps them via `V3_GAP_SILENCE`.
- `VieNeuV3Turbo.infer` joins with `join_audio_chunks(..., silence_ps=gaps_to_silence(gaps))`; `infer_stream` pads with `pause_pad_samples(..., pauses[ci-1])` (`src/vieneu/v3turbo.py:617-697`). Both already accept a per-boundary seconds list, so no new audio code is needed.
- Unknown `[...]` spans are phonemized as text today (`_emotion_tag_token` returns `None`).
- Gradio calls `normalize_to_chunks_v3` (no gaps) — tags must be stripped there.

## Files to Create / Modify

- Modify: `src/vieneu_utils/core_utils.py` — `RE_PAUSE_TAG = re.compile(r"\[\s*(\d{1,2}(?:\.\d{1,3})?)\s*(?:s)?\s*\]")`, `PAUSE_TAG_MIN=0.0`, `PAUSE_TAG_MAX=5.0`, `split_pause_tags(text) -> (segments, pauses)`; `gaps_to_silence` accepts `float` entries and returns them unchanged.
- Modify: `src/vieneu_utils/phonemize_text.py` — in `normalize_to_chunks_v3_with_gaps`, split raw text on pause tags first, chunk each segment as today, and join segment results with the explicit float as the gap; `_merge_short_chunks` never merges across a float gap; `normalize_to_chunks_v3` and the legacy `normalize_to_chunks`/`phonemize_to_chunks` strip tags (replace with a sentence boundary).
- Modify: `src/vieneu/v3turbo.py` — leading tag (before the first chunk) yields/prepends silence; trailing tag appends silence; both batch and stream. No other change.
- Create: `tests/test_pause_tags.py`.

## Tasks & Steps

- [ ] Add `split_pause_tags` and the float-aware `gaps_to_silence`; values outside 0–5 s clamp, malformed tags such as `[abc]` are untouched (emotion handling keeps owning them).
- [ ] Rework `normalize_to_chunks_v3_with_gaps` as described; keep the return type `tuple[list[str], list[str | float]]` and document it.
- [ ] Two adjacent tags `[0.3] [0.5]` sum to one boundary (0.8 s). A tag inside `<en>…</en>` is left as text.
- [ ] Make the gaps-less entry points strip tags.
- [ ] Leading and trailing silence in `infer` and `infer_stream`.
- [ ] Tests (no model needed; use the chunker directly and a fake `_infer_chunks`):
  - untagged text: chunks and gaps identical to a snapshot taken before the change (regression);
  - `"Một. [0.6] Hai. [1.4] Ba."` → 3 chunks, gaps `[0.6, 1.4]`;
  - tag never appears in any chunk text or phoneme string;
  - short segments around a tag are not merged;
  - clamping, adjacent tags, leading and trailing tags, `<en>` guard;
  - `normalize_to_chunks_v3` strips tags.

## Verification

- `uv run pytest tests/test_pause_tags.py tests/test_utils.py tests/test_base_utils.py tests/test_engine_turbo.py -q`
- Manual: `uv run python -c "from vieneu import Vieneu; ..."` render `"Xin chào. [1.5] Tạm biệt."` and confirm a ~1.5 s gap in the waveform (silence run length printed).

## Risk / rollback

Medium: the chunker is shared by every v3 path. The snapshot regression test guards untagged text. Rollback: revert the phase commit; no data involved.
