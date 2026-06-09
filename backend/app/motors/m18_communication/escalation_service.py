"""M18 Escalation Service — triggers de escalado del proyecto."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.collaboration import CollaborativeWorkspace
from backend.app.models.communication import EscalationEvent
from backend.app.motors.m20_workspace.workspace_service import WorkspaceService


TRIGGERS: dict[str, dict[str, Any]] = {
    "riesgo_materializado_alto": {
        "descripcion": "Un riesgo del proyecto se ha materializado con impacto alto",
        "notify": ["sponsor", "direccion"],
        "canal": "email_urgente",
        "auto_resolve_days": None,
    },
    "paron_por_cliente_5_dias": {
        "descripcion": "El cliente no responde/colabora en 5+ días laborables",
        "notify": ["sponsor"],
        "canal": "email_formal",
        "auto_resolve_days": 10,
    },
    "hallazgo_critico_auditoria": {
        "descripcion": "NC mayor o hallazgo crítico detectado en auditoría simulada o real",
        "notify": ["sponsor", "direccion", "comite"],
        "canal": "reunion_urgente",
        "auto_resolve_days": None,
    },
    "evidencia_critica_caducada": {
        "descripcion": "Una evidencia crítica ha caducado sin renovación",
        "notify": ["sponsor"],
        "canal": "email_formal",
        "auto_resolve_days": 30,
    },
    "nc_mayor_detectada": {
        "descripcion": "No conformidad mayor detectada en simulación M10",
        "notify": ["sponsor", "direccion"],
        "canal": "email_urgente",
        "auto_resolve_days": None,
    },
    # C#35 (FRENTE C) · reloj Art.33: plazo de notificación CCN-CERT/LUCIA
    # (24/72h) próximo a vencer o vencido para un incidente aún no notificado.
    "incidente_deadline_notificacion_lucia": {
        "descripcion": (
            "Plazo Art.33 de notificación CCN-CERT/LUCIA próximo a vencer o "
            "vencido para un incidente aún no notificado"
        ),
        "notify": ["sponsor", "direccion"],
        "canal": "email_urgente",
        "auto_resolve_days": None,
    },
    # H#54 (FRENTE H · DEC-5) · reloj RGPD Art.33: plazo de 72h de notificación a
    # la AEPD próximo a vencer o vencido para una brecha de datos aún no notificada.
    "aepd_deadline_notificacion_72h": {
        "descripcion": (
            "Plazo RGPD Art.33 de notificación a la AEPD (72h) próximo a vencer o "
            "vencido para una brecha de datos personales aún no notificada"
        ),
        "notify": ["sponsor", "direccion"],
        "canal": "email_urgente",
        "auto_resolve_days": None,
    },
}


class EscalationError(Exception):
    pass


class EscalationService:
    """Gestiona escalados por triggers del proyecto."""

    async def create_escalation(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        trigger: str,
        descripcion: str | None = None,
    ) -> EscalationEvent:
        if trigger not in TRIGGERS:
            raise EscalationError(
                f"Trigger desconocido: {trigger}. Válidos: {sorted(TRIGGERS)}"
            )
        cfg = TRIGGERS[trigger]
        event = EscalationEvent(
            project_id=project_id,
            trigger=trigger,
            descripcion=descripcion or cfg["descripcion"],
            notificados=list(cfg["notify"]),
            canal=cfg["canal"],
            resuelto=False,
        )
        db.add(event)
        await db.flush()

        # Publicar en feed del workspace si existe
        ws = (await db.execute(
            select(CollaborativeWorkspace).where(
                CollaborativeWorkspace.project_id == project_id,
            )
        )).scalar_one_or_none()
        if ws:
            try:
                feed_item = await WorkspaceService().add_feed_item(
                    db,
                    workspace_id=ws.id,
                    project_id=project_id,
                    tipo="alerta",
                    titulo=f"Escalado: {trigger}",
                    descripcion=event.descripcion,
                    autor="plataforma",
                    metadata={
                        "escalation_id": str(event.id),
                        "trigger": trigger,
                        "canal": cfg["canal"],
                        "notificados": cfg["notify"],
                    },
                )
                event.feed_item_id = feed_item.id
                await db.flush()
            except Exception:
                # No bloquear el escalado si el feed falla
                pass

        return event

    async def resolve_escalation(
        self, db: AsyncSession, event_id: uuid.UUID,
    ) -> EscalationEvent:
        res = await db.execute(
            select(EscalationEvent).where(EscalationEvent.id == event_id)
        )
        event = res.scalar_one_or_none()
        if not event:
            raise EscalationError(f"EscalationEvent {event_id} no encontrado")
        if event.resuelto:
            return event
        event.resuelto = True
        event.resuelto_at = datetime.now(timezone.utc)
        await db.flush()
        return event

    async def list_escalations(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        resuelto: bool | None = None,
    ) -> list[EscalationEvent]:
        stmt = select(EscalationEvent).where(
            EscalationEvent.project_id == project_id,
        )
        if resuelto is not None:
            stmt = stmt.where(EscalationEvent.resuelto.is_(resuelto))
        stmt = stmt.order_by(EscalationEvent.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_active_count(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> int:
        res = await db.execute(
            select(func.count(EscalationEvent.id)).where(
                EscalationEvent.project_id == project_id,
                EscalationEvent.resuelto.is_(False),
            )
        )
        return res.scalar() or 0

    async def get_escalation(
        self, db: AsyncSession, event_id: uuid.UUID,
    ) -> EscalationEvent | None:
        res = await db.execute(
            select(EscalationEvent).where(EscalationEvent.id == event_id)
        )
        return res.scalar_one_or_none()
