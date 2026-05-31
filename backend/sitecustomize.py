"""Dev convenience for running from the backend/ directory.

When you run commands like:
  uvicorn backend.main:app --reload
from inside the `backend/` folder, Python's import root becomes that folder,
so `import backend` fails (it would look for backend/backend).

Python auto-imports `sitecustomize` on startup if it's importable on sys.path.
Placing this file in `backend/` lets us patch sys.path only in that scenario.

This is intentionally minimal and safe: it only adds the parent directory when
needed so imports resolve the same way as running from repo root.
"""

from __future__ import annotations

import os
import sys


def _ensure_repo_root_on_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    parent = os.path.abspath(os.path.join(here, ".."))

    # If we are running from within backend/ (sys.path[0] == '' or backend path),
    # `import backend` would fail unless the repo root is on sys.path.
    if parent not in sys.path:
        sys.path.insert(0, parent)


_ensure_repo_root_on_syspath()
