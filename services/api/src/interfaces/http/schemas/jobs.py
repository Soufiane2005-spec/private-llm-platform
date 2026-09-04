"""HTTP schemas for asynchronous job endpoints."""

from pydantic import BaseModel, Field

from domain.jobs.job import JobStatus


class JobCreateRequest(BaseModel):
    """Request payload used to submit an asynchronous job."""

    job_type: str = Field(
        min_length=1,
        max_length=100,
    )


class JobResponse(BaseModel):
    """Public representation of an asynchronous job."""

    job_id: str
    job_type: str
    status: JobStatus
    error: str | None
    attempts: int
    max_attempts: int
