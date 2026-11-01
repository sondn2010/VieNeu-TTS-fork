"""Admin maintenance CLI: ``python -m vieneu_admin <command>``.

Commands: create-admin USER, reset-password USER, export-dicts DIR, import-dict FILE.
The database path comes from ``--db`` or ``VIENEU_ADMIN_DB`` (default vieneu_data/admin.sqlite3).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from typing import Optional, Sequence

from vieneu_preprocess.dictionary_schema import DictionaryFormatError, dump_dictionary_json, load_dictionary_json

from .models import StoreError
from .store import AdminStore
from .store_dictionaries import slugify


def _prompt_password() -> str:
    first = getpass.getpass("Password: ")
    if first != getpass.getpass("Repeat password: "):
        raise StoreError("Passwords do not match.")
    return first


def cmd_create_admin(store: AdminStore, args: argparse.Namespace) -> int:
    if store.get_user_by_name(args.username) is not None:
        raise StoreError(f"User {args.username!r} already exists; use reset-password.")
    store.create_user(args.username, _prompt_password(), "admin")
    print(f"Admin {args.username!r} created.")
    return 0


def cmd_reset_password(store: AdminStore, args: argparse.Namespace) -> int:
    user = store.get_user_by_name(args.username)
    if user is None:
        raise StoreError(f"User {args.username!r} not found.")
    store.reset_password(user.id, _prompt_password())
    print(f"Password for {user.username!r} reset; their sessions were ended.")
    return 0


def cmd_export_dicts(store: AdminStore, args: argparse.Namespace) -> int:
    out = Path(args.directory)
    out.mkdir(parents=True, exist_ok=True)
    for info in store.list_dictionaries():
        path = out / f"{slugify(info.name, f'dictionary-{info.id}')}.json"
        path.write_text(dump_dictionary_json(store.export_dictionary(info.id)) + "\n", encoding="utf-8")
        print(f"wrote {path} ({info.entry_count} entries)")
    return 0


def cmd_import_dict(store: AdminStore, args: argparse.Namespace) -> int:
    parsed = load_dictionary_json(Path(args.file).read_bytes())
    existing = next((d for d in store.list_dictionaries() if d.name.casefold() == parsed.name.casefold()), None)
    if args.mode == "new" or existing is None:
        if existing is not None:
            raise StoreError(f"Dictionary {parsed.name!r} exists; pass --mode merge or --mode replace.")
        store.import_dictionary(parsed)
        print(f"Imported {parsed.name!r} ({len(parsed.entries)} entries).")
    elif args.mode == "merge":
        print(f"Merged {store.merge_entries(existing.id, parsed.entries)} entries into {existing.name!r}.")
    else:
        print(f"Replaced {existing.name!r} with {store.replace_entries(existing.id, parsed.entries)} entries.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m vieneu_admin", description="VieNeu admin maintenance")
    p.add_argument("--db", help="SQLite path (default: $VIENEU_ADMIN_DB or vieneu_data/admin.sqlite3)")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("create-admin", help="create an admin account (prompts for the password)")
    s.add_argument("username")
    s.set_defaults(func=cmd_create_admin)
    s = sub.add_parser("reset-password", help="set a new password and end the user's sessions")
    s.add_argument("username")
    s.set_defaults(func=cmd_reset_password)
    s = sub.add_parser("export-dicts", help="write every dictionary as <slug>.json into DIR")
    s.add_argument("directory")
    s.set_defaults(func=cmd_export_dicts)
    s = sub.add_parser("import-dict", help="import one vieneu-dictionary/1 JSON file")
    s.add_argument("file")
    s.add_argument("--mode", choices=("new", "merge", "replace"), default="new",
                   help="new (default), or merge/replace into the dictionary with the same name")
    s.set_defaults(func=cmd_import_dict)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = AdminStore(args.db)
    except Exception as e:  # unreadable path, corrupt file, failed migration
        print(f"error: cannot open admin database: {e}", file=sys.stderr)
        return 2
    try:
        return args.func(store, args)
    except (StoreError, DictionaryFormatError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("aborted", file=sys.stderr)
        return 130
    finally:
        store.close()
