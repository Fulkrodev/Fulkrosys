"""m30: client_contacts + client_contact_interactions tables (FASE 5.5.A).

Revision ID: f4a8c7b1d2e3
Revises: 8e02b4ed6004
Create Date: 2026-04-29 16:30:00.000000

Motor 30 — Client Contacts. Catálogo contactos profesionales por cliente
(distinto de ``ClientUser`` portal). Plan v4.2 FASE 5.5.A.

Decisiones audit pre-impl 2026-04-29:
  - H1 ``magic_links.sent_to_contact_id`` FK diferido
    (TODO-M30-M12-INTEGRATION-001 BAJA · post-deploy).
  - H2 plan inline DDL aplicado (sin ADR-012 doc accesible).
  - R4 RLS ``USING (true)`` permissive + RBAC ``require_owner`` API-side
    (M30 admin-only; sin scope tenant per-row porque sólo Marcos accede).

Schema:
  - ``client_contacts`` (FullMixin + 18 cols negocio) + UniqueConstraint
    (client_id, email) + Index (client_id, is_active) + GIN search sobre
    ``notes_marcos``.
  - ``client_contact_interactions`` (FullMixin + 5 cols) + Index DESC
    (contact_id, created_at).
  - 2 triggers ``tg_audit_*`` siguiendo pattern fn_audit_track existente
    (12 tablas usan pattern hoy + admin_settings añadida 4.A.2.d).

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate`` (Alembic
default no detecta triggers + GIN op_classes, evita re-derivar drift
cross-motor 380+ ops). Conserva SOLO operaciones M30.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f4a8c7b1d2e3"
down_revision: Union[str, None] = "8e02b4ed6004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _full_mixin_cols():
    """Helper FullMixin (UUID PK + timestamps + soft_delete).

    Idéntico a ``COMMON_COLS()`` de migrations m22 / m21 — extraído
    aquí para mantener M30 self-contained.
    """
    return [
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    # ====================================================================
    # 1. client_contacts
    # ====================================================================
    op.create_table(
        "client_contacts",
        *_full_mixin_cols(),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Identidad
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("preferred_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        # Rol
        sa.Column("role_title", sa.String(150), nullable=False),
        sa.Column("role_category", sa.String(50), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "is_signatory", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "has_portal_access", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "client_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Notas + preferencias
        sa.Column("notes_marcos", sa.Text(), nullable=True),
        sa.Column(
            "preferred_communication", sa.String(20), nullable=True,
        ),
        sa.Column(
            "timezone", sa.String(50),
            nullable=False, server_default="Europe/Madrid",
        ),
        # Estado
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column("inactive_reason", sa.String(200), nullable=True),
        sa.Column(
            "inactive_since", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        # Auditoría aplicación
        sa.Column(
            "created_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "client_id", "email",
            name="uq_client_contacts_client_email",
        ),
    )
    op.create_index(
        "ix_client_contacts_client_active",
        "client_contacts",
        ["client_id", "is_active"],
    )
    # GIN full-text search en notas_marcos (búsqueda libre Marcos).
    op.execute(
        "CREATE INDEX ix_client_contacts_notes_fts "
        "ON client_contacts "
        "USING gin (to_tsvector('spanish', coalesce(notes_marcos, '')))"
    )

    # ====================================================================
    # 2. client_contact_interactions
    # ====================================================================
    op.create_table(
        "client_contact_interactions",
        *_full_mixin_cols(),
        sa.Column(
            "contact_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("interaction_type", sa.String(40), nullable=False),
        sa.Column("source_motor", sa.String(20), nullable=True),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True), nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_client_contact_interactions_contact_created_desc",
        "client_contact_interactions",
        ["contact_id", "created_at"],
    )

    # ====================================================================
    # 3. RLS — USING (true) permissive
    # ====================================================================
    # M30 es admin-only por diseño (RBAC.D commit b5ae36f require_owner
    # router-level). Habilitamos RLS para consistencia con las demás
    # tablas (fulkro_app NOSUPERUSER asume RLS enabled) — política
    # ``USING (true)`` permite acceso completo a Marcos y NO requiere
    # current_client_id() helper greenfield.
    for table in ("client_contacts", "client_contact_interactions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY admin_all ON {table} "
            f"USING (true) WITH CHECK (true)"
        )

    # ====================================================================
    # 4. Audit triggers (pattern fn_audit_track + tg_audit_<table>)
    # ====================================================================
    # fn_audit_track existe desde S1-S2 (12 tablas la usan). Patrón
    # canónico FULKRO documentado en migración 8e02b4ed6004
    # (admin_settings 4.A.2.d).
    for table in ("client_contacts", "client_contact_interactions"):
        op.execute(
            f"CREATE TRIGGER tg_audit_{table} "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
        )


def downgrade() -> None:
    # Triggers (fn_audit_track NO se toca — compartida 12+ tablas)
    for table in ("client_contact_interactions", "client_contacts"):
        op.execute(f"DROP TRIGGER IF EXISTS tg_audit_{table} ON {table}")

    # RLS policies + DISABLE
    for table in ("client_contact_interactions", "client_contacts"):
        op.execute(f"DROP POLICY IF EXISTS admin_all ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Indexes + tablas
    op.drop_index(
        "ix_client_contact_interactions_contact_created_desc",
        table_name="client_contact_interactions",
    )
    op.drop_table("client_contact_interactions")

    op.execute("DROP INDEX IF EXISTS ix_client_contacts_notes_fts")
    op.drop_index(
        "ix_client_contacts_client_active",
        table_name="client_contacts",
    )
    op.drop_table("client_contacts")
