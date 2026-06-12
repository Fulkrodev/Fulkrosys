"""r26_conformity_cert_documents_001 · R26 · adjuntar distintivo + certificado a la ruta

Al alcanzar ``RouteState.REGISTERED`` la ruta de conformidad adjunta dos
Documents descargables, claramente diferenciados (regla de nomenclatura
CCN-STIC 809 · R26):

  - ``distintivo_document_id``  → DISTINTIVO de Conformidad con el ENS
    (CCN-STIC 809) que GENERA FULKRO (autopublicable · nº + vigencia 2 años).
  - ``external_cert_document_id`` → CERTIFICADO emitido por la entidad de
    certificación acreditada (MEDIA/ALTA · slot de adjunto). FULKRO NUNCA lo
    emite; se persiste cuando la entidad de certificación lo entrega.

ADDITIVE · DB-safe: dos columnas FK nullable sobre ``conformity_routes``
(tabla ya aislada por ``project_id``). ``ON DELETE SET NULL`` evita huérfanos
si se borra el Document. Sin cambios de RLS.

Revision ID: r26_conformity_cert_documents_001
Revises: policy_ack_mp_per3_001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r26_conformity_cert_documents_001"
down_revision: Union[str, None] = "policy_ack_mp_per3_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conformity_routes",
        sa.Column("distintivo_document_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "conformity_routes",
        sa.Column("external_cert_document_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_conformity_routes_distintivo_doc",
        "conformity_routes", "documents",
        ["distintivo_document_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_conformity_routes_external_cert_doc",
        "conformity_routes", "documents",
        ["external_cert_document_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conformity_routes_external_cert_doc",
        "conformity_routes", type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conformity_routes_distintivo_doc",
        "conformity_routes", type_="foreignkey",
    )
    op.drop_column("conformity_routes", "external_cert_document_id")
    op.drop_column("conformity_routes", "distintivo_document_id")
