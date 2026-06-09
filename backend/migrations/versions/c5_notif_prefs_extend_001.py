"""Sesión 3B-2B.8 CLUSTER 5 Phase 5E delta · NotificationPreference extension.

ADD whatsapp_enabled BOOLEAN + event_opt_outs JSONB columns to
notification_preferences table.

Filosofía:
- whatsapp_enabled defaults FALSE · opt-in explicit cliente via M31 OTP
  flow existing (whatsapp_number + whatsapp_opt_in_at en client_users).
  Esta columna duplica intencionalmente para UI settings independencia ·
  permite cliente disable WhatsApp temporal SIN borrar opt-in M31 row.
- event_opt_outs JSONB key=event_type value=bool · per-event granular
  opt-out. Por defecto vacío {} · NotificationOrchestrator consulta
  event_type IN event_opt_outs.keys() AND event_opt_outs[event_type] is
  TRUE → skip dispatch.

Reconciliation con m31 ClientUser opt-in:
- Si client_users.whatsapp_opt_in_at IS NULL → WhatsApp NUNCA (m31 enforces)
- Si client_users.whatsapp_opt_in_at IS NOT NULL AND
  notification_preferences.whatsapp_enabled = FALSE → cliente desactivó
  WhatsApp temporal · m31 dispatch_critical_event consulta esta col.

Revision ID: c5_notif_prefs_extend_001
Revises: c5_chat_wa_routing_001
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "c5_notif_prefs_extend_001"
down_revision: Union[str, None] = "c5_chat_wa_routing_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "whatsapp_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "notification_preferences",
        sa.Column(
            "event_opt_outs",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_preferences", "event_opt_outs")
    op.drop_column("notification_preferences", "whatsapp_enabled")
