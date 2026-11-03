"""`/api/v1/admin/system-dictionaries*`: pack CRUD, JSON and `.txt`
import/export round-trips, `ENGLISH_FALLBACK` rules round-tripping as
`mode: "en"`, and the `If-Match` etag guard on rule replacement.
"""
from __future__ import annotations

import json

from sqlalchemy import select, update

from vieneu_portal.db.models_admin_audit_log import AdminAuditLog
from vieneu_portal.db.models_users_and_sessions import User

_PASSWORD = "correct horse battery"
_FORMAT = "vieneu-dictionary/1"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup_admin(client, db_session, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201
    db_session.execute(update(User).where(User.email == email).values(role="SUPERADMIN"))
    db_session.commit()
    return _csrf(client)


def test_create_via_bare_fields_and_via_json_upload(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss@example.com")

    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Bare pack", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    assert resp.json()["dictionary"]["name"] == "Bare pack"

    payload = {
        "format": _FORMAT, "name": "Uploaded pack", "kind": "name", "enabled": True, "description": "",
        "entries": [{"term": "ABC", "replacement": "a bê xê", "mode": "phonetic", "case_sensitive": False, "note": ""}],
    }
    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps(payload),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    assert resp.json()["dictionary"]["name"] == "Uploaded pack"
    assert resp.json()["rejected"] == []

    rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "sysdict.create")).scalars())
    assert len(rows) == 2


def test_update_enable_and_sort_order_write_one_audit_row(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss2@example.com")
    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Pack A", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    pack_id = resp.json()["dictionary"]["id"]

    resp = client.patch(
        f"/api/v1/admin/system-dictionaries/{pack_id}",
        json={"name": "Pack A renamed", "sort_order": 5, "is_enabled": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()["dictionary"]
    assert body["name"] == "Pack A renamed"
    assert body["sort_order"] == 5

    rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "sysdict.update")).scalars())
    assert len(rows) == 1


def test_replace_rules_etag_mismatch_is_rejected(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss3@example.com")
    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Pack B", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    pack_id = resp.json()["dictionary"]["id"]
    etag = resp.json()["dictionary"]["etag"]

    resp = client.put(
        f"/api/v1/admin/system-dictionaries/{pack_id}/rules",
        json={"rules": [{"term": "km/h", "replacement": "ki lô mét trên giờ", "mode": "phonetic"}]},
        headers={"X-CSRF-Token": csrf, "If-Match": "a-stale-etag"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ETAG_MISMATCH"

    resp = client.put(
        f"/api/v1/admin/system-dictionaries/{pack_id}/rules",
        json={
            "rules": [
                {"term": "km/h", "replacement": "ki lô mét trên giờ", "mode": "phonetic"},
                {"term": "B2B", "replacement": "", "mode": "en"},
            ]
        },
        headers={"X-CSRF-Token": csrf, "If-Match": etag},
    )
    assert resp.status_code == 200
    assert resp.json()["rejected"] == []

    rules_resp = client.get(f"/api/v1/admin/system-dictionaries/{pack_id}/rules")
    rules = {r["source_term"]: r for r in rules_resp.json()["items"]}
    assert rules["km/h"]["rule_kind"] == "REPLACE"
    assert rules["B2B"]["rule_kind"] == "ENGLISH_FALLBACK"


def test_json_export_import_round_trip_preserves_english_fallback_mode(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss4@example.com")
    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Pack C", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    pack_id = resp.json()["dictionary"]["id"]
    client.put(
        f"/api/v1/admin/system-dictionaries/{pack_id}/rules",
        json={"rules": [{"term": "F0", "replacement": "", "mode": "en"}]},
        headers={"X-CSRF-Token": csrf},
    )

    export_resp = client.get(f"/api/v1/admin/system-dictionaries/{pack_id}/export?format=json")
    assert export_resp.status_code == 200
    exported = json.loads(export_resp.text)
    assert exported["entries"][0] == {"term": "F0", "replacement": "", "mode": "en", "case_sensitive": False, "note": ""}

    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Pack D", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    pack_d_id = resp.json()["dictionary"]["id"]
    # `mode=merge`: a JSON import's `name`/`kind` describe the exported pack,
    # not the destination — `replace` would also rename the destination to
    # match and collide with the source pack's own name.
    import_resp = client.post(
        f"/api/v1/admin/system-dictionaries/{pack_d_id}/import?format=json&mode=merge",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("pack.json", export_resp.text, "application/json")},
    )
    assert import_resp.status_code == 200
    rules_resp = client.get(f"/api/v1/admin/system-dictionaries/{pack_d_id}/rules")
    assert rules_resp.json()["items"][0]["rule_kind"] == "ENGLISH_FALLBACK"


def test_txt_export_skips_english_fallback_and_round_trips_replace_rules(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss5@example.com")
    resp = client.post(
        "/api/v1/admin/system-dictionaries", content=json.dumps({"name": "Pack E", "kind": "term"}),
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
    )
    pack_id = resp.json()["dictionary"]["id"]
    client.put(
        f"/api/v1/admin/system-dictionaries/{pack_id}/rules",
        json={
            "rules": [
                {"term": "COVID-19", "replacement": "cô vít mười chín", "mode": "phonetic"},
                {"term": "F1", "replacement": "", "mode": "en"},
            ]
        },
        headers={"X-CSRF-Token": csrf},
    )

    export_resp = client.get(f"/api/v1/admin/system-dictionaries/{pack_id}/export?format=txt")
    assert export_resp.status_code == 200
    assert "COVID-19 = cô vít mười chín" in export_resp.text
    assert "F1" not in export_resp.text
