"""m28 · fn_refresh_drift_summary() SECURITY DEFINER + grants (D5 campaña fix)

El endpoint GET /api/v1/projects/{id}/drift-summary lee la matview
``mv_drift_summary_10x4`` (OWNER fulkro) pero NINGÚN job la refrescaba en
producción → datos obsoletos/vacíos. El worker Celery corre como ``fulkro_app``
(NOSUPERUSER, no-owner) y NO puede ``REFRESH MATERIALIZED VIEW`` directamente;
además ``CONCURRENTLY`` no puede ejecutarse dentro de una función/transacción.

Fix: función ``SECURITY DEFINER`` (creada por ``fulkro_migrate`` superuser → al
ejecutarse corre como el definidor, refresca y bypassa RLS) que hace un REFRESH
NO-concurrente (la matview es pequeña, refresco semanal off-hours · lock breve
aceptable). Se concede EXECUTE a los roles de runtime. La task Celery
``m28.refresh_drift_summary`` (lunes 06:45, tras m23.drift_weekly_compute 06:00)
la invoca.

Revision ID: m28_refresh_drift_summary_fn_001
Revises: drop_deadcode_controls_effort_001
Create Date: 2026-06-17
"""
from __future__ import annotations

from alembic import op

revision = "m28_refresh_drift_summary_fn_001"
down_revision = "drop_deadcode_controls_effort_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_refresh_drift_summary()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW mv_drift_summary_10x4;
        END;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION fn_refresh_drift_summary() FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION fn_refresh_drift_summary() TO fulkro_app;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app_bypassrls') THEN
                GRANT EXECUTE ON FUNCTION fn_refresh_drift_summary() TO fulkro_app_bypassrls;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_refresh_drift_summary();")
