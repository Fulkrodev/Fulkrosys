"""Batch A diagnóstico previo · tabla precliente_diagnostic_consents (consent del lead).

Append-only ledger del consentimiento del LEAD (interesado pre-contractual) para el
cuestionario de diagnóstico previo. Base jurídica: interés legítimo art. 6.1.f RGPD
(captación en frío). DEDICADO (NO reusa fulkro_consent_audit_log · cookies).
Versiona el texto Art. 13 mostrado (consent_text_version).

SIN RLS a propósito (espejo onboarding_responses): lo escribe el lead account-less,
sin contexto tenant. El riesgo RLS del flujo account-less de SESIÓN (patrón F-18) se
verifica en Batch B · ver docs/audits/EJECUTABLE_8_BATCH2_FASE0_RECORRIDO_AUDIT.md.

up: create_table precliente_diagnostic_consents (FK onboarding_sessions · CASCADE) + index.
down: drop_index + drop_table.

Revision ID: precliente_consent_001
Revises: radar_v3_fase7_directory_match_001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, TIMESTAMP, UUID


revision = "precliente_consent_001"
down_revision = "radar_v3_fase7_directory_match_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "precliente_diagnostic_consents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "onboarding_session_id", UUID(as_uuid=True),
            sa.ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("interlocutor_email", sa.String(255), nullable=True),
        sa.Column("consent_text_version", sa.String(20), nullable=False),
        sa.Column(
            "legal_basis", sa.String(60), nullable=False,
            server_default="interes_legitimo_art_6_1_f",
        ),
        sa.Column("consented", sa.Boolean(), nullable=False),
        sa.Column("consent_scope", sa.String(80), nullable=True),
        sa.Column("consented_at", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_precliente_consents_session",
        "precliente_diagnostic_consents",
        ["onboarding_session_id"],
    )
    # Runtime role fulkro_app (NOSUPERUSER): SOLO SELECT + INSERT → append-only
    # enforced a nivel BD (sin UPDATE/DELETE · ledger de consentimiento legal).
    op.execute(
        "GRANT SELECT, INSERT ON precliente_diagnostic_consents TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_precliente_consents_session",
        table_name="precliente_diagnostic_consents",
    )
    op.drop_table("precliente_diagnostic_consents")
