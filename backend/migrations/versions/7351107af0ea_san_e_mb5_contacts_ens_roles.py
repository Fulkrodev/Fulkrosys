"""san_e_mb5_contacts_ens_roles

ADR-020 v5 SAN-E v3.MB-5.0.bis: stakeholders ENS_REQUIRED como M30 contactos
INVISIBLE al cliente. Marcos los maneja desde admin (existing AssignContactModal
MB-3.5). Documentos ENS auto-populate stakeholders via M6 helper.

Adds 2 cols nullable backwards-compatible:
- role_ens_required (String 30 nullable · CHECK constraint enum 6 roles RD 311/2022 art. 11 + sponsor)
- contact_role_notes (Text nullable · admin-only notes Marcos)

NOTA: plan v5 also lists `has_portal_account` pero ese campo YA EXISTE como
`has_portal_access` (Boolean) en client_contacts FASE 5.5.B · skip duplicación.

Index parcial NEW: idx_client_contacts_role_ens_required (client_id, role_ens_required)
WHERE role_ens_required IS NOT NULL · acelera admin status overview queries.

CHECK constraint NEW: ck_client_contacts_role_ens_required · enum 6 valores
permitidos (sponsor + 5 RD 311/2022 art. 11 a-e).

Revision ID: 7351107af0ea
Revises: b8e1d4f7a3c5
Create Date: 2026-05-10 14:37:36.515870
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7351107af0ea'
down_revision: Union[str, None] = 'b8e1d4f7a3c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "client_contacts",
        sa.Column("role_ens_required", sa.String(30), nullable=True),
    )
    op.add_column(
        "client_contacts",
        sa.Column("contact_role_notes", sa.Text, nullable=True),
    )

    op.execute(
        """
        ALTER TABLE client_contacts
        ADD CONSTRAINT ck_client_contacts_role_ens_required
        CHECK (role_ens_required IS NULL OR role_ens_required IN (
            'sponsor',
            'responsable_informacion',
            'responsable_servicio',
            'responsable_seguridad',
            'responsable_sistema',
            'administrador_seguridad'
        ))
        """
    )

    op.create_index(
        "idx_client_contacts_role_ens_required",
        "client_contacts",
        ["client_id", "role_ens_required"],
        postgresql_where=sa.text("role_ens_required IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_client_contacts_role_ens_required",
        table_name="client_contacts",
    )
    op.execute(
        "ALTER TABLE client_contacts "
        "DROP CONSTRAINT IF EXISTS ck_client_contacts_role_ens_required"
    )
    op.drop_column("client_contacts", "contact_role_notes")
    op.drop_column("client_contacts", "role_ens_required")
