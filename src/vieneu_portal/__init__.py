"""VieNeu Portal: torch-free FastAPI + Postgres user portal (`/api/v1`).

Never imports `vieneu` or `vieneu_preprocess` — the portal image ships without
onnxruntime/torch (see `tests/portal/test_health_and_error_envelope.py`).
"""

__version__ = "0.1.0"
