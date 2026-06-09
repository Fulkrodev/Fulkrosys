"""M18 Communication Plan Service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import CommunicationPlan


DEFAULT_DESTINATARIOS: dict = {
    "sponsor": {"nombre": "", "email": "", "reports": ["weekly_sponsor"], "channel": "email"},
    "comite": {"miembros": [], "reports": ["monthly_comite"], "channel": "email"},
    "direccion": {"nombre": "", "email": "", "reports": ["quarterly_direccion"], "channel": "email"},
    "cliente_general": {"reports": ["quick_wins"], "channel": "feed"},
}

DEFAULT_FRECUENCIAS: dict = {
    "weekly": {"dia": "friday", "hora": "16:00", "activo": True},
    "monthly": {"semana": 1, "dia_antes_reunion": True, "activo": True},
    "quarterly": {"mes_offset": 0, "semana": 1, "activo": True},
}

DEFAULT_ESCALATIONS: list = [
    {
        "trigger": "riesgo_materializado_alto",
        "notify": ["sponsor", "direccion"],
        "channel": "email_urgente",
    },
    {
        "trigger": "paron_por_cliente_5_dias",
        "notify": ["sponsor"],
        "channel": "email_formal",
    },
    {
        "trigger": "hallazgo_critico_auditoria",
        "notify": ["sponsor", "direccion", "comite"],
        "channel": "reunion_urgente",
    },
]


class PlanError(Exception):
    pass


class CommunicationPlanService:
    """Gestión del plan de comunicación por proyecto (1:1)."""

    async def create_plan(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        destinatarios: dict | None = None,
        frecuencias: dict | None = None,
        escalations: list | None = None,
    ) -> CommunicationPlan:
        existing = await self.get_plan(db, project_id)
        if existing:
            raise PlanError(
                f"CommunicationPlan ya existe para project {project_id}"
            )
        plan = CommunicationPlan(
            project_id=project_id,
            destinatarios={**DEFAULT_DESTINATARIOS, **(destinatarios or {})},
            frecuencias={**DEFAULT_FRECUENCIAS, **(frecuencias or {})},
            escalations=escalations if escalations is not None else list(DEFAULT_ESCALATIONS),
            estado="draft",
        )
        db.add(plan)
        await db.flush()
        return plan

    async def get_plan(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> CommunicationPlan | None:
        res = await db.execute(
            select(CommunicationPlan).where(CommunicationPlan.project_id == project_id)
        )
        return res.scalar_one_or_none()

    async def activate_plan(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> CommunicationPlan:
        plan = await self.get_plan(db, project_id)
        if not plan:
            raise PlanError(f"Plan no encontrado para {project_id}")
        if plan.estado == "active":
            return plan
        plan.estado = "active"
        plan.activado_at = datetime.now(timezone.utc)
        await db.flush()
        return plan

    async def update_plan(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        updates: dict,
    ) -> CommunicationPlan:
        plan = await self.get_plan(db, project_id)
        if not plan:
            raise PlanError(f"Plan no encontrado para {project_id}")
        if "destinatarios" in updates and updates["destinatarios"] is not None:
            plan.destinatarios = updates["destinatarios"]
        if "frecuencias" in updates and updates["frecuencias"] is not None:
            plan.frecuencias = updates["frecuencias"]
        if "escalations" in updates and updates["escalations"] is not None:
            plan.escalations = updates["escalations"]
        if "estado" in updates and updates["estado"] is not None:
            plan.estado = updates["estado"]
        await db.flush()
        return plan
