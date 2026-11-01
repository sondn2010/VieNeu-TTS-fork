"""`python -m vieneu_admin` maintenance commands."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from vieneu_admin import AdminStore, cli

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "admin.sqlite3")


def _passwords(monkeypatch, *values):
    it = iter(values)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(it))


def test_create_admin_and_reset_password(db, monkeypatch, capsys):
    _passwords(monkeypatch, "password123", "password123")
    assert cli.main(["--db", db, "create-admin", "boss"]) == 0
    _passwords(monkeypatch, "password123", "password123")
    assert cli.main(["--db", db, "create-admin", "boss"]) == 1  # already exists
    _passwords(monkeypatch, "newpass123", "different")
    assert cli.main(["--db", db, "reset-password", "boss"]) == 1  # mismatch
    _passwords(monkeypatch, "newpass123", "newpass123")
    assert cli.main(["--db", db, "reset-password", "boss"]) == 0
    assert cli.main(["--db", db, "reset-password", "ghost"]) == 1
    store = AdminStore(db)
    try:
        assert store.authenticate("boss", "newpass123").is_admin
    finally:
        store.close()


def test_export_and_import_round_trip(db, tmp_path):
    doc = {"format": "vieneu-dictionary/1", "name": "Từ điển IT", "kind": "term",
           "entries": [{"term": "API", "replacement": "ây-pi-ai", "case_sensitive": True}]}
    src = tmp_path / "in.json"
    src.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert cli.main(["--db", db, "import-dict", str(src)]) == 0
    assert cli.main(["--db", db, "import-dict", str(src)]) == 1  # name exists without --mode
    assert cli.main(["--db", db, "import-dict", str(src), "--mode", "merge"]) == 0
    out = tmp_path / "out"
    assert cli.main(["--db", db, "export-dicts", str(out)]) == 0
    exported = json.loads((out / "tu-dien-it.json").read_text(encoding="utf-8"))
    assert exported["entries"][0]["replacement"] == "ây-pi-ai"
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    assert cli.main(["--db", db, "import-dict", str(bad)]) == 1


def test_cli_does_not_import_fastapi(db):
    code = ("import sys; from vieneu_admin import cli; "
            "assert 'fastapi' not in sys.modules, 'CLI pulled in FastAPI'")
    subprocess.run([sys.executable, "-c", code], check=True, env={"PYTHONPATH": str(SRC), "SYSTEMROOT": "C:\\Windows"}
                   if sys.platform == "win32" else {"PYTHONPATH": str(SRC)})
