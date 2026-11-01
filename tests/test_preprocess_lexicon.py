"""Stage 4 lexicon mapper: longest match, case rules, <en>, guard regions, caps-to-title, regex safety."""
from vieneu_preprocess.lexicon_mapper import map_lexicon
from vieneu_preprocess.types import LexiconEntry as E


def test_longest_term_wins():
    lex = [E("Harry", "Ha-ri"), E("Harry Potter", "Ha-ri Pót-tơ (đầy đủ)")]
    assert map_lexicon("Cậu Harry Potter và Harry.", lex) == "Cậu Ha-ri Pót-tơ (đầy đủ) và Ha-ri."


def test_case_insensitive_by_default_and_capital_rule():
    lex = [E("api", "ây-pi-ai")]
    assert map_lexicon("Api mới. Gọi api cũ.", lex) == "Ây-pi-ai mới. Gọi ây-pi-ai cũ."


def test_case_sensitive_acronym_matches_only_original_casing():
    lex = [E("UBND", "ủy ban nhân dân", case_sensitive=True)]
    assert map_lexicon("UBND xã và Ubnd.", lex) == "ủy ban nhân dân xã và Ubnd."


def test_whole_word_boundaries():
    lex = [E("Ron", "Rôn")]
    assert map_lexicon("Ron và Ronald, Bron.", lex) == "Rôn và Ronald, Bron."


def test_en_mode_wraps_original_text():
    lex = [E("Scotland", mode="en")]
    assert map_lexicon("cao nguyên Scotland.", lex) == "cao nguyên <en>Scotland</en>."


def test_guard_regions_are_untouched():
    lex = [E("cười", "XX"), E("Hogwarts", "Hốc-goát")]
    text = "[cười] <en>Hogwarts</en> và Hogwarts <|emotion_1|>"
    assert map_lexicon(text, lex) == "[cười] <en>Hogwarts</en> và Hốc-goát <|emotion_1|>"


def test_unmapped_caps_become_title_case_after_lexicon():
    lex = [E("GRYFFINDOR", "Gờ-ríp-phin-đo"), E("THPT", "tê hát pê tê", case_sensitive=True)]
    out = map_lexicon("SLYTHERIN! GRYFFINDOR! THPT và ĐI và [HÔ VANG]", lex)
    assert out == "Slytherin! Gờ-ríp-phin-đo! tê hát pê tê và ĐI và [HÔ VANG]"


def test_caps_min_letters_is_configurable():
    assert map_lexicon("ĐI NGAY", [], caps_min_letters=2) == "Đi Ngay"


def test_symbol_terms_are_escaped_and_match_cleanly():
    lex = [E("C++", "xi cộng cộng"), E("C#", "xi sáp"), E(".NET", "đót nét"), E("a.b", "AB")]
    out = map_lexicon("Học C++, C# và .NET; axb khác a.b.", lex)
    assert out == "Học xi cộng cộng, xi sáp và đót nét; axb khác AB."


def test_regex_metacharacters_never_raise():
    lex = [E("(?P<x>", "ok"), E("[a-z]+", "ok2"), E("\\d*", "ok3")]
    assert map_lexicon("x (?P<x> y \\d* z", lex) == "x ok y ok3 z"


def test_empty_lexicon_is_noop_except_caps():
    assert map_lexicon("Xin chào HOGWARTS.", []) == "Xin chào Hogwarts."
