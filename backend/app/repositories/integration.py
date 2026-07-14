from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.integration import Integration
from pydantic import BaseModel

class IntegrationRepository(BaseRepository[Integration, BaseModel, BaseModel]):
    
    async def get_by_provider_and_user(
        self, db: AsyncSession, *, provider: str, user_id: UUID
    ) -> Optional[Integration]:
        statement = select(self.model).where(
            self.model.provider == provider,
            self.model.user_id == user_id
        )
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_external_id_and_provider(
        self, db: AsyncSession, *, external_account_id: str, provider: str
    ) -> Optional[Integration]:
        statement = select(self.model).where(
            self.model.external_account_id == external_account_id,
            self.model.provider == provider
        )
        result = await db.execute(statement)
        return result.scalar_one_or_none()

integration_repo = IntegrationRepository(Integration)
