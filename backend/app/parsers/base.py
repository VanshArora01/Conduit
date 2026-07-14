from abc import ABC, abstractmethod

class BaseParser(ABC):
    """
    Abstract Base Class for all document parsers.
    Why it exists: To ensure consistent parsing behavior regardless of the file type.
    """
    
    @abstractmethod
    def parse(self, content: bytes, mime_type: str) -> str:
        """
        Parse raw bytes into processed text content.
        """
        raise NotImplementedError
