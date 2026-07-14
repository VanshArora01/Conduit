import uuid
import os
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.ai.indexing.service import indexing_service, run_background_indexing
from app.api.deps import get_current_user
from app.parsers.implementations import ParserFactory

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("")
async def list_documents(
    status: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List documents for the current user. Useful for 'Choose Documents' UI.
    """
    conditions = [Document.user_id == current_user.id]
    
    if status:
        conditions.append(Document.status == status)
    if provider:
        conditions.append(Document.provider == provider)
    if search:
        conditions.append(Document.title.ilike(f"%{search}%"))
        
    query = select(Document).where(and_(*conditions)).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return [{
        "id": doc.id,
        "title": doc.title,
        "provider": doc.provider,
        "status": doc.status,
        "mime_type": doc.mime_type
    } for doc in documents]

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a local document, parse it, store it, and start indexing.
    """
    try:
        raw_bytes = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        # 1. Parse
        parser = ParserFactory.get_parser(mime_type, file.filename)
        processed_text = parser.parse(raw_bytes, mime_type)
        
        # 2. Local Storage
        storage_dir = os.path.join("storage", "documents", str(current_user.id), "local")
        os.makedirs(storage_dir, exist_ok=True)
        safe_file_id = str(uuid.uuid4())
        file_path = os.path.join(storage_dir, f"{safe_file_id}.bin")
        
        with open(file_path, "wb") as f:
            f.write(raw_bytes)
            
        file_size = len(raw_bytes)
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        
        # 3. Store in DB
        document = Document(
            user_id=current_user.id,
            integration_id=None,
            title=file.filename,
            provider="local",
            external_id=safe_file_id,
            mime_type=mime_type,
            status="IMPORTED",
            storage_path=file_path,
            file_size=file_size,
            checksum=checksum,
            processed_content=processed_text,
            metadata_={
                "original_filename": file.filename
            }
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # 4. Trigger Indexing
        background_tasks.add_task(run_background_indexing, document.id)
        
        return {
            "status": "success",
            "document_id": str(document.id),
            "message": "Upload complete and indexing started."
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

@router.post("/{document_id}/index", status_code=202)
async def index_document_endpoint(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the complete indexing pipeline for a document.
    Runs asynchronously in the background.
    """
    result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.status == "INDEXED":
        return {"message": "Document is already indexed", "status": document.status}
        
    if document.status in ["PARSING", "CHUNKING", "EMBEDDING"]:
        return {"message": "Document is currently being indexed", "status": document.status}
        
    # Launch indexing pipeline in background
    background_tasks.add_task(run_background_indexing, document_id)
    
    return {"message": "Indexing pipeline started", "document_id": str(document_id)}


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current indexing status of a document.
    """
    result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {
        "document_id": str(document.id),
        "status": document.status
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document, clear its chunks from Qdrant vector store, and delete the physical storage file.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # 1. Delete physical local file if it exists
    if document.storage_path and os.path.exists(document.storage_path):
        try:
            os.remove(document.storage_path)
            logger.info(f"Deleted physical document file at {document.storage_path}")
        except Exception as e:
            logger.error(f"Failed to delete physical file {document.storage_path}: {e}")
            
    # 2. Delete from Qdrant vector store
    from app.ai.vectorstore.qdrant import QdrantVectorStore
    try:
        vector_store = QdrantVectorStore()
        await vector_store.delete_by_document(None, document.id)
        logger.info(f"Deleted Qdrant vectors for document {document.id}")
    except Exception as q_err:
        logger.error(f"Failed to delete Qdrant points for document {document.id}: {q_err}")
        
    # 3. Delete from DB (will cascade delete chunks and conversation_documents)
    await db.delete(document)
    await db.commit()
    
    return {"status": "success", "message": "Document deleted successfully."}
