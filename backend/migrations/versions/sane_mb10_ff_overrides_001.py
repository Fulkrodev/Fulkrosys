"""MB-10 Atom 10.2.A · feature_flag_overrides table + RLS + indexes (ADR-046).

Materializa ADR-036 deferred ``feature_flag_overrides`` AHORA (estaba
diferido a MB-19+ pero MB-10 Atom 10.2 lo adelanta per ADR-046).

ADR-046 (renamed post-audit B1.2 · was ADR-037 MB-10) architecturally unifies:
M32 in ISMS docs = LOGICAL motor concept
terminology · implementation lives in ``backend/app/core/feature_flags/``
· NO separate ``m32_capabilities/`` motor (avoid 2 paralelos divergence).

Schema feature_flag_overrides:
  - FullMixin (UUID PK + created_at + updated_at + deleted_at)
  - project_id UUID FK projects (nullable) · project-level override
  - client_id UUID FK clients (nullable) · tenant-wide override
  - feature_key VARCHAR(120) · target catalog feature
  - override_value JSONB · boolean OR complex value
  - granted_at TIMESTAMPTZ NOT NULL · business semantic
  - expires_at TIMESTAMPTZ NULLABLE · natural expiry filter
  - granted_by_user_id UUID FK auth_users NULLABLE · audit actor
  - revoked_at TIMESTAMPTZ NULLABLE · soft delete business
  - revoked_by_user_id UUID FK auth_users NULLABLE · audit actor
  - reason TEXT NULLABLE · justification grant/revoke

CHECK constraints:
  - scope_required: project_id OR client_id NOT NULL (al menos uno)
  - revoke_actor: revoked_at implica revoked_by_user_id

Indexes (OPS-040 canonical):
  - ix_feature_flag_overrides_project_feature (project_id, feature_key)
  - ix_feature_flag_overrides_client_feature (client_id, feature_key)
  - ix_feature_flag_overrides_active partial (revoked_at IS NULL AND
    deleted_at IS NULL) — hot path resolve

RLS:
  - OPS-054 sostained: ALTER OWNER TO fulkro_migrate pre-ENABLE RLS
    (fulkro_app es miembro fulkro → bypass si owner=fulkro; cambiar
    a fulkro_migrate restaura filtrado correcto · pattern email_log).
  - ENABLE + FORCE ROW LEVEL SECURITY (defense-in-depth admin too)
  - Policy USING: client_id matching current_client_id() OR project_id
    IN (SELECT FROM projects matching cliente) OR admin context
    (current_client_id() IS NULL allows admin/cron bypass).
  - GRANT CRUD a fulkro_app post-enable (consistent pattern).

Audit triggers:
  - tg_audit_feature_flag_overrides via fn_audit_track() shared canon
    (hash chain inmutable per audit_log_hash_chain_trigger 4f8b2a90001).

Revision ID: sane_mb10_ff_overrides_001
Revises: sane_polish_rls_email_log_001
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "sane_mb10_ff_overrides_001"
down_revision = "sane_polish_rls_email_log_001"
branch_labels = None
depends_on = None


def _full_mixin_cols():
    """Helper FullMixin (UUID PK + timestamps + soft_delete).

    Idéntico a M29/M30 _full_mixin_cols() · pattern shared 14+ tablas.
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
    # 1. feature_flag_overrides table
    # ====================================================================
    op.create_table(
        "feature_flag_overrides",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("feature_key", sa.String(120), nullable=False),
        sa.Column(
            "override_value", postgresql.JSONB(), nullable=False,
        ),
        sa.Column(
            "granted_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "expires_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "granted_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "revoked_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "project_id IS NOT NULL OR client_id IS NOT NULL",
            name="ck_feature_flag_overrides_scope_required",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_by_user_id IS NOT NULL",
            name="ck_feature_flag_overrides_revoke_actor",
        ),
    )

    # ====================================================================
    # 2. Indexes (OPS-040 canonical)
    # ====================================================================
    op.create_index(
        "ix_feature_flag_overrides_project_feature",
        "feature_flag_overrides",
        ["project_id", "feature_key"],
    )
    op.create_index(
        "ix_feature_flag_overrides_client_feature",
        "feature_flag_overrides",
        ["client_id", "feature_key"],
    )
    op.create_index(
        "ix_feature_flag_overrides_active",
        "feature_flag_overrides",
        ["feature_key"],
        postgresql_where=sa.text(
            "revoked_at IS NULL AND deleted_at IS NULL"
        ),
    )

    # ====================================================================
    # 3. RLS — tenant_isolation policy (OPS-041 + OPS-054)
    # ====================================================================
    # OPS-054 sostained: cambiar owner a fulkro_migrate antes ENABLE RLS
    # (fulkro_app es miembro fulkro → bypass herencia · pattern email_log
    # sane_polish_rls_email_log_001 + alert_queue MB-9).
    op.execute(
        "ALTER TABLE feature_flag_overrides OWNER TO fulkro_migrate"
    )
    op.execute(
        "ALTER TABLE feature_flag_overrides ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE feature_flag_overrides FORCE ROW LEVEL SECURITY"
    )
    # Policy: cliente pool ve solo overrides de su tenant (client_id
    # matching OR project_id de sus proyectos). Admin (current_client_id()
    # IS NULL) bypassa per pattern existing email_log/messaging.
    op.execute(
        """
        CREATE POLICY feature_flag_overrides_tenant_isolation
        ON feature_flag_overrides
        FOR ALL TO fulkro_app
        USING (
            current_client_id() IS NULL
            OR client_id = current_client_id()
            OR project_id IN (
                SELECT id FROM projects
                WHERE client_id = current_client_id()
            )
        )
        WITH CHECK (
            current_client_id() IS NULL
            OR client_id = current_client_id()
            OR project_id IN (
                SELECT id FROM projects
                WHERE client_id = current_client_id()
            )
        )
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON feature_flag_overrides TO fulkro_app"
    )

    # ====================================================================
    # 4. Audit trigger (fn_audit_track shared canon)
    # ====================================================================
    op.execute(
        "CREATE TRIGGER tg_audit_feature_flag_overrides "
        "AFTER INSERT OR UPDATE OR DELETE ON feature_flag_overrides "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_feature_flag_overrides "
        "ON feature_flag_overrides"
    )
    op.execute(
        "DROP POLICY IF EXISTS feature_flag_overrides_tenant_isolation "
        "ON feature_flag_overrides"
    )
    op.execute(
        "ALTER TABLE feature_flag_overrides "
        "DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_feature_flag_overrides_active",
        table_name="feature_flag_overrides",
    )
    op.drop_index(
        "ix_feature_flag_overrides_client_feature",
        table_name="feature_flag_overrides",
    )
    op.drop_index(
        "ix_feature_flag_overrides_project_feature",
        table_name="feature_flag_overrides",
    )
    op.drop_table("feature_flag_overrides")
