"""HTTP authentication routes."""

from fastapi import APIRouter, HTTPException, status

from application.services.auth_exceptions import InvalidCredentialsError
from interfaces.http.dependencies.auth import (
    AuthServiceDependency,
    CurrentUserDependency,
)
from interfaces.http.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    auth_service: AuthServiceDependency,
) -> TokenResponse:
    """Authenticate credentials and return a JWT token."""

    try:
        _, token = auth_service.authenticate(
            username=request.username,
            password=request.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=token,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    user: CurrentUserDependency,
) -> CurrentUserResponse:
    """Return the authenticated user."""

    return CurrentUserResponse(
        username=user.username,
    )