"""create_admin_settings_table_singleton

Revision ID: 506c7a897689
Revises: 76ecc899510d
Create Date: 2026-04-28 14:32:58.945367

Crea tabla admin_settings (singleton id UUID fija) + seed default
row con todos los JSONB vacíos. Tabla es root del módulo
backend/app/admin_settings/ que se construye en sub-bloques 4.A.2+
de FASE 4.

NOTA AUDIT-FIRST (TODO-DB-DRIFT-001 / ADR-016):

`alembic revision --autogenerate` produjo 380+ operaciones DDL
adicionales no relacionadas con admin_settings (drift cross-motor
modelos SQLAlchemy ↔ BD real). Esta migración conserva
EXCLUSIVAMENTE las operaciones específicas a admin_settings;
todas las operaciones drift fueron descartadas y preservadas como
artifact forense en
``progress/session_11/artifacts/drift_audit_2026-04-28.py.txt``.

Política firme S11: ninguna migración hasta Mini-Sesión 11.5
(post-FASE 12, pre-FASE 13) toca drift cross-motor. Las
migraciones nuevas conservan SOLO operaciones de su scope
declarado. La reconciliación drift es trabajo dedicado de
Mini-Sesión 11.5 (estimación 20-30h).

Ver:
- progress/backlog_formal.md TODO-DB-DRIFT-001
- docs/spec/DECISIONS.md ADR-016 sección Empirical Confirmation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '506c7a897689'
down_revision: Union[str, None] = '76ecc899510d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crear tabla admin_settings singleton + seed default row."""
    op.create_table(
        'admin_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'branding',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'notifications',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'smtp',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'general',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'analytics_prefs',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000001'::uuid",
            name='admin_settings_singleton',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Seed default singleton row. server_default popula JSONB
    # vacíos {} y created_at automáticamente. ON CONFLICT DO NOTHING
    # hace la migración idempotente para re-runs.
    op.execute(
        """
        INSERT INTO admin_settings (id)
        VALUES ('00000000-0000-0000-0000-000000000001')
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Drop admin_settings table. El drift cross-motor NO se toca
    (ver TODO-DB-DRIFT-001 / Mini-Sesión 11.5)."""
    op.drop_table('admin_settings')
