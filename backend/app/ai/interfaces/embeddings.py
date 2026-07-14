from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """
    Abstract Base Class for embedding providers.
    """
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string.
        """
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of text strings.
        """
        raise NotImplementedError
