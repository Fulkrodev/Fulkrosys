"""Evidence freshness checking service.

Classifies evidence as vigente, proxima_caducidad, or caducada
based on fecha_caducidad (date) vs date.today().
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class EvidenceStatus:
    """Status of a single evidence item."""
    evidence_id: uuid.UUID
    measure_code: str | None
    fecha_caducidad: date | None
    estado: str  # "vigente" | "proxima_caducidad" | "caducada" | "sin_caducidad"
    dias_restantes: int | None  # None if no fecha_caducidad


@dataclass
class FreshnessReport:
    """Freshness report for a project."""
    project_id: uuid.UUID
    total: int = 0
    vigentes: int = 0
    proxima_caducidad: int = 0
    caducadas: int = 0
    sin_caducidad: int = 0
    items: list[EvidenceStatus] = field(default_factory=list)


def _classify(fecha_caducidad: date | None, warning_days: int) -> tuple[str, int | None]:
    """Classify an evidence by its expiry date.

    Returns (estado, dias_restantes).
    """
    if fecha_caducidad is None:
        return "sin_caducidad", None

    today = date.today()
    dias = (fecha_caducidad - today).days

    if dias < 0:
        return "caducada", dias
    elif dias <= warning_days:
        return "proxima_caducidad", dias
    else:
        return "vigente", dias


async def check_freshness_for_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    warning_days: int = 30,
) -> FreshnessReport:
    """Check freshness for all vigente evidences in a project.

    Queries all evidences with vigente=True for the given project.
    Classifies each as vigente/proxima_caducidad/caducada based on
    fecha_caducidad vs date.today().
    """
    result = await session.execute(
        text(
            "SELECT id, measure_code, fecha_caducidad "
            "FROM evidence "
            "WHERE project_id = :pid AND vigente = TRUE AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    rows = result.fetchall()

    report = FreshnessReport(project_id=project_id)
    for row in rows:
        eid = row[0] if isinstance(row[0], uuid.UUID) else uuid.UUID(str(row[0]))
        measure_code = row[1]
        fc = row[2]

        estado, dias = _classify(fc, warning_days)

        item = EvidenceStatus(
            evidence_id=eid,
            measure_code=measure_code,
            fecha_caducidad=fc,
            estado=estado,
            dias_restantes=dias,
        )
        report.items.append(item)
        report.total += 1

        if estado == "vigente":
            report.vigentes += 1
        elif estado == "proxima_caducidad":
            report.proxima_caducidad += 1
        elif estado == "caducada":
            report.caducadas += 1
        else:
            report.sin_caducidad += 1

    return report


async def is_evidence_fresh(
    session: AsyncSession,
    evidence_id: uuid.UUID,
    warning_days: int = 0,
) -> tuple[bool, EvidenceStatus | None]:
    """Check if a single evidence is fresh.

    Returns (is_fresh, status). is_fresh is True if estado is
    'vigente' or 'sin_caducidad'. Returns (False, None) if not found.
    """
    result = await session.execute(
        text(
            "SELECT id, measure_code, fecha_caducidad "
            "FROM evidence "
            "WHERE id = :eid AND deleted_at IS NULL"
        ),
        {"eid": str(evidence_id)},
    )
    row = result.fetchone()
    if row is None:
        return False, None

    eid = row[0] if isinstance(row[0], uuid.UUID) else uuid.UUID(str(row[0]))
    fc = row[2]
    estado, dias = _classify(fc, warning_days)

    status = EvidenceStatus(
        evidence_id=eid,
        measure_code=row[1],
        fecha_caducidad=fc,
        estado=estado,
        dias_restantes=dias,
    )
    fresh = estado in ("vigente", "sin_caducidad")
    return fresh, status
