"""`system-dict list|seed|import FILE [--mode ...]|export DIR|enable NAME|disable NAME`."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ..dictionaries.system_dictionary_store import (
    DictionaryFormatError,
    create_pack_from_json,
    export_pack_json,
    get_pack_by_name,
    import_json_into_pack,
    import_text_rules_into_pack,
    list_packs,
    seed_if_empty,
    set_pack_enabled,
)
from ..errors import PortalError
from .cli_parser_and_dispatch import current_moderation, current_settings, open_session

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _handle_list(args: argparse.Namespace) -> int:
    db = open_session()
    try:
        for pack in list_packs(db):
            legacy = pack.legacy_source_id or "-"
            print(f"{pack.id}\t{pack.name}\t{pack.kind}\t{'on' if pack.is_enabled else 'off'}\tlegacy={legacy}")
    finally:
        db.close()
    return 0


def _handle_seed(args: argparse.Namespace) -> int:
    db = open_session()
    settings = current_settings()
    try:
        created = seed_if_empty(db, settings, current_moderation(settings))
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"seeded {len(created)} packs: {', '.join(created)}")
    return 0


def _handle_import(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8")
    db = open_session()
    settings = current_settings()
    moderation = current_moderation(settings)
    pack_name = None
    rejected: list = []
    line_errors: tuple = ()
    try:
        if Path(args.file).suffix.lower() == ".json":
            if args.mode == "new":
                pack, rejected = create_pack_from_json(db, settings, moderation, json_text=text)
            else:
                if not args.pack:
                    print("--pack NAME is required for --mode merge|replace", file=sys.stderr)
                    return 1
                pack = get_pack_by_name(db, args.pack)
                rejected = import_json_into_pack(db, settings, moderation, pack=pack, json_text=text, mode=args.mode)
        else:
            if not args.pack:
                print("--pack NAME is required for a .txt/.csv import", file=sys.stderr)
                return 1
            pack = get_pack_by_name(db, args.pack)
            mode = args.mode if args.mode in ("merge", "replace") else "merge"
            rejected, line_errors = import_text_rules_into_pack(db, settings, moderation, pack=pack, text=text, mode=mode)
        pack_name = pack.name
        db.commit()
    except (PortalError, DictionaryFormatError) as exc:
        db.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"imported into {pack_name!r}: {len(rejected)} rejected by moderation, {len(line_errors)} line errors")
    for r in rejected:
        print(f"  rejected: {r}")
    for e in line_errors:
        print(f"  line {e.line}: {e.message}")
    return 0


def _handle_export(args: argparse.Namespace) -> int:
    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db = open_session()
    try:
        packs = list_packs(db)
        for pack in packs:
            slug = _SLUG_RE.sub("-", pack.name.lower()).strip("-") or f"pack-{pack.id}"
            (out_dir / f"{slug}.json").write_text(export_pack_json(db, pack), encoding="utf-8")
    finally:
        db.close()
    print(f"exported {len(packs)} packs to {out_dir}")
    return 0


def _handle_set_enabled(args: argparse.Namespace, enabled: bool) -> int:
    db = open_session()
    settings = current_settings()
    try:
        pack = get_pack_by_name(db, args.name)
        set_pack_enabled(db, settings, pack, enabled)
        db.commit()
    except PortalError as exc:
        db.rollback()
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"{args.name} is now {'enabled' if enabled else 'disabled'}")
    return 0


def add_parsers(top_sub) -> None:
    parser = top_sub.add_parser("system-dict")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list").set_defaults(handler=_handle_list)
    sub.add_parser("seed").set_defaults(handler=_handle_seed)

    import_parser = sub.add_parser("import")
    import_parser.add_argument("file")
    import_parser.add_argument("--mode", choices=["new", "merge", "replace"], default="new")
    import_parser.add_argument("--pack", help="pack name (required for --mode merge|replace, or a .txt/.csv import)")
    import_parser.set_defaults(handler=_handle_import)

    export_parser = sub.add_parser("export")
    export_parser.add_argument("dir")
    export_parser.set_defaults(handler=_handle_export)

    enable_parser = sub.add_parser("enable")
    enable_parser.add_argument("name")
    enable_parser.set_defaults(handler=lambda args: _handle_set_enabled(args, True))

    disable_parser = sub.add_parser("disable")
    disable_parser.add_argument("name")
    disable_parser.set_defaults(handler=lambda args: _handle_set_enabled(args, False))
