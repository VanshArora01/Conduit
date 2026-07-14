import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func
from sqlalchemy.types import DateTime, Uuid

class Base(DeclarativeBase):
    """
    SQLAlchemy 2.x Declarative Base.
    All ORM models should inherit from this class.
    Why it exists: It acts as the registry for all models, allowing Alembic
    to auto-generate migrations by inspecting this Base's metadata.
    """
    pass

class BaseModel:
    """
    Reusable base model mixin that provides common columns for all tables.
    Why it exists: To ensure consistency across the database. Every future model
    will automatically inherit a UUID primary key and timestamp columns.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        server_default=func.now()
    )
