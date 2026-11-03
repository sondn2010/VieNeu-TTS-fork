"""`text preview TEXT [--user EMAIL] [--voice ID]`: runs `build_engine_text`
with the DB rules (the system layer, plus the given user's account rules)
and prints the processed text, char count and tokens — replaces the old
admin app's Script Lab preview with output identical to what the portal
actually sends to the engine, since it reuses phase 9's own
`load_rules_for_synthesis` / system-layer cache rather than a parallel copy.
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from ..db.models_users_and_sessions import User
from ..dictionaries.rules_for_synthesis_loader import load_rules_for_synthesis
from ..dictionaries.system_rule_layer_cache import get_cached_system_rules
from ..text.engine_text_pipeline import build_engine_text
from ..text.pronunciation_rule_types import compile_rules
from .cli_parser_and_dispatch import current_moderation, current_settings, open_session


def _handle_preview(args: argparse.Namespace) -> int:
    settings = current_settings()
    db = open_session()
    try:
        moderation = current_moderation(settings)
        if args.user:
            user = db.execute(select(User).where(func.lower(User.email) == args.user.strip().lower())).scalar_one_or_none()
            if user is None:
                print(f"no user with email {args.user!r}", file=sys.stderr)
                return 1
            compiled = load_rules_for_synthesis(db, user.id)
        else:
            compiled = compile_rules(get_cached_system_rules(db))
        try:
            result = build_engine_text(args.text, compiled, moderation, settings)
        except Exception as exc:   # noqa: BLE001 - CLI boundary: print and exit, never a traceback
            print(f"error: {exc}", file=sys.stderr)
            return 1
    finally:
        db.close()
    print(f"voice: {args.voice or '(default)'}")
    print(f"chars: {result.char_count}  processed_chars: {result.processed_char_count}  tokens: {result.estimated_tokens}")
    print("---")
    print(result.processed_text)
    return 0


def add_parsers(top_sub) -> None:
    parser = top_sub.add_parser("text")
    sub = parser.add_subparsers(dest="command", required=True)
    preview_parser = sub.add_parser("preview")
    preview_parser.add_argument("text")
    preview_parser.add_argument("--user", help="account email whose dictionary rules to include")
    preview_parser.add_argument("--voice", help="voice id (display only)")
    preview_parser.set_defaults(handler=_handle_preview)
