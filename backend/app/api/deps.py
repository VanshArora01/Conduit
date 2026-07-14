import jwt
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload
from app.repositories.user import user_repo

settings = get_settings()

# We use HTTPBearer to automatically extract the token from the Authorization header
security = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises an AppException (401/403) if the token is invalid or user doesn't exist.
    """
    settings = get_settings()
    try:
        # Decode the token
        payload = jwt.decode(
            token.credentials, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Check if it's explicitly a refresh token (we don't allow refresh tokens for standard auth)
        if payload.get("type") == "refresh":
             raise AppException("Invalid token type. Please use an access token.", status_code=status.HTTP_401_UNAUTHORIZED)
             
    except jwt.ExpiredSignatureError:
        raise AppException("Token has expired", status_code=status.HTTP_401_UNAUTHORIZED)
    except (jwt.InvalidTokenError, ValidationError):
        raise AppException("Could not validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)
        
    # Verify the user exists
    user = await user_repo.get_by_id(db, id=UUID(token_data.sub))
    if not user:
        raise AppException("User not found", status_code=status.HTTP_401_UNAUTHORIZED)
        
    if not user.is_active:
        raise AppException("Inactive user", status_code=status.HTTP_403_FORBIDDEN)
        
    return user
