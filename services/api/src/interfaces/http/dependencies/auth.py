"""FastAPI authentication and authorization dependencies."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.services.auth_exceptions import InvalidAccessTokenError
from application.services.auth_service import AuthService, UserManagementService
from domain.auth.user import AuthUser, PlatformUser, UserRole
from infrastructure.config import get_settings
from infrastructure.persistence.sqlite_user_repository import SQLiteUserRepository
from infrastructure.security.jwt_token_service import JWTTokenService
from infrastructure.security.password_hasher import Argon2PasswordHasher

_bearer_scheme = HTTPBearer(
    auto_error=False,
)
_user_repository: SQLiteUserRepository | None = None
_password_hasher: Argon2PasswordHasher | None = None


def get_user_repository() -> SQLiteUserRepository:
    """Return the configured persistent user repository."""

    global _user_repository

    if _user_repository is None:
        settings = get_settings()
        repository = SQLiteUserRepository(settings.sqlite_database_path)

        if repository.get(settings.auth_admin_username) is None:
            repository.save(
                PlatformUser(
                    username=settings.auth_admin_username,
                    password_hash=settings.auth_admin_password_hash,
                    role=settings.auth_admin_role,
                )
            )

        _user_repository = repository

    return _user_repository


def get_password_hasher() -> Argon2PasswordHasher:
    """Return the configured password hasher."""

    global _password_hasher

    if _password_hasher is None:
        _password_hasher = Argon2PasswordHasher()

    return _password_hasher


def create_auth_service() -> AuthService:
    """Create the configured authentication service."""

    settings = get_settings()

    password_hasher = get_password_hasher()

    token_service = JWTTokenService(
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expire_minutes=settings.auth_access_token_expire_minutes,
    )

    return AuthService(
        user_repository=get_user_repository(),
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


def get_user_management_service() -> UserManagementService:
    """Return the configured user management service."""

    return UserManagementService(
        user_repository=get_user_repository(),
        password_hasher=get_password_hasher(),
    )


UserManagementServiceDependency = Annotated[
    UserManagementService,
    Depends(get_user_management_service),
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
