"""Motor 9 Audit Preparation API (M9-A)."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from . import (
    checklist_service,
    cleanup_service,
    coaching,
    dossier_generator,
    internal_auditor,
    matriz_99,
)


router = APIRouter(
    prefix="/audit-prep", tags=["Motor 9 - Audit Preparation"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _load_run_or_404(
    session: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
):
    run = await checklist_service.get_run(session, run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="AuditPreparationRun no encontrado")
    return run


# ============ Schemas ============

class CreateRunBody(BaseModel):
    categoria: str = Field(..., min_length=1, max_length=10)


class ResolveBody(BaseModel):
    resuelto_por: str = Field(..., min_length=2, max_length=100)


# ============ Runs ============

@router.post("/projects/{project_id}/runs")
async def create_run_endpoint(
    project_id: uuid.UUID,
    body: CreateRunBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        run = await checklist_service.run_full_checklist(
            session, project_id, body.categoria,
        )
    except checklist_service.ChecklistError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    await session.commit()
    return checklist_service.run_to_dict(run)


# ============ Dossier (M9-B) ============

from datetime import datetime, timezone


@router.post("/projects/{project_id}/dossier/generate-signed-zip")
async def generate_signed_zip_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Convenience endpoint · ZIP firmado Ed25519 entrega ENAC final.

    Sesión 3B-2B.6 Cluster 1 Phase 1 · single-call convenience: encuentra
    la última run del proyecto (o falla si none exists con instrucciones) ·
    genera dossier completo con manifest Ed25519 signed · streams ZIP.

    No es BORRADOR (force=False forzado) · valida checklist completo. Si
    bloqueantes existen, devuelve 422 con detail explicando pending items.

    Auditor recibe ZIP descargable + manifest._signature verifiable
    independientemente con public_key_pem (ENAC integridad requirement).
    """
    from fastapi.responses import Response
    await _set_project_rls(project_id, session)

    # Find latest run for this project
    from sqlalchemy import select, desc
    from backend.app.models.audit_prep import AuditPreparationRun
    stmt = (
        select(AuditPreparationRun)
        .where(AuditPreparationRun.project_id == project_id)
        .order_by(desc(AuditPreparationRun.created_at))
        .limit(1)
    )
    run = (await session.execute(stmt)).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=(
                "No existe ningún AuditPreparationRun para este proyecto. "
                "Ejecuta primero POST /audit-prep/projects/{id}/runs."
            ),
        )

    try:
        data = await dossier_generator.generate_dossier(
            session, project_id, run.id, force=False, sign_manifest=True,
        )
    except dossier_generator.DossierError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )

    run.estado = "dossier_generated"
    run.dossier_generated_at = datetime.now(timezone.utc)
    await session.commit()

    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dossier_auditoria_{run.id}_signed.zip"'
            ),
            "X-Run-Id": str(run.id),
            "X-Dossier-Signed": "ed25519",
        },
    )


@router.post("/projects/{project_id}/runs/{run_id}/generate-dossier")
async def generate_dossier_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    force: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """Genera el dossier ZIP + marca el run como dossier_generated.

    Si ``force=true`` emite un dossier parcial BORRADOR aunque haya
    items bloqueantes en el checklist (solo para uso interno).
    """
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    try:
        data = await dossier_generator.generate_dossier(
            session, project_id, run_id, force=force,
        )
    except dossier_generator.DossierError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    # Marca el run como dossier generado (no persistimos el ZIP en disco aqui)
    run.estado = "dossier_generated"
    run.dossier_generated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()
    return {
        "run_id": str(run_id),
        "size_bytes": len(data),
        "generated_at": run.dossier_generated_at.isoformat(),
        "estado": run.estado,
    }


@router.get("/projects/{project_id}/runs/{run_id}/dossier")
async def download_dossier_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    force: bool = False,
    sign_manifest: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """Download ZIP dossier · optional `sign_manifest=true` Ed25519 firma manifest.

    Sesión 3B-2B.6 Cluster 1 Phase 1 · auditor ENAC final delivery requiere
    `sign_manifest=true` para verificar integridad + autoría Marcos.
    """
    from fastapi.responses import Response
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    try:
        data = await dossier_generator.generate_dossier(
            session, project_id, run_id, force=force, sign_manifest=sign_manifest,
        )
    except dossier_generator.DossierError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    filename = (
        f"dossier_auditoria_{run_id}_signed.zip"
        if sign_manifest else
        f"dossier_auditoria_{run_id}.zip"
    )
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/projects/{project_id}/runs/{run_id}/dossier/index")
async def dossier_index_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    try:
        return await dossier_generator.build_index_data(
            session, project_id, run_id,
        )
    except dossier_generator.DossierError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )


# ============ Matriz 99 (M9-B) ============

@router.get("/projects/{project_id}/runs/{run_id}/matriz-99")
async def download_matriz_99_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    data = await matriz_99.generate_matriz_99(
        session, project_id, run.categoria,
    )
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="matriz_99_{run_id}.xlsx"'
            ),
        },
    )


@router.get("/projects/{project_id}/runs/{run_id}/matriz-99/data")
async def matriz_99_data_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    rows = await matriz_99.generate_matriz_99_data(
        session, project_id, run.categoria,
    )
    return {
        "categoria": run.categoria,
        "total_rows": len(rows),
        "rows": rows,
    }


# ============ Coaching (M9-B) ============

@router.get("/coaching/roles")
async def coaching_roles_endpoint():
    return {"roles": coaching.get_all_roles()}


@router.get("/coaching/questions/{role}")
async def coaching_questions_by_role_endpoint(role: str):
    qs = coaching.get_questions_by_role(role)
    if not qs:
        raise HTTPException(
            status_code=404, detail=f"Rol '{role}' no encontrado",
        )
    return {"role": role, "total": len(qs), "questions": qs}


@router.get("/coaching/questions/by-measure/{measure_code}")
async def coaching_questions_by_measure_endpoint(measure_code: str):
    qs = coaching.get_questions_by_measure(measure_code)
    return {
        "measure_code": measure_code,
        "total": len(qs),
        "questions": qs,
    }


class CoachingPackBody(BaseModel):
    categoria: str = Field(..., min_length=1, max_length=10)


@router.post("/projects/{project_id}/coaching-pack")
async def coaching_pack_endpoint(
    project_id: uuid.UUID,
    body: CoachingPackBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await session.commit()
    return coaching.generate_coaching_pack(body.categoria)


# ============ Summary M9 (global) ============

@router.get("/projects/{project_id}/summary")
async def m09_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Resumen global M9: ultimo run + status dossier."""
    await _set_project_rls(project_id, session)
    runs = await checklist_service.list_runs(session, project_id)
    if not runs:
        return {
            "project_id": str(project_id),
            "has_runs": False,
            "last_run": None,
            "dossier_generated": False,
        }
    last = runs[0]
    return {
        "project_id": str(project_id),
        "has_runs": True,
        "total_runs": len(runs),
        "last_run": checklist_service.run_to_dict(last),
        "dossier_generated": last.dossier_generated_at is not None,
        "dossier_generated_at": (
            last.dossier_generated_at.isoformat()
            if last.dossier_generated_at else None
        ),
    }


@router.get("/projects/{project_id}/runs")
async def list_runs_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    runs = await checklist_service.list_runs(session, project_id)
    return [checklist_service.run_to_dict(r) for r in runs]


@router.get("/projects/{project_id}/runs/{run_id}")
async def get_run_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    return checklist_service.run_to_dict(run)


@router.delete("/projects/{project_id}/runs/{run_id}")
async def delete_run_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    await checklist_service.soft_delete_run(session, run_id)
    await session.commit()
    return {"deleted": True, "run_id": str(run_id)}


# ============ Items ============

@router.get("/projects/{project_id}/runs/{run_id}/items")
async def list_items_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    categoria_check: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    severidad: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    items = await checklist_service.get_items(
        session, run_id,
        categoria_check=categoria_check, estado=estado, severidad=severidad,
    )
    return [checklist_service.item_to_dict(i) for i in items]


@router.get("/projects/{project_id}/runs/{run_id}/items/{item_id}")
async def get_item_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    items = await checklist_service.get_items(session, run_id)
    match = next((i for i in items if i.id == item_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return checklist_service.item_to_dict(match)


@router.patch("/projects/{project_id}/runs/{run_id}/items/{item_id}/resolve")
async def resolve_item_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ResolveBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    item = await checklist_service.resolve_item(
        session, item_id, body.resuelto_por,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    await session.commit()
    return checklist_service.item_to_dict(item)


# ============ Contradictions ============

@router.get("/projects/{project_id}/runs/{run_id}/contradictions")
async def list_contradictions_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    await _load_run_or_404(session, project_id, run_id)
    items = await checklist_service.get_contradictions(session, run_id)
    return [checklist_service.item_to_dict(i) for i in items]


# ============ Summary ============

@router.get("/projects/{project_id}/runs/{run_id}/summary")
async def run_summary_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    score = run.readiness_score or 0
    interpretation = (
        "listo_auditoria" if score >= 90
        else "ajustes_menores" if score >= 70
        else "trabajo_significativo" if score >= 50
        else "no_presentar"
    )
    return {
        "run_id": str(run_id),
        "categoria": run.categoria,
        "estado": run.estado,
        "readiness_score": score,
        "interpretation": interpretation,
        "contradicciones_count": run.contradicciones_count,
        "alertas_count": run.alertas_count,
        "breakdown": run.checklist_results or {},
    }


# ============ Cleanup ============

@router.post("/projects/{project_id}/runs/{run_id}/cleanup")
async def run_cleanup_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await _load_run_or_404(session, project_id, run_id)
    items = await cleanup_service.run_cleanup(session, run)
    await session.commit()
    return {
        "items_created": len(items),
        "items": [checklist_service.item_to_dict(i) for i in items],
    }


# ============ Readiness quick ============

@router.get("/projects/{project_id}/readiness")
async def readiness_quick_endpoint(
    project_id: uuid.UUID,
    categoria: str = Query(..., min_length=1, max_length=10),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        return await checklist_service.readiness_quick(
            session, project_id, categoria,
        )
    except checklist_service.ChecklistError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )


@router.get("/projects/{project_id}/entregables-requeridos")
async def entregables_requeridos_endpoint(
    project_id: uuid.UUID,
    categoria: Optional[str] = Query(None, max_length=10),
    session: AsyncSession = Depends(get_db),
):
    """Que entregables exige el checklist para la categoria, y cuales faltan.

    P2 · el checklist sabia perfectamente que faltaba -- `check_deliverables`
    lo calcula desde la version 1 -- pero solo lo publicaba como CIFRA
    ("1 de 28"), nunca como LISTA. Sin la lista, la interfaz no podia ofrecer
    generarlos, y sin esa oferta el generador generico
    (`POST /projects/{id}/documents/generate`) no tenia quien lo llamara: el
    grep de "documents/generate" en frontend/ devolvia cero. El motor estaba
    entero y le faltaba el cable.

    Aqui se expone la MISMA lista que usa el checklist, no una copia: sale de
    `checklist_service.get_required_deliverables`. Y se cruza con el catalogo
    de plantillas para decir cuales de los que faltan son generables hoy y
    cuales no tienen plantilla -- que es informacion que el operador necesita
    antes de pulsar nada.
    """
    await _set_project_rls(project_id, session)
    # Si no la dan, se deriva del proyecto: la pantalla no tiene por que saber
    # la categoria para preguntar que le falta (mismo patron que el auditor
    # interno, api.py:run_internal_audit_endpoint).
    categoria = (categoria or "").strip().upper()
    if not categoria:
        fila = (await session.execute(
            text("SELECT categoria_objetivo FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )).first()
        categoria = (fila[0] if fila and fila[0] else "") or "BASICA"
    try:
        requeridos = checklist_service.get_required_deliverables(categoria)
    except checklist_service.ChecklistError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    presentes = {
        row[0] for row in (await session.execute(
            text(
                "SELECT DISTINCT template_codigo FROM documents "
                "WHERE project_id = :pid AND template_codigo IS NOT NULL "
                "  AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).all() if row[0]
    }
    con_plantilla = {
        row[0] for row in (await session.execute(
            text("SELECT codigo FROM templates WHERE is_active = true")
        )).all()
    }

    faltan = [c for c in requeridos if c not in presentes]
    return {
        "categoria": categoria.upper(),
        "requeridos": requeridos,
        "presentes": sorted(presentes & set(requeridos)),
        "faltan": [c for c in faltan if c in con_plantilla],
        "faltan_sin_plantilla": [c for c in faltan if c not in con_plantilla],
        "total": len(requeridos),
        "presentes_count": len(presentes & set(requeridos)),
    }


# ============ Auditoría interna virtual · E-701 (D4 fix campaña auditoría) ============

class InternalAuditRunBody(BaseModel):
    # categoria opcional · si se omite se deriva de projects.categoria_objetivo
    categoria: Optional[str] = Field(None, max_length=10)
    generate_document: bool = True


@router.post("/projects/{project_id}/internal-audit/run")
async def run_internal_audit_endpoint(
    project_id: uuid.UUID,
    body: InternalAuditRunBody,
    session: AsyncSession = Depends(get_db),
):
    """Ejecuta el auditor interno virtual (15 preguntas tipo ENAC · A11) y,
    opcionalmente, genera el informe E-701 vía DocumentFactoryService.

    Cierra el cableado del módulo LATENTE ``internal_auditor`` (run_internal_audit
    + build_e701_context): hasta ahora E-701 no se generaba en ningún flujo real
    pese a estar reservado en el dossier ENAC (carpeta 13_INFORMES_TECNICOS) y
    exigido por el checklist para MEDIA/ALTA.
    """
    await _set_project_rls(project_id, session)

    categoria = (body.categoria or "").strip().upper()
    if not categoria:
        row = (await session.execute(
            text("SELECT categoria_objetivo FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )).first()
        categoria = row[0] if row and row[0] else "BASICA"

    audit_result = await internal_auditor.run_internal_audit(
        session, project_id, categoria,
    )

    document = None
    if body.generate_document:
        from backend.app.motors.m06_document_factory.service import (
            DocumentFactoryService,
        )
        from .public_api import _load_client_info, _load_project_info

        cliente = await _load_client_info(session, project_id)
        proyecto = await _load_project_info(session, project_id)
        context = await internal_auditor.build_e701_context(
            session, project_id, audit_result,
            cliente=cliente, proyecto=proyecto, responsables={},
        )
        svc = DocumentFactoryService(session)
        document = await svc.generate_document(
            project_id, "E-701", context, generated_by="internal_auditor",
        )
        await session.commit()

    return {"audit": audit_result, "document": document}
