"""M18 Communication & Reporting models.

- CommunicationPlan: plan de comunicación por proyecto (1:1)
- EscalationEvent: eventos de escalado por triggers del proyecto
- (Acta E-005 vive en governance.CommitteeMeeting, extendido Sesión 6.)

StatusReport vive en models/planning.py (extendido en esta iteración).
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class CommunicationPlan(FullMixin, Base):
    """Plan de comunicación 1:1 con proyecto (spec F.6)."""
    __tablename__ = "communication_plans"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_communication_plan_project_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    destinatarios: Mapped[dict | None] = mapped_column(JSONB)
    # sponsor / comite / direccion / cliente_general
    frecuencias: Mapped[dict | None] = mapped_column(JSONB)
    # weekly / monthly / quarterly
    escalations: Mapped[list | None] = mapped_column(JSONB)
    # lista de {trigger, notify, channel}
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # draft → active → paused → completed
    activado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class EscalationEvent(FullMixin, Base):
    """Evento de escalado por trigger del proyecto."""
    __tablename__ = "escalation_events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    # riesgo_materializado_alto | paron_por_cliente_5_dias | hallazgo_critico_auditoria
    # | evidencia_critica_caducada | nc_mayor_detectada
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    notificados: Mapped[list | None] = mapped_column(JSONB)
    canal: Mapped[str] = mapped_column(String(50), nullable=False)
    # email_urgente | email_formal | reunion_urgente | feed
    resuelto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resuelto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    feed_item_id: Mapped[uuid.UUID | None] = mapped_column()
    # FK lógica a workspace_feed_items (sin constraint)


# NOTA: La acta E-005 ("Acta de Comite de Seguridad") usa el modelo
# CommitteeMeeting de governance.py extendido en Sesion 6 con las
# columnas: codigo, tipo_comite, titulo, lugar, presidente, secretario,
# orden_del_dia, proximos_pasos, notas_libres, docx_path, pdf_path,
# hash_sha256, signature_ed25519, firmas, estado, generado_at,
# enviada_at, fully_signed_at.
# Vease backend/app/models/governance.py CommitteeMeeting.
