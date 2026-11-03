from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok"}


def test_unknown_route_returns_error_envelope(client: TestClient) -> None:
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]


def test_validation_error_returns_sanitized_envelope() -> None:
    """A real 422 trigger (not just a GET-only route rejecting POST), and a
    check that Pydantic's `ctx`/`input`/`url` never leak into the response —
    `ctx` can hold a non-JSON-serializable exception, and `input` would echo
    back whatever the client submitted (e.g. a signup password).
    """
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    from vieneu_portal.errors import install_error_handlers

    app = FastAPI()
    install_error_handlers(app)

    class Body(BaseModel):
        count: int = Field(gt=0)

    @app.post("/throwaway")
    def _throwaway(body: Body) -> dict:
        return {"ok": True}

    with TestClient(app) as c:
        resp = c.post("/throwaway", json={"count": "not-a-number"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    details = body["error"]["details"]
    assert details
    for detail in details:
        assert "ctx" not in detail
        assert "input" not in detail
        assert "url" not in detail


def test_health_returns_503_when_db_unreachable() -> None:
    from vieneu_portal.errors import PortalError
    from vieneu_portal.routes_health import health

    class _BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("connection refused")

    with pytest.raises(PortalError) as exc_info:
        health(db=_BrokenSession())  # type: ignore[arg-type]
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "SERVICE_UNAVAILABLE"


def test_vieneu_portal_never_imports_vieneu_or_vieneu_preprocess() -> None:
    """Import-linter style check: the portal package must stay torch/onnx-free."""
    package_dir = Path(__file__).resolve().parents[2] / "src" / "vieneu_portal"
    forbidden = {"vieneu", "vieneu_preprocess"}

    for path in package_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            hit = names & forbidden
            assert not hit, f"{path} imports {hit}, which pulls in the torch/onnx engine stack"
