"""FastAPI application factory."""

from fastapi import FastAPI

from infrastructure.config import get_settings
from interfaces.http.errors import register_exception_handlers
from interfaces.http.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    register_exception_handlers(app)
    from interfaces.http.routes.engines import (
    router as engines_router,
)


    app.include_router(health_router)
    app.include_router(engines_router)

    return app


app = create_app()