"""HTTP authentication and authorization routes."""

from fastapi import APIRouter, HTTPException, status

from application.services.auth_exceptions import InvalidCredentialsError
from interfaces.http.dependencies.auth import (
    AdminUserDependency,
    AuthServiceDependency,
    CurrentUserDependency,
    EngineerUserDependency,
    ViewerUserDependency,
)
from interfaces.http.schemas.auth import (
    AuthorizationResponse,
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
    """Return the authenticated user and role."""

    return CurrentUserResponse(
        username=user.username,
        role=user.role,
    )


@router.get(
    "/rbac/admin",
    response_model=AuthorizationResponse,
)
def admin_access(
    user: AdminUserDependency,
) -> AuthorizationResponse:
    """Validate administrator authorization."""

    return AuthorizationResponse(
        username=user.username,
        role=user.role,
    )


@router.get(
    "/rbac/engineer",
    response_model=AuthorizationResponse,
)
def engineer_access(
    user: EngineerUserDependency,
) -> AuthorizationResponse:
    """Validate engineer-level authorization."""

    return AuthorizationResponse(
        username=user.username,
        role=user.role,
    )


@router.get(
    "/rbac/viewer",
    response_model=AuthorizationResponse,
)
def viewer_access(
    user: ViewerUserDependency,
) -> AuthorizationResponse:
    """Validate viewer-level authorization."""

    return AuthorizationResponse(
        username=user.username,
        role=user.role,
    )