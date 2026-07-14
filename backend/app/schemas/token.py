
from pydantic import BaseModel


class Token(BaseModel):
    """Schema for the JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for decoding the JWT token payload."""

    sub: str | None = None
    exp: int | None = None
