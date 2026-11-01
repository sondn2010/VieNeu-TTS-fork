"""Dictionary JSON import (admin) and export, via the phase-1 dictionary schema only."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from vieneu_preprocess.dictionary_schema import KINDS, DictionaryFormatError, dump_dictionary_json, load_dictionary_json

from .admin_app import AdminApp
from .auth import MAX_UPLOAD_BYTES
from .models import NotFoundError, Session, StoreError
from .store_dictionaries import slugify
from .web import apply_security_headers

IMPORT_ACTIONS = ("new", "merge", "replace")


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store

    def page(request: Request, session: Session, *, status: int, error: str = "", message: str = "") -> Response:
        return web.render(request, "dictionaries.html", session, status=status,
                          dictionaries=store.list_dictionaries(), kinds=KINDS, error=error, message=message)

    @router.post("/dictionaries/import", name="admin_dictionaries_import",
                 dependencies=[Depends(deps.csrf_protect)])
    def import_dictionary(request: Request, session: Session = Depends(deps.require_admin),
                          file: UploadFile = File(...), action: str = Form("new"),
                          dictionary_id: str = Form(""), name: str = Form("")) -> Response:
        if action not in IMPORT_ACTIONS:
            return page(request, session, status=400, error="Choose new, merge or replace.")
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            return page(request, session, status=413, error="The file is larger than 5 MB.")
        try:
            parsed = load_dictionary_json(data)
        except DictionaryFormatError as e:  # message carries line/column for JSON syntax errors
            return page(request, session, status=400, error=f"{file.filename or 'Upload'}: {e}")
        try:
            if action == "new":
                if name.strip():
                    parsed.name = name.strip()
                store.import_dictionary(parsed)
                done = f"Imported {parsed.name!r} with {len(parsed.entries)} entries."
            else:
                if not dictionary_id.isdigit():
                    return page(request, session, status=400, error="Choose the dictionary to update.")
                target = int(dictionary_id)
                if action == "merge":
                    n = store.merge_entries(target, parsed.entries)
                    done = f"Merged {n} entries."
                else:
                    n = store.replace_entries(target, parsed.entries)
                    done = f"Replaced all entries with {n} entries."
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        except StoreError as e:
            return page(request, session, status=400, error=str(e))
        return page(request, session, status=200, message=done)

    @router.get("/dictionaries/{dictionary_id}/export", name="admin_dictionary_export")
    def export_dictionary(dictionary_id: int, session: Session = Depends(deps.current_session)) -> Response:
        try:
            d = store.export_dictionary(dictionary_id)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        filename = slugify(d.name, f"dictionary-{dictionary_id}") + ".json"
        resp = Response(dump_dictionary_json(d), media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; "
                                                        f"filename*=UTF-8''{quote(filename)}"})
        return apply_security_headers(resp)
