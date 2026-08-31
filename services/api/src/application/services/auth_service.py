"""Authentication application service."""

from application.ports.password_hasher import PasswordHasher
from application.ports.token_service import TokenService
from application.services.auth_exceptions import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
)
from domain.auth.user import AuthUser


class AuthService:
    """Authenticate users and validate access tokens."""

    def __init__(
        self,
        *,
        username: str,
        password_hash: str,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        if not username.strip():
            raise ValueError("username cannot be empty.")

        if not password_hash.strip():
            raise ValueError("password_hash cannot be empty.")

        self._username = username
        self._password_hash = password_hash
        self._password_hasher = password_hasher
        self._token_service = token_service

    def authenticate(
        self,
        username: str,
        password: str,
    ) -> tuple[AuthUser, str]:
        """Authenticate credentials and return a JWT access token."""

        if (
            username != self._username
            or not self._password_hasher.verify(
                password,
                self._password_hash,
            )
        ):
            raise InvalidCredentialsError(
                "invalid username or password."
            )

        user = AuthUser(username=self._username)

        token = self._token_service.create_access_token(
            subject=user.username,
        )

        return user, token

    def get_current_user(self, token: str) -> AuthUser:
        """Validate an access token and return its user."""

        try:
            subject = self._token_service.get_subject(token)
        except InvalidAccessTokenError:
            raise

        if subject != self._username:
            raise InvalidAccessTokenError(
                "token subject is not a configured user."
            )

        return AuthUser(username=subject)