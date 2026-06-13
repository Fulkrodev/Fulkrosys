"""M8 v5.1 - Integracion con M3 DdA (spec §9.2).

Cruce bidireccional entre ``DdaEntry`` y ``VerificationFinding``:

- Para cada medida ENS con findings, devuelve un resumen tecnico que el
  generador de E-040/E-050 puede usar para enriquecer la DdA.
- Detecta contradicciones: medida declarada 'implantado' pero con
  findings abiertos high/critical.

Este modulo expone solo queries read-only; no modifica la tabla
``dda_entries`` porque en v5.1 no se reserva una columna
``tech_verification`` (la informacion vive en los findings y se agrega
on-the-fly). Cuando M3 evolucione y anada una columna persistida,
bastara con anadir ``apply_tech_verification`` aqui.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.models import VerificationFinding


SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _sev_rank(sev: str | None) -> int:
    return SEV_RANK.get((sev or "info").lower(), 0)


async def get_tech_verification_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    """Devuelve ``{measure_code: {status, open_findings, worst_severity,
    last_verified, source}}`` para cada medida con findings del proyecto.

    - ``status`` = 'non_compliant' si algun finding high/critical abierto,
                    'partial' si solo medium/low/info abiertos,
                    'compliant' si no hay findings abiertos (todos remediated).
    - ``open_findings`` = cuenta de findings con status in {open, needs_review}.
    - ``worst_severity`` = la mas alta entre los findings abiertos.
    - ``last_verified`` = fecha del ultimo run con findings en esa medida.
    - ``source`` = 'verification_v5.1'.
    """
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    findings = (await db.execute(stmt)).scalars().all()

    by_measure: dict[str, dict[str, Any]] = {}
    for f in findings:
        codes = _measures_of(f)
        for code in codes:
            entry = by_measure.setdefault(code, {
                "open_findings": 0,
                "total_findings": 0,
                "worst_severity": None,
                "last_verified": None,
                "source": "verification_v5.1",
            })
            entry["total_findings"] += 1
            if (f.status or "open") in ("open", "needs_review"):
                entry["open_findings"] += 1
                if (
                    entry["worst_severity"] is None
                    or _sev_rank(f.severity) > _sev_rank(entry["worst_severity"])
                ):
                    entry["worst_severity"] = f.severity
            dt = f.updated_at or f.created_at
            if dt and (
                not entry["last_verified"] or dt > entry["last_verified"]
            ):
                entry["last_verified"] = dt

    # Status
    for code, entry in by_measure.items():
        worst = entry["worst_severity"]
        if entry["open_findings"] == 0:
            entry["status"] = "compliant"
        elif worst in ("critical", "high"):
            entry["status"] = "non_compliant"
        else:
            entry["status"] = "partial"
        if entry["last_verified"]:
            entry["last_verified"] = entry["last_verified"].isoformat()

    return by_measure


def _measures_of(f: VerificationFinding) -> set[str]:
    out: set[str] = set()
    for m in (f.ens_measures or []):
        if isinstance(m, dict) and m.get("measure"):
            out.add(m["measure"])
        elif isinstance(m, str):
            out.add(m)
    if f.ens_primary_measure:
        out.add(f.ens_primary_measure)
    return out


async def detect_dda_contradictions(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Detecta contradicciones entre DdA (estado 'implantado') y findings abiertos.

    Cada contradiccion es ``{medida, dda_estado, open_findings, worst_severity,
    descripcion, severidad}``. Se usa desde M9 checklist_service.
    """
    verif = await get_tech_verification_summary(db, project_id)
    if not verif:
        return []

    dda_stmt = (
        select(DdaEntry, EnsMeasure.codigo)
        .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
        .where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
        )
    )
    rows = (await db.execute(dda_stmt)).all()

    contradictions: list[dict[str, Any]] = []
    for entry, codigo in rows:
        v = verif.get(codigo)
        if not v:
            continue
        estado = (entry.estado_implementacion or "").lower()
        if estado == "implantada" and v.get("status") == "non_compliant":
            contradictions.append({
                "medida": codigo,
                "dda_estado": entry.estado_implementacion,
                "open_findings": v["open_findings"],
                "worst_severity": v["worst_severity"],
                "descripcion": (
                    f"DdA declara 'implantada' pero hay {v['open_findings']}"
                    f" hallazgo(s) abierto(s) en {codigo} "
                    f"(peor severidad: {v['worst_severity']})"
                ),
                "severidad": "error",
            })
    return contradictions


async def get_findings_by_measure(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, list[VerificationFinding]]:
    """Indice ``{measure_code: [findings]}`` para consumo de M9 matriz 99."""
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    findings = (await db.execute(stmt)).scalars().all()
    out: dict[str, list[VerificationFinding]] = {}
    for f in findings:
        for code in _measures_of(f):
            out.setdefault(code, []).append(f)
    return out
