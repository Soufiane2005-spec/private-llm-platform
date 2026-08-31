from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from infrastructure.security.jwt_token_service import JWTTokenService
from infrastructure.security.password_hasher import Argon2PasswordHasher
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import get_auth_service


def create_test_client() -> TestClient:
    hasher = Argon2PasswordHasher()

    service = AuthService(
        username="admin",
        password_hash=hasher.hash("secret-password"),
        password_hasher=hasher,
        token_service=JWTTokenService(
            secret_key="test-secret-key-at-least-32-bytes-long",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )

    app = create_app()

    app.dependency_overrides[get_auth_service] = lambda: service

    return TestClient(app)


def test_login_returns_access_token() -> None:
    client = create_test_client()

    response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "secret-password",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_rejects_invalid_credentials() -> None:
    client = create_test_client()

    response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid username or password."
    }


def test_me_returns_authenticated_user() -> None:
    client = create_test_client()

    login_response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "secret-password",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "admin",
    }


def test_me_requires_authentication() -> None:
    client = create_test_client()

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_me_rejects_invalid_token() -> None:
    client = create_test_client()

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired access token."
    }
