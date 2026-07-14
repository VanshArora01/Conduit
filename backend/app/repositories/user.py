from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.user import UserCreate
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User, UserCreate, UserCreate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by their email address."""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()
        
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Fetch a user by their username."""
        result = await db.execute(select(User).filter(User.username == username))
        return result.scalars().first()

# Global instance
user_repo = UserRepository()
