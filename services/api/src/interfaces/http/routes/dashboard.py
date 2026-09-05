"""HTTP routes for dashboard aggregation."""

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
_dashboard_service = DashboardService(_resource_monitor)


@router.get(
    "",
    response_model=DashboardResponseSchema,
)
def get_dashboard() -> DashboardResponseSchema:
    """Return the current platform dashboard state."""

    dashboard = _dashboard_service.get_dashboard()

    return DashboardResponseSchema.model_validate(dashboard)
