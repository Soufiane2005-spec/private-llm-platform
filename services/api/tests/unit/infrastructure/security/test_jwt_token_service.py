"""Tests for JWT token service."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from application.services.auth_exceptions import InvalidAccessTokenError
from domain.auth.user import UserRole
from infrastructure.security.jwt_token_service import JWTTokenService

SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"
ALGORITHM = "HS256"


def create_service() -> JWTTokenService:
    return JWTTokenService(
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        expire_minutes=30,
    )


def test_rejects_empty_secret_key() -> None:
    with pytest.raises(
        ValueError,
        match="secret_key cannot be empty",
    ):
        JWTTokenService(
            secret_key="",
            algorithm=ALGORITHM,
            expire_minutes=30,
        )


def test_rejects_empty_algorithm() -> None:
    with pytest.raises(
        ValueError,
        match="algorithm cannot be empty",
    ):
        JWTTokenService(
            secret_key=SECRET_KEY,
            algorithm="",
            expire_minutes=30,
        )


def test_rejects_invalid_expiration() -> None:
    with pytest.raises(
        ValueError,
        match="expire_minutes must be greater than zero",
    ):
        JWTTokenService(
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            expire_minutes=0,
        )


def test_create_access_token_returns_jwt() -> None:
    service = create_service()

    token = service.create_access_token(
        subject="admin",
        role=UserRole.ADMIN,
    )

    assert isinstance(token, str)
    assert token


def test_create_access_token_rejects_empty_subject() -> None:
    service = create_service()

    with pytest.raises(
        ValueError,
        match="subject cannot be empty",
    ):
        service.create_access_token(
            subject="",
            role=UserRole.ADMIN,
        )


def test_get_identity_returns_subject_and_role() -> None:
    service = create_service()

    token = service.create_access_token(
        subject="admin",
        role=UserRole.ENGINEER,
    )

    subject, role = service.get_identity(token)

    assert subject == "admin"
    assert role is UserRole.ENGINEER


def test_get_identity_rejects_empty_token() -> None:
    service = create_service()

    with pytest.raises(
        InvalidAccessTokenError,
        match="access token cannot be empty",
    ):
        service.get_identity("")


def test_get_identity_rejects_invalid_token() -> None:
    service = create_service()

    with pytest.raises(
        InvalidAccessTokenError,
        match="invalid access token",
    ):
        service.get_identity("not-a-jwt")


def test_get_identity_rejects_expired_token() -> None:
    service = create_service()

    payload = {
        "sub": "admin",
        "role": UserRole.ADMIN.value,
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="invalid access token",
    ):
        service.get_identity(token)


def test_get_identity_rejects_missing_subject() -> None:
    service = create_service()

    payload = {
        "role": UserRole.ADMIN.value,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="access token subject is invalid",
    ):
        service.get_identity(token)


def test_get_identity_rejects_missing_role() -> None:
    service = create_service()

    payload = {
        "sub": "admin",
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="access token role is invalid",
    ):
        service.get_identity(token)


def test_get_identity_rejects_unknown_role() -> None:
    service = create_service()

    payload = {
        "sub": "admin",
        "role": "superuser",
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(
        InvalidAccessTokenError,
        match="access token role is invalid",
    ):
        service.get_identity(token)