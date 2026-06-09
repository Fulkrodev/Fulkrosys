"""Re-integration M2 + M12 Magic Link Engine for Informe E-028 MAGERIT signing.

Implements M12-G2. Allows requesting an eIDAS advanced electronic
signature of the MAGERIT risk analysis report (E-028) from the
Responsable del Sistema via magic link.

Prerequisite: the analysis must be frozen (snapshot_frozen_at IS NOT NULL).
A draft analysis cannot be signed -- the spec is explicit: freeze =
immutable snapshot for client delivery.

Pattern identical to M-REINT-1 (m01_categorization/signature_integration.py).
"""
from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.motors.m02_magerit.models import MageritAnalysis
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkNotFoundError,
)


class E028SignatureIntegrationError(ValueError):
    """Validation errors in the E-028 signature flow."""


def _compute_report_snapshot_hash(frozen_snapshot: dict) -> str:
    """Deterministic SHA-256 hash of the frozen MAGERIT report."""
    canonical = json.dumps(
        frozen_snapshot, sort_keys=True, separators=(",", ":"),
        default=str, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _load_analysis(session: AsyncSession, analysis_id: uuid.UUID) -> MageritAnalysis:
    analysis = await session.get(MageritAnalysis, analysis_id)
    if analysis is None or analysis.deleted_at is not None:
        raise E028SignatureIntegrationError(
            f"Analisis MAGERIT {analysis_id} no existe"
        )
    return analysis


async def request_e028_signature(
    session: AsyncSession,
    analysis_id: uuid.UUID,
    recipient_email: str,
    recipient_name: str | None,
    recipient_role: str,
    base_url: str | None = None,
) -> dict:
    """Request signature of Informe E-028 via magic link.

    Requires the analysis to be frozen. Soft idempotency: revokes
    previous link if one exists.

    base_url: si None, se lee de ``get_settings().app_base_url``.
    """
    if base_url is None:
        base_url = get_settings().app_base_url
    analysis = await _load_analysis(session, analysis_id)

    if analysis.snapshot_frozen_at is None:
        raise E028SignatureIntegrationError(
            f"El analisis {analysis_id} no esta congelado. "
            f"Ejecuta POST /api/v1/magerit/analysis/{analysis_id}/freeze "
            "antes de solicitar firma."
        )
    if not analysis.result_snapshot:
        raise E028SignatureIntegrationError(
            f"El analisis {analysis_id} esta marcado como frozen pero "
            "no tiene snapshot. Estado inconsistente."
        )

    report_hash = _compute_report_snapshot_hash(analysis.result_snapshot)

    ml_service = MagicLinkService(session)

    previous_revoked = False
    if analysis.signature_magic_link_id is not None:
        try:
            await ml_service.revoke_magic_link(
                magic_link_id=analysis.signature_magic_link_id,
                reason="superseded_by_new_signature_request",
            )
            previous_revoked = True
        except MagicLinkNotFoundError:
            pass

    request = MagicLinkGenerateRequest(
        project_id=analysis.project_id,
        purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
        recipient_email=recipient_email,
        scope={
            "document_type": "informe_e028_magerit",
            "analysis_id": str(analysis_id),
            "project_id": str(analysis.project_id),
            "report_snapshot_hash": report_hash,
            "frozen_at": analysis.snapshot_frozen_at.isoformat(),
            "recipient_name": recipient_name,
            "recipient_role": recipient_role,
        },
    )
    link = await ml_service.generate_magic_link(request, base_url)

    analysis.signature_magic_link_id = link.magic_link_id
    await session.flush()

    return {
        "link_id": link.magic_link_id,
        "magic_link_url": link.url,
        "otp": link.otp,
        "expires_at": link.expires_at,
        "recipient_email": recipient_email,
        "previous_link_revoked": previous_revoked,
        "report_snapshot_hash": report_hash,
        "frozen_at": analysis.snapshot_frozen_at,
    }


async def get_e028_signature_status(
    session: AsyncSession, analysis_id: uuid.UUID,
) -> dict:
    """Current status of the E-028 signature request."""
    analysis = await _load_analysis(session, analysis_id)

    is_frozen = analysis.snapshot_frozen_at is not None

    if analysis.signature_magic_link_id is None:
        return {
            "analysis_id": analysis_id,
            "has_signature_request": False,
            "is_frozen": is_frozen,
        }

    ml_service = MagicLinkService(session)
    try:
        status = await ml_service.get_magic_link_status(
            analysis.signature_magic_link_id,
        )
    except MagicLinkNotFoundError:
        return {
            "analysis_id": analysis_id,
            "has_signature_request": False,
            "is_frozen": is_frozen,
        }

    return {
        "analysis_id": analysis_id,
        "has_signature_request": True,
        "is_frozen": is_frozen,
        "link_id": uuid.UUID(status["id"]),
        "state": status["status"],
        "issued_at": status.get("created_at"),
        "expires_at": status.get("expires_at"),
        "consumed_at": None,
        "recipient_email": status.get("recipient_email"),
    }
