"""Registry of available connectors."""
from __future__ import annotations

from typing import Optional, Type

from .base import BaseConnector, ConnectorProvider

_REGISTRY: dict[ConnectorProvider, Type[BaseConnector]] = {}


def register_connector(provider: ConnectorProvider, cls: Type[BaseConnector]) -> None:
    _REGISTRY[provider] = cls


def get_connector_class(provider: ConnectorProvider) -> Optional[Type[BaseConnector]]:
    return _REGISTRY.get(provider)


def list_available_providers() -> list[ConnectorProvider]:
    return list(_REGISTRY.keys())


def create_connector(provider: ConnectorProvider, credentials: dict) -> BaseConnector:
    cls = get_connector_class(provider)
    if cls is None:
        raise ValueError(f"Connector {provider.value} no registrado")
    return cls(credentials)
