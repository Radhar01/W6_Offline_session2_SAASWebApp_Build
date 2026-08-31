"""Shared FastAPI dependencies.

This project has no authentication in the MVP (see INITIAL.md /
CLAUDE.md) — there is intentionally no `get_current_user` dependency here.

`get_db` is owned by `app.database` (DATABASE-AGENT). We re-export it here
so routers/services have a single, stable place to import dependencies
from: `from app.dependencies import get_db`.
"""

from app.database import get_db

__all__ = ["get_db"]
