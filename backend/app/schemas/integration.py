from datetime import datetime

from pydantic import BaseModel, Field


class NormalizedDocument(BaseModel):
    id: str | None = None
    external_id: str
    title: str
    provider: str
    mime_type: str
    modified_at: datetime
    size: int | None = None
    web_view_link: str
    is_folder: bool


class DocumentListResponse(BaseModel):
    documents: list[NormalizedDocument]
    next_page_token: str | None = None


class DocumentImportRequest(BaseModel):
    file_ids: list[str]


class DocumentImportResponse(BaseModel):
    imported: int
    failed: int
    errors: list[dict[str, str]] = Field(default_factory=list)
