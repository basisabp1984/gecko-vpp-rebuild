"""FastAPI application entrypoint for GECKO VPP.

Run with:
    uvicorn gecko_vpp.main:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from gecko_vpp.common.envelope import build_error
from gecko_vpp.common.errors import GeckoError, NotFound
from gecko_vpp.config import get_settings
from gecko_vpp.db import dispose_engine
from gecko_vpp.routers import admin as admin_router
from gecko_vpp.routers import agents as agents_router
from gecko_vpp.routers import core as core_router
from gecko_vpp.routers import dispatch as dispatch_router
from gecko_vpp.routers import ems as ems_router
from gecko_vpp.routers import market as market_router
from gecko_vpp.routers import regulatory as regulatory_router

log = logging.getLogger("gecko_vpp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Engine is created lazily on first request; nothing to warm here.
    yield
    await dispose_engine()


app = FastAPI(
    title="GECKO VPP API",
    version="1.0.0",
    description="Multi-tenant VPP backend — markets, dispatch, EMS, regulatory, agents.",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---- CORS ----

_settings = get_settings()
_cors_origins = [
    "http://localhost:3000",
    "https://gecko.radai-1984.dev",
    "https://krytsia.radai-1984.dev",
]
# Allow extra origins from .env if provided.
if _settings.cors_origins:
    for o in _settings.cors_origins.split(","):
        o = o.strip()
        if o and o not in _cors_origins:
            _cors_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "X-Tenant-Id", "X-Admin", "Authorization"],
)


# ---- request_id middleware ----


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


# ---- exception handlers ----


@app.exception_handler(GeckoError)
async def gecko_error_handler(request: Request, exc: GeckoError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=build_error(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=build_error(
            "VALIDATION_FAILED",
            "Request validation failed",
            {"errors": exc.errors()},
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # Map common HTTP codes to canonical envelope.
    code_map = {
        400: "VALIDATION_FAILED",
        401: "INVALID_TENANT",
        404: "NOT_FOUND",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        501: "STUB_NOT_IMPLEMENTED",
    }
    code = code_map.get(exc.status_code, "INTERNAL_ERROR")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error(code, detail or "HTTP error", {}),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=build_error("INTERNAL_ERROR", str(exc) or "Internal error", {}),
    )


# ---- routers ----

app.include_router(core_router.router)
app.include_router(market_router.router)
app.include_router(dispatch_router.router)
app.include_router(ems_router.router)
app.include_router(regulatory_router.router)
app.include_router(agents_router.router)
app.include_router(admin_router.router)


# ---- root ----


@app.get("/", include_in_schema=False)
async def root() -> dict[str, Any]:
    return {"data": {"name": "GECKO VPP API", "docs": "/docs", "openapi": "/openapi.json"}}
