"""Catalog derivation (pure, no DB) and sync (against the real Postgres
fixtures): slug/initials/gender/region mapping, slug-collision detection, and
the insert/deactivate/never-touch-existing sync semantics.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from vieneu_portal.db.models_voices_and_recordings import Voice
from vieneu_portal.engine.engine_http_client import EngineVoice
from vieneu_portal.voices.voice_catalog_from_engine import (
    VoiceSyncError,
    derive_voice_rows,
    initials_from_name,
    slug_id,
    sync_voice_catalog,
)

_BUNDLED_25_NAMES = [
    "Hải Đăng", "Mai Anh", "Minh Quân", "Thu Hà", "Việt Anh", "Ngọc Lan", "Quang Huy", "Thanh Tâm",
    "Hoàng Nam", "Kim Chi", "Tấn Phát", "Diễm My", "Bảo Long", "Thùy Linh", "Đức Anh", "Phương Thảo",
    "Gia Bảo", "Yến Nhi", "Trung Kiên", "Ánh Dương", "Xuân Mai", "Lan Anh", "Công Thành", "Bích Ngọc",
    "Anh Tuấn",
]


def _engine_voices(names, *, featured_name=None) -> list:
    return [
        EngineVoice(id=name, name=name, description="Nam · Bắc" if i % 2 == 0 else "Nữ · Trung",
                    gender="male" if i % 2 == 0 else "female", featured=(name == featured_name), aliases=[])
        for i, name in enumerate(names)
    ]


def test_slug_id_matches_the_spec_example():
    assert slug_id("Hải Đăng") == "hai-dang"


def test_initials_from_name_first_and_last_word():
    assert initials_from_name("Hải Đăng") == "HĐ"
    assert initials_from_name("Mai") == "M"


def test_derive_rows_gives_unique_slugs_over_the_bundled_25_names():
    rows = derive_voice_rows(_engine_voices(_BUNDLED_25_NAMES), "V4")
    ids = [r.id for r in rows]
    assert len(ids) == len(set(ids)) == 25


def test_derive_rows_maps_gender_and_region_from_description():
    rows = derive_voice_rows(_engine_voices(["Hải Đăng"]), "V4")
    assert rows[0].gender == "NAM" and rows[0].region == "MIEN_BAC"
    rows2 = derive_voice_rows(
        [EngineVoice(id="X", name="X", description="Nữ · Trung", gender="female", featured=False, aliases=[])],
        "V4",
    )
    assert rows2[0].gender == "NU" and rows2[0].region == "MIEN_TRUNG"


def test_derive_rows_sorts_featured_first_then_name():
    rows = derive_voice_rows(_engine_voices(["Zoe", "Anna", "Bao"], featured_name="Zoe"), "V4")
    assert [r.name for r in rows] == ["Zoe", "Anna", "Bao"]
    assert [r.sort_order for r in rows] == [0, 1, 2]


def test_derive_rows_raises_on_slug_collision():
    voices = [
        EngineVoice(id="Adam", name="Adam", description="Nam · Bắc", gender="male", featured=False, aliases=[]),
        EngineVoice(id="Adam!", name="Adam!", description="Nam · Bắc", gender="male", featured=False, aliases=[]),
    ]
    with pytest.raises(VoiceSyncError, match="slug collision"):
        derive_voice_rows(voices, "V4")


def test_derive_rows_raises_when_gender_and_region_are_unknown():
    voices = [EngineVoice(id="Ẩn danh", name="Ẩn danh", description="", gender="", featured=False, aliases=[])]
    with pytest.raises(VoiceSyncError):
        derive_voice_rows(voices, "V4")


class _FakeEngineClient:
    def __init__(self, voices):
        self._voices = voices

    def list_voices(self):
        return self._voices


def test_sync_inserts_new_voices_and_is_a_no_op_on_rerun(db_session):
    client = _FakeEngineClient(_engine_voices(["Hải Đăng", "Mai Anh"]))
    result = sync_voice_catalog(db_session, client, "V4")
    assert set(result.inserted) == {"hai-dang", "mai-anh"}
    assert result.deactivated == []

    result2 = sync_voice_catalog(db_session, client, "V4")
    assert result2.inserted == [] and result2.deactivated == []
    assert db_session.execute(select(Voice)).scalars().all().__len__() == 2


def test_sync_deactivates_a_voice_removed_from_the_engine(db_session):
    client = _FakeEngineClient(_engine_voices(["Hải Đăng", "Mai Anh"]))
    sync_voice_catalog(db_session, client, "V4")

    client2 = _FakeEngineClient(_engine_voices(["Hải Đăng"]))
    result = sync_voice_catalog(db_session, client2, "V4")
    assert result.deactivated == ["mai-anh"]

    mai_anh = db_session.get(Voice, "mai-anh")
    assert mai_anh.is_active is False


def test_sync_never_overwrites_an_admin_edited_row(db_session):
    client = _FakeEngineClient(_engine_voices(["Hải Đăng"]))
    sync_voice_catalog(db_session, client, "V4")

    row = db_session.get(Voice, "hai-dang")
    row.name = "Admin Edited Name"
    row.tags = ["custom"]
    db_session.commit()

    sync_voice_catalog(db_session, client, "V4")

    row2 = db_session.get(Voice, "hai-dang")
    assert row2.name == "Admin Edited Name"
    assert list(row2.tags) == ["custom"]


def test_sync_engine_failure_touches_no_row(db_session):
    client = _FakeEngineClient(_engine_voices(["Hải Đăng"]))
    sync_voice_catalog(db_session, client, "V4")

    class _BrokenEngineClient:
        def list_voices(self):
            raise RuntimeError("engine down")

    with pytest.raises(RuntimeError):
        sync_voice_catalog(db_session, _BrokenEngineClient(), "V4")

    assert db_session.get(Voice, "hai-dang").is_active is True
    assert len(db_session.execute(select(Voice)).scalars().all()) == 1
