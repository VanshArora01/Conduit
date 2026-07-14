import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    title: str
    provider: str
    external_id: str | None = None
    mime_type: str
    status: str = "IMPORTED"
    metadata_: dict[str, Any] = Field(default_factory=dict)

    storage_path: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    processed_content: str | None = None


class DocumentCreate(DocumentBase):
    user_id: uuid.UUID
    integration_id: uuid.UUID | None = None


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    integration_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
