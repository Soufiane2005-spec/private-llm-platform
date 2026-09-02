"""FastAPI authentication and authorization dependencies."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.services.auth_exceptions import InvalidAccessTokenError
from application.services.auth_service import AuthService
from domain.auth.user import AuthUser, UserRole
from infrastructure.config import get_settings
from infrastructure.security.jwt_token_service import JWTTokenService
from infrastructure.security.password_hasher import Argon2PasswordHasher

_bearer_scheme = HTTPBearer(
    auto_error=False,
)


def create_auth_service() -> AuthService:
    """Create the configured authentication service."""

    settings = get_settings()

    password_hasher = Argon2PasswordHasher()

    token_service = JWTTokenService(
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expire_minutes=settings.auth_access_token_expire_minutes,
    )

    return AuthService(
        username=settings.auth_admin_username,
        password_hash=settings.auth_admin_password_hash,
        role=settings.auth_admin_role,
        password_hasher=password_hasher,
        token_service=token_service,
    )


def get_auth_service() -> AuthService:
    """Return the configured authentication service."""

    return create_auth_service()


AuthServiceDependency = Annotated[
    AuthService,
    Depends(get_auth_service),
]


async def get_current_user(
    auth_service: AuthServiceDependency,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> AuthUser:
    """Return the authenticated user from a bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return auth_service.get_current_user(
            credentials.credentials,
        )
    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUserDependency = Annotated[
    AuthUser,
    Depends(get_current_user),
]


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[[AuthUser], AuthUser]:
    """Create a dependency requiring one of the allowed roles."""

    if not allowed_roles:
        raise ValueError(
            "at least one allowed role is required."
        )

    async def role_dependency(
        user: CurrentUserDependency,
    ) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return user

    return role_dependency


AdminUserDependency = Annotated[
    AuthUser,
    Depends(require_roles(UserRole.ADMIN)),
]

EngineerUserDependency = Annotated[
    AuthUser,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ENGINEER,
        )
    ),
]

ViewerUserDependency = Annotated[
    AuthUser,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ENGINEER,
            UserRole.VIEWER,
        )
    ),
]