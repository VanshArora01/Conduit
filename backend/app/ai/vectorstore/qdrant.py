from typing import List, Dict, Any, Optional
import uuid
import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from app.ai.interfaces.vectorstore import VectorStore
from app.core.config import get_settings
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class QdrantVectorStore(VectorStore):
    def __init__(self, collection_name: str = ai_config.QDRANT_DEFAULT_COLLECTION, vector_size: int = ai_config.EMBEDDING_DIMENSIONS):
        settings = get_settings()
        # Ensure we connect to Qdrant based on settings
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = collection_name
        self.vector_size = vector_size
        
    async def initialize_collection(self):
        """
        Create collection if it doesn't exist.
        """
        try:
            collections_response = await self.client.get_collections()
            collection_names = [c.name for c in collections_response.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
                
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                logger.info(f"Created payload index for 'document_id' in {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {str(e)}")
            raise

    async def insert(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> None:
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
            
        points = [
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        await self.client.upsert(
            collection_name=collection_name or self.collection_name,
            points=points
        )

    async def similarity_search(self, collection_name: str, query_vector: List[float], limit: int = 10, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query_filter = None
        if filter_criteria:
            must_conditions = []
            for k, v in filter_criteria.items():
                if isinstance(v, list):
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key=k,
                            match=qmodels.MatchAny(any=v)
                        )
                    )
                elif isinstance(v, (str, int, bool)):
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key=k,
                            match=qmodels.MatchValue(value=v)
                        )
                    )
                else:
                    logger.warning(f"Skipping unsupported filter type for key '{k}': {type(v)}")
                    
            if must_conditions:
                query_filter = qmodels.Filter(must=must_conditions)
            
        response = await self.client.query_points(
            collection_name=collection_name or self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )
        
        return [
            {
                "id": str(res.id),
                "score": res.score,
                "payload": res.payload
            }
            for res in response.points
        ]

    async def delete_by_document(self, collection_name: str, document_id: uuid.UUID) -> None:
        await self.client.delete(
            collection_name=collection_name or self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id))
                        )
                    ]
                )
            )
        )
