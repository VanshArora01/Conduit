from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class RetrievalService(ABC):
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top k chunks for a given query.
        Returns a list of dictionaries, where each dict has:
        - score: similarity score
        - payload: the enriched chunk data (document_title, content, etc.)
        """
        pass
