"""CampusHire API entrypoint: ``uvicorn app.main:app``."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router, ws_router
from app.core import redis as redis_core
from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("campushire")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("CampusHire API starting (env=%s)", settings.ENVIRONMENT)
    yield
    await redis_core.close_redis()
    await engine.dispose()
    log.info("CampusHire API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="CampusHire API",
        version="1.0.0",
        description="College internship and talent management platform.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware order: last added is outermost. CORS must be outermost so even error responses carry CORS headers.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/healthz", tags=["health"], include_in_schema=True)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> JSONResponse:
        checks: dict[str, str] = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["db"] = f"error: {type(exc).__name__}"
        try:
            await redis_core.get_redis().ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {type(exc).__name__}"
        ok = all(v == "ok" for v in checks.values())
        return JSONResponse(status_code=200 if ok else 503, content={"status": "ok" if ok else "unavailable", "checks": checks})

    return app


app = create_app()
