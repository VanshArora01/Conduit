import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.schemas.user import UserCreate, UserLogin
from app.repositories.user import user_repo
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

# Initialize modern password hashing using argon2
password_hash = PasswordHash((Argon2Hasher(),))

class AuthService:
    """
    Business logic layer for Authentication and User management.
    """
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return password_hash.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return password_hash.hash(password)

    @staticmethod
    def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
        settings = get_settings()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(subject: str | int) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
        encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
        """Register a new user after validation."""
        # Check if user already exists
        user = await user_repo.get_by_email(db, email=user_in.email)
        if user:
            raise AppException("A user with this email already exists.", status_code=400)
            
        if user_in.username:
            user_by_username = await user_repo.get_by_username(db, username=user_in.username)
            if user_by_username:
                raise AppException("A user with this username already exists.", status_code=400)

        # Hash password and create user object
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = AuthService.get_password_hash(user_in.password)
        
        # In a real app, you might trigger an email verification here
        
        new_user = await user_repo.create(db, obj_in=user_data)
        return new_user

    @staticmethod
    async def authenticate_user(db: AsyncSession, user_in: UserLogin) -> User:
        """Authenticate user and return the user object."""
        user = await user_repo.get_by_email(db, email=user_in.email)
        if not user:
            raise AppException("Incorrect email or password.", status_code=401)
            
        if not AuthService.verify_password(user_in.password, user.hashed_password):
            raise AppException("Incorrect email or password.", status_code=401)
            
        if not user.is_active:
            raise AppException("Inactive user.", status_code=403)
            
        return user
