"""san_e_mb5_signing_intents_events

ADR-020 v5 SAN-E v3.MB-5.2 · in-portal signing service · backend-only.

Replace cliente magic_link signing flow (DEPRECATED MB-4.bis3) con tabla
dedicated signing_intents + signing_events + signing_otp_codes.

3 tablas:
- signing_intents · 1 row per intent firma cliente · per project_id · 11
  signable_types · 6 statuses (state machine) · TTL 48h default.
- signing_events · INMUTABLE log de events (intent_created · otp_sent ·
  otp_verified · signature_generated · rejected · expired) · hash chain
  SHA256 · linked previous_signature_hash · audit trail per project.
- signing_otp_codes · OTP storage para step-up OTP · 6-digit codes ·
  TTL 5min · 5 attempts max (alternativa Redis simplificada · DB ephemeral
  con cleanup via expires_at).

RLS forced per project_id (alinea pattern existing M07/M18/M23/M25).

Ed25519 keypair: process-level (reuse pattern var/keys/ existing m07/m06).
NOTA: keypair NO se almacena en BD para v5 (futura mejora MB-7+ encrypted
admin_secrets storage + rotation). Document hash sha256 binds signature
a cada documento individualmente.

Revision ID: 123920e86153
Revises: 7351107af0ea
Create Date: 2026-05-10 15:04:22.668509
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '123920e86153'
down_revision: Union[str, None] = '7351107af0ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =================================================================
    # signing_intents · 1 row per intent firma cliente
    # =================================================================
    op.create_table(
        "signing_intents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signable_type", sa.String(40), nullable=False),
        sa.Column("signable_ref_id", UUID(as_uuid=True), nullable=True),
        sa.Column("signable_ref_type", sa.String(50), nullable=True),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("document_hash_sha256", sa.String(64), nullable=False),
        sa.Column("document_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "intent_payload", JSONB, nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "requires_step_up_otp", sa.Boolean,
            nullable=False, server_default=sa.false(),
        ),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=False,
        ),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "idx_signing_intents_project_status",
        "signing_intents", ["project_id", "status"],
    )
    op.create_index(
        "idx_signing_intents_signable",
        "signing_intents", ["signable_type", "signable_ref_id"],
    )
    op.create_index(
        "idx_signing_intents_user",
        "signing_intents", ["created_by_user_id"],
    )

    op.execute("""
        ALTER TABLE signing_intents
        ADD CONSTRAINT ck_signing_intents_signable_type
        CHECK (signable_type IN (
            'dda', 'magerit_validation', 'pentest_authorization',
            'conformidad_ens', 'acta_comite', 'retainer_offer',
            'policy_approval', 'incident_close', 'dpc_anual',
            'renewal', 'document_generic'
        ))
    """)
    op.execute("""
        ALTER TABLE signing_intents
        ADD CONSTRAINT ck_signing_intents_status
        CHECK (status IN (
            'pending', 'otp_required', 'otp_verified',
            'signed', 'rejected', 'expired'
        ))
    """)

    # =================================================================
    # signing_events · INMUTABLE log + hash chain
    # =================================================================
    op.create_table(
        "signing_events",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "signing_intent_id", UUID(as_uuid=True),
            sa.ForeignKey("signing_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column(
            "event_payload", JSONB, nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("signature_ed25519", sa.LargeBinary, nullable=True),
        sa.Column("signature_public_key", sa.LargeBinary, nullable=True),
        sa.Column("signature_message", sa.Text, nullable=True),
        sa.Column("previous_signature_hash", sa.String(64), nullable=True),
        sa.Column("event_hash_sha256", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "idx_signing_events_project",
        "signing_events", ["project_id", "created_at"],
    )
    op.create_index(
        "idx_signing_events_intent",
        "signing_events", ["signing_intent_id", "created_at"],
    )
    op.create_index(
        "idx_signing_events_actor",
        "signing_events", ["actor_user_id"],
    )

    op.execute("""
        ALTER TABLE signing_events
        ADD CONSTRAINT ck_signing_events_event_type
        CHECK (event_type IN (
            'intent_created', 'otp_sent', 'otp_verified',
            'signature_generated', 'rejected', 'expired'
        ))
    """)
    op.execute("""
        ALTER TABLE signing_events
        ADD CONSTRAINT ck_signing_events_actor_type
        CHECK (actor_type IN ('client_user', 'system', 'admin'))
    """)

    # =================================================================
    # signing_otp_codes · ephemeral OTP storage step-up
    # =================================================================
    op.create_table(
        "signing_otp_codes",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "signing_intent_id", UUID(as_uuid=True),
            sa.ForeignKey("signing_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code_sha256", sa.String(64), nullable=False),
        sa.Column(
            "attempts", sa.Integer, nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "max_attempts", sa.Integer, nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=False,
        ),
        sa.Column(
            "consumed_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint(
            "signing_intent_id", "user_id",
            name="uq_signing_otp_codes_intent_user",
        ),
    )
    op.create_index(
        "idx_signing_otp_codes_expires",
        "signing_otp_codes", ["expires_at"],
        postgresql_where=sa.text("consumed_at IS NULL"),
    )

    # =================================================================
    # RLS per project_id (alinea pattern M07/M18/M23/M25 · usa
    # current_project_id() PG function existing · NULL = admin bypass)
    # =================================================================
    op.execute("ALTER TABLE signing_intents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signing_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signing_otp_codes ENABLE ROW LEVEL SECURITY")

    # Tenant policies · pattern alineado con client_messages/m07_evidence:
    # admin sin tenant context (current_project_id() IS NULL) bypass · cliente
    # con context project_id-scoped solo ve su project.
    op.execute("""
        CREATE POLICY project_isolation_signing_intents ON signing_intents
        FOR ALL
        USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
        )
        WITH CHECK (
            project_id = current_project_id()
            OR current_project_id() IS NULL
        )
    """)
    op.execute("""
        CREATE POLICY project_isolation_signing_events ON signing_events
        FOR ALL
        USING (
            project_id = current_project_id()
            OR current_project_id() IS NULL
        )
        WITH CHECK (
            project_id = current_project_id()
            OR current_project_id() IS NULL
        )
    """)
    op.execute("""
        CREATE POLICY project_isolation_signing_otp_codes ON signing_otp_codes
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM signing_intents si
                WHERE si.id = signing_otp_codes.signing_intent_id
                  AND (
                      si.project_id = current_project_id()
                      OR current_project_id() IS NULL
                  )
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM signing_intents si
                WHERE si.id = signing_otp_codes.signing_intent_id
                  AND (
                      si.project_id = current_project_id()
                      OR current_project_id() IS NULL
                  )
            )
        )
    """)

    # GRANT runtime user
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON signing_intents TO fulkro_app"
    )
    op.execute(
        # signing_events INMUTABLES · NO update/delete (audit trail)
        "GRANT SELECT, INSERT ON signing_events TO fulkro_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON signing_otp_codes TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_otp_codes ON signing_otp_codes"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_events ON signing_events"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation_signing_intents ON signing_intents"
    )
    op.drop_table("signing_otp_codes")
    op.drop_table("signing_events")
    op.drop_table("signing_intents")
