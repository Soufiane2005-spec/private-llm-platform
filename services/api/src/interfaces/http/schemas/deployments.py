"""HTTP schemas for model deployment management."""

from pydantic import BaseModel, Field

from domain.jobs.job import JobStatus
from domain.models.deployment import ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


class DeploymentCreateRequest(BaseModel):
    """Request payload for model deployment creation."""

    model: str = Field(min_length=1, max_length=200)
    engine: LLMEngine


class DeploymentJobResponse(BaseModel):
    """Job summary attached to a deployment operation."""

    job_id: str
    status: JobStatus
    error: str | None


class DeploymentResponse(BaseModel):
    """Public model deployment representation."""

    deployment_id: str
    model: str
    engine: LLMEngine
    status: ModelDeploymentStatus
    runtime_state: str
    error: str | None
    gpu_available: bool | None


class DeploymentOperationResponse(BaseModel):
    """Response returned by lifecycle operations."""

    deployment: DeploymentResponse | None
    job: DeploymentJobResponse
