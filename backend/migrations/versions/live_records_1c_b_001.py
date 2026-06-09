"""live_records_1c_b_001 · sub-lote 1.C.B (registros vivos E-300..E-325).

Crea tabla generica `live_records` con discriminator `register_type` para
los 26 registros operativos exigidos durante la conformidad ENS (sub-fase
1.5 plan v2 al 0% segun audit v4 dim 4).

Diseño:
  - Tabla unica con JSONB entry_data + discriminator register_type.
  - 26 tipos validos: E-300..E-325 (cubre 9 bloques: Activos, Personas,
    Incidentes, Cambios, Proveedores, Backup, Continuidad, Auditoria, Comite).
  - CHECK constraint regex enforces register_type shape.
  - RLS project-scoped (LECCION-OPS-008 sostenido).
  - 3 indexes: (project_id, register_type) · status partial · gin entry_data.
  - Trigger updated_at coherente con resto de la plataforma.

Auto-population posterior (commit separado): M19 incidents → E-305 ·
M28 change_governance → E-308 · M23 retainer evals → E-312.

Revision ID: live_records_1c_b_001
Revises: m27_uceens_dropout_1b8a_001
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op


revision: str = "live_records_1c_b_001"
down_revision: Union[str, None] = "m27_uceens_dropout_1b8a_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FIX LECCION-OPS-029: spec referenciaba ``users(id)`` pero realidad
    # codigo tiene 2 pools (auth_users + client_users via ADR-013). Pattern
    # plataforma sostenido (ej. incidents.client_reviewed_by_user_id): UUID
    # NOT NULL sin FK constraint para no acoplar a un pool concreto.
    op.execute(
        """
        CREATE TABLE live_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            register_type VARCHAR(10) NOT NULL,
            entry_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by UUID NOT NULL,
            CONSTRAINT ck_live_records_register_type
                CHECK (register_type ~ '^E-3(0[0-9]|1[0-9]|2[0-5])$'),
            CONSTRAINT ck_live_records_status
                CHECK (status IN ('active', 'archived'))
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_live_records_project_type
        ON live_records (project_id, register_type)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_live_records_status_active
        ON live_records (project_id, register_type)
        WHERE status = 'active'
        """
    )
    op.execute(
        """
        CREATE INDEX ix_live_records_entry_data_gin
        ON live_records USING gin (entry_data)
        """
    )

    op.execute("ALTER TABLE live_records OWNER TO fulkro_migrate")

    op.execute("ALTER TABLE live_records ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY live_records_project_isolation ON live_records
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
        GRANT SELECT, INSERT, UPDATE, DELETE ON live_records TO fulkro_app
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION live_records_set_updated_at()
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
        CREATE TRIGGER trg_live_records_updated_at
        BEFORE UPDATE ON live_records
        FOR EACH ROW
        EXECUTE FUNCTION live_records_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_live_records_updated_at ON live_records")
    op.execute("DROP FUNCTION IF EXISTS live_records_set_updated_at()")
    op.execute("DROP POLICY IF EXISTS live_records_project_isolation ON live_records")
    op.execute("DROP INDEX IF EXISTS ix_live_records_entry_data_gin")
    op.execute("DROP INDEX IF EXISTS ix_live_records_status_active")
    op.execute("DROP INDEX IF EXISTS ix_live_records_project_type")
    op.execute("DROP TABLE IF EXISTS live_records")
