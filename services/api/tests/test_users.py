"""HTTP tests for admin user management endpoints."""

from fastapi.testclient import TestClient

from application.services.auth_service import AuthService, UserManagementService
from domain.auth.user import PlatformUser, UserRole
from infrastructure.persistence.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.jwt_token_service import JWTTokenService
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import (
    get_auth_service,
    get_user_management_service,
)

SECRET_KEY = "users-test-secret-long-enough-for-hs256"
PASSWORD = "correct-password"
PASSWORD_HASH = "users-test-hash"


class TestPasswordHasher:
    """Deterministic password hasher for user management tests."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password == PASSWORD and password_hash == PASSWORD_HASH


def create_client(role: UserRole = UserRole.ADMIN) -> TestClient:
    """Create an authenticated test client with isolated users."""

    repository = InMemoryUserRepository(
        (
            PlatformUser(
                username="admin",
                password_hash=PASSWORD_HASH,
                role=role,
            ),
        )
    )
    hasher = TestPasswordHasher()
    auth_service = AuthService(
        user_repository=repository,
        password_hasher=hasher,
        token_service=JWTTokenService(
            secret_key=SECRET_KEY,
            algorithm="HS256",
            expire_minutes=30,
        ),
    )
    management_service = UserManagementService(
        user_repository=repository,
        password_hasher=hasher,
    )
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_user_management_service] = lambda: management_service
    return TestClient(app)


def auth_headers(client: TestClient) -> dict[str, str]:
    """Return bearer auth headers for the test admin."""

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_creates_lists_updates_and_deletes_user() -> None:
    """Admin can manage users without exposing password hashes."""

    client = create_client()
    headers = auth_headers(client)

    create_response = client.post(
        "/users",
        json={
            "username": "engineer",
            "password": "strong-password",
            "role": "engineer",
        },
        headers=headers,
    )
    list_response = client.get("/users", headers=headers)
    update_response = client.patch(
        "/users/engineer",
        json={"role": "viewer", "is_active": False},
        headers=headers,
    )
    delete_response = client.delete("/users/engineer", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json() == {
        "username": "engineer",
        "role": "engineer",
        "is_active": True,
    }
    assert list_response.status_code == 200
    assert "password_hash" not in list_response.text
    assert update_response.status_code == 200
    assert update_response.json() == {
        "username": "engineer",
        "role": "viewer",
        "is_active": False,
    }
    assert delete_response.status_code == 204


def test_user_management_is_admin_only() -> None:
    """Engineer and viewer roles cannot manage users."""

    client = create_client(UserRole.ENGINEER)
    headers = auth_headers(client)

    response = client.get("/users", headers=headers)

    assert response.status_code == 403
