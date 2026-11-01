"""In-app Help: renders the bilingual docs with markdown-it-py (raw HTML disabled).

``doc`` and ``lang`` are looked up in fixed maps, never joined into a path, so the
query string cannot reach any file other than the four known documents.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from markdown_it import MarkdownIt

from .admin_app import AdminApp
from .models import Session
from .web_paths import docs_dir

log = logging.getLogger("vieneu.admin")

DOC_MAP = {"functions": "web-admin-functions", "guide": "user-guide"}
DOC_TITLES = {"functions": "Web admin functions", "guide": "User guide"}
LANG_SUFFIX = {"en": ".md", "vi": ".vi.md"}
MAX_DOC_BYTES = 2 * 1024 * 1024

_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable("table")


def render_markdown(text: str) -> str:
    """HTML for trusted-layout, untrusted-content Markdown: raw HTML is escaped."""
    return _md.render(text)


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web = app.deps, app.web

    @router.get("/help", name="admin_help")
    def help_page(request: Request, session: Session = Depends(deps.current_session),
                  doc: str = Query("guide", max_length=20), lang: str = Query("en", max_length=4)) -> Response:
        if doc not in DOC_MAP or lang not in LANG_SUFFIX:
            raise HTTPException(404, "Unknown help document.")
        path = docs_dir() / (DOC_MAP[doc] + LANG_SUFFIX[lang])
        html, missing = "", False
        try:
            if path.stat().st_size > MAX_DOC_BYTES:
                raise OSError("document too large")
            html = render_markdown(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as e:
            # Never echo the server path to the browser; log it for the operator.
            log.warning("help document %s unavailable: %s", path, e)
            missing = True
        return web.render(request, "help.html", session, doc=doc, lang=lang, docs=DOC_TITLES,
                          content=html, missing=missing)
