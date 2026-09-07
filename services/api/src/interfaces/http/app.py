"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.services.job_service import fail_orphaned_running_jobs
from infrastructure.config import get_settings
from infrastructure.persistence.factory import get_persistent_job_repository
from interfaces.http.errors import register_exception_handlers
from interfaces.http.routes.auth import router as auth_router
from interfaces.http.routes.benchmarks import router as benchmarks_router
from interfaces.http.routes.chat import router as chat_router
from interfaces.http.routes.dashboard import router as dashboard_router
from interfaces.http.routes.deployments import router as deployments_router
from interfaces.http.routes.engines import router as engines_router
from interfaces.http.routes.health import router as health_router
from interfaces.http.routes.jobs import router as jobs_router
from interfaces.http.routes.metrics import router as metrics_router
from interfaces.http.routes.models import router as models_router
from interfaces.http.routes.users import router as users_router


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
    fail_orphaned_running_jobs(get_persistent_job_repository())

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(engines_router)
    app.include_router(dashboard_router)
    app.include_router(models_router)
    app.include_router(deployments_router)
    app.include_router(jobs_router)
    app.include_router(benchmarks_router)
    app.include_router(chat_router)

    return app


app = create_app()
