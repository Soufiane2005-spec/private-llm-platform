"""Tests for the authentication application service."""

import pytest

from application.services.auth_exceptions import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
)
from application.services.auth_service import AuthService
from domain.auth.user import PlatformUser, UserRole
from infrastructure.persistence.in_memory_user_repository import InMemoryUserRepository


class FakePasswordHasher:
    """Deterministic password hasher for service tests."""

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return (
            password == "correct-password"
            and password_hash == "stored-hash"
        )

    def hash(self, password: str) -> str:
        return f"hashed:{password}"


class FakeTokenService:
    """Deterministic token service for service tests."""

    def __init__(
        self,
        identity: tuple[str, UserRole] = (
            "admin",
            UserRole.ADMIN,
        ),
    ) -> None:
        self.identity = identity

    def create_access_token(
        self,
        subject: str,
        role: UserRole,
    ) -> str:
        return f"token:{subject}:{role.value}"

    def get_identity(
        self,
        token: str,
    ) -> tuple[str, UserRole]:
        if token == "invalid":
            raise InvalidAccessTokenError(
                "invalid access token."
            )

        return self.identity


def create_service(
    *,
    role: UserRole = UserRole.ADMIN,
    token_service: FakeTokenService | None = None,
    is_active: bool = True,
) -> AuthService:
    repository = InMemoryUserRepository(
        (
            PlatformUser(
                username="admin",
                password_hash="stored-hash",
                role=role,
                is_active=is_active,
            ),
        )
    )

    return AuthService(
        user_repository=repository,
        password_hasher=FakePasswordHasher(),
        token_service=token_service or FakeTokenService(),
    )


def test_auth_service_rejects_empty_username() -> None:
    service = AuthService(
        user_repository=InMemoryUserRepository(),
        password_hasher=FakePasswordHasher(),
        token_service=FakeTokenService(),
    )

    with pytest.raises(InvalidCredentialsError):
        service.authenticate("", "correct-password")


def test_auth_service_rejects_empty_password_hash() -> None:
    with pytest.raises(ValueError, match="password_hash cannot be empty"):
        PlatformUser(
            username="admin",
            password_hash="",
            role=UserRole.ADMIN,
        )


def test_authenticate_returns_user_and_token() -> None:
    service = create_service()

    user, token = service.authenticate(
        username="admin",
        password="correct-password",
    )

    assert user.username == "admin"
    assert user.role is UserRole.ADMIN
    assert token == "token:admin:admin"


def test_authenticate_rejects_wrong_username() -> None:
    service = create_service()

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="other",
            password="correct-password",
        )


def test_authenticate_rejects_wrong_password() -> None:
    service = create_service()

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="admin",
            password="wrong-password",
        )


def test_authenticate_rejects_disabled_user() -> None:
    service = create_service(is_active=False)

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="admin",
            password="correct-password",
        )


def test_get_current_user_returns_identity() -> None:
    service = create_service()

    user = service.get_current_user("valid-token")

    assert user.username == "admin"
    assert user.role is UserRole.ADMIN


def test_get_current_user_rejects_invalid_token() -> None:
    service = create_service()

    with pytest.raises(InvalidAccessTokenError):
        service.get_current_user("invalid")


def test_get_current_user_rejects_unknown_subject() -> None:
    service = create_service(
        token_service=FakeTokenService(
            identity=("other", UserRole.ADMIN),
        )
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="token subject is not a configured user",
    ):
        service.get_current_user("valid-token")


def test_get_current_user_rejects_wrong_role() -> None:
    service = create_service(
        role=UserRole.ADMIN,
        token_service=FakeTokenService(
            identity=("admin", UserRole.VIEWER),
        ),
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="token role does not match",
    ):
        service.get_current_user("valid-token")


def test_get_current_user_rejects_disabled_subject() -> None:
    service = create_service(
        is_active=False,
        token_service=FakeTokenService(
            identity=("admin", UserRole.ADMIN),
        ),
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="token subject is disabled",
    ):
        service.get_current_user("valid-token")
