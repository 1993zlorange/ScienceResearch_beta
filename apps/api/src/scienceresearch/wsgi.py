"""Production WSGI entry point for Waitress or another WSGI server."""

from __future__ import annotations

import os
from pathlib import Path

from .flask_app import create_app


def _runtime_dir() -> Path:
    value = os.environ.get("SCIENCERESEARCH_DATA_DIR")
    if value:
        return Path(value)
    return Path(__file__).resolve().parents[4] / "storage" / "runtime"


application = create_app(data_dir=_runtime_dir())
