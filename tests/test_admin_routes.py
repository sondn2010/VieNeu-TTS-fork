"""Admin router end to end on a bare FastAPI app with a temp DB, a stub preprocessor and a fake engine."""
import json
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import vieneu_preprocess
from vieneu_admin import AdminStore, create_admin_router
from vieneu_preprocess.types import Chunk, PreprocessResult

PW = "password123"


def fake_preprocess(text, lexicon=(), *, voices=None, rules_path=None):
    """Stand-in for the story preprocessor: one chunk per line, lexicon applied by plain replace."""
    chunks = []
    for i, line in enumerate(l for l in text.splitlines() if l.strip()):
        speaker, sep, body = line.partition(":")
        speaker, body = (speaker.strip(), body.strip()) if sep else ("Narrator", line.strip())
        for e in lexicon:
            body = body.replace(e.term, e.replacement or e.term)
        chunks.append(Chunk(f"c{i}", speaker, "dialogue", body, pause_after_sec=0.35,
                            voice_preset=(voices or {}).get(speaker)))
    return PreprocessResult(chunks, "\n".join(f"{c.speaker}: {c.text} [0.35]" for c in chunks))


class FakeProvider:
    def __init__(self, available=True):
        self._available, self.calls = available, []

    def available(self):
        return self._available

    def voices(self):
        return ["Mai Anh", "Hải Đăng"]

    def render(self, result, voices, fmt):
        self.calls.append((result, dict(voices), fmt))
        return (b"RIFF" if fmt == "wav" else b"fLaC") + b"\0" * 64


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(vieneu_preprocess, "preprocess", fake_preprocess)
    store = AdminStore(tmp_path / "admin.sqlite3")
    store.create_user("root", PW, "admin")
    store.create_user("bob", PW, "user")
    provider = FakeProvider()
    app = FastAPI()
    app.include_router(create_admin_router(store, tts_provider=provider), prefix="/admin")
    yield store, app, provider
    store.close()


def _token(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "page has no CSRF field"
    return m.group(1)


def login(app, username="root", password=PW):
    c = TestClient(app)
    tok = _token(c.get("/admin/login").text)
    r = c.post("/admin/login", data={"username": username, "password": password, "csrf_token": tok},
               follow_redirects=False)
    assert r.status_code == 303, r.text
    c.csrf = _token(c.get("/admin/").text)
    return c


def post(c, url, **data):
    return c.post(url, data={**data, "csrf_token": c.csrf}, follow_redirects=False)


# -- auth -----------------------------------------------------------------------------
def test_login_logout_and_redirects(env):
    store, app, _ = env
    anon = TestClient(app)
    r = anon.get("/admin/keys", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/login"
    assert anon.get("/admin/keys", headers={"HX-Request": "true"}).headers["HX-Redirect"] == "/admin/login"
    c = login(app)
    cookie = c.cookies.get("vieneu_session")
    assert cookie and store.db.query_one("SELECT COUNT(*) FROM sessions")[0] == 1
    assert cookie not in json.dumps([tuple(r) for r in store.db.query("SELECT * FROM sessions")])
    r = post(c, "/admin/logout")
    assert r.status_code == 303 and store.db.query_one("SELECT COUNT(*) FROM sessions")[0] == 0


def test_login_page_creates_no_session_rows(env):
    store, app, _ = env
    for _ in range(5):
        TestClient(app).get("/admin/login")
    assert store.db.query_one("SELECT COUNT(*) FROM sessions")[0] == 0


def test_login_lockout_by_username_and_ip(env):
    _, app, _ = env
    c = TestClient(app)
    tok = _token(c.get("/admin/login").text)
    for _ in range(5):
        r = c.post("/admin/login", data={"username": "root", "password": "bad", "csrf_token": tok})
        assert r.status_code == 401
    r = c.post("/admin/login", data={"username": "root", "password": PW, "csrf_token": tok})
    assert r.status_code == 429 and "Too many failed attempts" in r.text
    login(app, "bob")  # another account from the same address is unaffected


def test_csrf_required(env):
    _, app, _ = env
    c = TestClient(app)
    c.get("/admin/login")
    assert c.post("/admin/login", data={"username": "root", "password": PW}).status_code == 403
    assert c.post("/admin/login", data={"username": "root", "password": PW,
                                        "csrf_token": "forged.token"}).status_code == 403
    c = login(app)
    assert c.post("/admin/keys", data={"name": "x"}).status_code == 403
    assert c.post("/admin/keys", data={"name": "x", "csrf_token": "a" * 20 + ".b"}).status_code == 403
    assert c.post("/admin/keys", data={"name": "x"}, headers={"X-CSRF-Token": c.csrf}).status_code == 200
    # A token from an anonymous page does not authorize a logged-in user's POST.
    anon_tok = _token(TestClient(app).get("/admin/login").text)
    assert c.post("/admin/keys", data={"name": "x", "csrf_token": anon_tok}).status_code == 403


def test_password_change_and_session_invalidation(env):
    store, app, _ = env
    other = login(app, "bob")
    c = login(app, "bob")
    r = post(c, "/admin/account/password", current=PW, new="newpassword1", confirm="newpassword1")
    assert r.status_code == 200 and "Password changed" in r.text
    assert c.get("/admin/", follow_redirects=False).status_code == 200  # fresh session issued
    assert other.get("/admin/", follow_redirects=False).status_code == 303  # old session ended
    assert post(c, "/admin/keys", name="k").status_code == 403  # CSRF nonce rotated with the session
    c.csrf = _token(r.text)
    assert post(c, "/admin/account/password", current="wrong", new="x" * 9, confirm="x" * 9).status_code == 400


def test_disabling_user_ends_their_session(env):
    store, app, _ = env
    bob = login(app, "bob")
    admin = login(app)
    bob_id = store.get_user_by_name("bob").id
    assert post(admin, f"/admin/users/{bob_id}/active", active="0").status_code == 200
    assert bob.get("/admin/", follow_redirects=False).status_code == 303
    assert post(admin, f"/admin/users/{bob_id}/password", password="anotherpw1").status_code == 200


# -- roles and users ------------------------------------------------------------------
def test_non_admin_gets_403_on_admin_routes(env):
    store, app, _ = env
    c = login(app, "bob")
    d = store.create_dictionary("IT", "term")
    assert c.get("/admin/users").status_code == 403
    for url, data in [("/admin/users", {"username": "x1x", "password": PW}), ("/admin/users/1/role", {"role": "user"}),
                      ("/admin/users/1/delete", {}), ("/admin/dictionaries", {"name": "N", "kind": "term"}),
                      (f"/admin/dictionaries/{d}/toggle", {}), (f"/admin/dictionaries/{d}/delete", {}),
                      (f"/admin/dictionaries/{d}/rename", {"name": "Z"}),
                      (f"/admin/dictionaries/{d}/entries", {"term": "A", "replacement": "a"})]:
        assert post(c, url, **data).status_code == 403, url
    assert c.post("/admin/dictionaries/import", data={"csrf_token": c.csrf, "action": "new"},
                  files={"file": ("d.json", b"{}", "application/json")}).status_code == 403
    assert c.get("/admin/dictionaries").status_code == 200  # read access stays open
    assert "Users</a>" not in c.get("/admin/").text


def test_user_management_and_last_admin_guard(env):
    store, app, _ = env
    c = login(app)
    root_id = store.get_user_by_name("root").id
    assert post(c, "/admin/users", username="carol", password=PW, role="user").status_code == 200
    assert post(c, "/admin/users", username="carol", password=PW).status_code == 400
    r = post(c, f"/admin/users/{root_id}/delete")
    assert r.status_code == 400 and "own account" in r.text
    assert post(c, f"/admin/users/{root_id}/role", role="user").status_code == 400
    carol = store.get_user_by_name("carol").id
    assert post(c, f"/admin/users/{carol}/role", role="admin").status_code == 200
    assert post(c, f"/admin/users/{carol}/delete").status_code == 200
    assert post(c, "/admin/users/9999/delete").status_code == 404


# -- keys -------------------------------------------------------------------------------
def test_key_plaintext_shown_once_and_revoke_idor(env):
    store, app, _ = env
    bob = login(app, "bob")
    r = post(bob, "/admin/keys", name="laptop")
    plain = re.search(r'id="new-key-value">(vn_[^<]+)<', r.text).group(1)
    assert r.headers["cache-control"] == "no-store"
    listing = bob.get("/admin/keys").text
    assert plain not in listing and plain[:8] in listing
    key_id = store.list_keys()[0].id
    eve = (store.create_user("eve", PW), login(app, "eve"))[1]
    assert post(eve, f"/admin/keys/{key_id}/revoke").status_code == 403
    assert store.get_key(key_id).active
    admin = login(app)
    assert "<th>Owner</th>" in admin.get("/admin/keys").text
    assert post(admin, f"/admin/keys/{key_id}/revoke").status_code == 303
    assert not store.get_key(key_id).active
    assert post(bob, "/admin/keys/999/revoke").status_code == 404
    assert post(bob, "/admin/keys", name="").status_code == 400


def test_security_headers_and_static_whitelist(env):
    _, app, _ = env
    c = TestClient(app)
    r = c.get("/admin/login")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    js = c.get("/admin/static/htmx.min.js")
    assert js.status_code == 200 and "htmx 1.9.12" in js.text[:200]
    assert c.get("/admin/static/app.css").status_code == 200
    assert c.get("/admin/static/..%2F__init__.py").status_code == 404
    assert c.get("/admin/static/cli.py").status_code == 404
