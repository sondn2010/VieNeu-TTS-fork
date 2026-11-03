"""`GET/PUT /dictionary`, `POST /dictionary/import`, `GET /dictionary/export`:
one account's own pronunciation dictionary. Every query filters by the
session's `user_id` — there is no id in any URL, so there is no IDOR surface.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Header, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, require_csrf, require_user
from ..config import get_settings
from ..db.session_factory import get_db
from ..errors import PortalError
from ..moderation.moderation_provider_factory import build_moderation_provider
from ..moderation.moderation_provider_interface import ContentPolicyViolation, ModerationUnavailable
from ..text.engine_text_pipeline import check_moderation_or_raise
from ..text.dictionary_import_export_and_merge import (
    MAX_IMPORT_BYTES,
    ImportedRule,
    ImportTooLargeError,
    export_dictionary_txt,
    merge_imported_rules,
    parse_dictionary_import,
    validate_rule,
)
from .account_dictionary_store import MAX_RULES, RuleInput, compute_etag, list_rules, replace_all_rules

router = APIRouter()


class DictionaryRuleIn(BaseModel):
    source_term: str
    phonetic_replacement: str
    match_whole_word: bool = True
    case_sensitive: bool = False
    is_enabled: bool = True


class PutDictionaryRequest(BaseModel):
    rules: list[DictionaryRuleIn]


def _serialize_rule(r) -> dict:
    return {
        "id": str(r.id), "source_term": r.source_term, "phonetic_replacement": r.phonetic_replacement,
        "match_whole_word": r.match_whole_word, "case_sensitive": r.case_sensitive,
        "is_enabled": r.is_enabled, "sort_order": r.sort_order,
    }


def _validate_no_duplicates(rules) -> None:
    """Field-level checks (phase 7's `validate_rule`) plus duplicate-source
    detection; raises on the first problem, naming its index.
    """
    seen: dict = {}
    for i, r in enumerate(rules):
        errors = validate_rule(r.source_term, r.phonetic_replacement)
        if errors:
            raise PortalError(422, "INVALID_RULE", "; ".join(errors), index=i)
        key = r.source_term if r.case_sensitive else r.source_term.lower()
        if key in seen:
            raise PortalError(422, "DUPLICATE_SOURCE", f"duplicate source term at index {i}", index=i, duplicate_of_index=seen[key])
        seen[key] = i


def _moderate_targets(rules, moderation, settings) -> None:
    """Moderates every non-empty target. Raises on the first rejection
    (`422 CONTENT_POLICY_VIOLATION`, naming its index and category) or the
    first provider outage (`503 MODERATION_UNAVAILABLE`); nothing is saved
    either way.
    """
    for i, r in enumerate(rules):
        target = r.phonetic_replacement if hasattr(r, "phonetic_replacement") else r.target
        if not target:
            continue
        try:
            check_moderation_or_raise(moderation, target, settings)
        except ContentPolicyViolation as exc:
            raise PortalError(422, "CONTENT_POLICY_VIOLATION", exc.message, index=i, category=exc.category)
        except ModerationUnavailable as exc:
            raise PortalError(503, "MODERATION_UNAVAILABLE", str(exc))


@router.get("/dictionary")
def get_dictionary(db: Session = Depends(get_db), ctx: AuthContext = Depends(require_user)) -> dict:
    rules = list_rules(db, ctx.user.id)
    return {"rules": [_serialize_rule(r) for r in rules], "max_rules": MAX_RULES, "etag": compute_etag(rules)}


@router.put("/dictionary")
def put_dictionary(
    payload: PutDictionaryRequest,
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    current_rules = list_rules(db, ctx.user.id)
    if if_match is not None and if_match != compute_etag(current_rules):
        raise PortalError(412, "DICTIONARY_CHANGED", "the dictionary changed since you last loaded it")

    if len(payload.rules) > MAX_RULES:
        raise PortalError(422, "DICTIONARY_LIMIT_EXCEEDED", f"at most {MAX_RULES} rules")

    _validate_no_duplicates(payload.rules)
    _moderate_targets(payload.rules, build_moderation_provider(settings), settings)

    saved = replace_all_rules(db, ctx.user.id, [
        RuleInput(r.source_term, r.phonetic_replacement, r.match_whole_word, r.case_sensitive, r.is_enabled)
        for r in payload.rules
    ])
    db.commit()
    return {"rules": [_serialize_rule(r) for r in saved], "max_rules": MAX_RULES, "etag": compute_etag(saved)}


@router.post("/dictionary/import")
def import_dictionary(
    dry_run: bool = False,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()

    raw = file.file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise PortalError(422, "FILE_TOO_LARGE", f"file must be at most {MAX_IMPORT_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise PortalError(422, "FILE_NOT_UTF8", "file must be UTF-8 encoded")

    try:
        imported, parse_errors = parse_dictionary_import(text)
    except ImportTooLargeError as exc:
        raise PortalError(422, "FILE_TOO_LARGE", str(exc))

    current_rules = list_rules(db, ctx.user.id)
    existing_as_imported = [
        ImportedRule(source=r.source_term, target=r.phonetic_replacement, whole_word=r.match_whole_word,
                     case_sensitive=r.case_sensitive)
        for r in current_rules
    ]
    merge_result = merge_imported_rules(existing_as_imported, imported)
    if merge_result.error:
        raise PortalError(422, "DICTIONARY_LIMIT_EXCEEDED", f"at most {MAX_RULES} rules after merge")

    merged = list(merge_result.rules)
    _moderate_targets(merged, build_moderation_provider(settings), settings)

    existing_keys = {r.source.lower() if not r.case_sensitive else r.source for r in existing_as_imported}
    imported_keys = {r.source.lower() if not r.case_sensitive else r.source for r in imported}
    replaced_count = len(existing_keys & imported_keys)

    if dry_run:
        return {
            "rules": [
                {"source_term": r.source, "phonetic_replacement": r.target, "match_whole_word": r.whole_word,
                 "case_sensitive": r.case_sensitive, "is_enabled": True, "sort_order": i}
                for i, r in enumerate(merged)
            ],
            "imported_count": len(imported), "replaced_count": replaced_count,
            "errors": [{"line": e.line, "reason": e.message} for e in parse_errors],
            "etag": compute_etag(current_rules),
        }

    saved = replace_all_rules(db, ctx.user.id, [
        RuleInput(r.source, r.target, r.whole_word, r.case_sensitive, True) for r in merged
    ])
    db.commit()
    return {
        "rules": [_serialize_rule(r) for r in saved],
        "imported_count": len(imported), "replaced_count": replaced_count,
        "errors": [{"line": e.line, "reason": e.message} for e in parse_errors],
        "etag": compute_etag(saved),
    }


@router.get("/dictionary/export")
def export_dictionary(
    format: str = "txt", db: Session = Depends(get_db), ctx: AuthContext = Depends(require_user),
) -> Response:
    if format not in ("txt", "csv"):
        raise PortalError(422, "VALIDATION_ERROR", "format must be 'txt' or 'csv'")
    rules = list_rules(db, ctx.user.id)
    imported = [
        ImportedRule(source=r.source_term, target=r.phonetic_replacement, whole_word=r.match_whole_word,
                     case_sensitive=r.case_sensitive)
        for r in rules
    ]
    body = export_dictionary_txt(imported)
    return Response(
        content=body, media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="vieneu-dictionary.{format}"'},
    )
