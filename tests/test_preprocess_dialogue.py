"""Stage 2 dialogue parser: the six spec section 2 edge cases and both dialogue conventions."""
from pathlib import Path

import pytest

from vieneu_preprocess.dialogue_parser import parse_segments
from vieneu_preprocess.rules import load_rules
from vieneu_preprocess.sanitizer import sanitize

CAST = str(Path(__file__).parent / "fixtures" / "preprocess" / "dracaena_cast_rules.yaml")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def cast_rules():
    return load_rules(CAST)


def parse(text, rules):
    return [(s.kind, s.speaker, s.text) for s in parse_segments(sanitize(text, rules), rules)
            if s.kind != "scene_break"]


def test_telepathy_after_mind_cue_colon_with_backfilled_speaker(cast_rules):
    text = ("Ngay lập tức, một giọng nói khô khốc vang lên trong tâm trí cô:\n"
            "Chà, một người nhà Malfoy nữa. Đã lâu rồi đấy.\n"
            "Dracaena ngồi im. Thông minh. Rất thông minh, chiếc nón thì thầm. "
            "Con biết chính xác mình là ai, phải không? Dracaena khẽ nhíu mày. "
            "Tôi là một Malfoy. Tôi thuộc về Slytherin.")
    assert parse(text, cast_rules) == [
        ("narration", None, "Ngay lập tức, một giọng nói khô khốc vang lên trong tâm trí cô:"),
        ("inner_voice", "Nón Phân Loại", "Chà, một người nhà Malfoy nữa. Đã lâu rồi đấy."),
        ("narration", None, "Dracaena ngồi im."),
        ("inner_voice", "Nón Phân Loại", "Thông minh. Rất thông minh."),
        ("narration", None, "Chiếc nón thì thầm."),
        ("inner_voice", "Nón Phân Loại", "Con biết chính xác mình là ai, phải không?"),
        ("narration", None, "Dracaena khẽ nhíu mày."),
        ("inner_voice", "Dracaena (Nội tâm)", "Tôi là một Malfoy. Tôi thuộc về Slytherin."),
    ]


def test_telepathy_without_named_voice_uses_unknown_inner_label(rules):
    text = "Một giọng nói vang lên trong đầu hắn:\nĐúng vậy, ngươi sẽ tới đó."
    segs = parse(text, rules)
    assert segs[1] == ("inner_voice", rules.unknown_inner_label, "Đúng vậy, ngươi sẽ tới đó.")


def test_interjected_mid_sentence_tag(rules):
    segs = parse("Đúng vậy, giọng nói tiếp tục, con sẽ làm được.", rules)
    assert segs == [("inner_voice", "Giọng nói", "Đúng vậy."),
                    ("narration", None, "Giọng nói tiếp tục."),
                    ("inner_voice", "Giọng nói", "Con sẽ làm được.")]


def test_inner_passage_closes_after_plain_narration(rules):
    text = ("Hắn nghe tiếng thì thầm trong đầu:\nĐi đi.\nHắn rời khỏi phòng.\n"
            "Trời đã sáng hẳn.")
    kinds = [k for k, _, _ in parse(text, rules)]
    assert kinds == ["narration", "inner_voice", "narration", "narration"]


def test_roll_call_and_shout_speakers(cast_rules):
    text = '"Potter, Harry!"\nRồi chiếc nón hét vang:\n"GRYFFINDOR!"'
    assert parse(text, cast_rules) == [
        ("shout", "McGonagall", "Potter, Harry!"),
        ("narration", None, "Rồi chiếc nón hét vang:"),
        ("shout", "Nón Phân Loại", "GRYFFINDOR!"),
    ]


def test_roll_call_without_cast_falls_back_to_unknown(rules):
    assert parse('"Granger, Hermione!"', rules) == [("shout", rules.unknown_label, "Granger, Hermione!")]


def test_split_dialogue_linker_english_american(rules):
    text = ('"Trần nhà không có thật đâu," cô bé thì thầm. '
            '"Nó chỉ được yểm bùa để trông giống bầu trời thôi."')
    assert parse(text, rules) == [
        ("dialogue", "Cô bé", "Trần nhà không có thật đâu."),
        ("narration", None, "Cô bé thì thầm."),
        ("dialogue", "Cô bé", "Nó chỉ được yểm bùa để trông giống bầu trời thôi."),
    ]


def test_vietnamese_french_dash_tag_and_bare_name(rules):
    text = '"Không còn đường lui nữa." — Gorgûl nói.\n"Ra khỏi đây!" — Gandalf.'
    assert parse(text, rules) == [
        ("dialogue", "Gorgûl", "Không còn đường lui nữa."),
        ("narration", None, "Gorgûl nói."),
        ("dialogue", "Gandalf", "Ra khỏi đây!"),
    ]


def test_colon_tag_before_quote_and_pronoun_resolution(rules):
    text = 'Muzgash đứng trên tường thành.\n"Chúng đến rồi," hắn lẩm bẩm.\nHắn nói: "Đi thôi."'
    segs = parse(text, rules)
    assert segs[1] == ("dialogue", "Muzgash", "Chúng đến rồi.")
    assert segs[-1] == ("dialogue", "Muzgash", "Đi thôi.")


def test_embedded_quote_guard_keeps_narration(rules):
    text = ('Suốt đêm hôm đó, câu nói "Chính xác là người mà con được kỳ vọng phải trở thành" '
            'vẫn vương lại trong tâm trí cô.')
    assert parse(text, rules) == [("narration", None, text)]


def test_quote_after_noun_with_terminal_punctuation_is_dialogue(rules):
    segs = parse('Hắn nhắc lại câu nói "Đi ngay." rồi im lặng.', rules)
    assert any(k == "dialogue" for k, _, _ in segs)


def test_emotion_from_tag(rules):
    segs = parse_segments(sanitize('"Thật buồn cười," cô bật cười.', rules), rules)
    assert segs[0].emotion == "laugh"


def test_unbalanced_quote_runs_to_paragraph_end(rules):
    segs = parse('"Chúng ta đi thôi', rules)
    assert segs == [("dialogue", rules.unknown_label, "Chúng ta đi thôi")]
