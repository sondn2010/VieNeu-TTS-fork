"""System dictionary pack CRUD, JSON import (`new`/`merge`/`replace`),
`.txt` import, export round-trip, the `SYSTEM_RULES_MAX` cap, and target
moderation (rejected rows reported, not a hard abort)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from vieneu_portal.config import get_settings
from vieneu_portal.db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from vieneu_portal.dictionaries.system_dictionary_store import (
    DictionaryFormatError,
    create_pack_from_json,
    export_pack_json,
    import_json_into_pack,
    import_text_rules_into_pack,
    list_packs,
    list_rules,
    parse_dictionary_pack_json,
    seed_if_empty,
    set_pack_enabled,
)
from vieneu_portal.errors import PortalError
from vieneu_portal.moderation.blocklist_moderation_provider import BlocklistModerationProvider
from vieneu_portal.moderation.moderation_provider_factory import OffModerationProvider

_PACK_JSON = json.dumps({
    "format": "vieneu-dictionary/1", "name": "Test Pack", "kind": "term", "enabled": True,
    "description": "", "entries": [
        {"term": "KPI", "replacement": "kây-pi-ai", "mode": "phonetic", "case_sensitive": True},
        {"term": "API", "replacement": "", "mode": "en", "case_sensitive": False},
    ],
})


def test_create_pack_from_json_inserts_rules_with_correct_rule_kind(db_session) -> None:
    pack, rejected = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)
    assert rejected == []
    rules = {r.source_term: r for r in list_rules(db_session, pack.id)}
    assert rules["KPI"].rule_kind == "REPLACE" and rules["KPI"].phonetic_replacement == "kây-pi-ai"
    assert rules["API"].rule_kind == "ENGLISH_FALLBACK" and rules["API"].phonetic_replacement == ""


def test_invalid_format_raises_dictionary_format_error(db_session) -> None:
    with pytest.raises(DictionaryFormatError):
        create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text='{"format": "nope"}')


def test_export_then_reimport_round_trips(db_session) -> None:
    pack, _ = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)
    exported = export_pack_json(db_session, pack)

    reparsed = parse_dictionary_pack_json(exported)
    assert reparsed.name == pack.name and reparsed.kind == pack.kind and reparsed.enabled == pack.is_enabled
    reparsed_tuples = {(e.term, e.replacement, e.mode) for e in reparsed.entries}
    assert reparsed_tuples == {("KPI", "kây-pi-ai", "phonetic"), ("API", "", "en")}


def test_merge_keeps_non_conflicting_existing_rules(db_session) -> None:
    pack, _ = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)

    merge_doc = json.dumps({
        "format": "vieneu-dictionary/1", "name": "ignored on merge", "kind": "term", "enabled": True,
        "description": "", "entries": [{"term": "KPI", "replacement": "kây-pi-ai mới", "mode": "phonetic"}],
    })
    rejected = import_json_into_pack(db_session, get_settings(), OffModerationProvider(), pack=pack, json_text=merge_doc, mode="merge")
    assert rejected == []

    rules = {r.source_term: r for r in list_rules(db_session, pack.id)}
    assert rules["KPI"].phonetic_replacement == "kây-pi-ai mới"   # overwritten by the merge
    assert "API" in rules   # untouched, kept from before
    assert pack.name == "Test Pack"   # merge never touches metadata


def test_replace_drops_old_rules_and_updates_metadata(db_session) -> None:
    pack, _ = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)

    replace_doc = json.dumps({
        "format": "vieneu-dictionary/1", "name": "Replaced Name", "kind": "name", "enabled": False,
        "description": "new", "entries": [{"term": "Only", "replacement": "survivor", "mode": "phonetic"}],
    })
    import_json_into_pack(db_session, get_settings(), OffModerationProvider(), pack=pack, json_text=replace_doc, mode="replace")

    assert pack.name == "Replaced Name" and pack.kind == "name" and pack.is_enabled is False
    rules = list_rules(db_session, pack.id)
    assert [r.source_term for r in rules] == ["Only"]


def test_txt_import_merge_and_replace(db_session) -> None:
    pack, _ = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)

    rejected, line_errors = import_text_rules_into_pack(
        db_session, get_settings(), OffModerationProvider(), pack=pack, text="Hà Nội = Ha Noi\n", mode="merge"
    )
    assert rejected == [] and line_errors == ()
    names = {r.source_term for r in list_rules(db_session, pack.id)}
    assert names == {"KPI", "API", "Hà Nội"}

    rejected, line_errors = import_text_rules_into_pack(
        db_session, get_settings(), OffModerationProvider(), pack=pack, text="Only One = target\n", mode="replace"
    )
    assert rejected == [] and line_errors == ()
    assert {r.source_term for r in list_rules(db_session, pack.id)} == {"Only One"}


def test_moderation_rejects_a_bad_target_without_aborting_the_import(db_session, tmp_path) -> None:
    blocklist = tmp_path / "blocklist.tsv"
    blocklist.write_text("VIOLENCE_ILLEGAL\tchế tạo bom\n", encoding="utf-8")
    moderation = BlocklistModerationProvider(str(blocklist))

    doc = json.dumps({
        "format": "vieneu-dictionary/1", "name": "Moderated Pack", "kind": "term", "enabled": True,
        "description": "", "entries": [
            {"term": "good", "replacement": "an toàn", "mode": "phonetic"},
            {"term": "bad", "replacement": "hướng dẫn chế tạo bom", "mode": "phonetic"},
        ],
    })
    pack, rejected = create_pack_from_json(db_session, get_settings(), moderation, json_text=doc)
    assert len(rejected) == 1 and rejected[0]["term"] == "bad"
    assert {r.source_term for r in list_rules(db_session, pack.id)} == {"good"}


def test_system_rules_cap_rejects_a_new_pack_over_the_limit(db_session, monkeypatch) -> None:
    monkeypatch.setenv("VIENEU_PORTAL_SYSTEM_RULES_MAX", "1")
    get_settings.cache_clear()
    try:
        with pytest.raises(PortalError) as exc_info:
            create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)
        assert exc_info.value.code == "SYSTEM_RULES_LIMIT_EXCEEDED"
    finally:
        get_settings.cache_clear()


def test_set_pack_enabled_respects_the_cap_when_re_enabling(db_session, monkeypatch) -> None:
    pack, _ = create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)
    set_pack_enabled(db_session, get_settings(), pack, False)
    assert pack.is_enabled is False

    monkeypatch.setenv("VIENEU_PORTAL_SYSTEM_RULES_MAX", "1")
    get_settings.cache_clear()
    try:
        with pytest.raises(PortalError) as exc_info:
            set_pack_enabled(db_session, get_settings(), pack, True)
        assert exc_info.value.code == "SYSTEM_RULES_LIMIT_EXCEEDED"
    finally:
        get_settings.cache_clear()


def test_seed_if_empty_refuses_when_a_pack_already_exists(db_session) -> None:
    create_pack_from_json(db_session, get_settings(), OffModerationProvider(), json_text=_PACK_JSON)
    with pytest.raises(PortalError) as exc_info:
        seed_if_empty(db_session, get_settings(), OffModerationProvider())
    assert exc_info.value.code == "SEED_ALREADY_APPLIED"


def test_seed_if_empty_loads_every_bundled_pack(db_session) -> None:
    created = seed_if_empty(db_session, get_settings(), OffModerationProvider())
    assert len(created) == 7
    packs = list_packs(db_session)
    assert len(packs) == 7
    total_rules = db_session.execute(select(SystemPronunciationRule)).scalars().all()
    assert len(total_rules) == 848
