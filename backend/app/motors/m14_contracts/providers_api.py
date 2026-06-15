"""M14 Providers + C-002 REST API · ADR-046 v3 SAN-E.MB-3.B.

7 endpoints scope project (pre-fulkro-1.0):
    GET    /projects/{project_id}/providers
    POST   /projects/{project_id}/providers
    DELETE /projects/{project_id}/providers/{provider_id}
    GET    /projects/{project_id}/providers/{provider_id}/c002-status
    GET    /projects/{project_id}/providers/{provider_id}/gaps
    POST   /projects/{project_id}/providers/{provider_id}/c002/generate
    POST   /projects/{project_id}/providers/{provider_id}/review

Sub-lote 1.B.7.1.3 (AMEND-014 OPCION C hibrida · cierre GAP-CRITICO-8):
    POST   /projects/{project_id}/providers/{provider_id}/generate-addendum
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m14_contracts.adenda_generator import AdendaGenerator
from backend.app.motors.m14_contracts.providers_service import (
    M14ProvidersService,
    ProvidersError,
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/projects/{project_id}/providers",
    tags=["Motor 14 - Providers / C-002"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


class CreateProviderBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    type: str = Field(..., pattern="^(cloud|saas|on-prem|staffing|hardware|consultoria)$")
    scope: str = Field(..., min_length=2, max_length=2000)
    criticality: str = Field(..., pattern="^(CRITICO|ALTO|MEDIO|BAJO)$")


def _provider_to_dict(p) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "project_id": str(p.project_id),
        "name": p.name,
        "type": p.type,
        "scope": p.scope,
        "criticality": p.criticality,
        "last_reviewed_at": p.last_reviewed_at.isoformat() if p.last_reviewed_at else None,
        "last_reviewed_by": p.last_reviewed_by,
        "c002_status": p.c002_status,
        "gaps_count": p.gaps_count,
    }


@router.get("")
async def list_providers(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    rows = await M14ProvidersService(db).list_providers(project_id)
    counts = {
        "total": len(rows),
        "critico": sum(1 for r in rows if r.criticality == "CRITICO"),
        "alto": sum(1 for r in rows if r.criticality == "ALTO"),
        "firmados": sum(1 for r in rows if r.c002_status == "firmado"),
        "con_gaps": sum(1 for r in rows if r.gaps_count > 0),
    }
    return {
        "project_id": str(project_id),
        "providers": [_provider_to_dict(p) for p in rows],
        "counts": counts,
    }


@router.post("", status_code=201)
async def create_provider(
    project_id: uuid.UUID,
    body: CreateProviderBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        provider, gaps = await M14ProvidersService(db).create_provider(
            project_id=project_id,
            name=body.name,
            type=body.type,
            scope=body.scope,
            criticality=body.criticality,
        )
    except ProvidersError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return {
        **_provider_to_dict(provider),
        "auto_detected_gaps": [g.to_dict() for g in gaps],
    }


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await _set_project_rls(project_id, db)
    try:
        await M14ProvidersService(db).delete_provider(project_id, provider_id)
    except ProvidersError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()


@router.get("/{provider_id}/c002-status")
async def get_c002_status(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        return await M14ProvidersService(db).get_c002_status(project_id, provider_id)
    except ProvidersError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{provider_id}/gaps")
async def get_gaps(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        result = await M14ProvidersService(db).get_gaps(project_id, provider_id)
    except ProvidersError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return result


@router.post("/{provider_id}/c002/generate")
async def generate_c002(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        result = await M14ProvidersService(db).generate_c002(project_id, provider_id)
    except ProvidersError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return result


@router.post("/{provider_id}/review")
async def mark_provider_reviewed(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        result = await M14ProvidersService(db).mark_reviewed(
            project_id=project_id,
            provider_id=provider_id,
            user_id=str(user.id) if user else None,
        )
    except ProvidersError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Sub-lote 1.B.7.1.3 · AMEND-014 OPCION C hibrida · adenda generator endpoint
# ---------------------------------------------------------------------------

class GenerateAddendumBody(BaseModel):
    addendum_code: str | None = Field(
        default=None, max_length=64,
        description="Codigo adenda (opcional · auto-gen ADENDA-ENS-YYYY-NNNN si null)",
    )
    normativas_aplicables: list[str] = Field(
        default_factory=lambda: ["ENS"],
        description="Lista normativas a materializar en bloques condicionales E-604",
    )
    contract_ref: str | None = Field(default=None, max_length=255)
    fecha_vigor: datetime | None = None
    vencimiento: datetime | None = None
    provider_extras: dict | None = Field(
        default=None,
        description="Campos no-ORM del proveedor: nif, domicilio, representante, categoria_servicio_ens",
    )
    client_extras: dict | None = Field(
        default=None,
        description="Campos no-ORM del cliente: domicilio, representante, contacto_compliance",
    )


@router.get("/adendas")
async def list_project_adendas(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Lista todas las adendas del project + audit trail metadata.

    FASE C Phase B · feed para frontend admin contracts page panel
    Sub-contratos con visibility de:
      - addendum_code + estado firmas
      - normativas_cubiertas (ENS/RGPD/NIS2/DORA detected)
      - generated_from_template_code (E-604)
      - metadata_.triggers_history (audit trail completo cross-events)
      - metadata_.last_trigger (workflow_step_completed | materiality_material_cascade | admin_manual | manual)

    Solo project-scoped · require_owner admin.
    Returns sorted desc por created_at.
    """
    await _set_project_rls(project_id, db)
    from sqlalchemy import desc, select as sa_select
    from backend.app.models.m14_providers import ProviderAddendum

    rows = (await db.execute(
        sa_select(ProviderAddendum)
        .where(ProviderAddendum.project_id == project_id)
        .where(ProviderAddendum.deleted_at.is_(None))
        .order_by(desc(ProviderAddendum.created_at))
    )).scalars().all()

    items: list[dict[str, Any]] = []
    for r in rows:
        meta = dict(r.metadata_ or {})
        items.append({
            "addendum_id": str(r.id),
            "addendum_code": r.addendum_code,
            "provider_id": str(r.provider_id),
            "contract_ref": r.contract_ref,
            "normativas_cubiertas": list(r.normativas_cubiertas or []),
            "template_code": r.generated_from_template_code,
            "firmado_cliente": bool(r.firmado_cliente),
            "firmado_proveedor": bool(r.firmado_proveedor),
            "fecha_firma": r.fecha_firma.isoformat() if r.fecha_firma else None,
            "fecha_vigor": r.fecha_vigor.isoformat() if r.fecha_vigor else None,
            "vencimiento": r.vencimiento.isoformat() if r.vencimiento else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "audit_trail": {
                "last_trigger": meta.get("last_trigger") or "manual",
                "last_auto_generated_at": meta.get("last_auto_generated_at"),
                "triggers_history": meta.get("triggers_history") or [],
            },
        })
    return {
        "project_id": str(project_id),
        "count": len(items),
        "adendas": items,
    }


class AdendaCheckBody(BaseModel):
    """Body opcional para el endpoint admin manual trigger."""

    completed_template_id: str | None = Field(
        default=None, max_length=128,
        description=(
            "Si se aporta · simula que ese template_id acaba de completarse · "
            "trigger pattern provider matches the same logic del hook automatico "
            "(workflow_hooks.template_id_triggers_adenda). Si null usa marker "
            "sintetico ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER."
        ),
    )


@router.post("/adenda/check", status_code=200)
async def admin_trigger_adenda_check(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    body: AdendaCheckBody | None = None,
) -> dict[str, Any]:
    """Admin manual trigger materiality + adenda check across all providers.

    FASE C Phase A · Reuse maybe_dispatch_adenda_on_step_completed con marker
    sintetico (o template_id explicito si Marcos sabe cual replicar).
    Permite ad-hoc re-evaluation cuando Marcos detecta drift.

    Retorna list de adendas generadas/idempotent-existing con audit trail.
    Si NO hay providers retorna empty list (no error).
    """
    await _set_project_rls(project_id, db)

    from backend.app.models.m14_providers import ProviderAddendum
    from backend.app.motors.m14_contracts.workflow_hooks import (
        maybe_dispatch_adenda_on_step_completed,
    )

    template_id = body.completed_template_id if body else None
    if not template_id:
        template_id = "ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER"

    triggered = await maybe_dispatch_adenda_on_step_completed(
        db=db,
        project_id=project_id,
        completed_template_id=template_id,
    )
    # Override trigger label en metadata trail when admin manual
    for entry in triggered:
        entry["trigger"] = "admin_manual"
        try:
            addendum = await db.get(
                ProviderAddendum,
                uuid.UUID(entry["addendum_id"]),
            )
            if addendum is not None:
                meta = dict(addendum.metadata_ or {})
                history = list(meta.get("triggers_history") or [])
                if history:
                    history[-1]["trigger"] = "admin_manual"
                    history[-1]["admin_user_id"] = (
                        str(user.id) if user else None
                    )
                meta["triggers_history"] = history
                meta["last_trigger"] = "admin_manual"
                addendum.metadata_ = meta
        except (ValueError, KeyError) as exc:
            # best-effort (actualización del audit trail del addendum) · no debe
            # tumbar el trigger admin, pero sí dejar rastro para soporte.
            logger.warning(
                "admin_trigger_adenda_check: no se pudo actualizar metadata del "
                "addendum (best-effort): %s", exc,
            )

    await db.commit()
    return {
        "project_id": str(project_id),
        "trigger_template_id": template_id,
        "adendas_processed": len(triggered),
        "details": triggered,
    }


@router.post("/{provider_id}/generate-addendum", status_code=201)
async def generate_addendum(
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    body: GenerateAddendumBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Auto-genera ADENDA E-604 desde provider + normativas + extras.

    Idempotente: si addendum_code ya existe en (project_id, code), devuelve existing.
    Sub-lote 1.B.7.1.3 cierre OPCION C hibrida AMEND-014.
    """
    await _set_project_rls(project_id, db)
    gen = AdendaGenerator(db=db)
    try:
        result = await gen.generate(
            project_id=project_id,
            provider_id=provider_id,
            normativas_aplicables=body.normativas_aplicables,
            addendum_code=body.addendum_code,
            contract_ref=body.contract_ref,
            fecha_vigor=body.fecha_vigor,
            vencimiento=body.vencimiento,
            provider_extras=body.provider_extras,
            client_extras=body.client_extras,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return {
        "addendum_id": str(result.addendum_id),
        "addendum_code": result.addendum_code,
        "minio_object_key": result.minio_object_key,
        "signed_url": result.signed_url,
        "signed_url_expires_at": result.signed_url_expires_at.isoformat(),
        "normativas_cubiertas": result.normativas_cubiertas,
        "docx_size_bytes": result.docx_size_bytes,
        "generated_at": result.generated_at.isoformat(),
        "template_code": result.template_code,
    }
