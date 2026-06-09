"""m12: magic_links.sent_to_contact_id FK + index (M30 integration).

Revision ID: c3a8d7f2b419
Revises: b2c3d4e5f6a7
Create Date: 2026-04-29 21:00:00.000000

Motor 12 ↔ Motor 30 integration (TODO-M30-M12-INTEGRATION-001 RESOLVED
en BLOQUE 3 BAJAS pre-FASE 6).

Resuelve hallazgo H1 audit pre-impl m30 (2026-04-29) sub-fase 5.5.A:
``magic_links.sent_to_contact_id`` FK diferido entonces, ahora aplicado.

Schema delta:
  - ``magic_links.sent_to_contact_id`` UUID NULL
    FK ``client_contacts.id`` ON DELETE SET NULL
  - Index ``ix_magic_links_contact_id`` (sent_to_contact_id)

Behaviour:
  - Magic link enviado A contacto profesional registrado en M30 →
    populate ``sent_to_contact_id`` en /generate.
  - Al consumir magic link → service M12 invoca
    ``ClientContactService.log_interaction(interaction_type="magic_link",
    source_motor="m12", source_id=magic_link.id)``.
  - Patrón coherente con A18 (meeting), M14 (contract_signature),
    A14 (copilot context M30 integrations).

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate``. Sólo
ALTER TABLE + CREATE INDEX necesarios.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3a8d7f2b419"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "magic_links",
        sa.Column(
            "sent_to_contact_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "FK client_contacts.id si magic link enviado a contacto "
                "profesional registrado M30. NULL = legacy o flow sin "
                "contact lookup. ON DELETE SET NULL preserva audit trail "
                "del link aunque se borre el contacto."
            ),
        ),
    )
    op.create_foreign_key(
        "fk_magic_links_sent_to_contact",
        source_table="magic_links",
        referent_table="client_contacts",
        local_cols=["sent_to_contact_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_magic_links_contact_id",
        "magic_links",
        ["sent_to_contact_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_magic_links_contact_id", table_name="magic_links")
    op.drop_constraint(
        "fk_magic_links_sent_to_contact",
        "magic_links",
        type_="foreignkey",
    )
    op.drop_column("magic_links", "sent_to_contact_id")
