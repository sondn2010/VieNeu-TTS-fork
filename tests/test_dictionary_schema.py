import json

import pytest

from vieneu_preprocess.dictionary_schema import (
    DictionaryFormatError, dump_dictionary_json, load_dictionary_json, merge_lexicon,
)
from vieneu_preprocess.types import Dictionary, LexiconEntry


def _doc(**over):
    d = {"format": "vieneu-dictionary/1", "name": "IT", "kind": "term", "enabled": True,
         "description": "", "entries": [{"term": "API", "replacement": "ây-pi-ai",
                                         "mode": "phonetic", "case_sensitive": True, "note": ""}]}
    d.update(over)
    return json.dumps(d, ensure_ascii=False)


def test_round_trip_sorted_utf8():
    d = Dictionary("IT", "term", True, "x", [
        LexiconEntry("Zed", "dét"), LexiconEntry("API", "ây-pi-ai", case_sensitive=True),
        LexiconEntry("C++", "xi cộng cộng")])
    text = dump_dictionary_json(d)
    assert "ây-pi-ai" in text and "\\u" not in text
    back = load_dictionary_json(text)
    assert [e.term for e in back.entries] == ["API", "C++", "Zed"]
    assert dump_dictionary_json(back) == text


def test_en_mode_without_replacement_ok():
    d = load_dictionary_json(_doc(entries=[{"term": "hello", "mode": "en"}]))
    assert d.entries[0].mode == "en" and d.entries[0].replacement == ""


@pytest.mark.parametrize("over,path", [
    ({"format": "x"}, "format"),
    ({"name": ""}, "name"),
    ({"name": "a" * 81}, "name"),
    ({"kind": "other"}, "kind"),
    ({"entries": [{"term": "", "replacement": "a"}]}, "entries[0].term"),
    ({"entries": [{"term": "a" * 81, "replacement": "a"}]}, "entries[0].term"),
    ({"entries": [{"term": "a", "replacement": ""}]}, "entries[0].replacement"),
    ({"entries": [{"term": "a", "replacement": "b" * 201}]}, "entries[0].replacement"),
    ({"entries": [{"term": "a", "replacement": "x[0.5]"}]}, "entries[0].replacement"),
    ({"entries": [{"term": "a", "replacement": "<|emotion_1|>"}]}, "entries[0].replacement"),
    ({"entries": [{"term": "a", "replacement": "<en>x</en>"}]}, "entries[0].replacement"),
    ({"entries": [{"term": "a", "replacement": "b", "mode": "zz"}]}, "entries[0].mode"),
    ({"entries": [{"term": "a", "replacement": "b"}, {"term": "A", "replacement": "c"}]},
     "entries[1].term"),
])
def test_rejections_carry_path(over, path):
    with pytest.raises(DictionaryFormatError) as ei:
        load_dictionary_json(_doc(**over))
    assert ei.value.path == path


def test_case_sensitive_duplicates_allowed():
    d = load_dictionary_json(_doc(entries=[
        {"term": "a", "replacement": "b", "case_sensitive": True},
        {"term": "A", "replacement": "c", "case_sensitive": True}]))
    assert len(d.entries) == 2


def test_too_many_entries():
    entries = [{"term": f"t{i}", "replacement": "x"} for i in range(20_001)]
    with pytest.raises(DictionaryFormatError):
        load_dictionary_json(_doc(entries=entries))


def test_broken_json_has_line_column():
    with pytest.raises(DictionaryFormatError) as ei:
        load_dictionary_json('{\n  "format": \n}')
    assert ei.value.line == 3 and ei.value.column is not None


def test_merge_precedence_and_disabled():
    name = Dictionary("n", "name", entries=[LexiconEntry("Foo", "from-name")])
    term = Dictionary("t", "term", entries=[LexiconEntry("foo", "from-term"), LexiconEntry("Bar", "bar-t")])
    eng = Dictionary("e", "english", entries=[LexiconEntry("Bar", "bar-e"), LexiconEntry("Baz", "baz")])
    off = Dictionary("off", "name", enabled=False, entries=[LexiconEntry("Baz", "never")])
    out = {e.term.lower(): e.replacement for e in merge_lexicon([eng, term, off, name])}
    assert out == {"foo": "from-name", "bar": "bar-t", "baz": "baz"}


def test_merge_tie_keeps_first_by_name():
    a = Dictionary("a", "term", entries=[LexiconEntry("x", "from-a")])
    b = Dictionary("b", "term", entries=[LexiconEntry("x", "from-b")])
    assert merge_lexicon([b, a])[0].replacement == "from-a"
