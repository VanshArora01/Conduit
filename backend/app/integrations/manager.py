from typing import Any, Dict, List
from app.models.integration import Integration
from app.integrations.registry import ConnectorRegistry
from app.integrations.base import BaseConnector
import app.integrations.providers  # This import ensures decorators trigger Registration

class ConnectorManager:
    """
    Factory class for instantiating and managing Connectors.
    
    Why it exists: It acts as the single entry point for the application to interact
    with third-party services. The application passes an Integration model, and the
    Manager looks up the correct provider in the Registry, instantiates it, and returns it.
    """

    @staticmethod
    def get_connector(integration: Integration) -> BaseConnector:
        """
        Instantiate the appropriate connector for the given integration.
        """
        connector_class = ConnectorRegistry.get_connector_class(integration.provider)
        return connector_class(integration)
