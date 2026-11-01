"""Load and validate `config/pause_rules.yaml` into frozen dataclasses.

A custom rules file is deep-merged over the packaged default, so callers only
override what they tune. Results are cached per (path, mtime) so an edited file
is picked up without a restart.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_RULES_PATH = Path(__file__).with_name("config") / "pause_rules.yaml"
_MAX_PAUSE_SEC = 10.0


class RulesError(ValueError):
    """The rules YAML is missing, malformed or out of range."""


@dataclass(frozen=True)
class PauseTable:
    p01_short_narration: float
    p02_standard_narration: float
    p03_long_narration: float
    p04_emphatic_short: float
    p06_question_exclaim: float
    p07_shout_before: float
    p07_shout_after: float
    p08_dash_pair_open: float
    p08_dash_pair_close: float
    p09_dash_tail: float
    p10_long_clause_breath: float
    p11_dialogue_narration: float
    p12_inner_voice: float
    p13_paragraph: float
    p14_scene: float
    roll_call_comma: float
    embedded_quote_before: float
    embedded_quote_after: float


@dataclass(frozen=True)
class Thresholds:
    p01_max_words: int
    p03_min_words: int
    emphatic_max_words: int
    long_clause_words: int
    soft_comma_max_words: int
    shout_max_words: int
    caps_min_letters: int
    inner_short_clause_words: int


@dataclass(frozen=True)
class CountdownRules:
    ladder: tuple[float, ...]
    speed_ladder: tuple[float, ...]
    max_words: int
    min_run: int
    time_run_min: int
    time_words: tuple[str, ...]
    soft_ending: str


@dataclass(frozen=True)
class EmotionRule:
    name: str
    keywords: tuple[str, ...]
    tag: str
    position: str
    speed: float
    end_pause: Optional[float] = None


@dataclass(frozen=True)
class Rules:
    pauses: PauseTable
    thresholds: Thresholds
    countdown: CountdownRules
    emotions: tuple[EmotionRule, ...]
    speech_verbs: tuple[str, ...]
    tag_lead_words: tuple[str, ...]
    max_subject_words: int
    pronoun_subjects: tuple[str, ...]
    embedded_quote_nouns: tuple[str, ...]
    long_clause_connectors: tuple[str, ...]
    mind_cues: tuple[str, ...]
    inner_tag_verbs: tuple[str, ...]
    self_openers: tuple[str, ...]
    other_openers: tuple[str, ...]
    narration_subjects: tuple[str, ...]
    self_suffix: str
    narrator: str
    narrator_label: str
    unknown_label: str
    unknown_inner_label: str
    roll_call_speaker: str
    aliases: tuple[tuple[str, str], ...]  # (casefolded subject, speaker)
    scene_label: str
    temperature: float
    chunk_prefix: str
    scene_markers: tuple[str, ...]
    metadata_patterns: tuple[str, ...]
    csv_min_fields: int
    csv_max_field_words: int
    drop_cap_openers: tuple[str, ...]

    def emotion(self, name: str) -> Optional[EmotionRule]:
        return next((e for e in self.emotions if e.name == name), None)

    def alias_for(self, subject: str) -> Optional[str]:
        key = subject.casefold()
        return next((v for k, v in self.aliases if k == key), None)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as e:
        raise RulesError(f"cannot read rules file {path}: {e}") from e
    except yaml.YAMLError as e:
        raise RulesError(f"invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise RulesError(f"{path}: top level must be a mapping")
    return data


def _section(data: dict, key: str) -> dict:
    v = data.get(key)
    if not isinstance(v, dict):
        raise RulesError(f"section {key!r} must be a mapping")
    return v


def _strs(v: Any, where: str) -> tuple[str, ...]:
    if not isinstance(v, list) or not all(isinstance(s, str) and s for s in v):
        raise RulesError(f"{where} must be a list of non-empty strings")
    return tuple(v)


def _floats(v: Any, where: str) -> tuple[float, ...]:
    if not isinstance(v, list) or not v or not all(isinstance(x, (int, float)) for x in v):
        raise RulesError(f"{where} must be a non-empty list of numbers")
    return tuple(float(x) for x in v)


def _build(cls, raw: dict, where: str):
    """Construct a flat dataclass from a mapping, validating names and number ranges."""
    names = {f.name for f in fields(cls)}
    missing, unknown = names - raw.keys(), raw.keys() - names
    if missing or unknown:
        raise RulesError(f"{where}: missing {sorted(missing)} / unknown {sorted(unknown)}")
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise RulesError(f"{where}.{k} must be a number")
        if v < 0 or (cls is PauseTable and v > _MAX_PAUSE_SEC):
            raise RulesError(f"{where}.{k} out of range: {v}")
    return cls(**raw)


def _emotions(raw: Any) -> tuple[EmotionRule, ...]:
    if not isinstance(raw, list):
        raise RulesError("emotions must be a list")
    out = []
    for i, e in enumerate(raw):
        if not isinstance(e, dict) or e.get("position") not in ("before", "after"):
            raise RulesError(f"emotions[{i}] needs position before|after")
        end_pause = e.get("end_pause")
        out.append(EmotionRule(
            name=str(e.get("name", "")), keywords=_strs(e.get("keywords"), f"emotions[{i}].keywords"),
            tag=str(e.get("tag", "")), position=e["position"], speed=float(e.get("speed", 1.0)),
            end_pause=None if end_pause is None else float(end_pause)))
    return tuple(out)


def _parse(data: dict) -> Rules:
    cd, sp, iv = _section(data, "countdown"), _section(data, "speech"), _section(data, "inner_voice")
    spk, sz, dflt = _section(data, "speakers"), _section(data, "sanitizer"), _section(data, "defaults")
    try:
        countdown = CountdownRules(
            ladder=_floats(cd["ladder"], "countdown.ladder"),
            speed_ladder=_floats(cd["speed_ladder"], "countdown.speed_ladder"),
            max_words=int(cd["max_words"]), min_run=int(cd["min_run"]),
            time_run_min=int(cd["time_run_min"]),
            time_words=_strs(cd["time_words"], "countdown.time_words"),
            soft_ending=str(cd["soft_ending"]))
        aliases = spk.get("aliases") or {}
        if not isinstance(aliases, dict):
            raise RulesError("speakers.aliases must be a mapping")
        return Rules(
            pauses=_build(PauseTable, _section(data, "pauses"), "pauses"),
            thresholds=_build(Thresholds, _section(data, "thresholds"), "thresholds"),
            countdown=countdown,
            emotions=_emotions(data.get("emotions")),
            speech_verbs=_strs(sp["verbs"], "speech.verbs"),
            tag_lead_words=_strs(sp["tag_lead_words"], "speech.tag_lead_words"),
            max_subject_words=int(sp["max_subject_words"]),
            pronoun_subjects=_strs(sp["pronoun_subjects"], "speech.pronoun_subjects"),
            embedded_quote_nouns=_strs(sp["embedded_quote_nouns"], "speech.embedded_quote_nouns"),
            long_clause_connectors=_strs(sp["long_clause_connectors"], "speech.long_clause_connectors"),
            mind_cues=_strs(iv["mind_cues"], "inner_voice.mind_cues"),
            inner_tag_verbs=_strs(iv["tag_verbs"], "inner_voice.tag_verbs"),
            self_openers=_strs(iv["self_openers"], "inner_voice.self_openers"),
            other_openers=_strs(iv["other_openers"], "inner_voice.other_openers"),
            narration_subjects=_strs(iv["narration_subjects"], "inner_voice.narration_subjects"),
            self_suffix=str(iv["self_suffix"]),
            narrator=str(spk["narrator"]), narrator_label=str(spk["narrator_label"]),
            unknown_label=str(spk["unknown_label"]),
            unknown_inner_label=str(spk["unknown_inner_label"]),
            roll_call_speaker=str(spk.get("roll_call_speaker") or ""),
            aliases=tuple((str(k).casefold(), str(v)) for k, v in aliases.items()),
            scene_label=str(_section(data, "labels")["scene"]),
            temperature=float(dflt["temperature"]), chunk_prefix=str(dflt["chunk_prefix"]),
            scene_markers=_strs(sz["scene_markers"], "sanitizer.scene_markers"),
            metadata_patterns=_strs(sz["metadata_patterns"], "sanitizer.metadata_patterns"),
            csv_min_fields=int(sz["csv_min_fields"]),
            csv_max_field_words=int(sz["csv_max_field_words"]),
            drop_cap_openers=_strs(sz["drop_cap_openers"], "sanitizer.drop_cap_openers"))
    except KeyError as e:
        raise RulesError(f"missing rules key: {e}") from e
    except (TypeError, ValueError) as e:
        if isinstance(e, RulesError):
            raise
        raise RulesError(f"invalid rules value: {e}") from e


@lru_cache(maxsize=16)
def _load_cached(path: Optional[str], _mtime_ns: int) -> Rules:
    data = _read_yaml(DEFAULT_RULES_PATH)
    if path is not None:
        data = _deep_merge(data, _read_yaml(Path(path)))
    return _parse(data)


def load_rules(path: Optional[str | os.PathLike] = None) -> Rules:
    """Return the default rules, or the default deep-merged with the file at `path`."""
    target = None if path is None else str(Path(path).resolve())
    try:
        mtime = os.stat(target or DEFAULT_RULES_PATH).st_mtime_ns
    except OSError as e:
        raise RulesError(f"rules file not found: {target or DEFAULT_RULES_PATH}") from e
    return _load_cached(target, mtime)
