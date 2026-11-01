"""Numeric pause tags ``[x.xx]``: exact silence on the v3 Turbo path, never spoken anywhere.

No model is needed: the chunker is exercised directly and the v3 Turbo engine is
replaced by a fake ``_infer_chunks`` / ``_stream_chunks_engine`` that renders each
chunk as a short tone with no silent edges, so every zero sample in the output is
silence inserted by the pause logic.
"""
import re

import numpy as np
import pytest

from vieneu_utils.core_utils import (
    PAUSE_TAG_MAX,
    RE_PAUSE_TAG,
    V3_GAP_SILENCE,
    gaps_to_silence,
    split_pause_tags,
    strip_pause_tags,
)
from vieneu_utils.phonemize_text import (
    normalize_to_chunks,
    normalize_to_chunks_v3,
    normalize_to_chunks_v3_with_gaps,
    normalize_to_chunks_v3_with_pauses,
    phonemize_text_with_emotions,
    phonemize_to_chunks,
)

SR = 16_000
TONE_S = 0.2
_NUMERIC_BRACKET = re.compile(r"\[\s*\d")


# ─── Regression: text without pause tags is chunked exactly as before ─────────
# Snapshot taken from the chunker before pause tags existed (max_chars=128).
_SNAPSHOT = [
    (
        "Xin chào các bạn. Hôm nay trời đẹp quá!",
        ["xin chào các bạn. hôm nay trời đẹp quá!"],
        [],
        ["xin chào các bạn. hôm nay trời đẹp quá!"],
    ),
    (
        "Chương một.\nNgày xửa ngày xưa, có một cô bé sống trong rừng sâu cùng bà ngoại. "
        "Cô bé rất thích hái hoa, bắt bướm và hát ca.\nMột hôm, bà sai cô mang bánh sang làng bên.",
        [
            "chương một. ngày xửa ngày xưa, có một cô bé sống trong rừng sâu cùng bà ngoại. "
            "cô bé rất thích hái hoa, bắt bướm và hát ca.",
            "một hôm, bà sai cô mang bánh sang làng bên.",
        ],
        ["para"],
        [
            "chương một.",
            "ngày xửa ngày xưa, có một cô bé sống trong rừng sâu cùng bà ngoại. "
            "cô bé rất thích hái hoa, bắt bướm và hát ca.",
            "một hôm, bà sai cô mang bánh sang làng bên.",
        ],
    ),
    (
        'Anh ấy cười [cười] rồi nói: "Thế à? Được thôi." Sau đó [thở dài] anh bỏ đi.',
        ["anh ấy cười <|emotion_1|> rồi nói, thế à? được thôi. sau đó <|emotion_2|> anh bỏ đi."],
        [],
        ["anh ấy cười, cười, rồi nói, thế à? được thôi. sau đó, thở dài, anh bỏ đi."],
    ),
    (
        "Giá SP500 hôm nay là 4.200,5 điểm, tăng 3% so với hôm qua; nhà đầu tư lạc quan, "
        "nhưng giới phân tích vẫn thận trọng vì lạm phát còn cao và lãi suất có thể tiếp tục "
        "tăng trong quý tới, khiến thị trường biến động mạnh hơn dự kiến.",
        [
            "giá ét pê năm trăm hôm nay là bốn nghìn hai trăm phẩy năm điểm, tăng ba phần trăm "
            "so với hôm qua, nhà đầu tư lạc quan,",
            "nhưng giới phân tích vẫn thận trọng vì lạm phát còn cao và lãi suất có thể tiếp tục "
            "tăng trong quý tới,",
            "khiến thị trường biến động mạnh hơn dự kiến.",
        ],
        ["minor", "minor"],
        None,  # legacy output identical to the v3 chunks for this text
    ),
    (
        "Vâng.\nĐược.\nTôi hiểu rồi, cảm ơn anh rất nhiều vì đã giúp đỡ.",
        ["vâng. được. tôi hiểu rồi, cảm ơn anh rất nhiều vì đã giúp đỡ."],
        [],
        ["vâng.", "được.", "tôi hiểu rồi, cảm ơn anh rất nhiều vì đã giúp đỡ."],
    ),
    (
        "[abc] Văn bản có ngoặc lạ [x1] ở giữa.",
        ["[abc] văn bản có ngoặc lạ [x1] ở giữa."],
        [],
        ["abc, văn bản có ngoặc lạ, ích một, ở giữa."],
    ),
]


@pytest.mark.parametrize("text,chunks,gaps,legacy", _SNAPSHOT)
def test_untagged_text_matches_snapshot(text, chunks, gaps, legacy):
    assert normalize_to_chunks_v3_with_gaps(text, max_chars=128) == (chunks, gaps)
    assert normalize_to_chunks_v3_with_pauses(text, max_chars=128) == (chunks, gaps, 0.0, 0.0)
    assert normalize_to_chunks_v3(text, max_chars=128) == chunks
    assert normalize_to_chunks(text, max_chars=128) == (legacy if legacy is not None else chunks)
    assert strip_pause_tags(text) is text


# ─── split / strip helpers ────────────────────────────────────────────────────

def test_split_pause_tags_basic_and_formats():
    assert split_pause_tags("Một. [0.6] Hai. [1.4s] Ba.") == (["Một. ", " Hai. ", " Ba."], [0.6, 1.4])
    assert split_pause_tags("a [ 0.25 s ] b") == (["a ", " b"], [0.25])
    assert split_pause_tags("a [2] b") == (["a ", " b"], [2.0])
    assert split_pause_tags("không có thẻ") == (["không có thẻ"], [])
    assert split_pause_tags("") == ([""], [])


def test_split_pause_tags_clamps_to_max():
    assert split_pause_tags("a [9.5] b")[1] == [PAUSE_TAG_MAX]
    assert split_pause_tags("a [0.0] b")[1] == [0.0]
    assert split_pause_tags("a [3.0] [4.0] b")[1] == [PAUSE_TAG_MAX]      # sum clamped too


def test_split_pause_tags_adjacent_tags_sum_into_one_boundary():
    segments, pauses = split_pause_tags("A. [0.3] [0.5] B.")
    assert segments == ["A. ", " B."] and pauses == [pytest.approx(0.8)]
    segments, pauses = split_pause_tags("[0.3][0.2] A.")
    assert segments == ["", " A."] and pauses == [pytest.approx(0.5)]


def test_split_pause_tags_leaves_malformed_and_cue_tags():
    for text in ("Xin [abc] chào", "Cười [cười] nhé", "[x1] a", "[0.5.5] a", "[123] a", "[.5] a"):
        assert split_pause_tags(text) == ([text], []), text


def test_split_pause_tags_en_guard():
    text = "Nói <en>hello [0.5] world</en> nhé [0.4] xong."
    segments, pauses = split_pause_tags(text)
    assert pauses == [0.4]
    assert segments[0] == "Nói <en>hello [0.5] world</en> nhé "


def test_strip_pause_tags_inserts_sentence_boundary():
    assert strip_pause_tags("Một. [0.6] Hai. [1.4] Ba.") == "Một. Hai. Ba."
    assert strip_pause_tags("Xin chào [0.5] bạn") == "Xin chào. bạn"
    assert strip_pause_tags('Hỏi "thật à?" [0.5] Ừ.') == 'Hỏi "thật à?" Ừ.'
    assert strip_pause_tags("[1.0] Xin chào [0.5]") == "Xin chào."
    assert strip_pause_tags("[2.0]") == ""
    assert strip_pause_tags("Dòng một.\n[0.8]\nDòng hai.") == "Dòng một.\nDòng hai."


def test_gaps_to_silence_accepts_explicit_floats():
    assert gaps_to_silence(["para", 0.6, "minor", 1.4]) == [
        V3_GAP_SILENCE["para"], 0.6, V3_GAP_SILENCE["minor"], 1.4,
    ]
    assert gaps_to_silence(["sentence", "unknown"]) == [V3_GAP_SILENCE["sentence"]] * 2


# ─── Chunker with pause tags ──────────────────────────────────────────────────

def test_explicit_pauses_become_float_gaps():
    chunks, gaps, lead, tail = normalize_to_chunks_v3_with_pauses("Một. [0.6] Hai. [1.4] Ba.")
    assert len(chunks) == 3 and gaps == [0.6, 1.4] and (lead, tail) == (0.0, 0.0)


def test_short_chunks_around_tag_are_not_merged():
    # Without tags these short sentences merge into a single chunk (see the snapshot).
    chunks, gaps, _, _ = normalize_to_chunks_v3_with_pauses(
        "Ừ. [0.5] Vâng. [0.5] Được rồi, tôi sẽ đến ngay."
    )
    assert chunks == ["ừ.", "vâng.", "được rồi, tôi sẽ đến ngay."]
    assert gaps == [0.5, 0.5]


def test_merge_still_happens_inside_a_segment():
    chunks, gaps, _, _ = normalize_to_chunks_v3_with_pauses(
        "Vâng.\nĐược.\nTôi hiểu rồi, cảm ơn anh rất nhiều vì đã giúp đỡ. [0.7] Hẹn gặp lại."
    )
    assert chunks == ["vâng. được. tôi hiểu rồi, cảm ơn anh rất nhiều vì đã giúp đỡ.", "hẹn gặp lại."]
    assert gaps == [0.7]


def test_named_gaps_and_explicit_pauses_mix():
    text = "Chương một.\nNgày xửa ngày xưa, có một cô bé sống trong rừng sâu. [1.2] Một hôm, bà sai cô đi."
    chunks, gaps, _, _ = normalize_to_chunks_v3_with_pauses(text)
    assert len(gaps) == len(chunks) - 1
    assert gaps[-1] == 1.2 and all(isinstance(g, str) for g in gaps[:-1])


def test_adjacent_tags_sum_in_chunker():
    chunks, gaps, _, _ = normalize_to_chunks_v3_with_pauses("A. [0.3] [0.5] B.")
    assert len(chunks) == 2 and gaps == [pytest.approx(0.8)]


def test_clamped_pause_in_chunker():
    _, gaps, _, _ = normalize_to_chunks_v3_with_pauses("Chờ [9.5] chút.")
    assert gaps == [PAUSE_TAG_MAX]


@pytest.mark.parametrize("text,n_chunks,gaps,lead,tail", [
    ("[1.0] Xin chào [0.5]", 1, [], 1.0, 0.5),
    ("[0.4] Một. [0.6] Hai.", 2, [0.6], 0.4, 0.0),
    ("Một. [0.6] Hai. [0.9]", 2, [0.6], 0.0, 0.9),
    ("[0.2] [0.3] Một. [0.4] [0.6]", 1, [], 0.5, 1.0),
    ("[2.0]", 0, [], 2.0, 0.0),
    ("[1.0]  [1.5]", 0, [], 2.5, 0.0),
])
def test_leading_and_trailing_pauses_keep_gap_alignment(text, n_chunks, gaps, lead, tail):
    chunks, g, lead_s, tail_s = normalize_to_chunks_v3_with_pauses(text)
    assert len(chunks) == n_chunks
    assert len(g) == max(0, len(chunks) - 1)
    assert g == pytest.approx(gaps) and lead_s == pytest.approx(lead) and tail_s == pytest.approx(tail)


def test_with_gaps_wrapper_keeps_two_tuple_contract():
    result = normalize_to_chunks_v3_with_gaps("[1.0] Một. [0.6] Hai. [0.5]")
    assert len(result) == 2
    chunks, gaps = result
    assert len(chunks) == 2 and gaps == [0.6]


def test_en_guard_in_chunker():
    chunks, gaps, lead, tail = normalize_to_chunks_v3_with_pauses("Nói <en>hello [0.5] world</en> nhé.")
    assert len(chunks) == 1 and gaps == [] and (lead, tail) == (0.0, 0.0)


_TAGGED_INPUTS = [
    "Một. [0.6] Hai. [1.4] Ba.",
    "[1.0] Xin chào [0.5]",
    "Xin chào [0.5] bạn ơi, hôm nay thế nào?",
    "Dòng một.\n[0.8]\nDòng hai. [0.3] [0.2] Dòng ba.",
    "Anh ấy [cười] nói [0.35s] rồi [thở dài] đi.",
    "[2.0]",
]


@pytest.mark.parametrize("text", _TAGGED_INPUTS)
def test_tag_never_reaches_chunk_text_or_phonemes(text):
    v3_chunks = normalize_to_chunks_v3_with_pauses(text)[0]
    for chunks in (v3_chunks, normalize_to_chunks_v3(text), normalize_to_chunks(text)):
        for c in chunks:
            assert not _NUMERIC_BRACKET.search(c), c
            assert not _NUMERIC_BRACKET.search(phonemize_text_with_emotions(c)), c
    for pc in phonemize_to_chunks(text):
        assert not _NUMERIC_BRACKET.search(pc.text), pc.text
    assert not RE_PAUSE_TAG.search(strip_pause_tags(text))


def test_gapless_entry_points_strip_tags_as_sentence_boundary():
    tagged = "Xin chào [0.5] bạn ơi."
    assert normalize_to_chunks_v3(tagged) == normalize_to_chunks_v3("Xin chào. bạn ơi.")
    assert normalize_to_chunks(tagged) == normalize_to_chunks("Xin chào. bạn ơi.")
    assert normalize_to_chunks_v3("[2.0]") == [] and normalize_to_chunks("[2.0]") == []
    assert phonemize_to_chunks("[2.0]") == []


# ─── v3 Turbo engine: exact silence in infer / infer_stream / infer_batch ────

def _tone(seconds: float = TONE_S) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32) + 0.01


@pytest.fixture
def fake_tts():
    from vieneu.v3turbo import V3TurboVieNeuTTS

    tts = V3TurboVieNeuTTS.__new__(V3TurboVieNeuTTS)
    tts.sample_rate = SR
    tts.watermarker = None
    tts.max_batch_size = 4
    tts.calls = []
    tts._resolve_ref = lambda *a, **k: (np.zeros(4, np.float32), None)

    def _infer_chunks(chunks, *args, **kwargs):
        tts.calls.append(list(chunks))
        return [_tone() for _ in chunks]

    def _stream_chunks_engine(chunks, *args, **kwargs):
        tts.calls.append(list(chunks))
        for _ in chunks:
            yield iter([_tone(TONE_S / 2), _tone(TONE_S / 2)])

    tts._infer_chunks = _infer_chunks
    tts._stream_chunks_engine = _stream_chunks_engine
    tts._get_stream_scheduler = lambda: None
    return tts


def _zero_runs(wav: np.ndarray) -> list:
    """Lengths (seconds) of the runs of exact zeros in ``wav``, in order."""
    runs, n = [], 0
    for is_zero in np.concatenate([wav == 0.0, [False]]):
        if is_zero:
            n += 1
        elif n:
            runs.append(n / SR)
            n = 0
    return runs


def _approx(seconds):
    return pytest.approx(seconds, abs=1.5 / SR)


def test_infer_inserts_exact_internal_pauses(fake_tts):
    wav = fake_tts.infer("Một. [0.6] Hai. [1.4] Ba.")
    assert fake_tts.calls == [["một.", "hai.", "ba."]]
    assert _zero_runs(wav) == [_approx(0.6), _approx(1.4)]
    assert wav.size == int(3 * TONE_S * SR) + int(0.6 * SR) + int(1.4 * SR)


def test_infer_leading_and_trailing_pauses(fake_tts):
    wav = fake_tts.infer("[1.0] Xin chào [0.5]")
    assert _zero_runs(wav) == [_approx(1.0), _approx(0.5)]
    assert np.all(wav[: int(1.0 * SR)] == 0) and np.all(wav[-int(0.5 * SR):] == 0)
    assert wav.size == int(1.0 * SR) + int(TONE_S * SR) + int(0.5 * SR)


def test_infer_solo_pause_tag_is_pure_silence(fake_tts):
    wav = fake_tts.infer("[2.0]")
    assert fake_tts.calls == []
    assert wav.size == 2 * SR and not wav.any()
    assert fake_tts.infer("").size == 0


def test_infer_untagged_has_no_edge_padding(fake_tts):
    wav = fake_tts.infer("Xin chào các bạn. Hôm nay trời đẹp quá!")
    assert wav.size == int(TONE_S * SR) and _zero_runs(wav) == []


def test_infer_stream_pauses(fake_tts):
    parts = list(fake_tts.infer_stream("[1.0] Một. [0.6] Hai. [0.5]"))
    assert fake_tts.calls == [["một.", "hai."]]
    assert not parts[0].any() and parts[0].size == int(1.0 * SR)
    assert not parts[-1].any() and parts[-1].size == int(0.5 * SR)
    wav = np.concatenate(parts)
    assert _zero_runs(wav) == [_approx(1.0), _approx(0.6), _approx(0.5)]


def test_infer_stream_solo_pause_tag_is_pure_silence(fake_tts):
    parts = list(fake_tts.infer_stream("[2.0]"))
    assert fake_tts.calls == []
    assert len(parts) == 1 and parts[0].size == 2 * SR and not parts[0].any()
    assert list(fake_tts.infer_stream("")) == []


def test_infer_batch_pauses_per_text(fake_tts):
    out = fake_tts.infer_batch(["[0.5] Một. [0.6] Hai.", "[2.0]", "", "Ba. [0.3]"])
    assert fake_tts.calls == [["một.", "hai.", "ba."]]
    assert _zero_runs(out[0]) == [_approx(0.5), _approx(0.6)]
    assert out[1].size == 2 * SR and not out[1].any()
    assert out[2].size == 0
    assert _zero_runs(out[3]) == [_approx(0.3)]
