"""fase4_5_magic_links_email_customization

FASE 4.5 sub-bloque A · email customization fields per ADR-011.

Spec: ADR-011 (Magic Links auditoría + ampliación + email destinatario
configurable · Aprobado 2026-04-25). Cierre parcial deuda 60% pendiente.

Schema delta:
  - ``magic_links.cc_emails`` TEXT[] NULL — carbon copy emails adicionales
  - ``magic_links.custom_subject`` VARCHAR(255) NULL — override default subject
  - ``magic_links.custom_body_intro`` TEXT NULL — override prepend body intro

Behaviour:
  - cc_emails: aplicado en EmailSender (no renderer) cuando el link se envía.
  - custom_subject: si presente, sobreescribe el subject default del
    ``_PURPOSE_EMAILS`` dict per purpose.
  - custom_body_intro: si presente, se inserta antes del párrafo contextual
    (override no-replace · cuerpo original sigue después).
  - Las 3 columnas son opcionales (NULL = comportamiento default existente).

Revision ID: f658961972a2
Revises: 9939749b94c7
Create Date: 2026-05-01 09:23:41.879513

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate``. Sólo
ALTER TABLE necesarios per spec ADR-011.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f658961972a2"
down_revision: Union[str, None] = "9939749b94c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "magic_links",
        sa.Column(
            "cc_emails",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            comment=(
                "Carbon copy emails adicionales (TEXT[]). Aplicado por "
                "EmailSender al enviar el link. NULL = sin CC."
            ),
        ),
    )
    op.add_column(
        "magic_links",
        sa.Column(
            "custom_subject",
            sa.String(length=255),
            nullable=True,
            comment=(
                "Override del subject default per purpose. NULL = usar "
                "subject definido en _PURPOSE_EMAILS dict."
            ),
        ),
    )
    op.add_column(
        "magic_links",
        sa.Column(
            "custom_body_intro",
            sa.Text(),
            nullable=True,
            comment=(
                "Texto Marcos antes del cuerpo template (override prepend, "
                "no replace). NULL = sin intro custom."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("magic_links", "custom_body_intro")
    op.drop_column("magic_links", "custom_subject")
    op.drop_column("magic_links", "cc_emails")
