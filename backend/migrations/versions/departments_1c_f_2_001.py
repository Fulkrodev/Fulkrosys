"""departments_1c_f_2_001 · sub-atom 1.C.F.2 (departments project-scoped).

Crea tabla `departments` project-scoped para soporte de áreas/divisiones
del cliente piloto. Single source of truth per proyecto · code+name+desc
+ unique constraint (project_id, code).

Diseño:
  - project_id NOT NULL FK projects(id) ON DELETE CASCADE
  - UNIQUE(project_id, code) · code repetible cross-proyectos
  - RLS project-scoped (LECCION-OPS-008 sostenido · pattern live_records)
  - Trigger updated_at (pattern m_live_records)
  - Index (project_id) ya implícito en FK · explicit btree por claridad

Sub-atom 1.C.F.3 añadirá FK ``client_contacts.department_id`` ON DELETE
SET NULL (1 empleado pertenece a 0..1 departamentos · simplifica M2M).

R23 sostenido · NO global cross-cliente. R28 (auto-prefill per category
B/M/A) implementado en service-layer suggestions (NO seed automatico
DB para no acoplar a category de creación).

Revision ID: departments_1c_f_2_001
Revises: projects_19dims_1c_d_a0_001
Create Date: 2026-05-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "departments_1c_f_2_001"
down_revision: Union[str, None] = "projects_19dims_1c_d_a0_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE departments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_departments_project_code
                UNIQUE (project_id, code)
        )
        """
    )

    op.execute("CREATE INDEX ix_departments_project ON departments (project_id)")

    op.execute("ALTER TABLE departments OWNER TO fulkro_migrate")
    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY departments_project_isolation ON departments
        FOR ALL TO fulkro_app
        USING (
            project_id::text = current_setting('app.current_project_id', true)
        )
        WITH CHECK (
            project_id::text = current_setting('app.current_project_id', true)
        )
        """
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE, DELETE ON departments TO fulkro_app
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION departments_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_departments_updated_at
        BEFORE UPDATE ON departments
        FOR EACH ROW
        EXECUTE FUNCTION departments_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_departments_updated_at ON departments")
    op.execute("DROP FUNCTION IF EXISTS departments_set_updated_at()")
    op.execute("DROP POLICY IF EXISTS departments_project_isolation ON departments")
    op.execute("DROP INDEX IF EXISTS ix_departments_project")
    op.execute("DROP TABLE IF EXISTS departments")
