"""Filesystem locations of the admin app's bundled templates, static assets and docs."""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
# Repository checkout: src/vieneu_admin -> repo root -> docs/
_REPO_DOCS_DIR = PACKAGE_DIR.parent.parent / "docs"


def docs_dir() -> Path:
    """Help documents folder: ``VIENEU_DOCS_DIR`` or the repository ``docs/``."""
    return Path(os.environ.get("VIENEU_DOCS_DIR") or _REPO_DOCS_DIR)
