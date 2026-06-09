"""PKG-lite service layer (graph API over SQL tables).

Motores downstream call PKGService, never do SQL directly against pkg_nodes/pkg_edges.
ADR: docs/decisions/pkg_lite_vs_apache_age.md
"""
from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pkg import PKGEdge, PKGNode


class PKGError(ValueError):
    pass


NODE_TYPES = {
    "person", "system", "asset", "process", "information",
    "service", "provider", "identity",
}

EDGE_TYPES = {
    "reports_to", "owns", "uses", "processes", "depends_on",
    "provides", "member_of", "has_role", "categorized_as",
}


# ==== NODES ====

async def add_node(
    session: AsyncSession,
    project_id: uuid.UUID,
    node_type: str,
    label: str,
    external_id: Optional[str] = None,
    properties: Optional[dict] = None,
) -> uuid.UUID:
    if node_type not in NODE_TYPES:
        raise PKGError(f"node_type {node_type} no valido. Validos: {NODE_TYPES}")

    if external_id:
        r = await session.execute(
            select(PKGNode).where(
                PKGNode.project_id == project_id,
                PKGNode.external_id == external_id,
            )
        )
        existing = r.scalar_one_or_none()
        if existing:
            existing.label = label
            existing.properties = {**(existing.properties or {}), **(properties or {})}
            existing.updated_at = datetime.now(timezone.utc)
            await session.flush()
            return existing.id

    node = PKGNode(
        project_id=project_id,
        node_type=node_type,
        label=label,
        external_id=external_id,
        properties=properties,
    )
    session.add(node)
    await session.flush()
    return node.id


async def bulk_upsert_nodes(
    session: AsyncSession,
    project_id: uuid.UUID,
    nodes: list[dict],
) -> list[uuid.UUID]:
    ids = []
    for n in nodes:
        nid = await add_node(
            session, project_id,
            node_type=n["node_type"],
            label=n["label"],
            external_id=n.get("external_id"),
            properties=n.get("properties"),
        )
        ids.append(nid)
    return ids


async def get_node(session: AsyncSession, node_id: uuid.UUID) -> Optional[dict]:
    r = await session.execute(select(PKGNode).where(PKGNode.id == node_id))
    n = r.scalar_one_or_none()
    return _node_to_dict(n) if n else None


async def get_nodes_by_type(
    session: AsyncSession,
    project_id: uuid.UUID,
    node_type: str,
    label_contains: Optional[str] = None,
) -> list[dict]:
    stmt = select(PKGNode).where(
        PKGNode.project_id == project_id,
        PKGNode.node_type == node_type,
    )
    if label_contains:
        stmt = stmt.where(PKGNode.label.ilike(f"%{label_contains}%"))
    stmt = stmt.order_by(PKGNode.label)
    r = await session.execute(stmt)
    return [_node_to_dict(n) for n in r.scalars().all()]


async def find_node_by_external_id(
    session: AsyncSession,
    project_id: uuid.UUID,
    external_id: str,
) -> Optional[dict]:
    r = await session.execute(
        select(PKGNode).where(
            PKGNode.project_id == project_id,
            PKGNode.external_id == external_id,
        )
    )
    n = r.scalar_one_or_none()
    return _node_to_dict(n) if n else None


async def delete_node(session: AsyncSession, node_id: uuid.UUID) -> bool:
    r = await session.execute(select(PKGNode).where(PKGNode.id == node_id))
    node = r.scalar_one_or_none()
    if node is None:
        return False
    await session.delete(node)
    await session.flush()
    return True


# ==== EDGES ====

async def add_edge(
    session: AsyncSession,
    project_id: uuid.UUID,
    source_node_id: uuid.UUID,
    target_node_id: uuid.UUID,
    edge_type: str,
    properties: Optional[dict] = None,
) -> uuid.UUID:
    if edge_type not in EDGE_TYPES:
        raise PKGError(f"edge_type {edge_type} no valido. Validos: {EDGE_TYPES}")

    for nid in [source_node_id, target_node_id]:
        r = await session.execute(select(PKGNode.id).where(PKGNode.id == nid))
        if r.scalar_one_or_none() is None:
            raise PKGError(f"Nodo {nid} no existe")

    r = await session.execute(
        select(PKGEdge).where(
            PKGEdge.source_node_id == source_node_id,
            PKGEdge.target_node_id == target_node_id,
            PKGEdge.edge_type == edge_type,
        )
    )
    existing = r.scalar_one_or_none()
    if existing:
        existing.properties = {**(existing.properties or {}), **(properties or {})}
        await session.flush()
        return existing.id

    edge = PKGEdge(
        project_id=project_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        edge_type=edge_type,
        properties=properties,
    )
    session.add(edge)
    await session.flush()
    return edge.id


# ==== QUERIES ====

async def get_neighbors(
    session: AsyncSession,
    node_id: uuid.UUID,
    edge_type: Optional[str] = None,
    direction: str = "both",
) -> list[dict]:
    neighbor_ids: set[uuid.UUID] = set()

    if direction in ("outgoing", "both"):
        stmt = select(PKGEdge.target_node_id).where(PKGEdge.source_node_id == node_id)
        if edge_type:
            stmt = stmt.where(PKGEdge.edge_type == edge_type)
        r = await session.execute(stmt)
        neighbor_ids.update(row[0] for row in r.all())

    if direction in ("incoming", "both"):
        stmt = select(PKGEdge.source_node_id).where(PKGEdge.target_node_id == node_id)
        if edge_type:
            stmt = stmt.where(PKGEdge.edge_type == edge_type)
        r = await session.execute(stmt)
        neighbor_ids.update(row[0] for row in r.all())

    if not neighbor_ids:
        return []

    r = await session.execute(select(PKGNode).where(PKGNode.id.in_(neighbor_ids)))
    return [_node_to_dict(n) for n in r.scalars().all()]


async def get_edges_for_node(
    session: AsyncSession,
    node_id: uuid.UUID,
    edge_type: Optional[str] = None,
    direction: str = "both",
) -> list[dict]:
    conditions = []
    if direction in ("outgoing", "both"):
        conditions.append(PKGEdge.source_node_id == node_id)
    if direction in ("incoming", "both"):
        conditions.append(PKGEdge.target_node_id == node_id)

    stmt = select(PKGEdge).where(or_(*conditions))
    if edge_type:
        stmt = stmt.where(PKGEdge.edge_type == edge_type)
    r = await session.execute(stmt)
    return [_edge_to_dict(e) for e in r.scalars().all()]


async def traverse_bfs(
    session: AsyncSession,
    start_node_id: uuid.UUID,
    max_depth: int = 3,
    edge_types: Optional[list[str]] = None,
) -> dict:
    visited_nodes: set[uuid.UUID] = set()
    visited_edges: set[uuid.UUID] = set()
    queue: deque[tuple[uuid.UUID, int]] = deque([(start_node_id, 0)])
    result_nodes: list[dict] = []
    result_edges: list[dict] = []

    while queue:
        current_id, depth = queue.popleft()
        if current_id in visited_nodes:
            continue
        visited_nodes.add(current_id)

        node = await get_node(session, current_id)
        if node:
            result_nodes.append(node)

        if depth >= max_depth:
            continue

        stmt = select(PKGEdge).where(PKGEdge.source_node_id == current_id)
        if edge_types:
            stmt = stmt.where(PKGEdge.edge_type.in_(edge_types))
        r = await session.execute(stmt)

        for edge in r.scalars().all():
            if edge.id not in visited_edges:
                visited_edges.add(edge.id)
                result_edges.append(_edge_to_dict(edge))
                queue.append((edge.target_node_id, depth + 1))

    return {
        "nodes": result_nodes,
        "edges": result_edges,
        "total_nodes": len(result_nodes),
        "total_edges": len(result_edges),
    }


async def get_project_summary(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    r = await session.execute(
        select(PKGNode.node_type, func.count(PKGNode.id))
        .where(PKGNode.project_id == project_id)
        .group_by(PKGNode.node_type)
    )
    nodes_by_type = {row[0]: row[1] for row in r.all()}

    r = await session.execute(
        select(PKGEdge.edge_type, func.count(PKGEdge.id))
        .where(PKGEdge.project_id == project_id)
        .group_by(PKGEdge.edge_type)
    )
    edges_by_type = {row[0]: row[1] for row in r.all()}

    return {
        "project_id": project_id,
        "total_nodes": sum(nodes_by_type.values()),
        "total_edges": sum(edges_by_type.values()),
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
    }


# ==== HELPERS ====

def _node_to_dict(n: PKGNode) -> dict:
    return {
        "id": n.id, "project_id": n.project_id, "node_type": n.node_type,
        "label": n.label, "external_id": n.external_id, "properties": n.properties,
        "created_at": n.created_at, "updated_at": n.updated_at,
    }


def _edge_to_dict(e: PKGEdge) -> dict:
    return {
        "id": e.id, "project_id": e.project_id,
        "source_node_id": e.source_node_id, "target_node_id": e.target_node_id,
        "edge_type": e.edge_type, "properties": e.properties, "created_at": e.created_at,
    }
