import pytest

from application.services.auth_exceptions import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
)
from application.services.auth_service import AuthService
from infrastructure.security.jwt_token_service import JWTTokenService
from infrastructure.security.password_hasher import Argon2PasswordHasher


def create_service() -> AuthService:
    hasher = Argon2PasswordHasher()

    return AuthService(
        username="admin",
        password_hash=hasher.hash("secret-password"),
        password_hasher=hasher,
        token_service=JWTTokenService(
            secret_key="test-secret-key-at-least-32-bytes-long",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )


def test_auth_service_authenticates_valid_credentials() -> None:
    service = create_service()

    user, token = service.authenticate(
        username="admin",
        password="secret-password",
    )

    assert user.username == "admin"
    assert token


def test_auth_service_rejects_invalid_username() -> None:
    service = create_service()

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="unknown",
            password="secret-password",
        )


def test_auth_service_rejects_invalid_password() -> None:
    service = create_service()

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(
            username="admin",
            password="wrong-password",
        )


def test_auth_service_returns_current_user() -> None:
    service = create_service()

    _, token = service.authenticate(
        username="admin",
        password="secret-password",
    )

    user = service.get_current_user(token)

    assert user.username == "admin"


def test_auth_service_rejects_invalid_access_token() -> None:
    service = create_service()

    with pytest.raises(InvalidAccessTokenError):
        service.get_current_user("invalid-token")
