from abc import ABC, abstractmethod
from typing import TypedDict, Optional

class ChunkDict(TypedDict):
    content: str
    token_count: int
    character_count: int
    section_title: Optional[str]
    page_number: Optional[int]

class BaseChunker(ABC):
    """
    Abstract Base Class for all document chunkers.
    """
    @abstractmethod
    def chunk(self, text: str) -> list[ChunkDict]:
        """
        Split text into chunks.
        """
        raise NotImplementedError
