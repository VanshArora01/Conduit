from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import uuid

class VectorStore(ABC):
    """
    Abstract Base Class for vector databases.
    """
    @abstractmethod
    async def insert(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> None:
        """
        Insert vectors into the collection.
        """
        raise NotImplementedError

    @abstractmethod
    async def similarity_search(self, collection_name: str, query_vector: List[float], limit: int = 10, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        """
        raise NotImplementedError
        
    @abstractmethod
    async def delete_by_document(self, collection_name: str, document_id: uuid.UUID) -> None:
        """
        Delete all vectors associated with a document_id.
        """
        raise NotImplementedError
