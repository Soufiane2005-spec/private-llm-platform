"""HTTP schemas for asynchronous job endpoints."""

from pydantic import BaseModel

from domain.jobs.job import JobStatus


class JobResponse(BaseModel):
    """Public representation of an asynchronous job."""

    job_id: str
    job_type: str
    status: JobStatus
    error: str | None
    attempts: int
    max_attempts: int