"""Authentication application exceptions."""


class InvalidCredentialsError(Exception):
    """Raised when supplied authentication credentials are invalid."""


class InvalidAccessTokenError(Exception):
    """Raised when an access token is missing, malformed, or invalid."""