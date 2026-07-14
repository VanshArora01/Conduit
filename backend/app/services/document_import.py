import logging
import uuid
import os
import hashlib
from typing import List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.models.integration import Integration
from app.integrations.registry import ConnectorRegistry
from app.parsers.implementations import ParserFactory
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

class DocumentImportService:
    @staticmethod
    async def import_documents(
        db: AsyncSession, 
        user_id: uuid.UUID, 
        integration: Integration, 
        file_ids: List[str],
        background_tasks: Any = None
    ) -> dict[str, Any]:
        """
        Imports a batch of documents from an integration.
        Returns a dictionary with import statistics (e.g., {"imported": 2, "failed": 0, "errors": [...]}).
        """
        try:
            connector_class = ConnectorRegistry.get_connector_class(integration.provider)
        except ValueError:
            raise AppException(f"No connector found for provider: {integration.provider}", status_code=500)
            
        connector = connector_class(integration)
        
        imported_count = 0
        failed_count = 0
        errors = []
        
        integration_id = integration.id
        integration_provider = integration.provider
        
        
        # Collect all file metadata objects to import (expanding folders recursively if supported)
        docs_to_import = []
        for file_id in file_ids:
            try:
                normalized_doc = await connector.fetch_document(file_id)
                if normalized_doc.is_folder:
                    logger.info(f"Folder detected: {file_id}. Fetching files recursively...")
                    if hasattr(connector, "list_folder_files_recursive"):
                        folder_files = await connector.list_folder_files_recursive(file_id)
                        logger.info(f"Found {len(folder_files)} files in folder {file_id}")
                        docs_to_import.extend(folder_files)
                    else:
                        failed_count += 1
                        errors.append({"file_id": file_id, "reason": "Folders are not supported for this integration"})
                else:
                    docs_to_import.append(normalized_doc)
            except Exception as e:
                failed_count += 1
                errors.append({"file_id": file_id, "reason": f"Failed to fetch metadata: {str(e)}"})

        for normalized_doc in docs_to_import:
            file_id = normalized_doc.external_id
            mime_type = normalized_doc.mime_type
            try:
                # 2. Download contents
                raw_bytes = await connector.download_file(file_id, normalized_doc.mime_type)
                
                # 3. Parse contents
                parser = ParserFactory.get_parser(normalized_doc.mime_type, normalized_doc.title)
                processed_text = parser.parse(raw_bytes, normalized_doc.mime_type)
                
                # 3.5. Save to local storage
                storage_dir = os.path.join("storage", "documents", str(user_id), str(integration_id))
                os.makedirs(storage_dir, exist_ok=True)
                # Secure file name format
                safe_file_id = "".join(c for c in file_id if c.isalnum() or c in ('-', '_'))
                if not safe_file_id:
                    safe_file_id = str(uuid.uuid4())
                file_path = os.path.join(storage_dir, f"{safe_file_id}.bin")
                
                with open(file_path, "wb") as f:
                    f.write(raw_bytes)
                    
                file_size = len(raw_bytes)
                checksum = hashlib.sha256(raw_bytes).hexdigest()
                
                # Check if document already exists for this user (prevent duplicate imports)
                existing_doc_result = await db.execute(
                    select(Document).where(
                        Document.external_id == normalized_doc.external_id,
                        Document.provider == normalized_doc.provider,
                        Document.user_id == user_id
                    )
                )
                existing_document = existing_doc_result.scalar_one_or_none()
                
                if existing_document:
                    logger.info(f"Document with external_id {normalized_doc.external_id} already exists. Updating it...")
                    # Update fields
                    existing_document.title = normalized_doc.title
                    existing_document.mime_type = normalized_doc.mime_type
                    existing_document.status = "IMPORTED"
                    existing_document.storage_path = file_path
                    existing_document.file_size = file_size
                    existing_document.checksum = checksum
                    existing_document.processed_content = processed_text
                    existing_document.metadata_ = {
                        "size": normalized_doc.size,
                        "web_view_link": normalized_doc.web_view_link
                    }
                    document = existing_document
                else:
                    # 4. Store in database
                    document = Document(
                        user_id=user_id,
                        integration_id=integration_id,
                        title=normalized_doc.title,
                        provider=normalized_doc.provider,
                        external_id=normalized_doc.external_id,
                        mime_type=normalized_doc.mime_type,
                        status="IMPORTED",
                        storage_path=file_path,
                        file_size=file_size,
                        checksum=checksum,
                        processed_content=processed_text,
                        metadata_={
                            "size": normalized_doc.size,
                            "web_view_link": normalized_doc.web_view_link
                        }
                    )
                    db.add(document)
                
                await db.commit()
                
                if background_tasks:
                    from app.ai.indexing.service import run_background_indexing
                    background_tasks.add_task(run_background_indexing, document.id)
                
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Failed to import file {file_id} (MIME: {mime_type}): {str(e)}", exc_info=True)
                await db.rollback()
                failed_count += 1
                errors.append({"file_id": file_id, "reason": str(e)})
                
        return {
            "imported": imported_count,
            "failed": failed_count,
            "errors": errors
        }

document_import_service = DocumentImportService()
