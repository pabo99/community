"""FastAPI application entry point.

Exposes an application factory (:func:`create_app`) and a module-level ``app``
instance for the ASGI server (``uvicorn app.main:app``). The API and worker
share this codebase/image with different commands (technical-design.md §12);
the worker runtime behavior is introduced in M1-11.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    OpenAPI docs are served outside production (technical-design.md §13).
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(admin_router)

    return app


app = create_app()
