from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
import uuid
import datetime

class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat")

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: Dict[str, Any]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    document_count: Optional[int] = None
    last_message: Optional[str] = None
    messages: Optional[List[MessageResponse]] = None
    documents: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)

class ConversationDocumentResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    provider: str
    status: str
    attached_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    # Replaced generic filters with specific ones or none, as conversation_id is used for filtering
    # Added optional provider/mime_type for the Search Filters phase
    provider: Optional[str] = None
    mime_type: Optional[str] = None
    response_mode: Literal["AUTO", "KNOWLEDGE_ONLY", "GENERAL_ONLY", "HYBRID"] = "AUTO"

class TimingMetrics(BaseModel):
    planning_ms: int = 0
    retrieval_ms: int = 0
    embedding_ms: int = 0
    llm_ms: int = 0
    total_ms: int = 0

class CitationSchema(BaseModel):
    document_title: str
    provider: str
    chunk_index: int
    score: float

class RetrievedChunkSchema(BaseModel):
    score: float
    document_title: str
    content: str

class ChatQueryResponse(BaseModel):
    answer: str
    sources: List[CitationSchema]
    retrieved_chunks: List[RetrievedChunkSchema]
    provenance: str = "general"
    timing: TimingMetrics = Field(default_factory=TimingMetrics)
    debug_metadata: Optional[Dict[str, Any]] = None
    
class SearchResponse(BaseModel):
    chunks: List[RetrievedChunkSchema]

