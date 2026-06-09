"""Batch A diagnóstico previo · registro DEDICADO de consentimiento del lead.

Append-only ledger del consentimiento del LEAD (interesado pre-contractual) para
el tratamiento de sus datos en el cuestionario de diagnóstico previo.
Base jurídica: interés legítimo art. 6.1.f RGPD (captación en frío).

DEDICADO a propósito (NO reusa ``fulkro_consent_audit_log``, que es de cookies).
Versiona el texto Art. 13 mostrado (``consent_text_version``) → prueba legal de
qué versión vio cada lead.

SIN RLS (espejo ``onboarding_responses``): lo escribe el lead account-less, sin
contexto tenant. El riesgo RLS del flujo account-less de SESIÓN (patrón F-18) se
verifica en Batch B · ver docs/audits/EJECUTABLE_8_BATCH2_FASE0_RECORRIDO_AUDIT.md.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class PreClienteDiagnosticConsent(UUIDPrimaryKeyMixin, Base):
    """Consentimiento del lead para el diagnóstico previo (append-only)."""

    __tablename__ = "precliente_diagnostic_consents"

    # identificador de sesión/lead
    onboarding_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    interlocutor_email: Mapped[str | None] = mapped_column(String(255))
    # versión del texto Art. 13 mostrado (lo que protege legalmente)
    consent_text_version: Mapped[str] = mapped_column(String(20), nullable=False)
    legal_basis: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default="interes_legitimo_art_6_1_f",
    )
    # qué se consintió
    consented: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_scope: Mapped[str | None] = mapped_column(String(80))
    consented_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
