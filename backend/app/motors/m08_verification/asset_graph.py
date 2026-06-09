"""Grafo de activos M8 sobre PKG-lite (doc §3 · D2 PKG-lite reuse).

El doc cita "Apache AGE"; FULKRO usa PKG-lite (pkg_nodes/pkg_edges,
decisión docs/decisions/pkg_lite_vs_apache_age.md) ya productivo en M22.
Reutilizamos `pkg_service` para mapear cada activo afectado por un hallazgo
a un nodo del grafo y estimar blast-radius/MTTR vía BFS sobre `depends_on`.

Idempotente (external_id estable `m8-asset:{project}:{host}`). No introduce
AGE. Toca BD (no es pura) pero es thin wrapper sobre pkg_service.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m16_onboarding import pkg_service

logger = logging.getLogger(__name__)


async def upsert_asset_for_finding(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    host: str,
    worst_severity: str | None = None,
    service: str | None = None,
    extra: dict[str, Any] | None = None,
) -> uuid.UUID | None:
    """Crea/actualiza el nodo de activo PKG-lite para un host afectado.

    Devuelve el pkg_node_id (→ verification_findings.asset_node_id) o None
    si falla (fail-soft · no rompe el pipeline).
    """
    if not host or host == "unknown":
        return None
    external_id = f"m8-asset:{project_id}:{host}"
    props: dict[str, Any] = {"host": host, "source": "m08_verification"}
    if worst_severity:
        props["worst_severity"] = worst_severity
    if service:
        props["service"] = service
    if extra:
        props.update(extra)
    try:
        return await pkg_service.add_node(
            db, project_id, "asset", label=host,
            external_id=external_id, properties=props,
        )
    except Exception as exc:  # pragma: no cover — fail-soft
        logger.warning("upsert_asset_for_finding(%s) falló: %s", host, exc)
        return None


async def blast_radius(
    db: AsyncSession,
    asset_node_id: uuid.UUID,
    *,
    max_depth: int = 2,
) -> dict[str, Any]:
    """Estima el alcance (blast-radius) de comprometer un activo, vía BFS
    sobre aristas `depends_on` del grafo PKG-lite. Para priorización/MTTR.

    Devuelve {nodes, edges, total_nodes, total_edges} o un dict vacío
    seguro si el grafo no es navegable.
    """
    try:
        return await pkg_service.traverse_bfs(
            db, asset_node_id, max_depth=max_depth, edge_types=["depends_on"],
        )
    except Exception as exc:  # pragma: no cover — fail-soft
        logger.warning("blast_radius(%s) falló: %s", asset_node_id, exc)
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}
