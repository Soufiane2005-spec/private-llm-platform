"""Tests for authentication user domain models."""

import pytest

from domain.auth.user import AuthUser, PlatformUser, UserRole


def test_auth_user_is_created_with_role() -> None:
    user = AuthUser(
        username="admin",
        role=UserRole.ADMIN,
    )

    assert user.username == "admin"
    assert user.role is UserRole.ADMIN


def test_auth_user_rejects_empty_username() -> None:
    with pytest.raises(
        ValueError,
        match="username cannot be empty",
    ):
        AuthUser(
            username="",
            role=UserRole.ADMIN,
        )


def test_auth_user_rejects_blank_username() -> None:
    with pytest.raises(
        ValueError,
        match="username cannot be empty",
    ):
        AuthUser(
            username="   ",
            role=UserRole.VIEWER,
        )


def test_supported_user_roles() -> None:
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.ENGINEER.value == "engineer"
    assert UserRole.VIEWER.value == "viewer"


def test_platform_user_requires_password_hash() -> None:
    with pytest.raises(ValueError, match="password_hash cannot be empty"):
        PlatformUser(
            username="admin",
            password_hash=" ",
            role=UserRole.ADMIN,
        )
