"""Cliente continuidad service · CLUSTER 2 Phase 2F.

Servicio cliente questionnaire+approve BIA/DRP filosofía cliente-mínimo:
- upsert_input: cliente raw input questionnaire (1 row per project)
- get_input: cliente reads own submission
- list_drafts: lists admin-prepared BIA entries + DRP document drafts ready
- record_approval: cliente binding approve/reject/comment per draft

NO creator mode cliente · cliente provides INPUT raw + APPROVE/COMMENT decisions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.bia import BiaAnalysis
from backend.app.models.cliente_continuidad import (
    ClienteContinuidadApproval,
    ClienteContinuidadInput,
)


VALID_ARTIFACT_TYPES = frozenset({"bia", "drp"})
VALID_APPROVAL_ACTIONS = frozenset({"approved", "rejected", "comment"})


async def upsert_input(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    procesos_criticos: Optional[list[dict]] = None,
    rto_horas_tolerancia: Optional[int] = None,
    rpo_horas_tolerancia: Optional[int] = None,
    impacto_diario_eur: Optional[Decimal] = None,
    activos_core: Optional[list[dict]] = None,
    notas_cliente: Optional[str] = None,
    completed: bool = False,
) -> ClienteContinuidadInput:
    """Crea o actualiza questionnaire input cliente (1 row per project).

    Filosofía cliente-mínimo: cliente provides INPUT raw · NO ENS técnico.
    """
    now = datetime.now(timezone.utc)

    existing = (await db.execute(
        select(ClienteContinuidadInput).where(
            ClienteContinuidadInput.project_id == project_id,
        )
    )).scalar_one_or_none()

    if existing is None:
        row = ClienteContinuidadInput(
            project_id=project_id,
            client_user_id=client_user_id,
            submitted_at=now,
            updated_at=now,
            procesos_criticos=procesos_criticos,
            rto_horas_tolerancia=rto_horas_tolerancia,
            rpo_horas_tolerancia=rpo_horas_tolerancia,
            impacto_diario_eur=impacto_diario_eur,
            activos_core=activos_core,
            notas_cliente=notas_cliente,
            completed=completed,
        )
        db.add(row)
        await db.flush()
        return row

    # Update existing · preserve submitted_at + cycle updated_at
    existing.client_user_id = client_user_id
    existing.updated_at = now
    if procesos_criticos is not None:
        existing.procesos_criticos = procesos_criticos
    if rto_horas_tolerancia is not None:
        existing.rto_horas_tolerancia = rto_horas_tolerancia
    if rpo_horas_tolerancia is not None:
        existing.rpo_horas_tolerancia = rpo_horas_tolerancia
    if impacto_diario_eur is not None:
        existing.impacto_diario_eur = impacto_diario_eur
    if activos_core is not None:
        existing.activos_core = activos_core
    if notas_cliente is not None:
        existing.notas_cliente = notas_cliente
    existing.completed = completed
    await db.flush()
    return existing


async def get_input(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> Optional[ClienteContinuidadInput]:
    """Devuelve questionnaire input cliente del project (None si no existe)."""
    return (await db.execute(
        select(ClienteContinuidadInput).where(
            ClienteContinuidadInput.project_id == project_id,
        )
    )).scalar_one_or_none()


async def list_drafts(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Lista drafts admin-prepared listos para preview/approve cliente.

    Returns BIA entries (m19_risk admin table) + DRP document drafts cuando
    existen (m06 document factory query forward-compat).

    Filosofía: cliente VE drafts · NO crea ni edita técnico.
    """
    drafts: list[dict[str, Any]] = []

    # BIA entries (m19_risk admin working table)
    bia_rows = (await db.execute(
        select(BiaAnalysis).where(BiaAnalysis.project_id == project_id)
    )).scalars().all()
    for entry in bia_rows:
        drafts.append({
            "artifact_type": "bia",
            "draft_id": str(entry.id),
            "summary": entry.service_name,
            "rto_hours": entry.rto_hours,
            "rpo_hours": entry.rpo_hours,
            "daily_impact_eur": (
                str(entry.daily_impact_eur)
                if entry.daily_impact_eur is not None else None
            ),
        })

    # DRP documents (m06 document factory · scoped E403 via template_codigo)
    # Forward-compat: documents table query con columnas reales (nombre +
    # template_codigo) · placeholder empty cuando NO drp document exists.
    drp_rows = await db.execute(
        text(
            "SELECT id, nombre FROM documents "
            "WHERE project_id = :pid AND template_codigo = 'E403' "
            "ORDER BY created_at DESC"
        ),
        {"pid": str(project_id)},
    )
    for row in drp_rows:
        drafts.append({
            "artifact_type": "drp",
            "draft_id": str(row[0]),
            "summary": row[1] or "DRP draft",
        })

    return drafts


async def record_approval(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    artifact_type: str,
    draft_id: Optional[uuid.UUID],
    action: str,
    comment_text: Optional[str] = None,
) -> ClienteContinuidadApproval:
    """Persiste cliente approval/comment binding decision · audit trail.

    Filosofía cliente-mínimo: cliente APROVA o COMENTA · NO edita técnico draft.
    """
    if artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValueError(
            f"artifact_type invalido: {artifact_type!r} · "
            f"valid: {sorted(VALID_ARTIFACT_TYPES)}"
        )
    if action not in VALID_APPROVAL_ACTIONS:
        raise ValueError(
            f"action invalido: {action!r} · "
            f"valid: {sorted(VALID_APPROVAL_ACTIONS)}"
        )

    row = ClienteContinuidadApproval(
        project_id=project_id,
        client_user_id=client_user_id,
        artifact_type=artifact_type,
        draft_id=draft_id,
        action=action,
        comment_text=comment_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    return row
