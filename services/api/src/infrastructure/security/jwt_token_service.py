"""JWT access token implementation."""

from datetime import UTC, datetime, timedelta

import jwt

from application.ports.token_service import TokenService
from application.services.auth_exceptions import InvalidAccessTokenError


class JWTTokenService(TokenService):
    """Create and validate signed JWT access tokens."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        expire_minutes: int,
    ) -> None:
        if not secret_key.strip():
            raise ValueError("secret_key cannot be empty.")

        if not algorithm.strip():
            raise ValueError("algorithm cannot be empty.")

        if expire_minutes <= 0:
            raise ValueError(
                "expire_minutes must be greater than zero."
            )

        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, subject: str) -> str:
        """Create a signed JWT access token."""

        if not subject.strip():
            raise ValueError("subject cannot be empty.")

        now = datetime.now(UTC)

        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(
                minutes=self._expire_minutes,
            ),
        }

        return jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )

    def get_subject(self, token: str) -> str:
        """Validate a JWT and return its subject."""

        if not token.strip():
            raise InvalidAccessTokenError(
                "access token cannot be empty."
            )

        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidAccessTokenError(
                "invalid access token."
            ) from exc

        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.strip():
            raise InvalidAccessTokenError(
                "access token subject is invalid."
            )

        return subject