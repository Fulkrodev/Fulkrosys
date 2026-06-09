"""Motor 28 — Recategorization workflow (C#55).

Recategorización REAL cross-motor. Cambia ``project.categoria_objetivo`` y
regenera los borradores dependientes de categoría (propuesta + plan + gap)
REUTILIZANDO el orquestador ``floor_elevation_service`` (OPS-026 DRY · misma
fuente que la elevación de suelo AAPP · evita divergencia). Respeta los guards
por nivel: NUNCA toca contratos firmados (N3) ni en vuelo (N2.5) — esos exigen
vía formal (nuevo contrato/adenda) · el documento firmado no se toca.

Direccional (sube o baja, a diferencia de la elevación de suelo que solo sube):
la recat puede venir de un cambio gobernado (M28) que reduce o aumenta categoría
tras reanálisis de impacto/materialidad. Los guards N3/N2.5 protegen lo firmado
en CUALQUIER dirección.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project

# Reuse canónico del orquestador de elevación de suelo (OPS-026). Importamos los
# helpers internos a propósito: son la lógica probada de guard + regeneración
# cross-motor · duplicarla divergiría (la lección que motiva OPS-026).
from backend.app.motors.m01_categorization.floor_elevation_service import (  # noqa: E501
    detect_level,
    _record_blocked_attempt,
    _regenerate_drafts,
)

VALID_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}


@dataclass
class RecategorizationResult:
    recategorization_id: uuid.UUID
    project_id: uuid.UUID
    change_id: uuid.UUID
    old_category: str | None
    new_category: str
    rationale: str
    state: str  # applied | blocked_signed | blocked_in_flight
    level: str  # N1 | N2 | N2.5 | N3
    regenerated: list[str] = field(default_factory=list)
    documents_required: list[str] = field(default_factory=lambda: ["E-048"])
    opened_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


async def recategorize_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    change_id: uuid.UUID,
    new_category: str,
    rationale: str,
) -> RecategorizationResult:
    """Aplica una recategorización gobernada (M28) con guards por nivel.

    NO commitea: el caller (endpoint) gestiona la transacción. Flush para que la
    constancia N3 y el cambio de categoría queden visibles en la misma tx.
    """
    new_category = (new_category or "").upper()
    if new_category not in VALID_CATEGORIES:
        raise ValueError(f"Categoría inválida: {new_category}")

    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise ValueError("Proyecto no encontrado")
    old_category = project.categoria_objetivo

    base = dict(
        recategorization_id=uuid.uuid4(),
        project_id=project_id,
        change_id=change_id,
        old_category=old_category,
        new_category=new_category,
        rationale=(rationale or "")[:1000],
    )

    level = await detect_level(db, project_id)

    # Sin cambio efectivo de categoría → no hay cirugía, solo el registro.
    if old_category == new_category:
        return RecategorizationResult(**base, state="applied", level=level)

    # N3 · contrato firmado / factura emitida → NO se toca · constancia + bloqueo.
    if level == "N3":
        await _record_blocked_attempt(db, project_id, old_category, new_category)
        await db.flush()
        return RecategorizationResult(
            **base, state="blocked_signed", level=level
        )

    # N2.5 · contrato en vuelo (enviado, sin firma) → bloqueo (retirar antes).
    if level == "N2.5":
        return RecategorizationResult(
            **base, state="blocked_in_flight", level=level
        )

    # N1 (libre) / N2 (regenera borradores) · aplica el cambio de categoría.
    project.categoria_objetivo = new_category
    regenerated: list[str] = []
    if level == "N2":
        regenerated = await _regenerate_drafts(db, project_id, new_category)
    await db.flush()
    return RecategorizationResult(
        **base, state="applied", level=level, regenerated=regenerated
    )
