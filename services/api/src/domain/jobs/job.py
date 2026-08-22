"""Domain models for asynchronous jobs."""

from dataclasses import dataclass
from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle states of an asynchronous job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Job:
    """Asynchronous job tracked by the platform."""

    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate job invariants."""

        if not self.job_id.strip():
            raise ValueError("job_id cannot be empty.")

        if not self.job_type.strip():
            raise ValueError("job_type cannot be empty.")

        if self.status is JobStatus.FAILED and not self.error:
            raise ValueError("failed jobs must contain an error.")