import pytest

from domain.auth.user import AuthUser


def test_auth_user_can_be_created() -> None:
    user = AuthUser(username="admin")

    assert user.username == "admin"


@pytest.mark.parametrize(
    "username",
    ["", " ", "   "],
)
def test_auth_user_rejects_empty_username(
    username: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="username cannot be empty",
    ):
        AuthUser(username=username)