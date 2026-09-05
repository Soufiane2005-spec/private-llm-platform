"""HTTP routes for asynchronous job visualization."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.services.job_service import JobService
from domain.jobs.job import Job
from infrastructure.persistence.factory import get_persistent_job_repository
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from interfaces.http.schemas.jobs import JobCreateRequest, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_repository = get_persistent_job_repository()
_queue = InMemoryJobQueue()
_service = JobService(queue=_queue, repository=_repository)


def get_job_service() -> JobService:
    """Return the job service used by HTTP endpoints."""

    return _service


JobServiceDependency = Annotated[
    JobService,
    Depends(get_job_service),
]


def _to_response(job: Job) -> JobResponse:
    """Convert a domain job to its HTTP representation."""

    return JobResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        error=job.error,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
    )


@router.get("", response_model=list[JobResponse])
def list_jobs(
    service: JobServiceDependency,
) -> list[JobResponse]:
    """Return all jobs tracked by the platform."""

    return [_to_response(job) for job in service.list_jobs()]


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_job(
    request: JobCreateRequest,
    service: JobServiceDependency,
) -> JobResponse:
    """Submit a new asynchronous platform job."""

    try:
        job = service.submit(request.job_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    service: JobServiceDependency,
) -> JobResponse:
    """Return one job by identifier."""

    job = service.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return _to_response(job)
