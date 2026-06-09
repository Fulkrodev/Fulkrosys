"""Pydantic schemas in/out · M05 in-portal signing · SAN-E v3.MB-5.2."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateSigningIntentRequest(BaseModel):
    project_id: uuid.UUID
    signable_type: str = Field(..., max_length=40)
    document_hash_sha256: str = Field(..., min_length=64, max_length=64)
    document_id: uuid.UUID | None = None
    signable_ref_id: uuid.UUID | None = None
    signable_ref_type: str | None = Field(None, max_length=50)
    document_version_id: uuid.UUID | None = None
    intent_payload: dict[str, Any] = Field(default_factory=dict)


class SigningIntentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    signable_type: str
    status: str
    requires_step_up_otp: bool
    document_hash_sha256: str
    expires_at: datetime
    created_by_user_id: uuid.UUID
    created_at: datetime


class RequestOtpResponse(BaseModel):
    """Response request-otp · OTP NOT incluido · sent via email out-of-band."""

    otp_sent: bool
    sent_to_email_masked: str
    expires_in_seconds: int
    expires_at: datetime
    # OTP plain code NEVER en response · solo via email


class VerifyOtpRequest(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)


class RejectIntentRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class SignedDocumentResponse(BaseModel):
    intent_id: uuid.UUID
    signature_event_id: uuid.UUID
    signed_at: datetime
    event_hash_sha256: str


class ChainIntegrityResponse(BaseModel):
    project_id: uuid.UUID
    total_signatures: int
    chain_valid: bool
    broken_links: list[dict[str, Any]]


# ════════════════════════════════════════════════════════════════════
# Ejecutable 7.7 · TIER 1 canvas signature schemas
# ════════════════════════════════════════════════════════════════════


class SignCanvasRequest(BaseModel):
    """TIER 1 canvas sign · cliente submit signature image + nombre + apellido.

    NO OTP re-prompt (cliente session already MFA-authenticated portal).
    Field signature_canvas_dataurl debe ser base64 PNG dataurl
    ("data:image/png;base64,...") · captured by react-signature-canvas
    `.toDataURL()`.
    """

    signature_canvas_dataurl: str = Field(
        ...,
        min_length=64,
        max_length=500_000,  # ~375KB base64 == ~280KB binary · empirical canvas typical 5-50KB
        description="Base64 PNG dataurl signature image",
    )
    signed_name: str = Field(..., min_length=1, max_length=120)
    signed_surname: str = Field(..., min_length=1, max_length=120)


class AdminRequestSignatureRequest(BaseModel):
    """Admin trigger signature intent on behalf of cliente."""

    project_id: uuid.UUID
    signable_type: str = Field(..., max_length=40)
    document_hash_sha256: str = Field(..., min_length=64, max_length=64)
    document_id: uuid.UUID | None = None
    signable_ref_id: uuid.UUID | None = None
    signable_ref_type: str | None = Field(None, max_length=50)
    intent_payload: dict[str, Any] = Field(default_factory=dict)
    cliente_user_id: uuid.UUID = Field(
        ...,
        description="Cliente user al que se solicita firma",
    )


class PendingSignatureCard(BaseModel):
    """Cliente vista pendiente de firma · enriched intent info."""

    intent_id: uuid.UUID
    signable_type: str
    signable_label: str
    document_id: uuid.UUID | None = None
    document_hash_sha256: str
    requires_step_up_otp: bool
    expires_at: datetime
    created_at: datetime
    portal_path: str


class PendingSignaturesResponse(BaseModel):
    cliente_user_id: uuid.UUID
    total_pending: int
    pending: list[PendingSignatureCard]


class VerifySignatureResponse(BaseModel):
    intent_id: uuid.UUID
    valid: bool
    event_id: uuid.UUID | None = None
    signed_at: datetime | None = None
    signature_hex_8chars: str | None = None
    event_hash_sha256: str | None = None
    signature_verify: str | None = None
    reason: str | None = None


# ════════════════════════════════════════════════════════════════════
# SAN-E v3.MB-6 atom 0.2 · Cliente firmas hub · history visualization
# ════════════════════════════════════════════════════════════════════


class SignatureCardView(BaseModel):
    """Tarjeta cliente per signable_type · combina intent + signature event."""

    signable_type: str
    signable_label: str  # Human-readable etiqueta cliente-friendly
    intent_id: uuid.UUID | None = None  # NULL si nunca se ha iniciado
    status: str  # pending_creation / pending / otp_required / signed / rejected / expired
    signed_at: datetime | None = None
    signature_event_id: uuid.UUID | None = None
    document_hash_sha256: str | None = None
    event_hash_sha256: str | None = None  # Chain link hash (post-firma)
    chain_position: int | None = None  # 1-indexed posición en chain proyecto
    portal_path: str  # Link al portal flow correspondiente (firmar o ver detalle)


class SigningHistoryClientResponse(BaseModel):
    """Vista cliente firmas hub · history list + chain integrity status."""

    project_id: uuid.UUID
    signatures: list[SignatureCardView]
    chain_valid: bool
    broken_links_count: int
    total_signed: int
    total_expected: int  # Currently 4 (DdA, MAGERIT, Pentest, Conformidad) · expand MB-6
    readiness_snapshot: dict[str, Any] | None = None  # Post-conformidad firma
