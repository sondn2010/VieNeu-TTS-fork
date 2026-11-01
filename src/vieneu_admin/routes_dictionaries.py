"""Dictionary list and detail pages (everyone), dictionary writes and lexicon preview."""
from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response

from vieneu_preprocess.dictionary_schema import KINDS

from .admin_app import AdminApp
from .auth import is_htmx
from .models import NotFoundError, Session, StoreError
from .preprocess_bridge import PreprocessFailed, run_preprocess
from .store_dictionaries import PAGE_SIZE

MAX_PREVIEW_CHARS = 2000


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store
    write = [Depends(deps.csrf_protect)]

    def list_page(request: Request, session: Session, *, status: int = 200, error: str = "",
                  message: str = "") -> Response:
        return web.render(request, "dictionaries.html", session, status=status,
                          dictionaries=store.list_dictionaries(), kinds=KINDS, error=error, message=message)

    def mutate(request: Request, session: Session, action, done: str) -> Response:
        try:
            action()
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        except StoreError as e:
            return list_page(request, session, status=400, error=str(e))
        return list_page(request, session, message=done)

    @router.get("/dictionaries", name="admin_dictionaries")
    def list_dictionaries(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        return list_page(request, session)

    @router.post("/dictionaries", name="admin_dictionaries_create", dependencies=write)
    def create(request: Request, session: Session = Depends(deps.require_admin), name: str = Form(""),
               kind: str = Form("term"), description: str = Form("")) -> Response:
        return mutate(request, session, lambda: store.create_dictionary(name, kind, description),
                      f"Dictionary {name.strip()!r} created.")

    @router.post("/dictionaries/preview", name="admin_dictionaries_preview", dependencies=write)
    def preview(request: Request, session: Session = Depends(deps.current_session),
                text: str = Form(""), dictionary_id: str = Form("")) -> Response:
        """Sentence in, lexicon-applied text out: one dictionary, or every enabled one."""
        text = text.strip()
        error, output = "", ""
        if dictionary_id and not dictionary_id.isdigit():
            raise HTTPException(422, "Invalid dictionary id.")
        if not text:
            error = "Enter a sentence to preview."
        elif len(text) > MAX_PREVIEW_CHARS:
            error = f"Preview text is limited to {MAX_PREVIEW_CHARS} characters."
        else:
            try:
                lexicon = (store.export_dictionary(int(dictionary_id)).entries if dictionary_id
                           else store.enabled_lexicon())
                output = run_preprocess(text, lexicon).to_tagged_text()
            except NotFoundError as e:
                raise HTTPException(404, str(e)) from e
            except PreprocessFailed as e:
                error = str(e)
        return web.render(request, "partials/preview_result.html", session,
                          status=400 if error else 200, output=output, error=error)

    @router.get("/dictionaries/{dictionary_id}", name="admin_dictionary")
    def detail(request: Request, dictionary_id: int, session: Session = Depends(deps.current_session),
               q: str = Query("", max_length=80), page: int = Query(1, ge=1, le=100_000)) -> Response:
        info = store.get_dictionary(dictionary_id)
        if info is None:
            raise HTTPException(404, "Dictionary not found.")
        entries, total = store.search_entries(dictionary_id, q, page)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        ctx = dict(dictionary=info, entries=entries, total=total, q=q, page=min(page, pages), pages=pages)
        if is_htmx(request) and request.headers.get("HX-Target") == "entries-panel":
            return web.render(request, "partials/entries_panel.html", session, **ctx)
        return web.render(request, "dictionary.html", session, kinds=KINDS, **ctx)

    @router.post("/dictionaries/{dictionary_id}/rename", name="admin_dictionary_rename", dependencies=write)
    def rename(request: Request, dictionary_id: int, session: Session = Depends(deps.require_admin),
               name: str = Form(""), description: Optional[str] = Form(None)) -> Response:
        return mutate(request, session,
                      lambda: store.update_dictionary(dictionary_id, name=name, description=description),
                      "Dictionary updated.")

    @router.post("/dictionaries/{dictionary_id}/toggle", name="admin_dictionary_toggle", dependencies=write)
    def toggle(request: Request, dictionary_id: int, session: Session = Depends(deps.require_admin)) -> Response:
        return mutate(request, session, lambda: store.toggle_dictionary(dictionary_id), "Dictionary toggled.")

    @router.post("/dictionaries/{dictionary_id}/delete", name="admin_dictionary_delete", dependencies=write)
    def delete(request: Request, dictionary_id: int, session: Session = Depends(deps.require_admin)) -> Response:
        return mutate(request, session, lambda: store.delete_dictionary(dictionary_id), "Dictionary deleted.")
