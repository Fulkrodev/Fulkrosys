"""san_c_lucia_federation_tables

Revision ID: sancluciafed01
Revises: sancseed091001
Create Date: 2026-05-05 14:00:00.000000

Crea 2 tablas LUCIA federación CCN-CERT (SAN-C.MB-10.3):

* ``lucia_credentials`` · credenciales OAuth/API por cliente (Fernet at-rest)
* ``lucia_submissions`` · log submissions + status polling

NOTA: la federación LUCIA real requiere acreditación CCN-CERT del cliente
(sector público o entidad esencial NIS2). FULKRO orquesta el flow con
credenciales aportadas por el cliente · NO tiene credenciales propias.
Si el cliente no aporta credenciales, las submissions quedan en estado
``pending_credentials`` con artefacto JSON canónico generable manualmente.

Refs: SAN-C.MB-10.3 · cierra IMPORTANTE-4 SAN-C audit
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "sancluciafed01"
down_revision: Union[str, None] = "sancseed091001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lucia_credentials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id_lucia",
            sa.String(length=100),
            nullable=False,
            comment="ID organización registrada en LUCIA (asignado por CCN-CERT)",
        ),
        sa.Column(
            "client_id_oauth",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "client_secret_encrypted",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted · clave maestra FULKRO_FERNET_KEY",
        ),
        sa.Column(
            "refresh_token_encrypted",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "endpoint_base_url",
            sa.String(length=500),
            nullable=False,
            server_default="https://lucia.ccn-cert.cni.es/api",
        ),
        sa.Column(
            "verified_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Última conexión válida verificada",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            name="uq_lucia_credentials_project",
        ),
    )
    op.create_index(
        "ix_lucia_credentials_project",
        "lucia_credentials",
        ["project_id"],
    )

    op.create_table(
        "lucia_submissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "submission_id_remote",
            sa.String(length=200),
            nullable=True,
            comment="ID asignado por LUCIA tras submit",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending_credentials",
            comment="pending_credentials/pending/sent/acknowledged/closed/error",
        ),
        sa.Column(
            "payload_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "response_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "error_detail",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "submitted_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_status_check",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lucia_submissions_project",
        "lucia_submissions",
        ["project_id"],
    )
    op.create_index(
        "ix_lucia_submissions_status",
        "lucia_submissions",
        ["status"],
    )

    # GRANTs a fulkro_app + fulkro_migrate (mismo pattern que tablas existentes)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON lucia_credentials TO fulkro_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON lucia_submissions TO fulkro_app"
    )

    # RLS project_isolation
    op.execute("ALTER TABLE lucia_credentials ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lucia_credentials FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON lucia_credentials "
        "USING (project_id = current_project_id())"
    )
    op.execute("ALTER TABLE lucia_submissions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lucia_submissions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON lucia_submissions "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON lucia_submissions")
    op.execute("DROP POLICY IF EXISTS project_isolation ON lucia_credentials")
    op.drop_index("ix_lucia_submissions_status", table_name="lucia_submissions")
    op.drop_index("ix_lucia_submissions_project", table_name="lucia_submissions")
    op.drop_table("lucia_submissions")
    op.drop_index("ix_lucia_credentials_project", table_name="lucia_credentials")
    op.drop_table("lucia_credentials")
