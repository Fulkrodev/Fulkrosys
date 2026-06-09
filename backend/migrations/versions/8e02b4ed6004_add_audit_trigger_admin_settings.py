"""add_audit_trigger_admin_settings

Revision ID: 8e02b4ed6004
Revises: 506c7a897689
Create Date: 2026-04-28 15:28:58.282617

Audit log via trigger Postgres-side. Patrón canónico FULKRO:
12 tablas existentes (clients, projects, contracts, invoices,
evidence, documents, document_versions, categorizations,
dda_entries, obligations, magerit_analysis, audit_findings) usan
``fn_audit_track`` función plpgsql genérica + ``tg_audit_<tabla>``
trigger AFTER INSERT/UPDATE/DELETE.

Esta migración añade ``tg_audit_admin_settings`` siguiendo el
mismo pattern. La función ``fn_audit_track`` ya existe (creada
en migración previa S1-S2) y el trigger separado
``tg_audit_log_hash_chain`` sobre ``audit_log`` calcula hash
chain inmutable automáticamente.

Identificador usuario: ``service.update_section`` ejecuta
``set_config('app.current_user', user.email, true)`` antes del
UPDATE. El trigger ``fn_audit_track`` lee
``current_setting('app.current_user', true)`` y lo persiste como
``audit_log.usuario``. Scope local-to-transaction preserva
atomicidad (UPDATE + audit_log entry en MISMA transaction).

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate``
(Alembic default no detecta triggers, evita re-derivar drift
cross-motor 380+ ops). Conserva SOLO operación trigger
admin_settings.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '8e02b4ed6004'
down_revision: Union[str, None] = '506c7a897689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea trigger tg_audit_admin_settings reutilizando fn_audit_track."""
    op.execute(
        """
        CREATE TRIGGER tg_audit_admin_settings
        AFTER INSERT OR UPDATE OR DELETE ON admin_settings
        FOR EACH ROW
        EXECUTE FUNCTION fn_audit_track();
        """
    )


def downgrade() -> None:
    """Drop trigger. fn_audit_track NO se toca (compartida 12 tablas)."""
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_admin_settings ON admin_settings;"
    )
