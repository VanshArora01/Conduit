from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from pydantic import ValidationError

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.token import Token, TokenPayload
from app.services.auth import AuthService
from app.models.user import User
from app.core.config import get_settings
from app.core.exceptions import AppException

router = APIRouter()
settings = get_settings()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    """
    user = await AuthService.register_user(db, user_in)
    return user

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return access and refresh tokens.
    """
    user = await AuthService.authenticate_user(db, user_in)
    
    access_token = AuthService.create_access_token(subject=user.id)
    refresh_token = AuthService.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(token: str = Body(...)):
    """
    Refresh an access token using a valid refresh token.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_REFRESH_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        if payload.get("type") != "refresh":
             raise AppException("Invalid token type.", status_code=status.HTTP_401_UNAUTHORIZED)
             
    except jwt.ExpiredSignatureError:
        raise AppException("Refresh token has expired", status_code=status.HTTP_401_UNAUTHORIZED)
    except (jwt.InvalidTokenError, ValidationError):
        raise AppException("Could not validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)
        
    access_token = AuthService.create_access_token(subject=token_data.sub)
    new_refresh_token = AuthService.create_refresh_token(subject=token_data.sub)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Placeholder for logout.
    In a fully stateless JWT architecture, the client just discards the token.
    To strictly enforce logout, we would add the token to a Redis blocklist here.
    """
    return {"message": "Successfully logged out. Please discard your token."}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile.
    """
    return current_user
