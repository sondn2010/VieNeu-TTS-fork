"""AdminStore: users, sessions, API keys, dictionaries, lexicon cache, seeding, threading."""
import json
import threading
import time

import pytest

from vieneu_admin import AdminStore, verify_api_key
from vieneu_admin.models import ForbiddenError, NotFoundError, StoreError
from vieneu_admin.store_dictionaries import slugify, validate_entry
from vieneu_preprocess.types import LexiconEntry


@pytest.fixture
def store(tmp_path):
    s = AdminStore(tmp_path / "admin.sqlite3")
    yield s
    s.close()


def _seed_doc(name, kind="term", entries=None, enabled=True):
    return json.dumps({"format": "vieneu-dictionary/1", "name": name, "kind": kind, "enabled": enabled,
                       "entries": entries or [{"term": "API", "replacement": "ây-pi-ai", "case_sensitive": True}]},
                      ensure_ascii=False)


# -- users and sessions -----------------------------------------------------------
def test_create_user_validation_and_case_insensitive_unique(store):
    u = store.create_user("Alice", "password1")
    assert u.role == "user" and u.active
    with pytest.raises(StoreError):
        store.create_user("alice", "password1")
    for name, pw, role in [("ab", "password1", "user"), ("bad name", "password1", "user"),
                           ("bob", "short", "user"), ("bob", "password1", "root")]:
        with pytest.raises(StoreError):
            store.create_user(name, pw, role)
    assert store.authenticate("ALICE", "password1").id == u.id
    assert store.authenticate("alice", "nope") is None and store.authenticate("ghost", "x") is None


def test_last_active_admin_is_protected(store):
    admin = store.create_user("root", "password1", "admin")
    for action in (lambda: store.set_role(admin.id, "user"), lambda: store.set_active(admin.id, False),
                   lambda: store.delete_user(admin.id)):
        with pytest.raises(StoreError):
            action()
    second = store.create_user("root2", "password1", "admin")
    store.set_role(admin.id, "user")
    with pytest.raises(StoreError):
        store.delete_user(second.id)
    with pytest.raises(NotFoundError):
        store.delete_user(999)


def test_disable_and_password_reset_end_sessions(store):
    store.create_user("root", "password1", "admin")
    u = store.create_user("bob", "password1")
    tok1, _ = store.create_session(u.id)
    assert store.get_session(tok1).user.id == u.id
    store.reset_password(u.id, "password2")
    assert store.get_session(tok1) is None
    tok2, _ = store.create_session(u.id)
    store.set_active(u.id, False)
    assert store.get_session(tok2) is None
    assert store.authenticate("bob", "password2") is None  # disabled cannot log in
    with pytest.raises(StoreError):
        store.create_session(u.id)


def test_session_expiry_and_hash_only_storage(store):
    u = store.create_user("bob", "password1")
    tok, sess = store.create_session(u.id)
    raw = store.db.query("SELECT token_hash FROM sessions")
    assert all(tok != r[0] for r in raw) and sess.token_hash == raw[0][0]
    store.db.conn().execute("UPDATE sessions SET expires_at = ?", (int(time.time()) - 1,))
    assert store.get_session(tok) is None
    assert store.purge_expired_sessions() == 1
    assert store.get_session("x" * 500) is None


def test_bootstrap_admin_only_when_no_active_admin(store):
    assert store.bootstrap_admin("boss", "password1") is True
    assert store.authenticate("boss", "password1").is_admin
    store.reset_password(store.get_user_by_name("boss").id, "changed-later")
    assert store.bootstrap_admin("boss", "password1") is False  # never overwrites
    assert store.authenticate("boss", "changed-later") is not None


# -- API keys ---------------------------------------------------------------------
def test_key_lifecycle_and_verify(store, tmp_path):
    store.create_user("root", "password1", "admin")
    u = store.create_user("bob", "password1")
    plain, key = store.create_key(u.id, " laptop ")
    assert key.name == "laptop" and key.prefix == plain[:8]
    owner = verify_api_key(store, f"Bearer {plain}")
    assert (owner.user_id, owner.key_name) == (u.id, "laptop")
    assert verify_api_key(store, f"bearer {plain}") is not None
    for bad in (None, "", plain, f"Basic {plain}", "Bearer vn_nope", "Bearer " + "x" * 300):
        assert verify_api_key(store, bad) is None
    # Plaintext never reaches the DB file.
    store.db.conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    assert plain.encode() not in (tmp_path / "admin.sqlite3").read_bytes()
    store.set_active(u.id, False)
    assert verify_api_key(store, f"Bearer {plain}") is None
    store.set_active(u.id, True)
    store.revoke_key(key.id, u)
    assert verify_api_key(store, f"Bearer {plain}") is None
    assert store.count_keys(u.id) == 0


def test_revoke_enforces_owner_unless_admin(store):
    admin = store.create_user("root", "password1", "admin")
    bob, eve = store.create_user("bob", "password1"), store.create_user("eve", "password1")
    _, key = store.create_key(bob.id, "k")
    with pytest.raises(ForbiddenError):
        store.revoke_key(key.id, eve)
    assert store.get_key(key.id).active
    assert not store.revoke_key(key.id, admin).active
    with pytest.raises(NotFoundError):
        store.revoke_key(12345, admin)
    assert [k.username for k in store.list_keys()] == ["bob"]
    assert store.list_keys(eve.id) == []


def test_last_used_is_throttled(store):
    u = store.create_user("bob", "password1")
    plain, key = store.create_key(u.id, "k")
    store.lookup(plain)
    first = store.get_key(key.id).last_used_at
    assert first is not None
    store.db.conn().execute("UPDATE api_keys SET last_used_at = ?", (first - 10,))
    store.lookup(plain)
    assert store.get_key(key.id).last_used_at == first - 10  # within a minute: unchanged
    store.db.conn().execute("UPDATE api_keys SET last_used_at = ?", (first - 120,))
    store.lookup(plain)
    assert store.get_key(key.id).last_used_at >= first


# -- dictionaries -------------------------------------------------------------------
def test_dictionary_crud_search_and_lexicon_cache(store, tmp_path):
    d = store.create_dictionary("Names", "name", "people")
    store.upsert_entry(d, validate_entry("Harry", "Ha-ri"))
    e = store.upsert_entry(d, validate_entry("100%_x", "trăm"))
    with pytest.raises(StoreError):
        store.upsert_entry(d, validate_entry("harry", "khác"))  # same case-insensitive key
    assert {x.term for x in store.enabled_lexicon()} == {"Harry", "100%_x"}
    rows, total = store.search_entries(d, "%_")
    assert total == 1 and rows[0].id == e.id  # LIKE wildcards are escaped
    other = AdminStore(tmp_path / "admin.sqlite3")  # simulates a CLI process writing
    try:
        other.toggle_dictionary(d)
    finally:
        other.close()
    assert store.enabled_lexicon() == []  # cache invalidated through the DB version counter
    store.set_dictionary_enabled(d, True)
    store.rename_dictionary(d, "Characters")
    assert store.get_dictionary(d).name == "Characters"
    with pytest.raises(StoreError):
        store.create_dictionary("characters", "term")
    store.delete_entry(d, e.id)
    with pytest.raises(NotFoundError):
        store.delete_entry(d, e.id)
    store.delete_dictionary(d)
    assert store.list_dictionaries() == []


def test_merge_and_replace_entries(store):
    d = store.create_dictionary("IT", "term", entries=[LexiconEntry("API", "ây-pi-ai", case_sensitive=True),
                                                        LexiconEntry("Docker", "", "en")])
    store.merge_entries(d, [LexiconEntry("API", "a-pi", case_sensitive=True), LexiconEntry("Git", "ghít")])
    got = {e.term: e.replacement for e in store.export_dictionary(d).entries}
    assert got == {"API": "a-pi", "Docker": "", "Git": "ghít"}
    store.replace_entries(d, [LexiconEntry("Only", "ôn-li")])
    assert [e.term for e in store.export_dictionary(d).entries] == ["Only"]


def test_validate_entry_uses_schema_rules():
    assert validate_entry(" C++ ", "xi cộng cộng").term == "C++"
    for args in [("", "x"), ("X", ""), ("X", "a [0.5]"), ("X", "<|emotion_1|>"), ("X", "y", "bogus")]:
        with pytest.raises(StoreError):
            validate_entry(*args)


def test_seed_if_empty(store, tmp_path):
    seeds = tmp_path / "seed"
    seeds.mkdir()
    (seeds / "a.json").write_text(_seed_doc("Alpha"), encoding="utf-8")
    (seeds / "b.json").write_text("{broken", encoding="utf-8")
    assert store.seed_if_empty(seeds) == 1
    assert store.seed_if_empty(seeds) == 0  # never re-seeds a non-empty DB
    assert store.seed_if_empty(tmp_path / "missing") == 0


def test_slugify():
    assert slugify("Từ điển Hogwarts!", "x") == "tu-dien-hogwarts"
    assert slugify("???", "fallback") == "fallback"


def test_concurrent_threads_use_separate_connections(store):
    u = store.create_user("bob", "password1")
    errors, conns = [], set()

    def worker(i):
        try:
            conns.add(id(store.db.conn()))
            for j in range(10):
                plain, _ = store.create_key(u.id, f"k{i}-{j}")
                assert store.lookup(plain) is not None
        except Exception as e:  # pragma: no cover - surfaced below
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(conns) == 8
    assert store.count_keys(u.id) == 80
