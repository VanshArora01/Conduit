import logging
import uuid
import datetime
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm.attributes import flag_modified

from app.models.document import Document
from app.models.chunk import Chunk
from app.ai.classifier.classifier import DocumentClassifier
from app.ai.cleaner.cleaners import CleanerFactory
from app.ai.chunking.implementations import ChunkerFactory
from app.ai.embeddings.huggingface import HuggingFaceEmbeddingProvider
from app.ai.vectorstore.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

class IndexingService:
    @staticmethod
    async def index_document(db: AsyncSession, document_id: uuid.UUID) -> None:
        """
        Executes the complete indexing pipeline for a document.
        """
        current_stage = "Load Document"
        
        try:
            logger.info(f"{current_stage}...")
            # Fetch document
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document with ID {document_id} not found.")
                
            if document.status == "INDEXED":
                logger.info(f"Document {document_id} is already indexed. Re-indexing requested. Clearing old chunks...")
                
            # Always clear existing DB chunks and Qdrant vectors before indexing (idempotency safety)
            await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
            try:
                vector_store = QdrantVectorStore()
                await vector_store.delete_by_document(None, document_id)
            except Exception as q_err:
                logger.warning(f"Failed to clear old Qdrant chunks for document {document_id}: {q_err}")
                
            document.status = "PARSING"
            await db.commit()
            
            if not document.processed_content:
                raise ValueError("Document has no processed content. Ensure parsing was successful.")
            logger.info("✓ Done")
            
            # 2. Classification
            current_stage = "Classifier"
            logger.info(f"{current_stage}...")
            classification = DocumentClassifier.classify(document.mime_type, document.title)
            logger.info("✓ Done")
            
            # 3. Cleaning
            current_stage = "Cleaner"
            logger.info(f"{current_stage}...")
            cleaner = CleanerFactory.get_cleaner(classification)
            cleaned_content = cleaner.clean(document.processed_content)
            logger.info("✓ Done")
            
            # 4. Chunking
            current_stage = "Chunker"
            logger.info(f"{current_stage}...")
            document.status = "CHUNKING"
            await db.commit()
            
            chunker = ChunkerFactory.get_chunker(classification)
            raw_chunks = chunker.chunk(cleaned_content)
            
            if not raw_chunks:
                logger.warning(f"No chunks produced for document {document_id}")
                document.status = "INDEXED"
                await db.commit()
                return
            logger.info("✓ Done")

            # 5. Embedding
            current_stage = "Embedding"
            logger.info(f"{current_stage}...")
            document.status = "EMBEDDING"
            await db.commit()
            
            embedder = HuggingFaceEmbeddingProvider()
            texts_to_embed = [rc["content"] for rc in raw_chunks]
            
            embeddings = embedder.embed_texts(texts_to_embed)
            logger.info("✓ Done")
            
            # 6. Vector Store and DB persistence
            current_stage = "Qdrant insertion"
            logger.info(f"{current_stage}...")
            vector_store = QdrantVectorStore()
            await vector_store.initialize_collection()
            
            chunk_ids = [str(uuid.uuid4()) for _ in raw_chunks]
            
            # Prepare payloads for Qdrant
            payloads = []
            db_chunks = []
            
            for idx, (rc, embedding, chunk_id) in enumerate(zip(raw_chunks, embeddings, chunk_ids)):
                metadata = {
                    "token_count": rc["token_count"],
                    "character_count": rc["character_count"],
                    "section_title": rc.get("section_title"),
                    "page_number": rc.get("page_number")
                }
                
                payload = {
                    "document_id": str(document_id),
                    "document_title": document.title,
                    "provider": document.provider,
                    "mime_type": document.mime_type,
                    "source_url": document.metadata_.get("source_url"),
                    "user_id": str(document.user_id),
                    "integration_id": str(document.integration_id) if document.integration_id else None,
                    "chunk_index": idx,
                    "content": rc["content"],
                    **metadata
                }
                payloads.append(payload)
                
                # Create DB Chunk
                db_chunk = Chunk(
                    id=uuid.UUID(chunk_id),
                    document_id=document_id,
                    chunk_index=idx,
                    content=rc["content"],
                    embedding_id=chunk_id, # Link back to vector DB point
                    metadata_=metadata
                )
                db_chunks.append(db_chunk)
                
            # Insert into Vector Store
            await vector_store.insert(
                collection_name=None, # Uses default
                vectors=embeddings,
                payloads=payloads,
                ids=chunk_ids
            )
            
            # Insert into DB
            db.add_all(db_chunks)
            logger.info("✓ Done")
            
            # 7. Finish
            current_stage = "Status update"
            logger.info(f"{current_stage}...")
            document.status = "INDEXED"
            await db.commit()
            logger.info("✓ Done")
            logger.info(f"Successfully indexed document {document_id} into {len(raw_chunks)} chunks.")
            
        except Exception as e:
            logger.info("✗ Failed")
            logger.error(f"Failed to index document {document_id} at stage '{current_stage}': {str(e)}", exc_info=True)
            # Re-fetch in case session is dirty
            await db.rollback()
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            if document:
                document.status = "FAILED"
                document.metadata_["failed_stage"] = current_stage
                document.metadata_["error_message"] = str(e)
                document.metadata_["error_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                flag_modified(document, "metadata_")
                await db.commit()
            raise

indexing_service = IndexingService()

async def run_background_indexing(document_id: uuid.UUID) -> None:
    """
    Background worker helper that runs document indexing under a fresh database session.
    Protects against request-scoped session closures.
    """
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await indexing_service.index_document(session, document_id)
