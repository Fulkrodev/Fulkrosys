"""document_versions unique (document_id, version) · red de seguridad race (P2-6)

Additive. Índice ÚNICO parcial sobre ``document_versions (document_id, version)``
(versiones no borradas) para que una versión IDMS duplicada (carrera de
``create_version``) falle ruidoso en vez de duplicar. Complementa el
``pg_advisory_xact_lock`` por document_id de ``idms_service.create_version``.

Revision ID: document_version_unique_001
Revises: documents_interno_flag_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "document_version_unique_001"
down_revision: Union[str, None] = "documents_interno_flag_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_document_versions_doc_version
        ON document_versions (document_id, version)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_document_versions_doc_version")
