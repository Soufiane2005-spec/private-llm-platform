import pytest

from application.services.auth_exceptions import InvalidAccessTokenError
from infrastructure.security.jwt_token_service import JWTTokenService


def create_service() -> JWTTokenService:
    return JWTTokenService(
        secret_key="test-secret-key-at-least-32-bytes-long",
        algorithm="HS256",
        expire_minutes=30,
    )


def test_token_service_creates_and_decodes_token() -> None:
    service = create_service()

    token = service.create_access_token("admin")

    assert service.get_subject(token) == "admin"


def test_token_service_rejects_invalid_token() -> None:
    service = create_service()

    with pytest.raises(InvalidAccessTokenError):
        service.get_subject("invalid-token")


def test_token_service_rejects_empty_token() -> None:
    service = create_service()

    with pytest.raises(InvalidAccessTokenError):
        service.get_subject("")


def test_token_service_rejects_empty_subject() -> None:
    service = create_service()

    with pytest.raises(
        ValueError,
        match="subject cannot be empty",
    ):
        service.create_access_token("")


@pytest.mark.parametrize(
    ("secret", "algorithm", "expire_minutes"),
    [
        ("", "HS256", 30),
        ("secret", "", 30),
        ("secret", "HS256", 0),
        ("secret", "HS256", -1),
    ],
)
def test_token_service_rejects_invalid_configuration(
    secret: str,
    algorithm: str,
    expire_minutes: int,
) -> None:
    with pytest.raises(ValueError):
        JWTTokenService(
            secret_key=secret,
            algorithm=algorithm,
            expire_minutes=expire_minutes,
        )
