"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config import get_settings
from interfaces.http.errors import register_exception_handlers
from interfaces.http.routes.auth import router as auth_router
from interfaces.http.routes.benchmarks import router as benchmarks_router
from interfaces.http.routes.chat import router as chat_router
from interfaces.http.routes.dashboard import router as dashboard_router
from interfaces.http.routes.deployments import router as deployments_router
from interfaces.http.routes.engines import router as engines_router
from interfaces.http.routes.health import router as health_router
from interfaces.http.routes.jobs import router as jobs_router
from interfaces.http.routes.models import router as models_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(engines_router)
    app.include_router(dashboard_router)
    app.include_router(models_router)
    app.include_router(deployments_router)
    app.include_router(jobs_router)
    app.include_router(benchmarks_router)
    app.include_router(chat_router)

    return app


app = create_app()
