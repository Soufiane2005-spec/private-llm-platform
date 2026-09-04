"""HTTP schemas for user management."""

from pydantic import BaseModel, Field

from domain.auth.user import UserRole


class UserResponse(BaseModel):
    """Public user representation without password hashes."""

    username: str
    role: UserRole
    is_active: bool


class UserCreateRequest(BaseModel):
    """Request payload for admin user creation."""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=200)
    role: UserRole


class UserUpdateRequest(BaseModel):
    """Request payload for admin user updates."""

    password: str | None = Field(default=None, min_length=8, max_length=200)
    role: UserRole | None = None
    is_active: bool | None = None
