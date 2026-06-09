"""sand_alert_queue_001

SAN-D MB-13.4 · Tabla alert_queue para alertas proactivas UI admin
(ADR-035). RLS opcional (admin Marcos accede todos sus proyectos).

Categorías iniciales:
- bienal_art31           auditoría bienal art.31 RD 311/2022
- payment_overdue_aapp   factura AAPP retrasada Ley 3/2004 (MB-18)
- client_inactivity      cliente sin actividad portal X días (MB-14)
- evidence_stale         evidencia próxima a expirar (M07 MB-13.4)
- retainer_overdue       retainer activity overdue (M23)
- milestone_due          hito contractual próximo (MB-18)
- workflow_blocked       workflow blocking checklist M09
- audit_due              auditoría programada próxima (M27)
- rgpd_72h               brecha datos pendiente notificación M18
- contract_milestone     hito contrato cercano (M14)
- renewal_due            retainer renewal próximo (M23)
- other                  fallback genérico

Severity: info | warning | critical (CHECK constraint).

Revision ID: sand_alert_queue_001
Revises: mb11_invaapp
Create Date: 2026-05-06 (SAN-D MB-13.4)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "sand_alert_queue_001"
down_revision: Union[str, None] = "mb11_invaapp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_queue",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=True),
        sa.Column(
            "triggered_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True,
        ),
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_alert_queue_severity",
        ),
        sa.CheckConstraint(
            "category IN ("
            "'bienal_art31','payment_overdue_aapp','client_inactivity',"
            "'evidence_stale','retainer_overdue','milestone_due',"
            "'workflow_blocked','audit_due','rgpd_72h',"
            "'contract_milestone','renewal_due','other')",
            name="ck_alert_queue_category",
        ),
    )

    op.create_index(
        "ix_alert_queue_project_active",
        "alert_queue", ["project_id", "acknowledged_at"],
    )
    op.create_index(
        "ix_alert_queue_triggered_at",
        "alert_queue", [sa.text("triggered_at DESC")],
    )

    # Grant runtime app role (fulkro_app) standard CRUD permissions
    # Pattern coherente con migrations existing (M14/M15/M27 etc).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON alert_queue TO fulkro_app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alert_queue_triggered_at", table_name="alert_queue",
    )
    op.drop_index(
        "ix_alert_queue_project_active", table_name="alert_queue",
    )
    op.drop_table("alert_queue")
