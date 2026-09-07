"""HTTP routes for dashboard aggregation."""

import httpx
from fastapi import APIRouter

from application.services.dashboard_service import DashboardService
from infrastructure.config import get_settings
from infrastructure.monitoring.prometheus_provider import PrometheusResourceProvider
from infrastructure.monitoring.resource_provider import SystemResourceProvider
from interfaces.http.schemas.dashboard import DashboardResponseSchema

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)

_settings = get_settings()
_resource_monitor = (
    PrometheusResourceProvider(base_url=_settings.prometheus_base_url)
    if _settings.prometheus_base_url
    else SystemResourceProvider()
)
def _grafana_reachable() -> bool:
    try:
        response = httpx.get(
            f"{_settings.grafana_url.rstrip('/')}/api/health",
            timeout=2.0,
        )
        return response.status_code < 500
    except Exception:
        return False


def _build_dashboard_service() -> DashboardService:
    return DashboardService(
        _resource_monitor,
        grafana_url=_settings.grafana_url,
        grafana_reachable=_grafana_reachable(),
        prometheus_configured=_settings.prometheus_base_url is not None,
    )


_dashboard_service = _build_dashboard_service()


@router.get(
    "",
    response_model=DashboardResponseSchema,
)
def get_dashboard() -> DashboardResponseSchema:
    """Return the current platform dashboard state."""

    dashboard = _build_dashboard_service().get_dashboard()

    return DashboardResponseSchema.model_validate(dashboard)
