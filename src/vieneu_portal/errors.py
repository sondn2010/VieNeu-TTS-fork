"""JSON error envelope: `{"error": {"code": "UPPER_SNAKE", "message": str, ...}}`."""
from __future__ import annotations

import logging
from typing import Any, Mapping

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

log = logging.getLogger("vieneu.portal.errors")


class PortalError(Exception):
    """Raise anywhere in the portal to produce a structured JSON error response."""

    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.extra = extra

    def envelope(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        body.update(self.extra)
        return {"error": body}


_HTTP_STATUS_CODES: Mapping[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


def _code_for_status(status_code: int) -> str:
    if status_code in _HTTP_STATUS_CODES:
        return _HTTP_STATUS_CODES[status_code]
    return "INTERNAL_ERROR" if status_code >= 500 else "ERROR"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PortalError)
    async def _portal_error(_: Request, exc: PortalError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.envelope())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic v2 puts a non-JSON-serializable exception under `ctx`, and
        # `input` echoes the submitted value (e.g. a signup password) back in
        # the response; drop both before encoding.
        details = [
            {k: v for k, v in err.items() if k not in ("ctx", "input", "url")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request",
                    "details": jsonable_encoder(details),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _code_for_status(exc.status_code)
        message = exc.detail if isinstance(exc.detail, str) else code
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        )
