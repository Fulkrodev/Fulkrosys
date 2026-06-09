"""M8 v5.1 — FP learner.

- ``seed_catalog_to_db``: idempotente. Sincroniza patrones del catalogo
  Python a la tabla ``false_positive_patterns``. Se ejecuta una vez al
  arrancar el motor.
- ``learn_from_finding``: cuando Marcos marca un finding como
  ``false_positive``, este modulo crea un patron nuevo basado en
  (tool, title-substring, condition opcional).
- ``increment_match``: cuando el ZFP gate 2 filtra un finding por un
  patron, incrementa ``times_matched``.
- ``find_matching_patterns``: busca patrones aplicables a un
  FindingCandidate.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.fp_patterns.catalog import (
    FALSE_POSITIVE_PATTERNS,
)
from backend.app.motors.m08_verification.models import FalsePositivePattern
from backend.app.motors.m08_verification.tools.base import FindingCandidate


# ────────────────────────────────────────────────────────────────────
# Seed catalog to DB
# ────────────────────────────────────────────────────────────────────

async def seed_catalog_to_db(db: AsyncSession) -> dict[str, int]:
    """Inserta los patrones del catalogo en la tabla; idempotente.

    Detecta duplicados por (tool, pattern). Si existe, no lo recrea.
    """
    existing_q = await db.execute(
        select(FalsePositivePattern.tool, FalsePositivePattern.pattern).where(
            FalsePositivePattern.deleted_at.is_(None),
        )
    )
    existing = {(row[0], row[1]) for row in existing_q.all()}

    created = 0
    skipped = 0
    for entry in FALSE_POSITIVE_PATTERNS:
        key = (entry["tool"], entry["pattern"])
        if key in existing:
            skipped += 1
            continue
        fp = FalsePositivePattern(
            tool=entry["tool"],
            pattern=entry["pattern"],
            condition_jsonb=entry.get("condition_jsonb"),
            reason=entry["reason"],
            learned_from_project_id=None,  # bootstrap
            created_by="bootstrap_catalog",
        )
        db.add(fp)
        created += 1
    await db.flush()
    return {"created": created, "skipped": skipped, "total_in_catalog": len(FALSE_POSITIVE_PATTERNS)}


# ────────────────────────────────────────────────────────────────────
# Learn from a finding marked as FP
# ────────────────────────────────────────────────────────────────────

async def learn_from_finding(
    db: AsyncSession,
    finding,                     # VerificationFinding
    reason: str,
    *,
    learned_from_project_id: uuid.UUID | None = None,
) -> FalsePositivePattern | None:
    """Crea un patron FP nuevo a partir de un finding marcado como FP.

    Usa como pattern el ``title`` del finding y como tool la primera
    fuente. Anade condition_jsonb minimo si hay metadata especifica
    (template_id de nuclei, lynis_test_id, alert_id de zap).

    Idempotente: si ya existe (tool, pattern), no duplica.
    """
    if not finding.tool_sources:
        return None
    tool = finding.tool_sources[0]
    pattern_text = finding.title.strip()
    if not pattern_text:
        return None

    # Comprobar si ya existe (tool, pattern)
    existing_q = await db.execute(
        select(FalsePositivePattern).where(
            FalsePositivePattern.tool == tool,
            FalsePositivePattern.pattern == pattern_text,
            FalsePositivePattern.deleted_at.is_(None),
        ).limit(1)
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        return existing

    # Construir condition_jsonb opcional desde tool_metadata del finding
    cond: dict[str, Any] | None = None
    metadata = (
        finding.raw_outputs[0] if finding.raw_outputs and isinstance(finding.raw_outputs[0], dict)
        else {}
    )
    # Si la metadata contiene template_id (nuclei) o lynis_test_id, lo usamos
    if metadata.get("template_id"):
        cond = {"template_id": metadata["template_id"]}
    elif metadata.get("lynis_test_id"):
        cond = {"lynis_test_id": metadata["lynis_test_id"]}
    elif metadata.get("alert_id"):
        cond = {"zap_alert_id": metadata["alert_id"]}
    elif metadata.get("nse_script_id"):
        cond = {"nse_script_id": metadata["nse_script_id"]}

    fp = FalsePositivePattern(
        tool=tool,
        pattern=pattern_text,
        condition_jsonb=cond,
        reason=reason,
        learned_from_project_id=learned_from_project_id,
        created_by="learned_from_finding",
    )
    db.add(fp)
    await db.flush()
    return fp


# ────────────────────────────────────────────────────────────────────
# Match patterns against a FindingCandidate
# ────────────────────────────────────────────────────────────────────

async def find_matching_patterns(
    db: AsyncSession,
    finding_candidate: FindingCandidate,
) -> list[FalsePositivePattern]:
    """Devuelve patrones FP que matchean el finding_candidate.

    Match: (tool == fp.tool) AND (fp.pattern in finding.title o description)
    AND (condition_jsonb se cumple si esta presente).
    """
    tool = finding_candidate.get("tool")
    title = finding_candidate.get("title", "")
    description = finding_candidate.get("description", "")
    metadata = finding_candidate.get("tool_metadata") or {}
    severity = finding_candidate.get("severity", "info")
    port = finding_candidate.get("affected_port")

    if not tool:
        return []
    patterns_q = await db.execute(
        select(FalsePositivePattern).where(
            FalsePositivePattern.tool == tool,
            FalsePositivePattern.deleted_at.is_(None),
        )
    )
    candidates = list(patterns_q.scalars().all())

    matches: list[FalsePositivePattern] = []
    for p in candidates:
        if p.pattern not in title and p.pattern not in description:
            continue
        if p.condition_jsonb and not _condition_matches(
            p.condition_jsonb, metadata, severity=severity, port=port,
        ):
            continue
        matches.append(p)
    return matches


def _condition_matches(
    cond: dict[str, Any],
    metadata: dict[str, Any],
    *,
    severity: str = "info",
    port: int | None = None,
) -> bool:
    """Aplica cada clave de condition_jsonb. Si falta info, devuelve False
    (conservador: no filtramos como FP por defecto)."""
    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for key, expected in cond.items():
        if key == "severity_eq":
            if severity != expected:
                return False
        elif key == "severity_lte":
            if severity_rank.get(severity, 0) > severity_rank.get(expected, 4):
                return False
        elif key == "severity_gte":
            if severity_rank.get(severity, 0) < severity_rank.get(expected, 0):
                return False
        elif key == "port_in":
            if port is None or port not in expected:
                return False
        elif key in metadata:
            # Match exacto contra valor de metadata
            mv = metadata[key]
            if isinstance(expected, list):
                if mv not in expected:
                    return False
            else:
                if mv != expected:
                    return False
        else:
            # Condicion no verificable con la info disponible:
            # ser conservador y NO filtrar.
            return False
    return True


# ────────────────────────────────────────────────────────────────────
# Increment match counter
# ────────────────────────────────────────────────────────────────────

async def increment_match(
    db: AsyncSession, pattern_id: uuid.UUID,
) -> None:
    await db.execute(
        update(FalsePositivePattern)
        .where(FalsePositivePattern.id == pattern_id)
        .values(times_matched=FalsePositivePattern.times_matched + 1)
    )


# ────────────────────────────────────────────────────────────────────
# Stats
# ────────────────────────────────────────────────────────────────────

async def stats(db: AsyncSession) -> dict[str, Any]:
    """Resumen del catalogo FP en BD."""
    total = (await db.execute(
        select(func.count(FalsePositivePattern.id)).where(
            FalsePositivePattern.deleted_at.is_(None),
        )
    )).scalar() or 0
    by_tool_q = await db.execute(
        select(
            FalsePositivePattern.tool, func.count(FalsePositivePattern.id),
        ).where(FalsePositivePattern.deleted_at.is_(None))
        .group_by(FalsePositivePattern.tool)
    )
    by_tool = {row[0]: row[1] for row in by_tool_q.all()}
    return {"total": total, "by_tool": by_tool}
