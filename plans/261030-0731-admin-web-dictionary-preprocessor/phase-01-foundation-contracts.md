---
phase: 1
title: "Foundation: packaging and shared contracts"
status: completed
priority: P1
effort: "3h"
dependencies: []
---

# Phase 1: Foundation — packaging and shared contracts

## Goal

Declare dependencies and package data once, and freeze the data contracts (dictionary JSON, lexicon entry, preprocessor result) that phases 2–5 code against in parallel.

## Files to Create / Modify

- Modify: `pyproject.toml` — add `jinja2` and `markdown-it-py` to `dependencies` (already in `uv.lock` via Gradio, so no lock churn beyond markers); add package-data `vieneu_preprocess = ["config/*.yaml"]`, `vieneu_admin = ["templates/*.html", "templates/**/*.html", "static/*", "seed/*.json"]`; add script `vieneu-preprocess = "vieneu_preprocess.cli:main"`; add script `vieneu-api = "apps.openai_speech:main"`.
- Modify: `.gitignore` — add `vieneu_data/`.
- Create: `src/vieneu_preprocess/__init__.py` — public API stubs (signatures below) that raise `NotImplementedError` until phase 3 fills them.
- Create: `src/vieneu_preprocess/types.py` — dataclasses below.
- Create: `src/vieneu_preprocess/dictionary_schema.py` — load, validate and dump dictionary JSON.
- Create: `tests/test_dictionary_schema.py`.

## Contracts

```python
# types.py
Mode = Literal["phonetic", "en"]
Kind = Literal["english", "term", "name"]

@dataclass(frozen=True)
class LexiconEntry:
    term: str
    replacement: str = ""      # required when mode == "phonetic"; ignored for "en"
    mode: Mode = "phonetic"
    case_sensitive: bool = False
    note: str = ""

@dataclass
class Dictionary:
    name: str
    kind: Kind
    enabled: bool = True
    description: str = ""
    entries: list[LexiconEntry] = field(default_factory=list)

@dataclass
class Chunk:                    # spec §5.3 shape
    chunk_id: str
    speaker: str                # "Narrator" or a character name
    role_type: str              # narration, narration_countdown, dialogue, dialogue_shout, inner_voice
    text: str                   # no [x.xx] tags; emotion tags allowed
    speed: float = 1.0
    pause_before_sec: float = 0.0
    pause_after_sec: float = 0.0
    voice_preset: Optional[str] = None
    temperature: float = 0.8

@dataclass
class PreprocessResult:
    chunks: list[Chunk]
    script: str                 # spec mode 1: "Speaker: text [0.35] ..." with "// scene" comments
    def to_json(self) -> list[dict]: ...
    def to_tagged_text(self) -> str: ...  # single-voice text with [x.xx] tags, for the API path
```

```python
# __init__.py public API (implemented in phase 3)
def preprocess(text: str, lexicon: Sequence[LexiconEntry] = (), *,
               voices: Optional[Mapping[str, str]] = None,
               rules_path: Optional[str] = None) -> PreprocessResult: ...
def render(result: PreprocessResult, tts, *, default_voice: Optional[str] = None,
           apply_speed: bool = True) -> np.ndarray: ...   # 48 kHz float32
```

```python
# dictionary_schema.py
class DictionaryFormatError(ValueError): line: int | None; column: int | None; path: str
def load_dictionary_json(data: str | bytes) -> Dictionary
def dump_dictionary_json(d: Dictionary) -> str   # UTF-8, ensure_ascii=False, indent=2, entries sorted by term
def merge_lexicon(dicts: Iterable[Dictionary]) -> list[LexiconEntry]
```

JSON file shape (one dictionary per file):

```json
{"format": "vieneu-dictionary/1", "name": "Thuật ngữ IT", "kind": "term", "enabled": true,
 "description": "", "entries": [{"term": "API", "replacement": "ây-pi-ai", "mode": "phonetic",
 "case_sensitive": true, "note": ""}]}
```

Validation rules: `format` must equal `vieneu-dictionary/1`; `name` 1–80 chars; `kind` in the three values; `term` 1–80 chars, unique per dictionary (case-folded unless `case_sensitive`); `replacement` ≤ 200 chars and must not contain `[`, `]`, `<|`, `|>` or any `<tag>` (the `en` mode adds `<en>` itself); max 20 000 entries. `json.JSONDecodeError` maps to `DictionaryFormatError(line, column)`; schema errors carry a JSON path such as `entries[12].term`.
<!-- red-team finding 7: lexicon term regex safety -->
In addition, `term` must be safe for regex compilation; all terms will be escaped via `re.escape()` in mapper stages to prevent regex syntax errors or ReDoS on technical terms containing symbols (e.g. `C++`, `C#`, `.NET`).

`merge_lexicon` precedence on duplicate terms: `name` > `term` > `english`; ties keep the first dictionary by name order. Disabled dictionaries are skipped.

## Tasks & Steps

- [ ] Edit `pyproject.toml` and `.gitignore` as listed; run `uv lock` and confirm only the explicit-dependency markers change.
- [x] Write `types.py` and the `__init__.py` stubs exactly as the contracts above.
- [x] Implement `dictionary_schema.py` with the validation rules.
- [x] Tests: round-trip, every rejection rule, line/column on broken JSON, precedence in `merge_lexicon`, disabled skip.

## Verification

- `uv run pytest tests/test_dictionary_schema.py -q`
- `uv run python -c "import vieneu_preprocess, vieneu_preprocess.types"`

## Risk / rollback

Low. Contract changes after phase 1 must be coordinated across phases 3–5; treat these signatures as frozen. Rollback: revert the phase commit.
