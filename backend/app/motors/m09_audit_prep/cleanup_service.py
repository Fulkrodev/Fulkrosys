"""Cleanup documental pre-dossier (M9-A).

Spec §3.7.3: verificar firmas, fechas, ubicaciones, consistencia antes
de generar el dossier final. Detecta borradores, duplicados, fechas
incoherentes, clasificacion ausente.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_prep import (
    AuditChecklistItem,
    AuditPreparationRun,
)
from backend.app.models.documents import Document


# Estados que indican documento NO listo
_NOT_APPROVED_STATES = {"borrador", "draft", "en_revision", "pending", None}


async def run_cleanup(
    db: AsyncSession, run: AuditPreparationRun,
) -> list[AuditChecklistItem]:
    """Ejecuta los 5 checks de limpieza documental."""
    items: list[AuditChecklistItem] = []

    r = await db.execute(
        select(Document).where(
            Document.project_id == run.project_id,
            Document.deleted_at.is_(None),
        )
    )
    docs = list(r.scalars().all())

    # 1. Estado borrador/pendiente
    for d in docs:
        estado = (d.estado or "").lower() if d.estado else None
        if estado in {s for s in _NOT_APPROVED_STATES if s}:
            item = AuditChecklistItem(
                run_id=run.id, project_id=run.project_id,
                categoria_check="cleanup_borrador",
                referencia=d.template_codigo or d.nombre,
                descripcion=(
                    f"Documento '{d.nombre}' en estado no aprobado ({d.estado})"
                ),
                estado="fail", severidad="warning",
                detalle=f"document.id={d.id}, estado={d.estado}",
                accion_sugerida=(
                    "Aprobar el documento o descartarlo si ha quedado obsoleto"
                ),
            )
            db.add(item)
            items.append(item)

    # 2. Duplicados (mismo template_codigo con distintas versiones activas)
    by_code: dict[str, list[Document]] = defaultdict(list)
    for d in docs:
        if d.template_codigo:
            by_code[d.template_codigo].append(d)
    for code, dups in by_code.items():
        if len(dups) > 1:
            item = AuditChecklistItem(
                run_id=run.id, project_id=run.project_id,
                categoria_check="cleanup_duplicado",
                referencia=code,
                descripcion=(
                    f"Entregable {code} tiene {len(dups)} documentos "
                    "activos (posibles duplicados)"
                ),
                estado="warning", severidad="warning",
                detalle=(
                    "document_ids: " + ", ".join(str(d.id) for d in dups[:5])
                ),
                accion_sugerida=(
                    "Soft-delete versiones obsoletas, dejar solo la vigente"
                ),
            )
            db.add(item)
            items.append(item)

    # 3. Clasificacion (tipo) ausente
    for d in docs:
        if not d.tipo:
            item = AuditChecklistItem(
                run_id=run.id, project_id=run.project_id,
                categoria_check="cleanup_clasificacion",
                referencia=d.template_codigo or str(d.id),
                descripcion=(
                    f"Documento '{d.nombre}' sin clasificacion (campo tipo)"
                ),
                estado="warning", severidad="info",
                accion_sugerida=(
                    "Asignar tipo INTERNO/CONFIDENCIAL/PUBLICO"
                ),
            )
            db.add(item)
            items.append(item)

    # 4. Fecha de aprobacion futura (anomalía)
    today = date.today()
    for d in docs:
        if d.fecha_aprobacion and d.fecha_aprobacion > today:
            item = AuditChecklistItem(
                run_id=run.id, project_id=run.project_id,
                categoria_check="cleanup_fecha",
                referencia=d.template_codigo or str(d.id),
                descripcion=(
                    f"Documento '{d.nombre}' con fecha_aprobacion futura: "
                    f"{d.fecha_aprobacion}"
                ),
                estado="fail", severidad="error",
                accion_sugerida="Corregir fecha_aprobacion",
            )
            db.add(item)
            items.append(item)

    # 5. Coherencia: politicas antes que procedimientos
    # Encontrar una politica (E-1XX) y un procedimiento (E-2XX) del proyecto
    politicas = [
        d for d in docs
        if d.template_codigo and d.template_codigo.startswith("E-1")
        and d.fecha_aprobacion
    ]
    procedimientos = [
        d for d in docs
        if d.template_codigo and d.template_codigo.startswith("E-2")
        and d.fecha_aprobacion
    ]
    # Si algun procedimiento es anterior a alguna politica -> alerta
    if politicas and procedimientos:
        latest_politica = max(d.fecha_aprobacion for d in politicas)
        earliest_proc = min(d.fecha_aprobacion for d in procedimientos)
        if earliest_proc < latest_politica:
            item = AuditChecklistItem(
                run_id=run.id, project_id=run.project_id,
                categoria_check="cleanup_coherencia",
                referencia="temporal_politicas_procedimientos",
                descripcion=(
                    "Algun procedimiento aprobado antes que la "
                    "politica mas reciente"
                ),
                estado="warning", severidad="info",
                detalle=(
                    f"politica_max={latest_politica}, "
                    f"procedimiento_min={earliest_proc}"
                ),
                accion_sugerida=(
                    "Revisar orden temporal de aprobacion "
                    "(politica antes que procedimientos)"
                ),
            )
            db.add(item)
            items.append(item)

    await db.flush()
    return items
