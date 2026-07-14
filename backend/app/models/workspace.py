from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base, BaseModel

class Workspace(Base, BaseModel):
    """
    SQLAlchemy Workspace Model.
    A workspace belongs to a User and contains integrations, documents, and chats.
    """
    __tablename__ = "workspaces"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="workspaces")
    sync_jobs: Mapped[list["SyncJob"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
