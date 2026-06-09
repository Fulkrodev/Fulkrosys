"""san_e_mb6_atom3_incidents_workflow_routing

Revision ID: 726e561c0cc6
Revises: 9f4153c49d44
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 3 · Incidents cliente review + CCN-CERT routing opt-in.

CCN-STIC 817 incident response workflow + LUCIA opt-in per-project.

7 decisiones Marcos · 3 considerations L99:
- Q1: Marcos crea+clasifica · cliente VE+acknowledge
- Q2: tier-aware · LUCIA opt-in projects.lucia_enabled (default False · ICP empresas privadas)
- Q3: 1 firma per incident_close (signable_type existing reused)
- Q4: 6 estados workflow (CCN-STIC 817)
- Q5: severity classification admin-only
- Q6: firmas-hub section separada "Cierres incidentes"
- Q7: ccn_cert_decision_tree.py lightweight (gate lucia_enabled primero)

Cambios:
1. ALTER incidents · 9 cols nuevas (workflow + cliente review MixinA + routing)
2. ALTER projects · lucia_enabled (admin toggle)
3. WIDEN ck_alert_queue_category · 2 categories nuevas (incident_critical_pending_route + incident_ccn_cert_overdue)
4. CHECK + Index para workflow_state + cliente review

Reversible · downgrade preserva 4 datos `severidad/descripcion/notificado_lucia/lucia_id/resolucion` existing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '726e561c0cc6'
down_revision: Union[str, None] = '9f4153c49d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_WORKFLOW_STATES = (
    "created",
    "triaged",
    "investigated",
    "mitigated",
    "resolved",
    "closed",
)

_REVIEW_STATUSES = (
    "pendiente_revision",
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
)


def upgrade() -> None:
    # 1. ALTER incidents · workflow + cliente review + routing
    op.add_column(
        "incidents",
        sa.Column("workflow_state", sa.String(30), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("client_review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "client_reviewed_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "client_signing_intent_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "lucia_submission_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "ccn_cert_routing_decision",
            JSONB(),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "reported_to_ccn_cert_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "manual_notification_doc_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # CHECK workflow_state
    workflow_values_sql = ", ".join(f"'{v}'" for v in _WORKFLOW_STATES)
    op.create_check_constraint(
        "ck_incidents_workflow_state",
        "incidents",
        f"workflow_state IS NULL OR workflow_state IN ({workflow_values_sql})",
    )

    # CHECK client_review_status (MixinA pattern)
    review_values_sql = ", ".join(f"'{v}'" for v in _REVIEW_STATUSES)
    op.create_check_constraint(
        "ck_incidents_client_review_status",
        "incidents",
        f"client_review_status IS NULL OR client_review_status IN ({review_values_sql})",
    )

    # Index parcial workflow_state (no closed)
    op.create_index(
        "idx_incidents_workflow_state_active",
        "incidents",
        ["project_id", "workflow_state"],
        unique=False,
        postgresql_where=sa.text("workflow_state IS NOT NULL AND workflow_state != 'closed'"),
    )

    # Index parcial cliente review
    op.create_index(
        "idx_incidents_client_review_status",
        "incidents",
        ["project_id", "client_review_status"],
        unique=False,
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )

    # FK lucia_submission_id (NO restrict · permit NULL para manual flow)
    op.create_foreign_key(
        "fk_incidents_lucia_submission_id",
        "incidents",
        "lucia_submissions",
        ["lucia_submission_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # FK manual_notification_doc_id
    op.create_foreign_key(
        "fk_incidents_manual_notification_doc_id",
        "incidents",
        "documents",
        ["manual_notification_doc_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. ALTER projects · lucia_enabled
    op.add_column(
        "projects",
        sa.Column(
            "lucia_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 3. WIDEN ck_alert_queue_category · add 2 new categories
    op.drop_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        type_="check",
    )
    op.create_check_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        "category IN ('bienal_art31', 'payment_overdue_aapp', "
        "'client_inactivity', 'evidence_stale', 'retainer_overdue', "
        "'milestone_due', 'workflow_blocked', 'audit_due', 'rgpd_72h', "
        "'contract_milestone', 'renewal_due', 'dpc_due', "
        "'incident_critical_pending_route', 'incident_ccn_cert_overdue', "
        "'other')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        type_="check",
    )
    op.create_check_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        "category IN ('bienal_art31', 'payment_overdue_aapp', "
        "'client_inactivity', 'evidence_stale', 'retainer_overdue', "
        "'milestone_due', 'workflow_blocked', 'audit_due', 'rgpd_72h', "
        "'contract_milestone', 'renewal_due', 'dpc_due', 'other')",
    )

    op.drop_column("projects", "lucia_enabled")

    op.drop_constraint(
        "fk_incidents_manual_notification_doc_id",
        "incidents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_incidents_lucia_submission_id",
        "incidents",
        type_="foreignkey",
    )
    op.drop_index(
        "idx_incidents_client_review_status",
        table_name="incidents",
    )
    op.drop_index(
        "idx_incidents_workflow_state_active",
        table_name="incidents",
    )
    op.drop_constraint(
        "ck_incidents_client_review_status",
        "incidents",
        type_="check",
    )
    op.drop_constraint(
        "ck_incidents_workflow_state",
        "incidents",
        type_="check",
    )
    op.drop_column("incidents", "manual_notification_doc_id")
    op.drop_column("incidents", "reported_to_ccn_cert_at")
    op.drop_column("incidents", "ccn_cert_routing_decision")
    op.drop_column("incidents", "lucia_submission_id")
    op.drop_column("incidents", "client_signing_intent_id")
    op.drop_column("incidents", "client_reviewed_by_user_id")
    op.drop_column("incidents", "client_reviewed_at")
    op.drop_column("incidents", "client_review_note")
    op.drop_column("incidents", "client_review_status")
    op.drop_column("incidents", "workflow_state")
