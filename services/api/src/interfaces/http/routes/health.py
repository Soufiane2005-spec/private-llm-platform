"""Health check HTTP endpoints."""

from fastapi import APIRouter, status

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
)
def liveness() -> dict[str, str]:
    """Report whether the API process is alive."""

    return {"status": "ok"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
)
def readiness() -> dict[str, str]:
    """Report whether the API is ready to serve requests."""

    return {"status": "ready"}