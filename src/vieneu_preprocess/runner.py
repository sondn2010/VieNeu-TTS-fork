"""Render preprocessed chunks to one 48 kHz waveform.

Consecutive chunks that share voice, speed and temperature are synthesised in
one `tts.infer()` call; pauses inside a group travel as numeric `[x.xx]` tags
(the engine turns them into silence), pauses between groups are padded here
with `effective_pause = max(prev.pause_after_sec, next.pause_before_sec)`.

Speed is applied by resampling with soxr (a core dependency) and only when
`apply_speed` is set and `speed != 1.0`; no time-stretching. Tag pauses inside
a sped-up group are pre-scaled by `speed` so they keep their exact length.
"""
from __future__ import annotations

from itertools import groupby
from typing import Optional, Sequence

import numpy as np

from .exporters import boundary_pauses
from .types import Chunk

SAMPLE_RATE = 48_000
_SPEED_EPS = 1e-6


def pause_pad_samples(seconds: float, sample_rate: int = SAMPLE_RATE) -> int:
    return max(0, int(round(seconds * sample_rate)))


def _resample(wav: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or wav.size == 0:
        return wav
    import soxr

    return soxr.resample(wav, src_rate, dst_rate).astype(np.float32)


def change_speed(wav: np.ndarray, speed: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Play `wav` `speed` times faster (pitch follows, like a tape)."""
    if speed <= 0:
        raise ValueError(f"speed must be > 0, got {speed}")
    return _resample(wav, int(round(sample_rate * speed)), sample_rate)


def _to_mono_float32(wav) -> np.ndarray:
    arr = np.asarray(wav, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=0 if arr.shape[0] < arr.shape[-1] else -1)
    return arr.reshape(-1)


def render_chunks(chunks: Sequence[Chunk], tts, *, default_voice: Optional[str] = None,
                  apply_speed: bool = True) -> np.ndarray:
    """Synthesize `chunks` with `tts.infer(text, voice=..., temperature=...)`."""
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    engine_rate = int(getattr(tts, "sample_rate", SAMPLE_RATE) or SAMPLE_RATE)
    lead, after = boundary_pauses(chunks)
    indexed = list(enumerate(chunks))

    def key(item: tuple[int, Chunk]):
        c = item[1]
        return (c.voice_preset or default_voice, c.speed if apply_speed else 1.0, c.temperature)

    pieces: list[np.ndarray] = [np.zeros(pause_pad_samples(lead), dtype=np.float32)]
    for (voice, speed, temperature), group_iter in groupby(indexed, key=key):
        group = list(group_iter)
        stretch = apply_speed and abs(speed - 1.0) > _SPEED_EPS
        scale = speed if stretch else 1.0
        parts: list[str] = []
        for pos, (i, c) in enumerate(group):
            parts.append(c.text)
            if pos < len(group) - 1 and after[i] > 0:
                parts.append(f"[{after[i] * scale:.3f}]")  # engine tags accept ms precision
        text = " ".join(parts)
        try:
            wav = tts.infer(text, voice=voice, temperature=temperature)
        except Exception as e:
            raise RuntimeError(f"TTS failed on chunk {group[0][1].chunk_id}: {e}") from e
        wav = _resample(_to_mono_float32(wav), engine_rate, SAMPLE_RATE)
        if stretch:
            wav = change_speed(wav, speed)
        pieces.append(wav)
        pieces.append(np.zeros(pause_pad_samples(after[group[-1][0]]), dtype=np.float32))
    return np.concatenate(pieces).astype(np.float32, copy=False)
