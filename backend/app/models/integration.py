from sqlalchemy import String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db.base import Base, BaseModel

class Integration(Base, BaseModel):
    """
    SQLAlchemy Integration Model.
    Represents a connected third-party account (e.g. Google Drive, GitHub) within a workspace.
    """
    __tablename__ = "integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # e.g. "google_drive", "github"
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    settings: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="integrations")
    documents: Mapped[list["Document"]] = relationship(back_populates="integration", cascade="all, delete-orphan")
    sync_jobs: Mapped[list["SyncJob"]] = relationship(back_populates="integration", cascade="all, delete-orphan")
