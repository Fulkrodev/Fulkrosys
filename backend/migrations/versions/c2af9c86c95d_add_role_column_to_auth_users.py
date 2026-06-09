"""add_role_column_to_auth_users

Revision ID: c2af9c86c95d
Revises: dd9a2d20be76
Create Date: 2026-04-27

Añade columna ``role`` a ``auth_users`` como identidad invariante del
usuario. Distinto de capabilities como ``ens_radar_owner`` que viven en
Settings (ver ADR-015).

Server default ``'owner'`` preserva Marcos (único user actual) sin
intervención manual sobre el INSERT del seed (migración
a7f1e4b8c2d5).

IMPORTANTE: ``alembic --autogenerate`` detectó drift masivo entre los
modelos SQLAlchemy y la BD real al generar esta migración (~50
operaciones DDL no relacionadas con el cambio buscado, incluyendo
DROP COLUMN destructivos en ``audit_log.seq``,
``external_pentester_handoffs.client_id``, ``lms_assignments.client_id``,
``verification_findings.client_id``, ``verification_runs.client_id`` y
4 columnas en ``ens_measure_evidencia_types``).

El drift se documenta en TODO-DB-DRIFT-001 (``progress/backlog_formal.md``)
y ADR-016 (``docs/spec/DECISIONS.md``). Snapshot del autogenerate
problemático conservado como evidencia en
``progress/session_11/artifacts/drift_audit_2026-04-27.py.txt``.

Esta migración es DELIBERADAMENTE manual y minimalista para no
contaminar el scope de FASE 3 con la resolución del drift, que se
aborda en Mini-Sesión 11.5 (entre FASE 12 y FASE 13).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2af9c86c95d"
down_revision: Union[str, None] = "dd9a2d20be76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column(
            "role",
            sa.String(length=32),
            server_default=sa.text("'owner'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("auth_users", "role")
