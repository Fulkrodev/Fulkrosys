"""M25 Exit Checklist service · gestion items granulares pre-cierre proyecto.

ADR-046 v3 SAN-E.MB-3.A. Capa de validacion sobre lifecycle FSM existente:
items deben estar completados antes de transitar a estado cerrado.

Operaciones:
- list_items: con seed lazy 16 default items (4 categorias x 4)
- complete_item / uncomplete_item: con audit trail (user + timestamp)
- check_readiness: agrega bloqueantes y warnings para decidir si cerrable
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.m25_exit_checklist import ExitChecklistItem


# 16 items default · 4 por categoria · seed lazy en primera llamada list
DEFAULT_ITEMS: list[dict[str, str]] = [
    # legal
    {"code": "contrato_firmado",      "label": "Contrato firmado por ambas partes",      "category": "legal"},
    {"code": "NDA_proveedores",       "label": "NDA proveedores cerrado",                 "category": "legal"},
    {"code": "LOPDGDD_compliance",    "label": "Cumplimiento LOPDGDD verificado",         "category": "legal"},
    {"code": "clausulas_finales",     "label": "Clausulas finales contractuales firmadas", "category": "legal"},
    # tecnico
    {"code": "backups_validados",     "label": "Backups validados en restore test",       "category": "tecnico"},
    {"code": "cifrado_datos_finales", "label": "Cifrado datos finales aplicado",          "category": "tecnico"},
    {"code": "accesos_revocados",     "label": "Accesos privilegiados revocados",         "category": "tecnico"},
    {"code": "pentest_final",         "label": "Pentest final ejecutado y reportado",     "category": "tecnico"},
    # documentacion
    {"code": "dossier_entregado",     "label": "Dossier final entregado al cliente",      "category": "documentacion"},
    {"code": "evidencias_archivadas", "label": "Evidencias archivadas en M24 IDMS",       "category": "documentacion"},
    {"code": "DdA_actualizada",       "label": "Declaracion de Aplicabilidad actualizada", "category": "documentacion"},
    {"code": "acta_cierre",           "label": "Acta de cierre firmada",                   "category": "documentacion"},
    # operacional
    {"code": "handover_cliente",          "label": "Handover operativo a cliente completado",     "category": "operacional"},
    {"code": "soporte_post_cierre_definido", "label": "Soporte post-cierre formalizado",        "category": "operacional"},
    {"code": "KPIs_finales",              "label": "KPIs finales reportados",                     "category": "operacional"},
    {"code": "feedback_NPS",              "label": "Feedback NPS recolectado",                    "category": "operacional"},
]

# Items considerados criticos (bloqueantes para cerrar)
CRITICAL_ITEMS = {
    "contrato_firmado",
    "LOPDGDD_compliance",
    "backups_validados",
    "accesos_revocados",
    "dossier_entregado",
    "evidencias_archivadas",
    "acta_cierre",
    "handover_cliente",
}


class ExitChecklistError(Exception):
    pass


@dataclass
class ChecklistItemDTO:
    id: uuid.UUID
    item_code: str
    label: str
    category: str
    status: str
    evidence_id: uuid.UUID | None
    completed_at: datetime | None
    completed_by: str | None
    note: str | None

    @classmethod
    def from_orm(cls, row: ExitChecklistItem) -> "ChecklistItemDTO":
        return cls(
            id=row.id,
            item_code=row.item_code,
            label=row.label,
            category=row.category,
            status=row.status,
            evidence_id=row.evidence_id,
            completed_at=row.completed_at,
            completed_by=row.completed_by,
            note=row.note,
        )


@dataclass
class ChecklistData:
    items: list[ChecklistItemDTO]
    progress: dict[str, Any] = field(default_factory=dict)


@dataclass
class Readiness:
    ready_to_close: bool
    total: int
    completed: int
    blockers: list[str]
    warnings: list[str]


class M25ExitService:
    """Service para gestion del exit checklist de un proyecto."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _ensure_seeded(self, project_id: uuid.UUID) -> None:
        """Seed lazy: si project no tiene items, crea los 16 defaults."""
        existing_count = (await self.db.execute(
            select(ExitChecklistItem).where(
                ExitChecklistItem.project_id == project_id,
                ExitChecklistItem.deleted_at.is_(None),
            )
        )).scalars().all()
        if existing_count:
            return
        for entry in DEFAULT_ITEMS:
            self.db.add(ExitChecklistItem(
                project_id=project_id,
                item_code=entry["code"],
                label=entry["label"],
                category=entry["category"],
                status="pendiente",
            ))
        await self.db.flush()

    async def list_items(self, project_id: uuid.UUID) -> ChecklistData:
        await self._ensure_seeded(project_id)
        rows = (await self.db.execute(
            select(ExitChecklistItem)
            .where(
                ExitChecklistItem.project_id == project_id,
                ExitChecklistItem.deleted_at.is_(None),
            )
            .order_by(ExitChecklistItem.category, ExitChecklistItem.item_code)
        )).scalars().all()
        items = [ChecklistItemDTO.from_orm(r) for r in rows]
        total = len(items)
        completed = sum(1 for i in items if i.status == "completado")
        not_applicable = sum(1 for i in items if i.status == "no_aplica")
        applicable = total - not_applicable
        pct = round(100 * completed / applicable, 1) if applicable else 0.0
        progress = {
            "total": total,
            "completed": completed,
            "applicable": applicable,
            "not_applicable": not_applicable,
            "completed_pct": pct,
            "by_category": self._progress_by_category(items),
        }
        return ChecklistData(items=items, progress=progress)

    @staticmethod
    def _progress_by_category(items: list[ChecklistItemDTO]) -> dict[str, dict[str, int]]:
        by_cat: dict[str, dict[str, int]] = {}
        for it in items:
            cat = by_cat.setdefault(
                it.category, {"total": 0, "completed": 0, "blocked": 0, "not_applicable": 0}
            )
            cat["total"] += 1
            if it.status == "completado":
                cat["completed"] += 1
            elif it.status == "bloqueado":
                cat["blocked"] += 1
            elif it.status == "no_aplica":
                cat["not_applicable"] += 1
        return by_cat

    async def _get_item(
        self, project_id: uuid.UUID, item_id: uuid.UUID,
    ) -> ExitChecklistItem:
        row = (await self.db.execute(
            select(ExitChecklistItem).where(
                ExitChecklistItem.id == item_id,
                ExitChecklistItem.project_id == project_id,
                ExitChecklistItem.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if row is None:
            raise ExitChecklistError(f"Item {item_id} not found en project {project_id}")
        return row

    async def complete_item(
        self,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        evidence_id: uuid.UUID | None,
        note: str | None,
        user_id: str | None,
    ) -> ChecklistItemDTO:
        row = await self._get_item(project_id, item_id)
        row.status = "completado"
        row.completed_at = datetime.now(timezone.utc)
        row.completed_by = user_id
        row.evidence_id = evidence_id
        if note is not None:
            row.note = note
        await self.db.flush()
        return ChecklistItemDTO.from_orm(row)

    async def uncomplete_item(
        self,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: str | None,
    ) -> ChecklistItemDTO:
        row = await self._get_item(project_id, item_id)
        row.status = "pendiente"
        row.completed_at = None
        row.completed_by = None
        row.evidence_id = None
        await self.db.flush()
        return ChecklistItemDTO.from_orm(row)

    async def set_status(
        self,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        status: str,
        note: str | None,
        user_id: str | None,
    ) -> ChecklistItemDTO:
        if status not in ("pendiente", "completado", "bloqueado", "no_aplica"):
            raise ExitChecklistError(f"Status invalido: {status}")
        row = await self._get_item(project_id, item_id)
        row.status = status
        if status == "completado":
            row.completed_at = datetime.now(timezone.utc)
            row.completed_by = user_id
        else:
            row.completed_at = None
            row.completed_by = None
        if note is not None:
            row.note = note
        await self.db.flush()
        return ChecklistItemDTO.from_orm(row)

    async def check_readiness(self, project_id: uuid.UUID) -> Readiness:
        data = await self.list_items(project_id)
        items = data.items
        total = len(items)
        completed = sum(1 for i in items if i.status == "completado")
        blockers: list[str] = []
        warnings: list[str] = []
        for it in items:
            if it.status in ("completado", "no_aplica"):
                continue
            label = f"[{it.category}] {it.label}"
            if it.item_code in CRITICAL_ITEMS or it.status == "bloqueado":
                blockers.append(label)
            else:
                warnings.append(label)
        return Readiness(
            ready_to_close=not blockers,
            total=total,
            completed=completed,
            blockers=blockers,
            warnings=warnings,
        )
