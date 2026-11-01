"""Inline (HTMX) dictionary entry add, edit and delete; admin only."""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from .admin_app import AdminApp
from .models import NotFoundError, Session, StoreError
from .store_dictionaries import PAGE_SIZE, validate_entry
from .web import apply_security_headers


def _checked(value: str) -> bool:
    return value in ("1", "on", "true")


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store
    write = [Depends(deps.csrf_protect)]

    def panel(request: Request, session: Session, dictionary_id: int, *, status: int = 200,
              error: str = "", message: str = "", form: dict | None = None) -> Response:
        info = store.get_dictionary(dictionary_id)
        if info is None:
            raise HTTPException(404, "Dictionary not found.")
        entries, total = store.search_entries(dictionary_id)
        return web.render(request, "partials/entries_panel.html", session, status=status, dictionary=info,
                          entries=entries, total=total, q="", page=1, pages=max(1, math.ceil(total / PAGE_SIZE)),
                          error=error, message=message, form=form or {})

    def entry_or_404(dictionary_id: int, entry_id: int):
        entry = store.get_entry(dictionary_id, entry_id)
        if entry is None:
            raise HTTPException(404, "Entry not found.")
        return entry

    @router.post("/dictionaries/{dictionary_id}/entries", name="admin_entry_add", dependencies=write)
    def add_entry(request: Request, dictionary_id: int, session: Session = Depends(deps.require_admin),
                  term: str = Form(""), replacement: str = Form(""), mode: str = Form("phonetic"),
                  case_sensitive: str = Form(""), note: str = Form("")) -> Response:
        form = dict(term=term, replacement=replacement, mode=mode, case_sensitive=_checked(case_sensitive), note=note)
        try:
            entry = validate_entry(term, replacement, mode, _checked(case_sensitive), note)
            store.upsert_entry(dictionary_id, entry)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        except StoreError as e:
            return panel(request, session, dictionary_id, status=400, error=str(e), form=form)
        return panel(request, session, dictionary_id, message=f"Added {entry.term!r}.")

    @router.get("/dictionaries/{dictionary_id}/entries/{entry_id}", name="admin_entry_row")
    def entry_row(request: Request, dictionary_id: int, entry_id: int,
                  session: Session = Depends(deps.current_session)) -> Response:
        return web.render(request, "partials/entry_row.html", session, dictionary_id=dictionary_id,
                          entry=entry_or_404(dictionary_id, entry_id))

    @router.get("/dictionaries/{dictionary_id}/entries/{entry_id}/edit", name="admin_entry_edit")
    def edit_row(request: Request, dictionary_id: int, entry_id: int,
                 session: Session = Depends(deps.require_admin)) -> Response:
        return web.render(request, "partials/entry_edit_row.html", session, dictionary_id=dictionary_id,
                          entry=entry_or_404(dictionary_id, entry_id), error="")

    @router.post("/dictionaries/{dictionary_id}/entries/{entry_id}", name="admin_entry_save", dependencies=write)
    def save_entry(request: Request, dictionary_id: int, entry_id: int,
                   session: Session = Depends(deps.require_admin), term: str = Form(""),
                   replacement: str = Form(""), mode: str = Form("phonetic"), case_sensitive: str = Form(""),
                   note: str = Form("")) -> Response:
        current = entry_or_404(dictionary_id, entry_id)
        try:
            entry = validate_entry(term, replacement, mode, _checked(case_sensitive), note)
            saved = store.upsert_entry(dictionary_id, entry, entry_id)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        except StoreError as e:
            return web.render(request, "partials/entry_edit_row.html", session, status=400,
                              dictionary_id=dictionary_id, entry=current, error=str(e))
        return web.render(request, "partials/entry_row.html", session, dictionary_id=dictionary_id, entry=saved)

    @router.post("/dictionaries/{dictionary_id}/entries/{entry_id}/delete", name="admin_entry_delete",
                 dependencies=write)
    def delete_entry(dictionary_id: int, entry_id: int, session: Session = Depends(deps.require_admin)) -> Response:
        try:
            store.delete_entry(dictionary_id, entry_id)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        return apply_security_headers(HTMLResponse(""))  # HTMX removes the row
