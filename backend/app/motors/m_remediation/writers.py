"""Capa de escritura por proveedor · m_remediation (ADR-055).

`RemediationWriter` es la interfaz que EJECUTA la acción contra el sistema real
(API cloud o agente host). El motor (`service.py`) la consume de forma agnóstica:
preflight (read_state) → snapshot (read_state) → apply → verify (read_state) →
rollback si verify falla.

DEFAULT SEGURO: no hay writers reales registrados de fábrica. Si no hay writer
para un proveedor, el motor marca el job FAILED con mensaje explícito ("writer
no configurado") · NUNCA finge éxito. Los writers reales por proveedor se
registran explícitamente cuando el cliente concede scopes de escritura (opt-in).

Contrato de `read_state`: devuelve un dict que DEBE incluir la clave
`spec.desired_assertion` con valor booleano (True = ya cumple). El motor decide
idempotencia/verify con esa clave · el writer no decide tiers ni cumplimiento.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class WriterNotConfigured(Exception):
    """No hay writer registrado para el proveedor (default seguro)."""


class WriterError(Exception):
    """Fallo del writer aplicando/leyendo/revirtiendo (lo captura el motor)."""


@runtime_checkable
class RemediationWriter(Protocol):
    """Interfaz de escritura por proveedor. Implementaciones reales requieren
    credenciales de ESCRITURA concedidas por el cliente (opt-in)."""

    provider: str

    async def read_state(
        self, action_type: str, target_ref: str | None, params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Lee el estado actual del recurso. Incluye la clave desired_assertion."""
        ...

    async def apply(
        self, action_type: str, target_ref: str | None, params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Aplica la acción (idempotente). Devuelve metadatos del resultado."""
        ...

    async def rollback(
        self, action_type: str, target_ref: str | None, state_before: dict[str, Any],
    ) -> dict[str, Any]:
        """Restaura el estado previo capturado en el snapshot."""
        ...


# Registro de writers por proveedor (poblado en runtime · opt-in).
_WRITER_REGISTRY: dict[str, RemediationWriter] = {}


def register_writer(writer: RemediationWriter) -> None:
    """Registra un writer real para su proveedor (llamado al habilitar escritura)."""
    _WRITER_REGISTRY[writer.provider] = writer


def unregister_writer(provider: str) -> None:
    """Quita el writer de un proveedor (kill-switch · revocar escritura)."""
    _WRITER_REGISTRY.pop(provider, None)


def get_writer(provider: str) -> RemediationWriter:
    """Devuelve el writer del proveedor · alza WriterNotConfigured si no hay."""
    writer = _WRITER_REGISTRY.get(provider)
    if writer is None:
        raise WriterNotConfigured(
            f"No hay writer de remediación configurado para '{provider}'. "
            "La escritura es opt-in: requiere scopes concedidos por el cliente."
        )
    return writer


def has_writer(provider: str) -> bool:
    return provider in _WRITER_REGISTRY
