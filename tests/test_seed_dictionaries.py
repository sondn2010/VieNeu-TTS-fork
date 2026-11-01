"""Seed pronunciation dictionaries shipped with the admin app must be valid and complete."""
import re
from pathlib import Path

import pytest

from vieneu_preprocess.dictionary_schema import load_dictionary_json, merge_lexicon

SEED_DIR = Path(__file__).resolve().parents[1] / "src" / "vieneu_admin" / "seed"

# file -> (kind, minimum entry count)
EXPECTED = {
    "english-common.json": ("english", 200),
    "abbreviations.json": ("term", 150),
    "it-terms.json": ("term", 80),
    "business-finance.json": ("term", 60),
    "medical.json": ("term", 60),
    "fantasy-ash-land.json": ("name", 7),
    "fantasy-hogwarts.json": ("name", 15),
}

# Ordinary Vietnamese words that must never be remapped when matched case-insensitively.
VIETNAMESE_WORDS = {"to", "an", "con", "ai", "ba", "ca", "ma", "la", "da", "hay", "ban", "bia",
                    "pin", "sim", "ron", "cafe", "taxi", "tin", "can", "may", "man", "cam"}
# Letters that standard Vietnamese orthography never uses.
NON_VIETNAMESE_LETTERS = re.compile(r"[fjwzFJWZ]")


def _load(fname):
    return load_dictionary_json((SEED_DIR / fname).read_bytes())


@pytest.fixture(scope="module")
def seeds():
    return {f: _load(f) for f in EXPECTED}


def _lookup(lexicon, term):
    hits = [e for e in lexicon if e.term == term]
    assert hits, f"{term!r} missing from merged lexicon"
    return hits[0]


def test_seed_dir_contains_exactly_expected_files():
    assert sorted(p.name for p in SEED_DIR.glob("*.json")) == sorted(EXPECTED)


@pytest.mark.parametrize("fname", sorted(EXPECTED))
def test_each_seed_loads_with_schema_and_meets_minimums(fname):
    d = _load(fname)
    kind, minimum = EXPECTED[fname]
    assert d.kind == kind
    assert d.enabled is True
    assert d.description.strip()
    assert len(d.entries) >= minimum


def test_dictionary_names_unique(seeds):
    names = [d.name for d in seeds.values()]
    assert len(names) == len(set(names))


def test_no_term_defined_twice_across_seeds(seeds):
    """Stronger than merge_lexicon's same-kind rule: no seed term overlaps another, so priority never matters."""
    owner: dict[str, str] = {}
    for fname, d in seeds.items():
        for e in d.entries:
            key = e.term.casefold()
            assert key not in owner, f"{e.term!r} in both {owner[key]} and {fname}"
            owner[key] = fname


def test_merge_keeps_every_seed_entry(seeds):
    merged = merge_lexicon(seeds.values())
    assert len(merged) == sum(len(d.entries) for d in seeds.values())


def test_english_common_is_all_en_mode(seeds):
    assert all(e.mode == "en" for e in seeds["english-common.json"].entries)


def test_abbreviations_are_case_sensitive_phonetic(seeds):
    for e in seeds["abbreviations.json"].entries:
        assert e.mode == "phonetic" and e.case_sensitive, e.term
    for bad in ("TO", "AN", "CON"):
        assert bad not in {e.term for e in seeds["abbreviations.json"].entries}


def test_case_insensitive_terms_are_not_vietnamese_words(seeds):
    for d in seeds.values():
        for e in d.entries:
            if not e.case_sensitive:
                assert e.term.casefold() not in VIETNAMESE_WORDS, e.term
                assert len(e.term) > 2, f"short case-insensitive term {e.term!r} is risky"


def test_phonetic_replacements_use_vietnamese_orthography(seeds):
    for d in seeds.values():
        for e in d.entries:
            if e.mode == "phonetic":
                assert not NON_VIETNAMESE_LETTERS.search(e.replacement), (e.term, e.replacement)
                assert e.replacement == e.replacement.strip()
                assert "--" not in e.replacement and " -" not in e.replacement


@pytest.mark.parametrize("term,expected", [
    # tts-specs-v1 section 5.1 / 5.2
    ("Hogwarts", "Hốc-goát"), ("Slytherin", "Sờ-li-thơ-rin"), ("Dracaena", "Đờ-ra-xê-na"),
    ("Hagrid", "Ha-gờ-rít"), ("Malfoy", "Man-phôi"), ("Harry", "Ha-ri"), ("Potter", "Pót-tơ"),
    ("Gryffindor", "Gờ-ríp-phin-đo"), ("McGonagall", "Mắc-go-na-gôn"),
    # tts-specs-v1 section 4.4
    ("Hermione", "Hơ-mai-ơ-ni"), ("Granger", "Gờ-ren-giơ"), ("Daphne", "Đáp-ni"),
    ("Greengrass", "Gờ-rin-gờ-rát"), ("Pansy", "Pan-xi"),
    ("Udûn-gath", "U-đun gát"), ("Gorgûl", "Go-gun"), ("Muzgash", "Mút-gát"),
    ("Gorgoroth", "Go-gô-rốt"), ("Dorwinion", "Đo-uy-ni-on"), ("Ephel Dúath", "Ê-phen Đu-át"),
    ("Lugbúrz", "Lúc-bua"),
    # Abbreviation examples
    ("AI", "ây-ai"), ("API", "ây-pi-ai"), ("CEO", "xi-i-âu"), ("GDP", "giê-đê-pê"),
    ("USB", "u-ét-bê"), ("WHO", "vê-kép-hát-o"), ("UBND", "u-bê-en-đê"), ("THPT", "tê-hát-pê-tê"),
    # Domain spot checks
    ("Kubernetes", "Ku-bơ-nét-tít"), ("C++", "xi cộng cộng"), ("KPI", "kây-pi-ai"),
    ("VN-Index", "vê-en in-đéc"), ("COVID-19", "Cô-vít mười chín"), ("vaccine", "vắc-xin"),
    ("mmHg", "mi-li-mét thủy ngân"),
])
def test_key_phonetic_entries(seeds, term, expected):
    e = _lookup(merge_lexicon(seeds.values()), term)
    assert e.mode == "phonetic"
    assert e.replacement == expected


@pytest.mark.parametrize("term", ["Scotland", "email", "livestream", "check-in", "Docker", "startup"])
def test_key_en_entries(seeds, term):
    assert _lookup(merge_lexicon(seeds.values()), term).mode == "en"


def test_acronym_and_unit_entries_case_sensitive(seeds):
    lexicon = merge_lexicon(seeds.values())
    for term in ("AI", "KPI", "MRI", "mg", "ml", "HTML", "Ron"):
        assert _lookup(lexicon, term).case_sensitive, term
