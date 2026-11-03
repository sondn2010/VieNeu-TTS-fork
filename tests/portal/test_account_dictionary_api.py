"""`GET/PUT /dictionary`, `POST /dictionary/import`, `GET /dictionary/export`:
TC-14 end to end, etag concurrency, the rule cap, moderation (rejection and
provider outage), export/import round-trip, and that another user's rules
are invisible.
"""
from __future__ import annotations

import io

import vieneu_portal.dictionaries.routes_account_dictionary as routes_mod
from vieneu_portal.moderation.blocklist_moderation_provider import BlocklistModerationProvider

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup(client, email: str) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": email, "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201


def test_get_dictionary_starts_empty(client) -> None:
    _signup(client, "empty@example.com")
    resp = client.get("/api/v1/dictionary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rules"] == [] and body["max_rules"] == 2000 and body["etag"]


def test_put_then_get_round_trips(client) -> None:
    _signup(client, "put@example.com")
    resp = client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "VieNeu", "phonetic_replacement": "Vi Nơi"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rules"]) == 1 and body["rules"][0]["source_term"] == "VieNeu"
    etag = body["etag"]

    resp2 = client.get("/api/v1/dictionary")
    assert resp2.json()["etag"] == etag


def test_stale_if_match_returns_412(client) -> None:
    _signup(client, "stale@example.com")
    client.put("/api/v1/dictionary", json={"rules": [{"source_term": "A", "phonetic_replacement": "a"}]}, headers={"X-CSRF-Token": _csrf(client)})
    resp = client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "B", "phonetic_replacement": "b"}]},
        headers={"X-CSRF-Token": _csrf(client), "If-Match": "not-the-real-etag"},
    )
    assert resp.status_code == 412 and resp.json()["error"]["code"] == "DICTIONARY_CHANGED"


def test_fresh_if_match_succeeds(client) -> None:
    _signup(client, "fresh@example.com")
    first = client.put("/api/v1/dictionary", json={"rules": []}, headers={"X-CSRF-Token": _csrf(client)})
    etag = first.json()["etag"]
    resp = client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "A", "phonetic_replacement": "a"}]},
        headers={"X-CSRF-Token": _csrf(client), "If-Match": etag},
    )
    assert resp.status_code == 200


def test_over_the_cap_returns_422(client) -> None:
    _signup(client, "cap@example.com")
    rules = [{"source_term": f"term{i}", "phonetic_replacement": f"r{i}"} for i in range(2001)]
    resp = client.put("/api/v1/dictionary", json={"rules": rules}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "DICTIONARY_LIMIT_EXCEEDED"


def test_duplicate_source_returns_422(client) -> None:
    _signup(client, "dup@example.com")
    resp = client.put(
        "/api/v1/dictionary",
        json={"rules": [{"source_term": "A", "phonetic_replacement": "a"}, {"source_term": "a", "phonetic_replacement": "a2"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "DUPLICATE_SOURCE"


def test_invalid_rule_returns_422_with_index(client) -> None:
    _signup(client, "invalid@example.com")
    resp = client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "a=b", "phonetic_replacement": "x"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    body = resp.json()
    assert resp.status_code == 422 and body["error"]["code"] == "INVALID_RULE" and body["error"]["index"] == 0


def test_moderation_rejects_a_bad_target(client, tmp_path, monkeypatch) -> None:
    _signup(client, "moderated@example.com")
    blocklist = tmp_path / "blocklist.tsv"
    blocklist.write_text("VIOLENCE_ILLEGAL\tchế tạo bom\n", encoding="utf-8")
    monkeypatch.setattr(routes_mod, "build_moderation_provider", lambda settings: BlocklistModerationProvider(str(blocklist)))

    resp = client.put(
        "/api/v1/dictionary",
        json={"rules": [{"source_term": "a", "phonetic_replacement": "hướng dẫn chế tạo bom"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    body = resp.json()
    assert resp.status_code == 422
    assert body["error"]["code"] == "CONTENT_POLICY_VIOLATION"
    assert body["error"]["index"] == 0 and body["error"]["category"] == "VIOLENCE_ILLEGAL"
    assert client.get("/api/v1/dictionary").json()["rules"] == []   # nothing saved


def test_moderation_outage_returns_503(client, monkeypatch) -> None:
    _signup(client, "outage@example.com")

    class _BrokenProvider:
        def check(self, text):
            raise RuntimeError("provider is down")

    monkeypatch.setattr(routes_mod, "build_moderation_provider", lambda settings: _BrokenProvider())
    resp = client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "a", "phonetic_replacement": "b"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "MODERATION_UNAVAILABLE"
    assert client.get("/api/v1/dictionary").json()["rules"] == []   # nothing saved


def test_tc14_import_merge_new_rules_top_old_gone_comment_ignored(client) -> None:
    _signup(client, "tc14@example.com")
    client.put(
        "/api/v1/dictionary", json={"rules": [{"source_term": "VieNeu", "phonetic_replacement": "Vi Nơi"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )

    import_text = "# a comment\nGPU = Gờ Pê U\nVieNeu = Vi Nêu Mới\n"
    files = {"file": ("import.txt", io.BytesIO(import_text.encode("utf-8")), "text/plain")}
    resp = client.post("/api/v1/dictionary/import", files=files, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 200
    body = resp.json()

    sources = [r["source_term"] for r in body["rules"]]
    assert sources == ["GPU", "VieNeu"]   # new rules first, in file order
    vieneu_rule = next(r for r in body["rules"] if r["source_term"] == "VieNeu")
    assert vieneu_rule["phonetic_replacement"] == "Vi Nêu Mới"   # old VieNeu target is gone
    assert body["errors"] == []   # the comment line produced no error
    assert body["imported_count"] == 2
    assert body["replaced_count"] == 1   # VieNeu existed before and was replaced


def test_import_dry_run_does_not_save(client) -> None:
    _signup(client, "dryrun@example.com")
    before = client.get("/api/v1/dictionary").json()

    files = {"file": ("import.txt", io.BytesIO(b"GPU = Gpu\n"), "text/plain")}
    resp = client.post("/api/v1/dictionary/import?dry_run=true", files=files, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 200
    assert resp.json()["imported_count"] == 1

    after = client.get("/api/v1/dictionary").json()
    assert after == before   # unchanged


def test_export_then_reimport_round_trips(client) -> None:
    _signup(client, "roundtrip@example.com")
    client.put(
        "/api/v1/dictionary",
        json={"rules": [{"source_term": "VieNeu", "phonetic_replacement": "Vi Nơi"}, {"source_term": "GPU", "phonetic_replacement": "Gờ Pê U"}]},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    exported = client.get("/api/v1/dictionary/export?format=txt")
    assert exported.status_code == 200
    assert 'filename="vieneu-dictionary.txt"' in exported.headers["content-disposition"]

    files = {"file": ("reimport.txt", io.BytesIO(exported.content), "text/plain")}
    resp = client.post("/api/v1/dictionary/import", files=files, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 200
    sources = {(r["source_term"], r["phonetic_replacement"]) for r in resp.json()["rules"]}
    assert sources == {("VieNeu", "Vi Nơi"), ("GPU", "Gờ Pê U")}


def test_another_users_rules_are_invisible(client) -> None:
    _signup(client, "owner@example.com")
    client.put("/api/v1/dictionary", json={"rules": [{"source_term": "Secret", "phonetic_replacement": "x"}]}, headers={"X-CSRF-Token": _csrf(client)})

    _signup(client, "other@example.com")   # logs the client in as a different account
    resp = client.get("/api/v1/dictionary")
    assert resp.json()["rules"] == []
