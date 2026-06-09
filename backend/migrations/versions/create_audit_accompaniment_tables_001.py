"""create audit_accompaniment tables (capture Ejecutable 7.5 DDL)

Ejecutable 8 Pasada 16 (DB-DRIFT-01): las 3 tablas del motor m_audit_accompaniment
(audit_accompaniment_state / _artifacts / _transitions) se crearon en Ejecutable 7.5
por DDL DIRECTO (alembic multi-head DEFER de la época), por lo que el árbol de
migraciones NO las reproducía (gap detectado P16: en metadata, ausentes en `upgrade head`).
Esta migración captura el DDL exacto de la BD live para que `alembic upgrade head` sobre
una BD vacía reproduzca el esquema completo. NO stamp.

Revision ID: create_audit_accompaniment_tables_001
Revises: add_phase_changed_event_type_001
Create Date: 2026-05-31
"""
from alembic import op

revision = "create_audit_accompaniment_tables_001"
down_revision = "add_phase_changed_event_type_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_accompaniment_state (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            project_id uuid NOT NULL,
            current_state character varying(64) NOT NULL,
            category_branch character varying(16) NOT NULL,
            last_advanced_at timestamp with time zone,
            accompaniment_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone,
            deleted_at timestamp with time zone,
            CONSTRAINT audit_accompaniment_state_pkey PRIMARY KEY (id),
            CONSTRAINT audit_accompaniment_state_project_id_fkey
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_audit_accompaniment_state_project_unique
            ON audit_accompaniment_state USING btree (project_id);
        CREATE INDEX IF NOT EXISTS ix_audit_accompaniment_state_branch
            ON audit_accompaniment_state USING btree (category_branch);

        CREATE TABLE IF NOT EXISTS audit_accompaniment_artifacts (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            project_id uuid NOT NULL,
            state character varying(64) NOT NULL,
            artifact_type character varying(64) NOT NULL,
            file_path text NOT NULL,
            file_size_bytes bigint DEFAULT 0 NOT NULL,
            sha256 character varying(64) NOT NULL,
            uploaded_by character varying(255),
            uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
            artifact_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone,
            deleted_at timestamp with time zone,
            CONSTRAINT audit_accompaniment_artifacts_pkey PRIMARY KEY (id),
            CONSTRAINT audit_accompaniment_artifacts_project_id_fkey
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_audit_accompaniment_artifacts_project_state
            ON audit_accompaniment_artifacts USING btree (project_id, state);
        CREATE INDEX IF NOT EXISTS ix_audit_accompaniment_artifacts_uploaded_at
            ON audit_accompaniment_artifacts USING btree (uploaded_at);

        CREATE TABLE IF NOT EXISTS audit_accompaniment_transitions (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            project_id uuid NOT NULL,
            from_state character varying(64),
            to_state character varying(64) NOT NULL,
            advanced_by character varying(255),
            advanced_at timestamp with time zone DEFAULT now() NOT NULL,
            transition_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone,
            deleted_at timestamp with time zone,
            CONSTRAINT audit_accompaniment_transitions_pkey PRIMARY KEY (id),
            CONSTRAINT audit_accompaniment_transitions_project_id_fkey
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_audit_accompaniment_transitions_project_time
            ON audit_accompaniment_transitions USING btree (project_id, advanced_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_accompaniment_transitions")
    op.execute("DROP TABLE IF EXISTS audit_accompaniment_artifacts")
    op.execute("DROP TABLE IF EXISTS audit_accompaniment_state")
