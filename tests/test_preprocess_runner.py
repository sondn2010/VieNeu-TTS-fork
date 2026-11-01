"""Runner: grouping, exact pause padding, speed handling, sample-rate conversion, errors."""
import re

import numpy as np
import pytest

import vieneu_preprocess.runner as runner
from vieneu_preprocess import Chunk, PreprocessResult, render

SR = 48_000
TONE = 4_800  # samples of "speech" per text segment
_TAG = re.compile(r"\[(\d+(?:\.\d+)?)\]")


class FakeTTS:
    """Returns a fixed-length tone per text segment and exact silence for `[x.xx]` tags."""

    def __init__(self, sample_rate=SR, fail=False):
        self.sample_rate, self.fail, self.calls = sample_rate, fail, []

    def infer(self, text, voice=None, temperature=0.8, **_):
        if self.fail:
            raise RuntimeError("engine down")
        self.calls.append((text, voice, temperature))
        out = []
        for i, part in enumerate(_TAG.split(text)):
            if i % 2:
                out.append(np.zeros(int(round(float(part) * self.sample_rate)), np.float32))
            elif part.strip():
                n = TONE * self.sample_rate // SR
                out.append(0.1 * np.sin(np.arange(n, dtype=np.float32)).astype(np.float32))
        return np.concatenate(out) if out else np.zeros(0, np.float32)


def C(i, text, *, voice=None, speed=1.0, before=0.0, after=0.0):
    return Chunk(f"c{i}", "Narrator", "narration", text, speed=speed, pause_before_sec=before,
                 pause_after_sec=after, voice_preset=voice)


def expected_len(chunks):
    total = int(round(chunks[0].pause_before_sec * SR))
    for i, c in enumerate(chunks):
        nxt = chunks[i + 1].pause_before_sec if i + 1 < len(chunks) else 0.0
        total += TONE + int(round(max(c.pause_after_sec, nxt) * SR))
    return total


def test_total_length_is_audio_plus_pauses():
    chunks = [C(1, "Một.", before=0.5, after=0.35), C(2, "Hai.", voice="B", after=0.2),
              C(3, "Ba.", voice="B", before=0.65, after=1.0), C(4, "Bốn.", after=0.4)]
    tts = FakeTTS()
    wav = render(PreprocessResult(chunks, ""), tts)
    assert wav.dtype == np.float32 and wav.ndim == 1
    assert abs(len(wav) - expected_len(chunks)) <= 1
    # Grouped by voice: chunks 2-3 share one call with the effective pause as a tag.
    assert [(t, v) for t, v, _ in tts.calls] == [("Một.", None), ("Hai. [0.650] Ba.", "B"), ("Bốn.", None)]


def test_default_voice_applies_to_unvoiced_chunks():
    tts = FakeTTS()
    render(PreprocessResult([C(1, "A."), C(2, "B.", voice="X")], ""), tts, default_voice="D")
    assert [v for _, v, _ in tts.calls] == ["D", "X"]


def test_speed_one_skips_resampling(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("change_speed must not run at speed 1.0")

    monkeypatch.setattr(runner, "change_speed", fail)
    wav = render(PreprocessResult([C(1, "A.", after=0.3)], ""), FakeTTS())
    assert len(wav) == TONE + int(0.3 * SR)


def test_apply_speed_false_ignores_speed(monkeypatch):
    monkeypatch.setattr(runner, "change_speed", lambda *a, **k: pytest.fail("speed applied"))
    tts = FakeTTS()
    render(PreprocessResult([C(1, "A.", speed=0.9), C(2, "B.", speed=1.1)], ""), tts, apply_speed=False)
    assert len(tts.calls) == 1  # same group once speed is ignored


def test_speed_changes_speech_but_keeps_pauses_exact():
    chunks = [C(1, "A.", speed=1.25, after=0.5), C(2, "B.", speed=1.25, after=0.25)]
    tts = FakeTTS()
    wav = render(PreprocessResult(chunks, ""), tts)
    assert tts.calls[0][0] == "A. [0.625] B."  # 0.5 * 1.25 pre-scaled
    expected = 2 * TONE / 1.25 + 0.5 * SR + 0.25 * SR
    assert abs(len(wav) - expected) <= 2  # resampling rounding only


def test_engine_sample_rate_is_converted_to_48k():
    wav = render(PreprocessResult([C(1, "A.")], ""), FakeTTS(sample_rate=24_000))
    assert abs(len(wav) - TONE) <= 2


def test_pause_pad_samples():
    assert runner.pause_pad_samples(0.35) == 16_800
    assert runner.pause_pad_samples(-1) == 0


def test_empty_and_errors():
    assert render(PreprocessResult([], ""), FakeTTS()).size == 0
    with pytest.raises(RuntimeError, match="c1"):
        render(PreprocessResult([C(1, "A.")], ""), FakeTTS(fail=True))
    with pytest.raises(ValueError):
        runner.change_speed(np.zeros(10, np.float32), 0)


def test_runner_does_not_use_librosa():
    src = open(runner.__file__, encoding="utf-8").read()
    assert "librosa" not in src and "time_stretch" not in src
