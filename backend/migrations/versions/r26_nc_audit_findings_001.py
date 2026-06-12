"""r26_nc_audit_findings_001 · R26 · promover NC E-321/E-322 a modelo estructurado

Promueve las No Conformidades de auditoría externa (E-321 auditorías / E-322
hallazgos NC), hoy sólo JSONB en ``live_records``, a la proyección estructurada
``audit_sessions`` + ``audit_findings`` (severidad + PAC + plazos consultables).
El JSONB sigue siendo la fuente WORM; ``audit_findings`` es la proyección
derivada (re-ejecutable, upsert idempotente).

Reusa modelos existentes (OPS-026 · NO modelo nuevo):
- ``audit_sessions`` (ya RLS project-scoped) + columna ``codigo_externo`` para
  upsert idempotente desde E-321.
- ``audit_findings`` (modelo existente, sin uso previo en código) extendido con
  los campos de la NC + su acción correctiva (PAC) en línea. NO se toca
  ``remediation_plans`` (tabla compartida por A21, sin RLS · evitar regresión).

RLS: ``audit_findings`` no tenía RLS. Se habilita con el patrón child 1-level
(EXISTS via ``audit_sessions.project_id = current_project_id()``), espejo de
``sub_atom_5b_magerit_child_rls_001``. Fail-closed (sin contexto → 0 filas).
Bypass admin por ATRIBUTO de rol ``fulkro_app_bypassrls`` (no policy permisiva).

ADDITIVE · DB-safe (columnas nuevas nullable · audit_findings sin filas previas).

Revision ID: r26_nc_audit_findings_001
Revises: r26_conformity_cert_documents_001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r26_nc_audit_findings_001"
down_revision: Union[str, None] = "r26_conformity_cert_documents_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # E-321 → audit_sessions: clave para upsert idempotente.
    op.add_column(
        "audit_sessions",
        sa.Column("codigo_externo", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_audit_sessions_project_codigo_externo",
        "audit_sessions", ["project_id", "codigo_externo"],
    )

    # E-322 → audit_findings: NC + PAC en línea (proyección estructurada).
    op.add_column(
        "audit_findings",
        sa.Column("codigo_externo", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "audit_findings", sa.Column("estado", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "audit_findings", sa.Column("accion_correctiva", sa.Text(), nullable=True),
    )
    op.add_column(
        "audit_findings", sa.Column("responsable", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "audit_findings", sa.Column("fecha_compromiso", sa.Date(), nullable=True),
    )
    op.add_column(
        "audit_findings", sa.Column("fecha_cierre", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_audit_findings_session_codigo",
        "audit_findings", ["audit_session_id", "codigo_externo"],
    )

    # RLS child 1-level via audit_sessions.project_id (espejo magerit child).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON audit_findings "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute("ALTER TABLE audit_findings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_findings FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON audit_findings USING ("
        "EXISTS (SELECT 1 FROM audit_sessions s "
        "WHERE s.id = audit_findings.audit_session_id "
        "AND s.project_id = current_project_id()))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON audit_findings")
    op.execute("ALTER TABLE audit_findings DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_audit_findings_session_codigo", table_name="audit_findings")
    op.drop_column("audit_findings", "fecha_cierre")
    op.drop_column("audit_findings", "fecha_compromiso")
    op.drop_column("audit_findings", "responsable")
    op.drop_column("audit_findings", "accion_correctiva")
    op.drop_column("audit_findings", "estado")
    op.drop_column("audit_findings", "codigo_externo")
    op.drop_index(
        "ix_audit_sessions_project_codigo_externo", table_name="audit_sessions",
    )
    op.drop_column("audit_sessions", "codigo_externo")
