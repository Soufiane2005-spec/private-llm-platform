import pytest

from infrastructure.security.password_hasher import Argon2PasswordHasher


def test_password_hasher_hashes_and_verifies_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash("secret-password")

    assert password_hash != "secret-password"
    assert hasher.verify(
        "secret-password",
        password_hash,
    )


def test_password_hasher_rejects_wrong_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash("secret-password")

    assert not hasher.verify(
        "wrong-password",
        password_hash,
    )


def test_password_hasher_rejects_empty_password() -> None:
    hasher = Argon2PasswordHasher()

    with pytest.raises(
        ValueError,
        match="password cannot be empty",
    ):
        hasher.hash("")


def test_password_hasher_returns_false_for_invalid_hash() -> None:
    hasher = Argon2PasswordHasher()

    assert not hasher.verify(
        "secret",
        "invalid-hash",
    )