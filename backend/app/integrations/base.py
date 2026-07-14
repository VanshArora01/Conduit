from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from app.models.integration import Integration
from app.schemas.integration import NormalizedDocument

class BaseConnector(ABC):
    """
    Abstract Base Class for all external service connectors.
    
    Why it exists: To ensure every integration (Google Drive, GitHub, etc.)
    follows exactly the same lifecycle and interface, allowing the application
    to be completely agnostic of the underlying provider logic (Open/Closed Principle).
    """

    def __init__(self, integration: Integration):
        self.integration = integration
        self.credentials = integration.credentials or {}
        self.settings = integration.settings or {}

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish a connection or authenticate with the external service.
        Should return True if successful, raise an exception otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Revoke access, clean up resources, or log out of the external service.
        """
        raise NotImplementedError

    @abstractmethod
    async def sync(self) -> Dict[str, Any]:
        """
        High-level orchestration for synchronizing the integration.
        Typically calls fetch_documents, processes them, and returns a summary.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_documents(self, page_token: Optional[str] = None) -> Tuple[List[NormalizedDocument], Optional[str]]:
        """
        Retrieve normalized documents and metadata from the provider, along with an optional next page token.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_document(self, file_id: str) -> NormalizedDocument:
        """
        Retrieve a single normalized document and its metadata by ID.
        """
        raise NotImplementedError
        
    @abstractmethod
    async def download_file(self, file_id: str, mime_type: str) -> bytes:
        """
        Download the raw file contents from the provider.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify if the connection and credentials are still valid.
        """
        raise NotImplementedError
