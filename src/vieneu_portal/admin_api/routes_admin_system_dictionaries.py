"""`/api/v1/admin/system-dictionaries*` — a thin HTTP layer over phase 5's
`system_dictionary_store` (shared with the admin CLI); every mutation here
additionally writes one `admin_audit_log` row, which the store/CLI layer
itself does not.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..admin_services.admin_audit_log_writer import write_admin_audit
from ..auth.session_dependencies import AuthContext, get_client_ip, require_admin, require_csrf
from ..config import get_settings
from ..db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from ..db.session_factory import get_db
from ..dictionaries.system_dictionary_store import (
    FORMAT,
    KINDS,
    DictionaryFormatError,
    ParsedEntry,
    create_pack_from_json,
    delete_pack,
    export_pack_json,
    export_pack_txt,
    get_pack,
    import_json_into_pack,
    import_text_rules_into_pack,
    list_packs,
    list_rules,
    replace_all_rules,
    set_pack_enabled,
    update_pack_metadata,
)
from ..errors import PortalError
from ..moderation.moderation_provider_factory import build_moderation_provider

router = APIRouter()

MAX_IMPORT_BYTES = 1 * 1024 * 1024


def pack_etag(pack: SystemDictionary) -> str:
    return pack.updated_at.isoformat()


def serialize_system_dictionary(pack: SystemDictionary) -> dict:
    return {
        "id": pack.id, "name": pack.name, "kind": pack.kind, "is_enabled": pack.is_enabled,
        "description": pack.description, "sort_order": pack.sort_order, "updated_at": pack.updated_at,
        "etag": pack_etag(pack),
    }


def serialize_system_rule(rule: SystemPronunciationRule) -> dict:
    return {
        "id": str(rule.id), "source_term": rule.source_term, "phonetic_replacement": rule.phonetic_replacement,
        "match_whole_word": rule.match_whole_word, "case_sensitive": rule.case_sensitive,
        "is_enabled": rule.is_enabled, "sort_order": rule.sort_order, "note": rule.note, "rule_kind": rule.rule_kind,
    }


@router.get("/admin/system-dictionaries")
def list_system_dictionaries(
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> dict:
    return {"items": [serialize_system_dictionary(p) for p in list_packs(db)]}


@router.post("/admin/system-dictionaries", status_code=201)
async def create_system_dictionary(
    request: Request, db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
    _csrf: None = Depends(require_csrf),
) -> dict:
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
        obj = json.loads(body_text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PortalError(422, "VALIDATION_ERROR", "invalid JSON body")
    if not isinstance(obj, dict):
        raise PortalError(422, "VALIDATION_ERROR", "body must be a JSON object")

    settings = get_settings()
    rejected: list = []
    if obj.get("format") == FORMAT:
        try:
            pack, rejected = create_pack_from_json(db, settings, build_moderation_provider(settings), json_text=body_text)
        except DictionaryFormatError as exc:
            raise PortalError(422, "VALIDATION_ERROR", str(exc))
    else:
        name = obj.get("name")
        kind = obj.get("kind")
        if not isinstance(name, str) or not name or kind not in KINDS:
            raise PortalError(422, "VALIDATION_ERROR", f"name is required and kind must be one of {KINDS}")
        pack = SystemDictionary(
            name=name, kind=kind, is_enabled=bool(obj.get("is_enabled", True)), description=obj.get("description") or "",
        )
        db.add(pack)
        db.flush()

    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="sysdict.create",
        target_type="system_dictionary", target_id=str(pack.id), target_label=pack.name,
        before=None, after={"name": pack.name, "kind": pack.kind}, ip=get_client_ip(request),
    )
    db.commit()
    return {"dictionary": serialize_system_dictionary(pack), "rejected": rejected}


class UpdateSystemDictionaryRequest(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


@router.patch("/admin/system-dictionaries/{dictionary_id}")
def update_system_dictionary(
    dictionary_id: int, payload: UpdateSystemDictionaryRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    pack = get_pack(db, dictionary_id)
    settings = get_settings()
    before = {
        "name": pack.name, "kind": pack.kind, "is_enabled": pack.is_enabled,
        "description": pack.description, "sort_order": pack.sort_order,
    }
    if payload.name is not None or payload.kind is not None or payload.description is not None:
        update_pack_metadata(db, pack, name=payload.name, kind=payload.kind, description=payload.description)
    if payload.is_enabled is not None and payload.is_enabled != pack.is_enabled:
        set_pack_enabled(db, settings, pack, payload.is_enabled)
    if payload.sort_order is not None:
        pack.sort_order = payload.sort_order
    after = {
        "name": pack.name, "kind": pack.kind, "is_enabled": pack.is_enabled,
        "description": pack.description, "sort_order": pack.sort_order,
    }
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="sysdict.update",
        target_type="system_dictionary", target_id=str(pack.id), target_label=pack.name, before=before, after=after,
        ip=get_client_ip(request),
    )
    db.commit()
    return {"dictionary": serialize_system_dictionary(pack)}


@router.delete("/admin/system-dictionaries/{dictionary_id}", status_code=204)
def delete_system_dictionary(
    dictionary_id: int, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> None:
    pack = get_pack(db, dictionary_id)
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="sysdict.delete",
        target_type="system_dictionary", target_id=str(pack.id), target_label=pack.name, before=None, after=None,
        ip=get_client_ip(request),
    )
    delete_pack(db, pack)
    db.commit()
    return None


@router.get("/admin/system-dictionaries/{dictionary_id}/rules")
def list_system_dictionary_rules(
    dictionary_id: int, search: Optional[str] = None, page: int = 1, limit: int = 50,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> dict:
    pack = get_pack(db, dictionary_id)
    rows = list_rules(db, pack.id)
    if search:
        needle = search.lower()
        rows = [
            r for r in rows
            if needle in r.source_term.lower() or needle in (r.phonetic_replacement or "").lower()
        ]
    limit = min(max(limit, 1), 200)
    page = max(page, 1)
    total = len(rows)
    offset = (page - 1) * limit
    page_rows = rows[offset: offset + limit]
    return {
        "items": [serialize_system_rule(r) for r in page_rows], "total_count": total, "page": page, "limit": limit,
        "etag": pack_etag(pack),
    }


class RuleInput(BaseModel):
    term: str
    replacement: str = ""
    mode: str = "phonetic"
    case_sensitive: bool = False
    note: str = ""


class ReplaceRulesRequest(BaseModel):
    rules: list[RuleInput]


@router.put("/admin/system-dictionaries/{dictionary_id}/rules")
def replace_system_dictionary_rules(
    dictionary_id: int, payload: ReplaceRulesRequest, request: Request,
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    pack = get_pack(db, dictionary_id)
    if if_match is not None and if_match != pack_etag(pack):
        raise PortalError(409, "ETAG_MISMATCH", "the dictionary changed since it was last loaded; reload and retry")

    settings = get_settings()
    entries = tuple(
        ParsedEntry(term=r.term, replacement=r.replacement, mode=r.mode, case_sensitive=r.case_sensitive, note=r.note)
        for r in payload.rules
    )
    rejected = replace_all_rules(db, settings, build_moderation_provider(settings), pack, entries)
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="sysdict.rules_replace",
        target_type="system_dictionary", target_id=str(pack.id), target_label=pack.name,
        before=None, after={"rule_count": len(entries) - len(rejected)}, ip=get_client_ip(request),
    )
    db.commit()
    return {"dictionary": serialize_system_dictionary(pack), "rejected": rejected}


@router.post("/admin/system-dictionaries/{dictionary_id}/import")
async def import_system_dictionary(
    dictionary_id: int, request: Request, format: str, mode: str = "merge",
    file: UploadFile = File(...),
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    if format not in ("json", "txt"):
        raise PortalError(422, "VALIDATION_ERROR", "format must be 'json' or 'txt'")
    if mode not in ("merge", "replace"):
        raise PortalError(422, "VALIDATION_ERROR", "mode must be 'merge' or 'replace'")
    pack = get_pack(db, dictionary_id)
    data = await file.read(MAX_IMPORT_BYTES + 1)
    if len(data) > MAX_IMPORT_BYTES:
        raise PortalError(422, "FILE_TOO_LARGE", "import file must be at most 1 MB")
    text = data.decode("utf-8", errors="replace")

    settings = get_settings()
    moderation = build_moderation_provider(settings)
    line_errors: tuple = ()
    try:
        if format == "json":
            rejected = import_json_into_pack(db, settings, moderation, pack=pack, json_text=text, mode=mode)
        else:
            rejected, line_errors = import_text_rules_into_pack(db, settings, moderation, pack=pack, text=text, mode=mode)
    except DictionaryFormatError as exc:
        raise PortalError(422, "VALIDATION_ERROR", str(exc))

    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="sysdict.import",
        target_type="system_dictionary", target_id=str(pack.id), target_label=pack.name,
        before=None, after={"mode": mode, "format": format, "rejected_count": len(rejected)},
        ip=get_client_ip(request),
    )
    db.commit()
    return {
        "dictionary": serialize_system_dictionary(pack), "rejected": rejected,
        "line_errors": [{"line": e.line, "message": e.message} for e in line_errors],
    }


@router.get("/admin/system-dictionaries/{dictionary_id}/export")
def export_system_dictionary(
    dictionary_id: int, format: str = Query(default="json"),
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> Response:
    if format not in ("json", "txt"):
        raise PortalError(422, "VALIDATION_ERROR", "format must be 'json' or 'txt'")
    pack = get_pack(db, dictionary_id)
    if format == "json":
        return Response(content=export_pack_json(db, pack), media_type="application/json")
    return Response(content=export_pack_txt(db, pack), media_type="text/plain")
