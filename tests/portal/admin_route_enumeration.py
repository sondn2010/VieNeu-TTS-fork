"""Flattens `app.routes` into `(method, full_path)` pairs for the
permission-matrix test. Walks around a FastAPI-version detail: a plain
`Starlette`/`APIRoute` exposes `.methods`/`.path` directly, but this FastAPI
version wraps each `app.include_router(...)` call in an internal
`_IncludedRouter` whose real routes live at `original_router.routes`, with
the mount prefix on `include_context.prefix` — so a naive one-level scan of
`app.routes` finds nothing below `/api/v1/*` at all.
"""
from __future__ import annotations


def enumerate_routes(app) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def walk(routes, prefix: str) -> None:
        for r in routes:
            methods = getattr(r, "methods", None)
            path = getattr(r, "path", None)
            if methods and path is not None:
                for m in methods:
                    if m != "HEAD":
                        out.append((m, prefix + path))
                continue
            original_router = getattr(r, "original_router", None)
            if original_router is not None:
                include_context = getattr(r, "include_context", None)
                sub_prefix = prefix + (getattr(include_context, "prefix", "") or "") if include_context else prefix
                walk(original_router.routes, sub_prefix)

    walk(app.routes, "")
    return out
