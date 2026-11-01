"""Admin router: dictionaries (inline edits, import/export, preview), Script Lab and Help."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_admin_routes import PW, FakeProvider, env, login, post  # noqa: F401  (env is a fixture)
from vieneu_admin import create_admin_router
from vieneu_preprocess.dictionary_schema import load_dictionary_json


def _doc(name="Hogwarts", entries=None):
    return json.dumps({"format": "vieneu-dictionary/1", "name": name, "kind": "name", "enabled": True,
                       "description": "", "entries": entries if entries is not None else [
                           {"term": "Hogwarts", "replacement": "Hốc-goát", "mode": "phonetic",
                            "case_sensitive": False, "note": ""},
                           {"term": "Scotland", "replacement": "", "mode": "en",
                            "case_sensitive": False, "note": "đọc tiếng Anh"}]}, ensure_ascii=False).encode()


def _import(c, data, **form):
    return c.post("/admin/dictionaries/import", data={"csrf_token": c.csrf, **form},
                  files={"file": ("dict.json", data, "application/json")}, follow_redirects=False)


# -- dictionaries ---------------------------------------------------------------------
def test_import_new_export_round_trip_into_empty_db(env, tmp_path):
    store, app, _ = env
    c = login(app)
    assert _import(c, _doc(), action="new").status_code == 200
    d = store.list_dictionaries()[0]
    exported = c.get(f"/admin/dictionaries/{d.id}/export")
    assert exported.status_code == 200 and 'filename="hogwarts.json"' in exported.headers["content-disposition"]
    from vieneu_admin import AdminStore  # import the export into a brand-new DB
    fresh = AdminStore(tmp_path / "fresh.sqlite3")
    try:
        new_id = fresh.import_dictionary(load_dictionary_json(exported.content))
        assert fresh.export_dictionary(new_id) == store.export_dictionary(d.id)
    finally:
        fresh.close()


def test_import_merge_replace_and_errors(env):
    store, app, _ = env
    c = login(app)
    d = store.create_dictionary("Target", "name")
    merge = _doc(entries=[{"term": "Hagrid", "replacement": "Ha-gờ-rít"}])
    assert _import(c, merge, action="merge", dictionary_id=str(d)).status_code == 200
    assert _import(c, _doc(), action="merge", dictionary_id=str(d)).status_code == 200
    assert {e.term for e in store.export_dictionary(d).entries} == {"Hagrid", "Hogwarts", "Scotland"}
    assert _import(c, merge, action="replace", dictionary_id=str(d)).status_code == 200
    assert [e.term for e in store.export_dictionary(d).entries] == ["Hagrid"]
    r = _import(c, b'{\n  "format": "vieneu-dictionary/1",\n  "name": oops\n}', action="new")
    assert r.status_code == 400 and "line 3, column 11" in r.text
    assert _import(c, _doc(), action="merge").status_code == 400  # no target chosen
    assert _import(c, _doc(), action="replace", dictionary_id="999").status_code == 404
    assert _import(c, b"x" * (5 * 1024 * 1024 + 10), action="new").status_code == 413


def test_inline_entry_add_edit_delete(env):
    store, app, _ = env
    c = login(app)
    d = store.create_dictionary("Names", "name")
    hx = {"HX-Request": "true"}
    r = c.post(f"/admin/dictionaries/{d}/entries", headers=hx,
               data={"csrf_token": c.csrf, "term": "Harry", "replacement": "Ha-ri", "mode": "phonetic"})
    assert r.status_code == 200 and "Ha-ri" in r.text
    bad = c.post(f"/admin/dictionaries/{d}/entries", headers=hx,
                 data={"csrf_token": c.csrf, "term": "Bad", "replacement": "x [1.0]"})
    assert bad.status_code == 400 and "must not contain" in bad.text
    eid = store.search_entries(d)[0][0].id
    assert 'name="term"' in c.get(f"/admin/dictionaries/{d}/entries/{eid}/edit").text
    r = c.post(f"/admin/dictionaries/{d}/entries/{eid}", headers=hx,
               data={"csrf_token": c.csrf, "term": "Harry", "replacement": "Hê-ri", "case_sensitive": "1"})
    assert r.status_code == 200 and "Hê-ri" in r.text
    assert store.get_entry(d, eid).case_sensitive
    assert c.post(f"/admin/dictionaries/{d}/entries/{eid}/delete", headers=hx,
                  data={"csrf_token": c.csrf}).text == ""
    assert store.search_entries(d)[1] == 0


def test_entries_escape_html_and_paginate(env):
    store, app, _ = env
    c = login(app, "bob")
    from vieneu_preprocess.types import LexiconEntry
    d = store.create_dictionary("X", "term", entries=[LexiconEntry(f"t{i:03}", f"r{i}") for i in range(120)]
                                + [LexiconEntry("<script>", "xì")])
    page = c.get(f"/admin/dictionaries/{d}")
    assert "&lt;script&gt;" in page.text and "<script>alert" not in page.text
    assert "Page 1 / 3" in page.text
    r = c.get(f"/admin/dictionaries/{d}?q=t11&page=1", headers={"HX-Request": "true", "HX-Target": "entries-panel"})
    assert "<html" not in r.text and "t110" in r.text and "t050" not in r.text


def test_preview_applies_lexicon(env):
    store, app, _ = env
    c = login(app, "bob")
    store.import_dictionary(load_dictionary_json(_doc()))
    r = post(c, "/admin/dictionaries/preview", text="Harry về Hogwarts.")
    assert r.status_code == 200 and "Hốc-goát" in r.text
    assert post(c, "/admin/dictionaries/preview", text="").status_code == 400


# -- Script Lab -------------------------------------------------------------------------
def test_script_lab_preprocess_download_and_render(env):
    store, app, provider = env
    c = login(app, "bob")
    store.import_dictionary(load_dictionary_json(_doc()))
    text = "Harry: Về Hogwarts thôi.\nMalfoy: Không."
    r = post(c, "/admin/script-lab/preprocess", text=text)
    assert r.status_code == 200 and "Hốc-goát" in r.text and 'value="Malfoy"' in r.text
    js = c.get("/admin/script-lab/download.json").json()
    assert [ch["speaker"] for ch in js] == ["Harry", "Malfoy"]
    r = c.post("/admin/script-lab/render", data={"csrf_token": c.csrf, "text": text, "fmt": "flac",
                                                  "speaker": ["Harry", "Malfoy"], "voice": ["Mai Anh", "evil"]})
    assert r.status_code == 200 and "<audio" in r.text
    result, voices, fmt = provider.calls[-1]
    assert fmt == "flac" and voices == {"Harry": "Mai Anh"}  # unknown voices are dropped
    audio = c.get("/admin/script-lab/audio")
    assert audio.headers["content-type"] == "audio/flac" and audio.content.startswith(b"fLaC")
    assert "attachment" in c.get("/admin/script-lab/audio?download=1").headers["content-disposition"]
    r = c.post("/admin/script-lab/render", data={"csrf_token": c.csrf, "text": "Xin chào."})
    assert r.status_code == 200 and provider.calls[-1][2] == "wav"  # WAV is the default


def test_script_lab_limits(env):
    _, app, provider = env
    c = login(app, "bob")
    assert post(c, "/admin/script-lab/preprocess", text="a" * 50_001).status_code == 400
    assert post(c, "/admin/script-lab/preprocess", text="a" * 3_001).status_code == 200
    r = post(c, "/admin/script-lab/render", text="a" * 3_001)
    assert r.status_code == 400 and "CLI" in r.text
    assert post(c, "/admin/script-lab/render", text="hi", fmt="mp3").status_code == 400
    assert provider.calls == []
    assert c.get("/admin/script-lab/audio").status_code == 404


def test_script_lab_without_engine(env):
    store, _, _ = env
    app = FastAPI()
    app.include_router(create_admin_router(store, tts_provider=None), prefix="/admin")
    c = login(app, "bob")
    assert "Engine not loaded" in c.get("/admin/script-lab").text
    assert post(c, "/admin/script-lab/render", text="hi").status_code == 503


# -- Help -------------------------------------------------------------------------------
@pytest.fixture
def docs(tmp_path, monkeypatch):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "user-guide.md").write_text("# Guide\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n<script>x()</script>\n",
                                     encoding="utf-8")
    (d / "user-guide.vi.md").write_text("# Hướng dẫn\n", encoding="utf-8")
    (tmp_path / "secret.md").write_text("TOP SECRET", encoding="utf-8")
    monkeypatch.setenv("VIENEU_DOCS_DIR", str(d))
    return d


def test_help_renders_both_languages_and_escapes_html(env, docs):
    _, app, _ = env
    c = login(app, "bob")
    en = c.get("/admin/help?doc=guide&lang=en")
    assert en.status_code == 200 and "<h1>Guide</h1>" in en.text and "<table>" in en.text
    assert "&lt;script&gt;x()&lt;/script&gt;" in en.text and "<script>x()" not in en.text
    assert "Hướng dẫn" in c.get("/admin/help?doc=guide&lang=vi").text
    missing = c.get("/admin/help?doc=functions&lang=en")
    assert missing.status_code == 200 and "not available" in missing.text and str(docs) not in missing.text


@pytest.mark.parametrize("query", ["doc=../secret&lang=en", "doc=guide&lang=../../secret",
                                   "doc=..%2Fsecret&lang=en", "doc=user-guide&lang=en", "doc=guide&lang=fr"])
def test_help_rejects_unknown_doc_or_lang(env, docs, query):
    _, app, _ = env
    r = login(app, "bob").get(f"/admin/help?{query}")
    assert r.status_code in (404, 422) and "TOP SECRET" not in r.text
