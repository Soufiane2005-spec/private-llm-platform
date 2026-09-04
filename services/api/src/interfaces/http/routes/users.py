"""HTTP routes for platform user management."""

from fastapi import APIRouter, HTTPException, status

from domain.auth.user import PlatformUser
from interfaces.http.dependencies.auth import (
    AdminUserDependency,
    UserManagementServiceDependency,
)
from interfaces.http.schemas.users import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(user: PlatformUser) -> UserResponse:
    return UserResponse(
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("", response_model=list[UserResponse])
def list_users(
    _user: AdminUserDependency,
    service: UserManagementServiceDependency,
) -> list[UserResponse]:
    """Return all platform users."""

    return [_to_response(user) for user in service.list_users()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    _user: AdminUserDependency,
    service: UserManagementServiceDependency,
) -> UserResponse:
    """Create a platform user."""

    try:
        user = service.create_user(
            username=request.username,
            password=request.password,
            role=request.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_response(user)


@router.patch("/{username}", response_model=UserResponse)
def update_user(
    username: str,
    request: UserUpdateRequest,
    _user: AdminUserDependency,
    service: UserManagementServiceDependency,
) -> UserResponse:
    """Update a platform user."""

    try:
        user = service.update_user(
            username,
            password=request.password,
            role=request.role,
            is_active=request.is_active,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_response(user)


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    username: str,
    _user: AdminUserDependency,
    service: UserManagementServiceDependency,
) -> None:
    """Delete a platform user."""

    try:
        service.delete_user(username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
