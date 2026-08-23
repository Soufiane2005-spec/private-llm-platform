"""Domain models for asynchronous jobs."""

from dataclasses import dataclass, replace
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
    attempts: int = 0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        """Validate job invariants."""

        if not self.job_id.strip():
            raise ValueError("job_id cannot be empty.")

        if not self.job_type.strip():
            raise ValueError("job_type cannot be empty.")

        if self.status is JobStatus.FAILED and not self.error:
            raise ValueError("failed jobs must contain an error.")

        if self.attempts < 0:
            raise ValueError("attempts cannot be negative.")

        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero.")

        if self.attempts > self.max_attempts:
            raise ValueError("attempts cannot exceed max_attempts.")

    def mark_running(self) -> "Job":
        """Return the job in the running state."""

        if self.status is not JobStatus.PENDING:
            raise ValueError("only pending jobs can start running.")

        return replace(
            self,
            status=JobStatus.RUNNING,
            error=None,
        )

    def mark_completed(self) -> "Job":
        """Return the job in the completed state."""

        if self.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can complete.")

        return replace(
            self,
            status=JobStatus.COMPLETED,
            error=None,
        )

    def mark_failed(self, error: str) -> "Job":
        """Return the job in the failed state."""

        if self.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can fail.")

        if not error.strip():
            raise ValueError("failed jobs must contain an error.")

        return replace(
            self,
            status=JobStatus.FAILED,
            error=error,
        )

    def register_attempt(self) -> "Job":
        """Return the job with one additional execution attempt."""

        if self.attempts >= self.max_attempts:
            raise ValueError("maximum job attempts reached.")

        return replace(
            self,
            attempts=self.attempts + 1,
        )

    @property
    def can_retry(self) -> bool:
        """Return whether another execution attempt is allowed."""

        return self.attempts < self.max_attempts

    def mark_retry_pending(self) -> "Job":
        """Return a running job to pending for another attempt."""

        if self.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can be retried.")

        if not self.can_retry:
            raise ValueError("job has no retry attempts remaining.")

        return replace(
            self,
            status=JobStatus.PENDING,
            error=None,
        )