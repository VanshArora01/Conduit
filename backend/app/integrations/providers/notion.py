from typing import Any, Dict, List
from app.integrations.base import BaseConnector
from app.integrations.registry import ConnectorRegistry

@ConnectorRegistry.register("notion")
class NotionConnector(BaseConnector):
    """
    Placeholder Notion Connector.
    """

    async def connect(self) -> bool:
        raise NotImplementedError("Notion connect not implemented yet.")

    async def disconnect(self) -> bool:
        raise NotImplementedError("Notion disconnect not implemented yet.")

    async def sync(self) -> Dict[str, Any]:
        raise NotImplementedError("Notion sync not implemented yet.")

    async def fetch_documents(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Notion fetch_documents not implemented yet.")

    async def health_check(self) -> bool:
        raise NotImplementedError("Notion health_check not implemented yet.")
