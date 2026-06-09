"""Sesión 3B-2B.8 CLUSTER 5 Phase 5D delta · chat_admin_reply WhatsApp routing seed.

ADD seed row to whatsapp_critical_events_routing for chat_admin_reply event.
Tiers BASICA=digest · MEDIA=whatsapp · ALTA=whatsapp aligned to existing
m31 seed convention (MB-8 atom 8.2 critical events).

Per-tier route ladder honors cliente preferences when reconciled with
NotificationPreference (Phase 5E future) · MEDIA/ALTA receive realtime
WhatsApp when opt-in active.

Filosofía cliente-mínimo: cliente OPT-IN explicit via M31 OTP flow ·
NO WhatsApp dispatch sin opt-in_at + whatsapp_number en client_users
(dispatch_critical_event enforces skip).

Revision ID: cluster5_chat_whatsapp_routing_001
Revises: cluster5_chat_read_audit_001
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "c5_chat_wa_routing_001"
down_revision: Union[str, None] = "cluster5_chat_read_audit_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO whatsapp_critical_events_routing
            (event_type, tier_basica_route, tier_media_route,
             tier_alta_route, template_es)
        VALUES (
            'chat_admin_reply',
            'digest',
            'whatsapp',
            'whatsapp',
            E'💬 Marcos te respondió en {{ proyecto }}: "{{ preview }}"\n\nResponde en el portal: {{ link }}'
        )
        ON CONFLICT (event_type) DO NOTHING;
        """,
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM whatsapp_critical_events_routing "
        "WHERE event_type = 'chat_admin_reply'",
    )
