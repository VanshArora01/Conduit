from abc import ABC, abstractmethod

class BaseCleaner(ABC):
    """
    Abstract Base Class for document cleaners.
    """
    @abstractmethod
    def clean(self, text: str) -> str:
        """
        Clean and normalize extracted text before chunking.
        """
        raise NotImplementedError
