from typing import Type, Dict, TypeVar
from app.integrations.base import BaseConnector

C = TypeVar("C", bound=BaseConnector)

class ConnectorRegistry:
    """
    Registry for all external service connectors.
    
    Why it exists: To provide a centralized lookup mechanism so that the ConnectorManager
    can dynamically resolve a provider name (e.g., "google_drive") to its concrete 
    implementation class without needing hardcoded import statements everywhere.
    """
    
    _registry: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, provider_name: str):
        """
        Decorator to register a connector class with the registry.
        Usage:
            @ConnectorRegistry.register("google_drive")
            class GoogleDriveConnector(BaseConnector): ...
        """
        def wrapper(connector_class: Type[C]) -> Type[C]:
            cls._registry[provider_name] = connector_class
            return connector_class
        return wrapper

    @classmethod
    def get_connector_class(cls, provider_name: str) -> Type[BaseConnector]:
        """
        Retrieve a registered connector class by its provider name.
        """
        connector_class = cls._registry.get(provider_name)
        if not connector_class:
            raise ValueError(f"No connector registered for provider: {provider_name}")
        return connector_class
