"""add_fiscal_column_admin_settings

Revision ID: fiscal_settings_admin_001
Revises: precliente_rls_f18_001
Create Date: 2026-06-02

Punto #44 (datos fiscales del consultor · OLA 0). Añade la categoría
``fiscal`` (columna JSONB) a la tabla singleton ``admin_settings`` para
persistir la identidad fiscal del emisor (NIF, nombre fiscal, nombre
comercial, tipo de persona F/J, domicilio fiscal estructurado, régimen
IVA/IRPF, datos bancarios) como FUENTE ÚNICA editable desde
``/admin/settings`` y auditada: el trigger ``tg_audit_admin_settings``
(migración 8e02b4ed6004 · AFTER INSERT/UPDATE/DELETE a nivel tabla)
dispara ``audit_log`` también sobre esta nueva columna.

Additive + scope-only (política TODO-DB-DRIFT-001 · sin autogenerate,
conserva SOLO la operación de su scope):

- ADD COLUMN ``fiscal`` JSONB NOT NULL DEFAULT ``'{}'::jsonb``.
- La fila singleton existente queda con ``fiscal = '{}'`` (degradación
  elegante · el accessor ``get_fiscal_identity`` jamás emite el
  placeholder ``__CONSULTOR_NIF__``).
- ``fulkro_app`` hereda el GRANT de tabla sobre la nueva columna
  (privilegios a nivel tabla cubren columnas futuras).

Reversible: ``downgrade`` hace DROP COLUMN ``fiscal``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fiscal_settings_admin_001"
down_revision: Union[str, None] = "precliente_rls_f18_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ADD COLUMN admin_settings.fiscal JSONB NOT NULL DEFAULT '{}'."""
    op.add_column(
        "admin_settings",
        sa.Column(
            "fiscal",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """DROP COLUMN admin_settings.fiscal (reversible)."""
    op.drop_column("admin_settings", "fiscal")
