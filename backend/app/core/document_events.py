"""Emisión SSE para el gestor documental compartido (FIX P2-3 · 2026-06-09).

El gestor documental es un espacio por-proyecto compartido entre el admin (m24
IDMS) y el cliente (portal /files). Cuando cualquiera de los dos sube un
documento, el otro debe verlo aparecer en realtime (antes sólo via refetch
manual / on-mount).

Patrón: emitir ``document.uploaded`` en el canal ``project:{id}`` SÓLO tras el
commit (los endpoints llaman a este helper después de ``db.commit()``), best-effort
— la persistencia primaria NUNCA se bloquea por un fallo de notificación
(notify_best_effort). El filtro de audiencia (event_matches_audience) decide qué
ve cada portal: el admin todo; el cliente todo salvo los documentos ``interno``.
"""
from __future__ import annotations

import logging
import uuid

from backend.app.core.sse_dispatcher import sse_dispatcher

logger = logging.getLogger(__name__)


async def notify_document_uploaded(
    *,
    project_id: uuid.UUID | str,
    document_id: uuid.UUID | str,
    nombre: str | None,
    source: str,
    interno: bool = False,
) -> None:
    """Dispatch ``document.uploaded`` al canal del proyecto (best-effort).

    Args:
        project_id: proyecto dueño del documento (canal SSE).
        document_id: id del documento recién creado.
        nombre: nombre visible del documento (truncado a 255).
        source: ``"admin"`` | ``"cliente"`` — quién subió (UI puede matizar copy).
        interno: si True, el filtro de audiencia NO lo entrega al cliente.
    """
    try:
        await sse_dispatcher.dispatch(
            channel=f"project:{project_id}",
            event_type="document.uploaded",
            data={
                "project_id": str(project_id),
                "document_id": str(document_id),
                "nombre": (nombre or "")[:255],
                "source": source,
                "interno": bool(interno),
            },
        )
    except Exception:  # pragma: no cover · notify_best_effort
        logger.exception(
            "notify_document_uploaded best-effort failed · project=%s doc=%s",
            project_id, document_id,
        )
