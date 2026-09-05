"""HTTP schemas for dashboard aggregation."""

from pydantic import BaseModel


class DashboardResourcesSchema(BaseModel):
    """Resource metrics exposed by the dashboard."""

    cpu_percent: float
    memory_percent: float
    gpu_percent: float | None


class DashboardEngineSchema(BaseModel):
    """Runtime status of an LLM engine."""

    engine: str
    status: str


class DashboardPodSchema(BaseModel):
    """Kubernetes pod status exposed by monitoring."""

    namespace: str
    name: str
    ready: bool


class DashboardAlertSchema(BaseModel):
    """Active Prometheus alert exposed by monitoring."""

    name: str
    severity: str | None
    state: str


class DashboardResponseSchema(BaseModel):
    """Aggregated dashboard response."""

    resources: DashboardResourcesSchema
    engines: list[DashboardEngineSchema]
    pods: list[DashboardPodSchema] = []
    alerts: list[DashboardAlertSchema] = []
