"""Authentication application service."""

from application.ports.password_hasher import PasswordHasher
from application.ports.token_service import TokenService
from application.ports.user_repository import UserRepository
from application.services.auth_exceptions import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
)
from domain.auth.user import AuthUser, PlatformUser, UserRole


class AuthService:
    """Authenticate users and validate access tokens."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    def authenticate(
        self,
        username: str,
        password: str,
    ) -> tuple[AuthUser, str]:
        """Authenticate credentials and return a JWT access token."""

        user = self._user_repository.get(username)

        if (
            user is None
            or not user.is_active
            or not self._password_hasher.verify(password, user.password_hash)
        ):
            raise InvalidCredentialsError(
                "invalid username or password."
            )

        auth_user = AuthUser(
            username=user.username,
            role=user.role,
        )

        token = self._token_service.create_access_token(
            subject=auth_user.username,
            role=auth_user.role,
        )

        return auth_user, token

    def get_current_user(self, token: str) -> AuthUser:
        """Validate an access token and return its user."""

        try:
            subject, role = self._token_service.get_identity(token)
        except InvalidAccessTokenError:
            raise

        user = self._user_repository.get(subject)

        if user is None:
            raise InvalidAccessTokenError(
                "token subject is not a configured user."
            )

        if not user.is_active:
            raise InvalidAccessTokenError(
                "token subject is disabled."
            )

        if role != user.role:
            raise InvalidAccessTokenError(
                "token role does not match the configured user."
            )

        return AuthUser(
            username=subject,
            role=role,
        )


class UserManagementService:
    """Manage persisted platform users."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    def list_users(self) -> tuple[PlatformUser, ...]:
        """Return all users."""

        return self._user_repository.list()

    def create_user(
        self,
        *,
        username: str,
        password: str,
        role: UserRole,
    ) -> PlatformUser:
        """Create a user with an Argon2 password hash."""

        if self._user_repository.get(username) is not None:
            raise ValueError("user already exists.")

        user = PlatformUser(
            username=username.strip(),
            password_hash=self._password_hasher.hash(password),
            role=role,
        )
        self._user_repository.save(user)
        return user

    def update_user(
        self,
        username: str,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        password: str | None = None,
    ) -> PlatformUser:
        """Update mutable user account fields."""

        current = self._require_user(username)
        updated = PlatformUser(
            username=current.username,
            password_hash=(
                current.password_hash
                if password is None
                else self._password_hasher.hash(password)
            ),
            role=current.role if role is None else role,
            is_active=current.is_active if is_active is None else is_active,
        )
        self._user_repository.save(updated)
        return updated

    def delete_user(self, username: str) -> None:
        """Delete a user."""

        self._require_user(username)
        self._user_repository.delete(username)

    def _require_user(self, username: str) -> PlatformUser:
        user = self._user_repository.get(username)

        if user is None:
            raise KeyError("User not found.")

        return user
