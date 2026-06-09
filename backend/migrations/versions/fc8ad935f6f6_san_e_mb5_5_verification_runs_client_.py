"""san_e_mb5_5_verification_runs_client_authorization

Revision ID: fc8ad935f6f6
Revises: 210b0b0f82ad
Create Date: 2026-05-10 23:25:40.800905

ADR-020 v6 SAN-E v3.MB-5.5: cliente VE scope + ventana + plan + IR
revisa contexto + firma autoriza ventana pentest.

Pattern atom 5.3.A / 5.4.A sostenido: extender tabla existing (VerificationRun)
en vez de crear paralela. Audit empirico Claude Code detecto realidad:
motor es m08_verification, NO m08_pentest. VerificationRun semantic = pentest
authorization (ya tiene scope_jsonb + scheduled_start + authorized_by +
authorization_signed_at). Decision L99: Opcion A · extender existing.

17 cols NEW (mantiene scope_jsonb, scheduled_start, authorized_by,
authorization_signed_at, tools_config, external_pentester_* EXISTING).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'fc8ad935f6f6'
down_revision: Union[str, None] = '210b0b0f82ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ventana ejecucion (3 cols · ventana_inicio = scheduled_start existing)
    op.add_column("verification_runs", sa.Column("ventana_fin", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_runs", sa.Column("ventana_timezone", sa.String(50), nullable=True, server_default="Europe/Madrid"))
    op.add_column("verification_runs", sa.Column("ventana_business_hours_only", sa.Boolean(), nullable=True, server_default=sa.text("false")))

    # Plan tests (3 cols · extiende tools_config JSONB existing)
    op.add_column("verification_runs", sa.Column("plan_test_categorias", JSONB, nullable=True))
    op.add_column("verification_runs", sa.Column("plan_test_intensity", sa.String(20), nullable=True))
    op.add_column("verification_runs", sa.Column("plan_test_estimated_hours", sa.Integer(), nullable=True))

    # Contacto IR (4 cols · admin pre-set · cliente VE)
    op.add_column("verification_runs", sa.Column("contacto_ir_nombre", sa.String(200), nullable=True))
    op.add_column("verification_runs", sa.Column("contacto_ir_email", sa.String(255), nullable=True))
    op.add_column("verification_runs", sa.Column("contacto_ir_telefono", sa.String(50), nullable=True))
    op.add_column("verification_runs", sa.Column("contacto_ir_horario", sa.String(200), nullable=True))

    # Compromiso FULKRO (3 cols · admin pre-set · cliente VE)
    op.add_column("verification_runs", sa.Column("rules_of_engagement", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("responsibility_disclosure", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("data_handling_policy", sa.Text(), nullable=True))

    # Cliente review state (4 cols · pattern atoms 5.3.A · 5.4.A)
    op.add_column("verification_runs", sa.Column("client_reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("verification_runs", sa.Column("client_reviewed_by_user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("verification_runs", sa.Column("client_concerns_note", sa.Text(), nullable=True))
    op.add_column("verification_runs", sa.Column("client_signing_intent_id", UUID(as_uuid=True), nullable=True))

    # Index parcial · perf cliente review queries
    op.create_index(
        "idx_verification_runs_client_reviewed",
        "verification_runs",
        ["project_id", "client_reviewed_at"],
        postgresql_where=sa.text("client_reviewed_at IS NOT NULL"),
    )

    # GRANT runtime user
    op.execute("GRANT SELECT, UPDATE ON verification_runs TO fulkro_app;")


def downgrade() -> None:
    op.drop_index("idx_verification_runs_client_reviewed", table_name="verification_runs")

    # Cliente review (reverse order)
    op.drop_column("verification_runs", "client_signing_intent_id")
    op.drop_column("verification_runs", "client_concerns_note")
    op.drop_column("verification_runs", "client_reviewed_by_user_id")
    op.drop_column("verification_runs", "client_reviewed_at")

    # Compromiso
    op.drop_column("verification_runs", "data_handling_policy")
    op.drop_column("verification_runs", "responsibility_disclosure")
    op.drop_column("verification_runs", "rules_of_engagement")

    # IR
    op.drop_column("verification_runs", "contacto_ir_horario")
    op.drop_column("verification_runs", "contacto_ir_telefono")
    op.drop_column("verification_runs", "contacto_ir_email")
    op.drop_column("verification_runs", "contacto_ir_nombre")

    # Plan
    op.drop_column("verification_runs", "plan_test_estimated_hours")
    op.drop_column("verification_runs", "plan_test_intensity")
    op.drop_column("verification_runs", "plan_test_categorias")

    # Ventana
    op.drop_column("verification_runs", "ventana_business_hours_only")
    op.drop_column("verification_runs", "ventana_timezone")
    op.drop_column("verification_runs", "ventana_fin")
