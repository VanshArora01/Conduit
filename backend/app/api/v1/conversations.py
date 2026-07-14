import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import List

from app.schemas.conversation import (
    ConversationQueryRequest, ChatQueryResponse, SearchResponse,
    ConversationCreate, ConversationResponse, ConversationDocumentResponse
)
from app.services.conversation import ConversationService
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
conversation_service = ConversationService()

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.get_all(db, current_user.id)

@router.post("", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.create(db, current_user.id, data)

@router.get("/{id}", response_model=ConversationResponse)
async def get_conversation(
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.get_one(db, current_user.id, id)

@router.delete("/{id}")
async def delete_conversation(
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await conversation_service.delete(db, current_user.id, id)
    return {"status": "success"}

@router.post("/{id}/documents")
async def attach_document(
    id: uuid.UUID = Path(...),
    document_id: uuid.UUID = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.attach_document(db, current_user.id, id, document_id)

@router.delete("/{id}/documents/{document_id}")
async def detach_document(
    id: uuid.UUID = Path(...),
    document_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.detach_document(db, current_user.id, id, document_id)

@router.post("/{id}/query", response_model=ChatQueryResponse)
async def chat_query(
    request: ConversationQueryRequest,
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return await conversation_service.query(db, id, request, user_id=current_user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during chat query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the query.")

@router.post("/{id}/stream")
async def chat_stream(
    request: ConversationQueryRequest,
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return EventSourceResponse(conversation_service.query_stream(db, id, request, user_id=current_user.id))
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error initializing chat stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while initializing the stream.")


@router.post("/{id}/search", response_model=SearchResponse)
async def chat_search(
    request: ConversationQueryRequest,
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return await conversation_service.search_only(db, id, request, user_id=current_user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the search.")

@router.get("/debug/pipeline/{pipeline_id}")
async def get_pipeline_debug(
    pipeline_id: str,
    current_user: User = Depends(get_current_user)
):
    from app.ai.pipeline.recorder import get_pipeline_execution
    execution = get_pipeline_execution(pipeline_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Pipeline execution {pipeline_id} not found in memory.")
    return execution.model_dump()

