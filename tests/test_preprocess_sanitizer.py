"""Stage 1 sanitizer: normalisation, metadata removal, scene breaks, drop-cap recovery."""
import pytest

from vieneu_preprocess.html_to_text import html_to_text
from vieneu_preprocess.rules import load_rules
from vieneu_preprocess.sanitizer import SCENE_BREAK, recover_drop_cap, sanitize, unify_punctuation


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_unicode_nfc_normalisation(rules):
    decomposed = "Mặt nước"  # "ặ" written as base + combining marks
    assert sanitize(decomposed, rules) == "Mặt nước"


@pytest.mark.parametrize("raw, expected", [
    ("“Chào,” cô nói.", '"Chào," cô nói.'),
    ("«Đi thôi»", '"Đi thôi"'),
    ("« Đi thôi »", '"Đi thôi"'),
    ("„Xin chào‟", '"Xin chào"'),
])
def test_quotes_are_unified(raw, expected):
    assert unify_punctuation(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("vách đá – một quần thể", "vách đá — một quần thể"),
    ("vách đá--một quần thể", "vách đá — một quần thể"),
    ("vách đá—một quần thể", "vách đá — một quần thể"),
])
def test_dashes_are_unified(raw, expected):
    assert unify_punctuation(raw) == expected


def test_ellipsis_and_whitespace(rules):
    assert sanitize("Hoặc  ít nhất… con biết", rules) == "Hoặc ít nhất... con biết"


def test_metadata_lines_are_removed(rules):
    text = "\n".join([
        "# Chương 3: Tro tàn",
        "Số từ: 3.512 · Thời gian đọc: 15 phút",
        "Reading time: 12 min",
        "2.340 từ",
        "3,Chương 3,3512,15",
        "| --- | --- |",
        "Khi ông Bilbo trở về, cả làng đã ngủ.",
    ])
    assert sanitize(text, rules) == "Chương 3: Tro tàn\nKhi ông Bilbo trở về, cả làng đã ngủ."


def test_yaml_front_matter_and_markdown_markup_removed(rules):
    text = "---\ntitle: x\n---\n> **Gió** thổi _mạnh_ qua snake_case.\n"
    assert sanitize(text, rules) == "Gió thổi mạnh qua snake_case."


def test_scene_markers_are_normalised_and_collapsed(rules):
    text = "***\nĐoạn một.\n* * *\n...\n…\nĐoạn hai.\n---\n"
    assert sanitize(text, rules).split("\n") == ["Đoạn một.", SCENE_BREAK, "Đoạn hai.", SCENE_BREAK]


@pytest.mark.parametrize("line, expected", [
    ("ặt nước Hồ Đen vào đêm", "Mặt nước Hồ Đen vào đêm"),
    ("hi ông Bilbo trở về", "Khi ông Bilbo trở về"),
    ("ầu trời đỏ quạch", "Bầu trời đỏ quạch"),
    ("xyz không khớp", "Xyz không khớp"),
    ("Mặt nước đã đúng", "Mặt nước đã đúng"),
    ('"Chào," cô nói.', '"Chào," cô nói.'),
])
def test_drop_cap_recovery(rules, line, expected):
    assert recover_drop_cap(line, rules) == expected


def test_drop_cap_only_on_first_paragraph_and_after_headings(rules):
    text = "ặt nước phẳng lặng.\nhi đó trời tối.\n# Chương 2\nhi ông Bilbo trở về."
    assert sanitize(text, rules).split("\n") == [
        "Mặt nước phẳng lặng.", "hi đó trời tối.", "Chương 2", "Khi ông Bilbo trở về."]


def test_lone_drop_cap_letter_line_rejoins_word(rules):
    assert sanitize("M\n\nặt nước Hồ Đen.", rules) == "Mặt nước Hồ Đen."


def test_html_stripper_keeps_drop_cap_span():
    html = ('<html><head><style>p{}</style></head><body><h1>Chương 1</h1>'
            '<p><span class="dropcap">M</span>ặt nước Hồ Đen.</p><script>x()</script>'
            '<hr><p>Đoạn &amp; hai.</p></body></html>')
    assert html_to_text(html).split("\n") == ["Chương 1", "Mặt nước Hồ Đen.", "***", "Đoạn & hai."]
