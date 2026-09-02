"""HTTP authentication and RBAC integration tests."""

from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from domain.auth.user import UserRole
from infrastructure.security.jwt_token_service import JWTTokenService
from interfaces.http.app import app
from interfaces.http.dependencies.auth import get_auth_service

SECRET_KEY = "integration-test-secret-key-long-enough-for-hs256"
PASSWORD = "correct-password"
PASSWORD_HASH = "integration-test-hash"


class TestPasswordHasher:
    """Simple deterministic password checker."""

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return (
            password == PASSWORD
            and password_hash == PASSWORD_HASH
        )


def create_test_auth_service(
    role: UserRole = UserRole.ADMIN,
) -> AuthService:
    return AuthService(
        username="admin",
        password_hash=PASSWORD_HASH,
        role=role,
        password_hasher=TestPasswordHasher(),
        token_service=JWTTokenService(
            secret_key=SECRET_KEY,
            algorithm="HS256",
            expire_minutes=30,
        ),
    )


def create_client(
    role: UserRole = UserRole.ADMIN,
) -> TestClient:
    service = create_test_auth_service(role)

    app.dependency_overrides[get_auth_service] = lambda: service

    return TestClient(app)


def login(
    client: TestClient,
) -> str:
    response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_login_returns_access_token() -> None:
    client = create_client()

    response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_rejects_invalid_credentials() -> None:
    client = create_client()

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


def test_me_requires_authentication() -> None:
    client = create_client()

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_returns_authenticated_user_and_role() -> None:
    client = create_client(
        UserRole.ENGINEER,
    )

    token = login(client)

    response = client.get(
        "/auth/me",
        headers=bearer(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "admin",
        "role": "engineer",
    }


def test_me_rejects_invalid_token() -> None:
    client = create_client()

    response = client.get(
        "/auth/me",
        headers=bearer("invalid-token"),
    )

    assert response.status_code == 401


def test_admin_can_access_admin_endpoint() -> None:
    client = create_client(UserRole.ADMIN)
    token = login(client)

    response = client.get(
        "/auth/rbac/admin",
        headers=bearer(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "admin",
        "role": "admin",
        "authorized": True,
    }


def test_engineer_cannot_access_admin_endpoint() -> None:
    client = create_client(UserRole.ENGINEER)
    token = login(client)

    response = client.get(
        "/auth/rbac/admin",
        headers=bearer(token),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient permissions."
    }


def test_viewer_cannot_access_admin_endpoint() -> None:
    client = create_client(UserRole.VIEWER)
    token = login(client)

    response = client.get(
        "/auth/rbac/admin",
        headers=bearer(token),
    )

    assert response.status_code == 403


def test_admin_can_access_engineer_endpoint() -> None:
    client = create_client(UserRole.ADMIN)
    token = login(client)

    response = client.get(
        "/auth/rbac/engineer",
        headers=bearer(token),
    )

    assert response.status_code == 200


def test_engineer_can_access_engineer_endpoint() -> None:
    client = create_client(UserRole.ENGINEER)
    token = login(client)

    response = client.get(
        "/auth/rbac/engineer",
        headers=bearer(token),
    )

    assert response.status_code == 200


def test_viewer_cannot_access_engineer_endpoint() -> None:
    client = create_client(UserRole.VIEWER)
    token = login(client)

    response = client.get(
        "/auth/rbac/engineer",
        headers=bearer(token),
    )

    assert response.status_code == 403


def test_admin_can_access_viewer_endpoint() -> None:
    client = create_client(UserRole.ADMIN)
    token = login(client)

    response = client.get(
        "/auth/rbac/viewer",
        headers=bearer(token),
    )

    assert response.status_code == 200


def test_engineer_can_access_viewer_endpoint() -> None:
    client = create_client(UserRole.ENGINEER)
    token = login(client)

    response = client.get(
        "/auth/rbac/viewer",
        headers=bearer(token),
    )

    assert response.status_code == 200


def test_viewer_can_access_viewer_endpoint() -> None:
    client = create_client(UserRole.VIEWER)
    token = login(client)

    response = client.get(
        "/auth/rbac/viewer",
        headers=bearer(token),
    )

    assert response.status_code == 200


def test_rbac_endpoint_requires_authentication() -> None:
    client = create_client()

    response = client.get("/auth/rbac/admin")

    assert response.status_code == 401