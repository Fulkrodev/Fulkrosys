"""SAN-E MB-8 atom 8.1 · M31 WhatsApp Business motor tables.

Schema (Q1.B 360dialog + Q3.D opt-in + Q6.A RLS + Q4.C bidirectional):
- client_users · whatsapp_number E.164 + verified_at + opt_in_at + OTP cols
- projects · whatsapp_enabled flag
- whatsapp_threads · 1:1 cliente↔Marcos · same pattern chat_threads ADR-038
- whatsapp_messages · outbound/inbound · provider IDs + delivery tracking
- whatsapp_critical_events_routing · tier matrix BASICA/MEDIA/ALTA per event

RLS por project_id mandatory (Q6.A · ENS audit trail 7 años retention).

Revision ID: sane_mb8_m31_whatsapp_001
Revises: sane_mb7bis_timesheet_001
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "sane_mb8_m31_whatsapp_001"
down_revision = "sane_mb7bis_timesheet_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. client_users extension ───────────────────────────────────
    op.add_column(
        "client_users",
        sa.Column("whatsapp_number", sa.String(20), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "whatsapp_verified_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "whatsapp_opt_in_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.add_column(
        "client_users",
        sa.Column("whatsapp_verification_otp", sa.String(8), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "whatsapp_otp_sent_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )

    # ── 2. projects extension ───────────────────────────────────────
    op.add_column(
        "projects",
        sa.Column(
            "whatsapp_enabled", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )

    # ── 3. whatsapp_threads ─────────────────────────────────────────
    op.create_table(
        "whatsapp_threads",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "last_outbound_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "last_inbound_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("last_message_preview", sa.String(500), nullable=True),
        sa.Column(
            "messages_count", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed')",
            name="ck_whatsapp_threads_status",
        ),
    )
    op.create_index(
        "ix_whatsapp_threads_project_id", "whatsapp_threads", ["project_id"],
    )
    op.create_index(
        "ix_whatsapp_threads_active_inbound",
        "whatsapp_threads", ["status", sa.text("last_inbound_at DESC")],
    )

    op.execute(
        "ALTER TABLE whatsapp_threads ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY whatsapp_threads_isolation ON whatsapp_threads
        FOR ALL TO fulkro_app
        USING (project_id::text = current_setting('app.current_project_id', true))
        WITH CHECK (project_id::text = current_setting('app.current_project_id', true))
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON whatsapp_threads "
        "TO fulkro_app"
    )

    # ── 4. whatsapp_messages ────────────────────────────────────────
    op.create_table(
        "whatsapp_messages",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("whatsapp_message_id", sa.String(120), nullable=True),
        sa.Column(
            "sent_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "delivered_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "direction IN ('outbound', 'inbound')",
            name="ck_whatsapp_messages_direction",
        ),
        sa.CheckConstraint(
            "sender_type IN ('system', 'marcos', 'cliente')",
            name="ck_whatsapp_messages_sender",
        ),
    )
    op.create_index(
        "ix_whatsapp_messages_thread_sent",
        "whatsapp_messages", ["thread_id", sa.text("sent_at DESC")],
    )
    op.create_index(
        "ix_whatsapp_messages_unread_inbound",
        "whatsapp_messages",
        ["thread_id"],
        postgresql_where=sa.text(
            "direction = 'inbound' AND read_at IS NULL"
        ),
    )

    op.execute(
        "ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY whatsapp_messages_isolation ON whatsapp_messages
        FOR ALL TO fulkro_app
        USING (project_id::text = current_setting('app.current_project_id', true))
        WITH CHECK (project_id::text = current_setting('app.current_project_id', true))
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON whatsapp_messages "
        "TO fulkro_app"
    )

    # ── 5. whatsapp_critical_events_routing ─────────────────────────
    op.create_table(
        "whatsapp_critical_events_routing",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_type", sa.String(80), nullable=False, unique=True,
        ),
        sa.Column(
            "tier_basica_route", sa.String(20),
            nullable=False, server_default=sa.text("'digest'"),
        ),
        sa.Column(
            "tier_media_route", sa.String(20),
            nullable=False, server_default=sa.text("'whatsapp'"),
        ),
        sa.Column(
            "tier_alta_route", sa.String(20),
            nullable=False, server_default=sa.text("'whatsapp'"),
        ),
        sa.Column(
            "template_es", sa.Text(), nullable=False,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "tier_basica_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_basica",
        ),
        sa.CheckConstraint(
            "tier_media_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_media",
        ),
        sa.CheckConstraint(
            "tier_alta_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_alta",
        ),
    )
    op.execute(
        "GRANT SELECT ON whatsapp_critical_events_routing TO fulkro_app"
    )

    # Seed 5 critical events + 1 digest template
    op.execute(
        """
        INSERT INTO whatsapp_critical_events_routing
            (event_type, tier_basica_route, tier_media_route, tier_alta_route, template_es)
        VALUES
            (
                'incident_critical_resolved', 'digest', 'whatsapp', 'whatsapp',
                E'✅ Incidente {{ titulo }} resuelto en {{ proyecto }}. Detalles: {{ link }}'
            ),
            (
                'drift_critical_detected', 'digest', 'whatsapp', 'whatsapp',
                E'⚠️ Drift crítico detectado: {{ dim }}. Requiere revisión: {{ link }}'
            ),
            (
                'pentest_authorization_required', 'whatsapp', 'whatsapp', 'whatsapp',
                E'🔒 Autorización pentest pendiente · ventana {{ ventana }}. Firmar: {{ link }}'
            ),
            (
                'dpc_anual_due_30d', 'whatsapp', 'whatsapp', 'whatsapp',
                E'📅 DPC anual vence en 30 días. Iniciar revisión: {{ link }}'
            ),
            (
                'conformidad_signature_pending', 'whatsapp', 'whatsapp', 'whatsapp',
                E'✍️ Firma conformidad ENS pendiente: {{ link }}'
            )
        """
    )


def downgrade() -> None:
    op.drop_table("whatsapp_critical_events_routing")
    op.drop_index(
        "ix_whatsapp_messages_unread_inbound", table_name="whatsapp_messages",
    )
    op.drop_index(
        "ix_whatsapp_messages_thread_sent", table_name="whatsapp_messages",
    )
    op.drop_table("whatsapp_messages")
    op.drop_index(
        "ix_whatsapp_threads_active_inbound", table_name="whatsapp_threads",
    )
    op.drop_index(
        "ix_whatsapp_threads_project_id", table_name="whatsapp_threads",
    )
    op.drop_table("whatsapp_threads")
    op.drop_column("projects", "whatsapp_enabled")
    op.drop_column("client_users", "whatsapp_otp_sent_at")
    op.drop_column("client_users", "whatsapp_verification_otp")
    op.drop_column("client_users", "whatsapp_opt_in_at")
    op.drop_column("client_users", "whatsapp_verified_at")
    op.drop_column("client_users", "whatsapp_number")
