"""audit_log hash chain trigger + append-only enforcement + tracked tables

Adds:
- ``seq BIGSERIAL UNIQUE`` column on ``audit_log`` for deterministic ordering.
- ``fn_audit_log_hash_chain()`` trigger that computes ``hash_current = sha256(prev || fields)``
  on INSERT.
- ``fn_audit_log_immutable()`` trigger that rejects UPDATE/DELETE on ``audit_log``.
- ``fn_audit_track()`` generic AFTER INSERT/UPDATE/DELETE trigger attached to 13
  business-critical tables (evidence, documents, contracts, invoices, projects,
  clients, categorizations, dda_entries, obligations, magerit_analysis,
  audit_findings, pentest_findings, document_versions).
- ``fn_audit_log_verify_chain()`` function for integrity verification.

Revision ID: d4f8b2a90001
Revises: c3e9b7d2a841
Create Date: 2026-04-20 16:05:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4f8b2a90001"
down_revision: Union[str, None] = "c3e9b7d2a841"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRACKED_TABLES = [
    "evidence",
    "documents",
    "document_versions",
    "contracts",
    "invoices",
    "projects",
    "clients",
    "categorizations",
    "dda_entries",
    "obligations",
    "magerit_analysis",
    "audit_findings",
    "pentest_findings",
]


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE audit_log
        ADD COLUMN IF NOT EXISTS seq BIGSERIAL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_audit_log_seq_unique ON audit_log (seq);
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_log_hash_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_hash TEXT;
            payload   TEXT;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtext('audit_log_chain'));
            SELECT hash_current INTO last_hash
              FROM audit_log
              WHERE seq = (SELECT MAX(seq) FROM audit_log WHERE seq < NEW.seq);
            NEW.hash_prev := last_hash;
            payload := COALESCE(last_hash, '') || '|' ||
                       NEW.tabla || '|' ||
                       NEW.registro_id::text || '|' ||
                       NEW.accion || '|' ||
                       COALESCE(NEW.usuario, '') || '|' ||
                       NEW.timestamp::text || '|' ||
                       COALESCE(NEW.payload_old::text, '') || '|' ||
                       COALESCE(NEW.payload_new::text, '');
            NEW.hash_current := encode(digest(payload, 'sha256'), 'hex');
            RETURN NEW;
        END;
        $fn$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_hash_chain ON audit_log;")
    op.execute(
        """
        CREATE TRIGGER tg_audit_log_hash_chain
        BEFORE INSERT ON audit_log
        FOR EACH ROW EXECUTE FUNCTION fn_audit_log_hash_chain();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_log_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only; % not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $fn$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_no_update ON audit_log;")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_no_delete ON audit_log;")
    op.execute(
        """
        CREATE TRIGGER tg_audit_log_no_update
        BEFORE UPDATE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION fn_audit_log_immutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_audit_log_no_delete
        BEFORE DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION fn_audit_log_immutable();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_track() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            usr TEXT;
            rid UUID;
        BEGIN
            BEGIN
                usr := current_setting('app.current_user', true);
            EXCEPTION WHEN others THEN
                usr := session_user;
            END;
            IF TG_OP = 'DELETE' THEN
                rid := (to_jsonb(OLD)->>'id')::uuid;
                INSERT INTO audit_log (tabla, registro_id, accion, usuario, payload_old, payload_new)
                VALUES (TG_TABLE_NAME, rid, TG_OP, usr, to_jsonb(OLD), NULL);
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                rid := (to_jsonb(NEW)->>'id')::uuid;
                INSERT INTO audit_log (tabla, registro_id, accion, usuario, payload_old, payload_new)
                VALUES (TG_TABLE_NAME, rid, TG_OP, usr, to_jsonb(OLD), to_jsonb(NEW));
                RETURN NEW;
            ELSE
                rid := (to_jsonb(NEW)->>'id')::uuid;
                INSERT INTO audit_log (tabla, registro_id, accion, usuario, payload_old, payload_new)
                VALUES (TG_TABLE_NAME, rid, TG_OP, usr, NULL, to_jsonb(NEW));
                RETURN NEW;
            END IF;
        END;
        $fn$;
        """
    )
    for tbl in TRACKED_TABLES:
        op.execute(
            f"""
            DO $do$
            BEGIN
              IF EXISTS (SELECT 1 FROM information_schema.tables
                         WHERE table_schema='public' AND table_name='{tbl}') THEN
                EXECUTE 'DROP TRIGGER IF EXISTS tg_audit_{tbl} ON {tbl}';
                EXECUTE 'CREATE TRIGGER tg_audit_{tbl}
                         AFTER INSERT OR UPDATE OR DELETE ON {tbl}
                         FOR EACH ROW EXECUTE FUNCTION fn_audit_track()';
              END IF;
            END
            $do$;
            """
        )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_audit_log_verify_chain(
            OUT total BIGINT,
            OUT first_bad_seq BIGINT,
            OUT ok BOOLEAN
        )
        LANGUAGE plpgsql AS $fn$
        DECLARE
            r RECORD;
            prev_hash TEXT := NULL;
            expected TEXT;
            payload TEXT;
        BEGIN
            total := 0;
            first_bad_seq := NULL;
            ok := TRUE;
            FOR r IN SELECT * FROM audit_log ORDER BY seq LOOP
                total := total + 1;
                payload := COALESCE(prev_hash, '') || '|' ||
                           r.tabla || '|' ||
                           r.registro_id::text || '|' ||
                           r.accion || '|' ||
                           COALESCE(r.usuario, '') || '|' ||
                           r.timestamp::text || '|' ||
                           COALESCE(r.payload_old::text, '') || '|' ||
                           COALESCE(r.payload_new::text, '');
                expected := encode(digest(payload, 'sha256'), 'hex');
                IF r.hash_current IS DISTINCT FROM expected
                   OR r.hash_prev IS DISTINCT FROM prev_hash THEN
                    ok := FALSE;
                    first_bad_seq := r.seq;
                    RETURN;
                END IF;
                prev_hash := r.hash_current;
            END LOOP;
            RETURN;
        END;
        $fn$;
        """
    )


def downgrade() -> None:
    for tbl in TRACKED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS tg_audit_{tbl} ON {tbl};")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_no_delete ON audit_log;")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_no_update ON audit_log;")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_log_hash_chain ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_log_verify_chain();")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_track();")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_log_immutable();")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_log_hash_chain();")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_seq_unique;")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS seq;")
