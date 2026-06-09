"""san_e_mb6_atom5_committee_meetings_client_review

Revision ID: fb5ef0575945
Revises: 3175f643891f
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 5 · Actas 4 tipos signable + ClientReviewMixinA + admin curation.

7 decisiones Marcos + 3 sub-questions cement:
- Q1 A · extender committee_meetings (28 cols MUY madura · reuse 100%)
- Q2 D · reuse acta_comite signable_type + NEW acta_subtype col (NO proliferation)
- Q3 · 4 lifecycles · kickoff/cierre 1x · checkpoint/audit Nx
- Q3-extra · uniform 1x post-cert + on-demand admin (NO auto-Celery)
- Q4 A · TODOS MixinA (9a aplicacion · pattern atomic 11a)
- Q5 A · cliente VE TODAS (transparency)
- Q6 (c) · acta_comite outside chain · pagina /actas propia
- Q7 · NO widen signable_types (acta_comite already in CHECK · 12 stable)
- Sub-Q1 · acta_subtype='other' allowed (future-ready · 5 valores)
- Sub-Q2 · firmas jsonb multi-sig (admin Ed25519 + cliente signing_intent linked)
- Sub-Q3 · filter UI chip selector acta_subtype

Cambios:
1. ALTER committee_meetings ADD:
   - ClientReviewMixinA 4 cols (client_review_status / note / reviewed_at / by_user_id)
   - client_signing_intent_id (link signing_intent)
   - acta_subtype (String 20 · CHECK enum 5 valores)
   - admin_curation_status (String 20 default 'draft' · enum 3 valores)
   - admin_curated_at + admin_curated_by_user_id
2. CHECK ck_committee_meetings_acta_subtype (5 valores)
3. CHECK ck_committee_meetings_client_review_status (Pattern A enum 4 valores)
4. CHECK ck_committee_meetings_admin_curation_status (3 valores)
5. Index parcial idx_committee_meetings_client_review (Pattern A consistency)
6. Index idx_committee_meetings_acta_subtype (project_id, acta_subtype)
7. Index parcial idx_committee_meetings_admin_pending (project_id, admin_curation_status)

NO widen ck_signing_intents_signable_type · acta_comite ya registered (atom 4).

Reversible · downgrade limpio (table tenia 0 rows · NO data migration).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'fb5ef0575945'
down_revision: Union[str, None] = '3175f643891f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ACTA_SUBTYPES = ("kickoff", "checkpoint", "audit", "cierre", "other")
_ADMIN_CURATION_STATUSES = ("draft", "curated_by_admin", "sent_to_client")
_REVIEW_STATUSES = (
    "pendiente_revision",
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
)


def upgrade() -> None:
    # 1. ClientReviewMixinA cols (Pattern A) · String(30) match Mixin def
    op.add_column(
        "committee_meetings",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "committee_meetings",
        sa.Column("client_review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "committee_meetings",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "committee_meetings",
        sa.Column(
            "client_reviewed_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2. client_signing_intent_id · link signing_intents (FK logica · no constraint)
    op.add_column(
        "committee_meetings",
        sa.Column(
            "client_signing_intent_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 3. acta_subtype · 5 valores (Q2 D + sub-Q1 future-ready)
    op.add_column(
        "committee_meetings",
        sa.Column("acta_subtype", sa.String(20), nullable=True),
    )

    # 4. Admin curation workflow (Q3 + Q3-extra cement)
    op.add_column(
        "committee_meetings",
        sa.Column(
            "admin_curation_status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
    )
    op.add_column(
        "committee_meetings",
        sa.Column(
            "admin_curated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "committee_meetings",
        sa.Column(
            "admin_curated_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # CHECK acta_subtype (5 valores · sub-Q1 'other' allowed)
    subtype_values = ", ".join(f"'{v}'" for v in _ACTA_SUBTYPES)
    op.create_check_constraint(
        "ck_committee_meetings_acta_subtype",
        "committee_meetings",
        f"acta_subtype IS NULL OR acta_subtype IN ({subtype_values})",
    )

    # CHECK client_review_status (Pattern A enum 4 valores)
    review_values = ", ".join(f"'{v}'" for v in _REVIEW_STATUSES)
    op.create_check_constraint(
        "ck_committee_meetings_client_review_status",
        "committee_meetings",
        f"client_review_status IS NULL OR client_review_status IN ({review_values})",
    )

    # CHECK admin_curation_status (3 valores)
    curation_values = ", ".join(f"'{v}'" for v in _ADMIN_CURATION_STATUSES)
    op.create_check_constraint(
        "ck_committee_meetings_admin_curation_status",
        "committee_meetings",
        f"admin_curation_status IN ({curation_values})",
    )

    # Index parcial cliente review (consistency MixinA pattern atom 0.1)
    op.create_index(
        "idx_committee_meetings_client_review",
        "committee_meetings",
        ["project_id", "client_review_status"],
        unique=False,
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )

    # Index acta_subtype filter (sub-Q3 chip selector)
    op.create_index(
        "idx_committee_meetings_acta_subtype",
        "committee_meetings",
        ["project_id", "acta_subtype"],
        unique=False,
    )

    # Index parcial admin pending (Marcos workflow)
    op.create_index(
        "idx_committee_meetings_admin_pending",
        "committee_meetings",
        ["project_id", "admin_curation_status"],
        unique=False,
        postgresql_where=sa.text("admin_curation_status = 'draft'"),
    )

    # NO widen ck_signing_intents_signable_type · acta_comite already registered.


def downgrade() -> None:
    op.drop_index(
        "idx_committee_meetings_admin_pending",
        table_name="committee_meetings",
    )
    op.drop_index(
        "idx_committee_meetings_acta_subtype",
        table_name="committee_meetings",
    )
    op.drop_index(
        "idx_committee_meetings_client_review",
        table_name="committee_meetings",
    )
    op.drop_constraint(
        "ck_committee_meetings_admin_curation_status",
        "committee_meetings",
        type_="check",
    )
    op.drop_constraint(
        "ck_committee_meetings_client_review_status",
        "committee_meetings",
        type_="check",
    )
    op.drop_constraint(
        "ck_committee_meetings_acta_subtype",
        "committee_meetings",
        type_="check",
    )
    op.drop_column("committee_meetings", "admin_curated_by_user_id")
    op.drop_column("committee_meetings", "admin_curated_at")
    op.drop_column("committee_meetings", "admin_curation_status")
    op.drop_column("committee_meetings", "acta_subtype")
    op.drop_column("committee_meetings", "client_signing_intent_id")
    op.drop_column("committee_meetings", "client_reviewed_by_user_id")
    op.drop_column("committee_meetings", "client_reviewed_at")
    op.drop_column("committee_meetings", "client_review_note")
    op.drop_column("committee_meetings", "client_review_status")
