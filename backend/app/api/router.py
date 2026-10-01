"""Aggregates every module router under /api/v1.

Module routers are imported defensively (ImportError -> warning) so the app still boots while other work
packages are landing. A router import that fails for any *other* reason (syntax error, bug) is NOT swallowed.
"""

import importlib
import logging

from fastapi import APIRouter, Depends

from app.core.ratelimit import global_rate_limit

log = logging.getLogger(__name__)

# (module path, attribute names of routers to include)
_ROUTERS: list[tuple[str, tuple[str, ...]]] = [
    ("app.modules.auth.router", ("router",)),
    ("app.modules.users.router", ("router",)),
    ("app.modules.students.router", ("router",)),
    ("app.modules.faculty.router", ("router",)),
    ("app.modules.companies.router", ("router",)),
    ("app.modules.internships.router", ("router",)),
    ("app.modules.applications.router", ("router",)),
    ("app.modules.interviews.router", ("router",)),
    ("app.modules.evaluations.router", ("router", "forms_router")),
    ("app.modules.feedback.router", ("router",)),
    ("app.modules.documents.router", ("router",)),
    ("app.modules.notifications.router", ("router",)),
    ("app.modules.notifications.ws", ("router",)),  # WebSocket /api/v1/ws (WP4)
    ("app.modules.reports.router", ("router", "jobs_router")),
    ("app.modules.analytics.router", ("router",)),
    ("app.modules.admin.router", ("router",)),
]

# Default rate limit (300/min per user or ip) applies to every HTTP route; websockets are exempt.
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(global_rate_limit)])
ws_router = APIRouter(prefix="/api/v1")


def _include_all() -> None:
    for module_path, attrs in _ROUTERS:
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            missing = getattr(exc, "name", None) or ""
            if not missing.startswith("app."):
                raise  # a missing third-party dependency is a real error: do not hide it
            log.warning("router module %s not importable yet (%s): %s", module_path, missing, exc)
            continue
        for attr in attrs:
            router = getattr(module, attr, None)
            if router is None:
                continue
            # The websocket router must not carry the HTTP-only rate limit dependency
            target = ws_router if module_path.endswith(".ws") else api_router
            target.include_router(router)


_include_all()
