"""FastAPI application factory.

``create_app()`` creates a configured ``FastAPI`` instance.  It is the single
entry point for both production (``src/main.py``) and tests (via
``httpx.AsyncClient`` + dependency overrides).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config import settings
from interfaces.api.error_handlers import register_error_handlers
from interfaces.api.routers.appointments import router as appointments_router
from interfaces.api.routers.health import router as health_router
from interfaces.api.routers.services import router as services_router
from interfaces.api.routers.staff import router as staff_router
from interfaces.api.routers.staff_time_off import router as staff_time_off_router
from interfaces.api.routers.waitlist import router as waitlist_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    - Registers CORS middleware with origins from ``Settings.allowed_origins``.
    - Registers the health router (no auth).
    - Registers global error handlers for ``ApplicationError`` subclasses.
    - Disables OpenAPI docs when ``APP_ENV=production``.
    """
    is_production = settings.app_env == "production"

    app = FastAPI(
        title="Tools for Agents API",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    # ------------------------------------------------------------------ #
    # Middleware
    # ------------------------------------------------------------------ #

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Error handlers
    # ------------------------------------------------------------------ #

    register_error_handlers(app)

    # ------------------------------------------------------------------ #
    # Routers
    # ------------------------------------------------------------------ #

    app.include_router(health_router)
    app.include_router(services_router, prefix="/services", tags=["services"])
    app.include_router(staff_router, prefix="/staff", tags=["staff"])
    app.include_router(appointments_router, prefix="/appointments", tags=["appointments"])
    app.include_router(staff_time_off_router, prefix="/staff-time-off", tags=["staff-time-off"])
    app.include_router(waitlist_router, prefix="/waitlist", tags=["waitlist"])

    return app
