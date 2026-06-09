"""san_e_mb6_atom4_retainer_quarterly_checkin_signoff

Revision ID: 3175f643891f
Revises: 726e561c0cc6
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 4 · Retainer quarterly check-in workflow + cliente signoff.

Reframe audit-driven (cadence per tier divergente DESCARTADA):
- Trimestral uniforme · alineado retainer_quarterly_reports table existing
- Pricing diferencia CONTENIDO (tier-aware sections) NOT frecuencia

7 decisiones Marcos + 3 sub-questions + 3 considerations L99:
- Q1+Q4: trimestral uniforme + admin curate OBLIGATORIO + cliente review + firma
- Q2: completar generate_quarterly_reports Celery placeholder
- Q3: 5 secciones (Activities + Incidents + Vulns + Normativa + RAG) + bonus M30/M07
- Q5: empty state cuando NO retainer activo
- Q6: NEW retainer_quarterly_signoff signable_type
- Q7: TRANSIENT signatures pattern (cement atom 3)

Cambios:
1. ALTER retainer_quarterly_reports ADD:
   - ClientReviewMixinA 4 cols + client_signing_intent_id
   - admin_curation_status (String 20) + admin_curated_at + admin_curated_by_user_id
   - period_quarter (String 7 · format '2026-Q2') + schema_version (default '1.0')
2. UNIQUE partial (project_id, period_quarter) WHERE period_quarter NOT NULL
3. CHECK ck_retainer_quarterly_admin_curation_status (3 estados)
4. CHECK ck_retainer_quarterly_client_review_status (Pattern A enum)
5. Index parcial admin_pending
6. WIDEN ck_signing_intents_signable_type · add 'retainer_quarterly_signoff'

Reversible · downgrade preserva data existing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '3175f643891f'
down_revision: Union[str, None] = '726e561c0cc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ADMIN_CURATION_STATUSES = ("draft", "curated_by_admin", "sent_to_client")
_REVIEW_STATUSES = (
    "pendiente_revision",
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
)


def upgrade() -> None:
    # 1. ALTER retainer_quarterly_reports · ClientReviewMixinA cols + signing + admin curation
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column("client_review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "client_reviewed_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "client_signing_intent_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "admin_curation_status",
            sa.String(30),
            nullable=False,
            server_default="draft",
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "admin_curated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "admin_curated_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column("period_quarter", sa.String(7), nullable=True),
    )
    op.add_column(
        "retainer_quarterly_reports",
        sa.Column(
            "schema_version",
            sa.String(8),
            nullable=False,
            server_default="1.0",
        ),
    )

    # CHECK admin_curation_status
    curation_values = ", ".join(f"'{v}'" for v in _ADMIN_CURATION_STATUSES)
    op.create_check_constraint(
        "ck_retainer_quarterly_admin_curation_status",
        "retainer_quarterly_reports",
        f"admin_curation_status IN ({curation_values})",
    )

    # CHECK client_review_status (Pattern A enum)
    review_values = ", ".join(f"'{v}'" for v in _REVIEW_STATUSES)
    op.create_check_constraint(
        "ck_retainer_quarterly_client_review_status",
        "retainer_quarterly_reports",
        f"client_review_status IS NULL OR client_review_status IN ({review_values})",
    )

    # UNIQUE partial · evita duplicate per (project_id, period_quarter)
    op.create_index(
        "uq_retainer_quarterly_project_period",
        "retainer_quarterly_reports",
        ["project_id", "period_quarter"],
        unique=True,
        postgresql_where=sa.text("period_quarter IS NOT NULL"),
    )

    # Index parcial admin_pending (Marcos workflow)
    op.create_index(
        "idx_retainer_quarterly_admin_pending",
        "retainer_quarterly_reports",
        ["project_id", "admin_curation_status"],
        unique=False,
        postgresql_where=sa.text("admin_curation_status = 'draft'"),
    )

    # Index parcial cliente review (consistency MixinA pattern atom 0.1)
    op.create_index(
        "idx_retainer_quarterly_client_review",
        "retainer_quarterly_reports",
        ["project_id", "client_review_status"],
        unique=False,
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )

    # 2. WIDEN ck_signing_intents_signable_type · add 'retainer_quarterly_signoff'
    op.drop_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        "signable_type IN ('dda', 'magerit_validation', "
        "'pentest_authorization', 'conformidad_ens', 'acta_comite', "
        "'retainer_offer', 'policy_approval', 'incident_close', "
        "'dpc_anual', 'renewal', 'document_generic', "
        "'retainer_quarterly_signoff')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        "signable_type IN ('dda', 'magerit_validation', "
        "'pentest_authorization', 'conformidad_ens', 'acta_comite', "
        "'retainer_offer', 'policy_approval', 'incident_close', "
        "'dpc_anual', 'renewal', 'document_generic')",
    )

    op.drop_index(
        "idx_retainer_quarterly_client_review",
        table_name="retainer_quarterly_reports",
    )
    op.drop_index(
        "idx_retainer_quarterly_admin_pending",
        table_name="retainer_quarterly_reports",
    )
    op.drop_index(
        "uq_retainer_quarterly_project_period",
        table_name="retainer_quarterly_reports",
    )
    op.drop_constraint(
        "ck_retainer_quarterly_client_review_status",
        "retainer_quarterly_reports",
        type_="check",
    )
    op.drop_constraint(
        "ck_retainer_quarterly_admin_curation_status",
        "retainer_quarterly_reports",
        type_="check",
    )
    op.drop_column("retainer_quarterly_reports", "schema_version")
    op.drop_column("retainer_quarterly_reports", "period_quarter")
    op.drop_column("retainer_quarterly_reports", "admin_curated_by_user_id")
    op.drop_column("retainer_quarterly_reports", "admin_curated_at")
    op.drop_column("retainer_quarterly_reports", "admin_curation_status")
    op.drop_column("retainer_quarterly_reports", "client_signing_intent_id")
    op.drop_column("retainer_quarterly_reports", "client_reviewed_by_user_id")
    op.drop_column("retainer_quarterly_reports", "client_reviewed_at")
    op.drop_column("retainer_quarterly_reports", "client_review_note")
    op.drop_column("retainer_quarterly_reports", "client_review_status")
