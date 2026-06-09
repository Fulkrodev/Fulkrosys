"""PKG Tools — aggregated/anonymized functions for M11 Copiloto consumption.

Each tool returns aggregated data without PII. The LLM sees statistics and
categories, not raw client data.

Future (M16-MCP-TRANSPORT): wrap these in an MCP server when multi-process is needed.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OnboardingSession
from backend.app.models.pkg import PKGEdge

from . import pkg_service as pkg
from .enums import SessionState


async def pkg_project_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Complete PKG summary for a project."""
    return await pkg.get_project_summary(session, project_id)


async def pkg_count_assets_by_type(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Assets grouped by subtype."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "asset")
    by_subtype: dict[str, int] = {}
    for n in nodes:
        subtype = (n.get("properties") or {}).get("asset_subtype", "unclassified")
        by_subtype[subtype] = by_subtype.get(subtype, 0) + 1
    return {
        "project_id": str(project_id),
        "total_assets": len(nodes),
        "by_subtype": by_subtype,
    }


async def pkg_count_identities_by_type(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Identities grouped by type."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "identity")
    by_type: dict[str, int] = {}
    for n in nodes:
        itype = (n.get("properties") or {}).get("identity_type", "unknown")
        by_type[itype] = by_type.get(itype, 0) + 1
    return {
        "project_id": str(project_id),
        "total_identities": len(nodes),
        "by_type": by_type,
    }


async def pkg_get_mfa_coverage(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """MFA coverage among user identities. Critical for ENS op.acc.6."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "identity")
    users = [n for n in nodes if (n.get("properties") or {}).get("identity_type") == "user"]
    mfa_enabled = sum(1 for u in users if (u.get("properties") or {}).get("mfa_enabled") is True)
    mfa_disabled = sum(1 for u in users if (u.get("properties") or {}).get("mfa_enabled") is False)
    mfa_unknown = len(users) - mfa_enabled - mfa_disabled
    coverage = round(100.0 * mfa_enabled / len(users), 1) if users else 0.0
    return {
        "project_id": str(project_id),
        "total_users": len(users),
        "mfa_enabled": mfa_enabled,
        "mfa_disabled": mfa_disabled,
        "mfa_unknown": mfa_unknown,
        "coverage_percentage": coverage,
        "ens_compliant": coverage == 100.0,
    }


async def pkg_list_systems(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Systems (label + category, no PII)."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "system")
    systems = [
        {"label": n["label"], "category": (n.get("properties") or {}).get("ens_category"), "criticality": (n.get("properties") or {}).get("criticality")}
        for n in nodes
    ]
    return {"project_id": str(project_id), "total_systems": len(systems), "systems": systems}


async def pkg_list_providers(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """External providers."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "provider")
    return {
        "project_id": str(project_id),
        "total_providers": len(nodes),
        "providers": [{"label": n["label"], "properties": n.get("properties")} for n in nodes],
    }


async def pkg_get_stakeholder_roles(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """ENS roles assigned (no personal names, only presence)."""
    people = await pkg.get_nodes_by_type(session, project_id, "person")
    roles_found: dict[str, bool] = {}
    for p in people:
        role = (p.get("properties") or {}).get("role")
        if role:
            roles_found[role] = True
    ens_roles = {
        "sponsor": roles_found.get("sponsor", False),
        "rseg": roles_found.get("rseg", False),
        "rsi": roles_found.get("rsi", False),
        "ri": roles_found.get("ri", False),
        "dpo": roles_found.get("dpo", False),
    }
    return {
        "project_id": str(project_id),
        "ens_roles": ens_roles,
        "total_people": len(people),
        "roles_assigned": sum(1 for v in ens_roles.values() if v),
        "roles_missing": [k for k, v in ens_roles.items() if not v],
    }


async def pkg_get_critical_dependencies(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """depends_on chains between systems/assets."""
    r = await session.execute(
        select(PKGEdge).where(PKGEdge.project_id == project_id, PKGEdge.edge_type == "depends_on")
    )
    deps = []
    for e in r.scalars().all():
        source = await pkg.get_node(session, e.source_node_id)
        target = await pkg.get_node(session, e.target_node_id)
        if source and target:
            deps.append({
                "source": source["label"], "source_type": source["node_type"],
                "target": target["label"], "target_type": target["node_type"],
            })
    return {"project_id": str(project_id), "total_dependencies": len(deps), "dependencies": deps}


async def pkg_count_processes(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Business processes inventoried."""
    nodes = await pkg.get_nodes_by_type(session, project_id, "process")
    return {
        "project_id": str(project_id),
        "total_processes": len(nodes),
        "processes": [n["label"] for n in nodes],
    }


async def pkg_get_onboarding_completion(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Onboarding sessions completion status."""
    r = await session.execute(
        select(OnboardingSession.estado, func.count(OnboardingSession.id))
        .where(OnboardingSession.project_id == project_id, OnboardingSession.deleted_at.is_(None))
        .group_by(OnboardingSession.estado)
    )
    by_state = {row[0]: row[1] for row in r.all()}
    total = sum(by_state.values())
    completed = by_state.get(SessionState.COMPLETED.value, 0)
    return {
        "project_id": str(project_id),
        "total_sessions": total,
        "completed": completed,
        "in_progress": by_state.get(SessionState.IN_PROGRESS.value, 0),
        "pending": by_state.get(SessionState.CREATED.value, 0) + by_state.get(SessionState.SENT.value, 0),
        "completion_percentage": round(100.0 * completed / total, 1) if total else 0.0,
    }
