"""providers_extensions_1b71_001 · sub-lote 1.B.7.1.0 (AMEND-014 OPCION C hibrida).

Extiende el motor m14_contracts/providers con 2 tablas nuevas (provider_assessments
+ provider_addendums) para cerrar GAP-CRITICO-8 plan v2 scope OPCION C.

Patron heredado de migration f4b2c8d1e7a3 (m14_providers MB-3.B):
- idempotente (IF NOT EXISTS)
- RLS project_isolation directo (project_id columna nativa)
- GRANT runtime fulkro_app
- Audit trigger fn_audit_track

Tablas nuevas:
- provider_assessments: resultado cuestionario E-601 + decision E-602
- provider_addendums: ADENDA E-604 firmada + tracking MinIO + normativas

NO crea endpoints API en este sub-atom (esperan 1.B.7.1.3 con adenda_generator).
NO crea tabla provider_reviews (diferido a sub-lote 1.B.7.2 si proceda · OPCION C).

Revision ID: providers_extensions_1b71_001
Revises: corpus_norm_ext_1b50_001
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "providers_extensions_1b71_001"
down_revision: Union[str, None] = "corpus_norm_ext_1b50_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea provider_assessments + provider_addendums idempotente."""
    # ------------------------------------------------------------------
    # provider_assessments · resultado cuestionario onboarding (E-601 -> E-602)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_assessments (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            provider_id           uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
            assessment_date       date NOT NULL,
            assessor              text,
            questionnaire_version text NOT NULL DEFAULT 'v1.0',
            responses             jsonb NOT NULL,
            risk_score            real,
            risk_level            varchar(20),
            decision              varchar(20),
            decision_rationale    text,
            valid_until           date,
            created_at            timestamptz NOT NULL DEFAULT now(),
            updated_at            timestamptz,
            deleted_at            timestamptz,
            CONSTRAINT ck_provider_assessments_risk_score
                CHECK (risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 1)),
            CONSTRAINT ck_provider_assessments_risk_level
                CHECK (risk_level IS NULL OR risk_level IN ('CRITICO','ALTO','MEDIO','BAJO')),
            CONSTRAINT ck_provider_assessments_decision
                CHECK (decision IS NULL OR decision IN ('APROBADO','PENDIENTE','RECHAZADO','CONDICIONAL'))
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_provider_assessments_provider "
        "ON provider_assessments (provider_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_provider_assessments_project "
        "ON provider_assessments (project_id);"
    )

    # ------------------------------------------------------------------
    # provider_addendums · ADENDA E-604 firmada + tracking MinIO + normativas
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_addendums (
            id                              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id                      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            provider_id                     uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
            addendum_code                   text NOT NULL,
            contract_ref                    text,
            normativas_cubiertas            jsonb NOT NULL DEFAULT '[]'::jsonb,
            fecha_firma                     date,
            fecha_vigor                     date,
            vencimiento                     date,
            firmado_cliente                 boolean NOT NULL DEFAULT FALSE,
            firmado_proveedor               boolean NOT NULL DEFAULT FALSE,
            minio_object_key                text,
            generated_from_template_code    varchar(20),
            metadata                        jsonb,
            created_at                      timestamptz NOT NULL DEFAULT now(),
            updated_at                      timestamptz,
            deleted_at                      timestamptz,
            CONSTRAINT uq_provider_addendums_project_code
                UNIQUE (project_id, addendum_code)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_provider_addendums_provider "
        "ON provider_addendums (provider_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_provider_addendums_project "
        "ON provider_addendums (project_id);"
    )

    # ------------------------------------------------------------------
    # GRANT runtime fulkro_app
    # ------------------------------------------------------------------
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON provider_assessments TO fulkro_app;"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON provider_addendums TO fulkro_app;"
    )

    # ------------------------------------------------------------------
    # RLS project_isolation directo (project_id columna nativa · igual providers)
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE provider_assessments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE provider_assessments FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS project_isolation ON provider_assessments;
        CREATE POLICY project_isolation ON provider_assessments
            USING (project_id = current_project_id() OR project_id IS NULL);
        """
    )

    op.execute("ALTER TABLE provider_addendums ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE provider_addendums FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS project_isolation ON provider_addendums;
        CREATE POLICY project_isolation ON provider_addendums
            USING (project_id = current_project_id() OR project_id IS NULL);
        """
    )

    # ------------------------------------------------------------------
    # Audit triggers fn_audit_track (definida en migration 8e02b4ed6004 anterior)
    # ------------------------------------------------------------------
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_provider_assessments ON provider_assessments;
        CREATE TRIGGER tg_audit_provider_assessments
            AFTER INSERT OR UPDATE OR DELETE ON provider_assessments
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_provider_addendums ON provider_addendums;
        CREATE TRIGGER tg_audit_provider_addendums
            AFTER INSERT OR UPDATE OR DELETE ON provider_addendums
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_audit_provider_addendums ON provider_addendums;")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_provider_assessments ON provider_assessments;")
    op.execute("DROP POLICY IF EXISTS project_isolation ON provider_addendums;")
    op.execute("DROP POLICY IF EXISTS project_isolation ON provider_assessments;")
    op.execute("DROP INDEX IF EXISTS ix_provider_addendums_project;")
    op.execute("DROP INDEX IF EXISTS ix_provider_addendums_provider;")
    op.execute("DROP TABLE IF EXISTS provider_addendums;")
    op.execute("DROP INDEX IF EXISTS ix_provider_assessments_project;")
    op.execute("DROP INDEX IF EXISTS ix_provider_assessments_provider;")
    op.execute("DROP TABLE IF EXISTS provider_assessments;")
