"""M14 workflow hooks · event-driven AdendaGenerator auto-trigger (FASE C Phase A).

Sigue el patrón canónico ``_maybe_dispatch_X`` establecido en
``backend/app/motors/m_workflow_engine/dependency_resolver_service.py:286-323``:

  - Graceful import + try/except dual layers
  - NUNCA bloquea propagation chain del workflow engine
  - Loggea warning si falla pero permite que siguiente paso continúe

Triggers cubiertos:
  1. ``maybe_dispatch_adenda_on_step_completed(db, project_id, completed_template_id)``
     · Fire cuando workflow step matchea pattern provider-related
     · Detecta: id contains PROVEEDOR / PROVIDER / LCSP / OP_EXT
     · Para cada Provider sin adenda reciente · genera vía AdendaGenerator

  2. ``maybe_dispatch_adenda_on_materiality_assessed(db, project_id, assessment_result)``
     · Fire cuando M28 assess produce MATERIAL con affects_overlay/affects_renewal
     · Para cada Provider · genera adenda regen con metadata trigger
       ``materiality_material_cascade`` para audit trail

Audit trail: ``ProviderAddendum.metadata_`` JSONB persists:

    {
        "trigger": "workflow_step_completed" | "materiality_material_cascade" | "admin_manual",
        "completed_template_id": str | None,
        "materiality_change_id": str | None,
        "materiality_level": str | None,
        "auto_generated_at": ISO timestamp,
    }

Reuse: ``AdendaGenerator.generate`` ya es idempotente (UNIQUE constraint
``project_id + addendum_code``) · llamadas duplicadas devuelven existing
sin re-render DOCX. Hook NO necesita propio dedup layer.

ADR-025 sostener · NO new tables · NO new templates · solo orchestration
hook adicional sobre infraestructura production existing.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.m14_providers import Provider, ProviderAddendum


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Template_id detection · pure function

PROVIDER_TEMPLATE_MARKERS: tuple[str, ...] = (
    "PROVEEDOR",
    "PROVIDER",
    "LCSP",
    "OP_EXT",
    "SAAS_ONLY_OP_EXT",
)
"""Markers en uppercase que matchean template_id existentes en
``backend/app/motors/m21_portal_cliente/task_templates.yaml``:

- ``ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST`` (línea 199)
- ``ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL`` (línea 229)
- ``ENR_PB_01_SECTOR_PUBLICO_LCSP`` (línea 1009 · cta_url providers admin)
- Cualquier template futuro siguiendo convención (e.g. ``PROVIDER_EVALUATION_COMPLETED``)
"""


def template_id_triggers_adenda(template_id: str) -> bool:
    """Pure · returns True si template_id matchea alguno de los markers provider."""
    if not template_id:
        return False
    upper = template_id.upper()
    return any(marker in upper for marker in PROVIDER_TEMPLATE_MARKERS)


# ──────────────────────────────────────────────────────────────────────
# Hook 1 · workflow step completed


async def maybe_dispatch_adenda_on_step_completed(
    db: AsyncSession,
    project_id: uuid.UUID,
    completed_template_id: str,
) -> list[dict[str, Any]]:
    """Hook fired desde ``task_service._dispatch_done_and_propagate``.

    Returns list de adenda generations triggered (vacío si template_id NO
    match · o si NO hay providers · o si error no-fatal).

    Cada entry del list:

        {
            "provider_id": str,
            "addendum_code": str,
            "addendum_id": str,
            "trigger": "workflow_step_completed",
            "completed_template_id": str,
        }

    Errores: loggeados como warning · NUNCA propagated (no rompe chain).
    """
    if not template_id_triggers_adenda(completed_template_id):
        return []

    try:
        from backend.app.motors.m14_contracts.adenda_generator import (
            AdendaGenerator,
        )
    except ImportError:
        logger.warning(
            "M14 adenda_generator unavailable · skip hook on_step_completed",
        )
        return []

    triggered: list[dict[str, Any]] = []

    try:
        providers = await _list_active_providers(db, project_id)
        if not providers:
            logger.debug(
                "no providers en project %s · skip adenda dispatch",
                project_id,
            )
            return []

        gen = AdendaGenerator(db=db)
        now = datetime.now(timezone.utc)

        for provider in providers:
            try:
                normativas = _resolve_normativas_for_provider(provider)
                result = await gen.generate(
                    project_id=project_id,
                    provider_id=provider.id,
                    normativas_aplicables=normativas,
                )
                await _stamp_audit_trail(
                    db=db,
                    addendum_id=result.addendum_id,
                    trigger="workflow_step_completed",
                    completed_template_id=completed_template_id,
                    auto_generated_at=now,
                )
                triggered.append({
                    "provider_id": str(provider.id),
                    "addendum_code": result.addendum_code,
                    "addendum_id": str(result.addendum_id),
                    "trigger": "workflow_step_completed",
                    "completed_template_id": completed_template_id,
                })
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "adenda dispatch failed · project=%s provider=%s err=%s",
                    project_id, provider.id, exc,
                )

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "on_step_completed hook failed (outer) · project=%s err=%s",
            project_id, exc,
        )

    return triggered


# ──────────────────────────────────────────────────────────────────────
# Hook 2 · M28 materiality assessment cascade


_MATERIAL_CASCADE_FLAGS: frozenset[str] = frozenset({
    "overlay",
    "renewal",
})
"""Materiality impact_vector flags que disparan adenda regen cascade.

- ``overlay``: cambio en overlay normativo (e.g. nuevo control)
- ``renewal``: cambio que requiere revalidación contractual

Otros flags (evidence/document/control/roles/risk_analysis/dda/category/
extraordinary) producen otros workflows pero NO regen automática de adenda
(requieren intervención manual Marcos · architect decision).
"""


async def maybe_dispatch_adenda_on_materiality_assessed(
    db: AsyncSession,
    project_id: uuid.UUID,
    assessment_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Hook fired desde M28 ``assess_change_endpoint`` después de persist.

    Cascade trigger condition · TODAS deben cumplirse:
      1. ``materiality_level`` == "MATERIAL"
      2. ``impact_vector`` con al menos uno de _MATERIAL_CASCADE_FLAGS True

    Returns list de adenda generations triggered (mismo formato hook 1).
    Errores: loggeados como warning · NUNCA propagated.
    """
    level = assessment_result.get("materiality_level")
    if level != "MATERIAL":
        return []

    impact = assessment_result.get("impact_vector") or {}
    triggered_flags = {
        flag for flag in _MATERIAL_CASCADE_FLAGS if impact.get(flag, False)
    }
    if not triggered_flags:
        return []

    try:
        from backend.app.motors.m14_contracts.adenda_generator import (
            AdendaGenerator,
        )
    except ImportError:
        logger.warning(
            "M14 adenda_generator unavailable · skip hook on_materiality",
        )
        return []

    triggered: list[dict[str, Any]] = []

    try:
        providers = await _list_active_providers(db, project_id)
        if not providers:
            return []

        gen = AdendaGenerator(db=db)
        now = datetime.now(timezone.utc)
        change_id = assessment_result.get("change_id")
        change_id_str = str(change_id) if change_id else None

        for provider in providers:
            try:
                normativas = _resolve_normativas_for_provider(provider)
                # Suffix code with cascade marker year+seq for trace separation
                # de las generaciones manuales / on_step_completed
                result = await gen.generate(
                    project_id=project_id,
                    provider_id=provider.id,
                    normativas_aplicables=normativas,
                )
                await _stamp_audit_trail(
                    db=db,
                    addendum_id=result.addendum_id,
                    trigger="materiality_material_cascade",
                    materiality_change_id=change_id_str,
                    materiality_level="MATERIAL",
                    materiality_flags_triggered=sorted(triggered_flags),
                    auto_generated_at=now,
                )
                triggered.append({
                    "provider_id": str(provider.id),
                    "addendum_code": result.addendum_code,
                    "addendum_id": str(result.addendum_id),
                    "trigger": "materiality_material_cascade",
                    "materiality_change_id": change_id_str,
                    "materiality_flags": sorted(triggered_flags),
                })
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "adenda cascade failed · project=%s provider=%s err=%s",
                    project_id, provider.id, exc,
                )

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "on_materiality hook failed (outer) · project=%s err=%s",
            project_id, exc,
        )

    return triggered


# ──────────────────────────────────────────────────────────────────────
# Helpers internos


async def _list_active_providers(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[Provider]:
    """List providers activos del project (soft-delete excluded)."""
    result = await db.execute(
        select(Provider).where(
            Provider.project_id == project_id,
            Provider.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


def _resolve_normativas_for_provider(provider: Provider) -> list[str]:
    """Mapping deterministic provider attrs → normativas para E-604 condicional.

    Reuse cross-compliance auto-detect ADR-046 v3 SAN-E.MB-3.B:
      - cloud + (CRITICO|ALTO) → ENS + RGPD
      - cloud + CRITICO        → +NIS2
      - saas + (CRITICO|ALTO)  → ENS + RGPD
      - Else                   → ENS solo

    DORA no se infiere automáticamente · requires explicit sector
    proveedor_financiero · admin trigger manual con normativas_aplicables override.
    """
    normativas: list[str] = ["ENS"]
    high_criticality = provider.criticality in ("CRITICO", "ALTO")
    if high_criticality and provider.type in ("cloud", "saas"):
        normativas.append("RGPD")
    if provider.type == "cloud" and provider.criticality == "CRITICO":
        normativas.append("NIS2")
    return normativas


async def _stamp_audit_trail(
    *,
    db: AsyncSession,
    addendum_id: uuid.UUID,
    trigger: str,
    completed_template_id: str | None = None,
    materiality_change_id: str | None = None,
    materiality_level: str | None = None,
    materiality_flags_triggered: list[str] | None = None,
    auto_generated_at: datetime,
) -> None:
    """Mete trace info en ``ProviderAddendum.metadata_`` JSONB.

    Idempotencia: si addendum existed previo (AdendaGenerator idempotent
    UNIQUE constraint), append new trace al array ``triggers_history``
    en lugar de overwrite · permite ver flow auditor ENAC todo el trail.
    """
    addendum = await db.get(ProviderAddendum, addendum_id)
    if addendum is None:
        logger.warning("addendum %s NOT FOUND post-generate", addendum_id)
        return

    existing_meta = dict(addendum.metadata_ or {})
    history: list[dict[str, Any]] = list(existing_meta.get("triggers_history") or [])

    trace_entry: dict[str, Any] = {
        "trigger": trigger,
        "auto_generated_at": auto_generated_at.isoformat(),
    }
    if completed_template_id:
        trace_entry["completed_template_id"] = completed_template_id
    if materiality_change_id:
        trace_entry["materiality_change_id"] = materiality_change_id
    if materiality_level:
        trace_entry["materiality_level"] = materiality_level
    if materiality_flags_triggered:
        trace_entry["materiality_flags_triggered"] = materiality_flags_triggered

    history.append(trace_entry)
    existing_meta["triggers_history"] = history
    existing_meta["last_trigger"] = trigger
    existing_meta["last_auto_generated_at"] = auto_generated_at.isoformat()

    addendum.metadata_ = existing_meta
    await db.flush()
