"""Re-integration M1 + M12 Magic Link Engine for Acta E-012 signing.

Implements M12-G1. Allows requesting an eIDAS advanced electronic
signature of the Acta E-012 from the Responsable de la Informacion
via magic link.

This module does NOT handle the consume flow (requires frontend).
Only the issuance side: Marcos clicks "Request signature" -> system
generates magic link with scope for the specific acta E-012 ->
returns URL + OTP to send to the signer.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.core import Categorization, System
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkNotFoundError,
)


class SignatureIntegrationError(ValueError):
    """Validation errors in the signature flow."""


def _compute_acta_snapshot_hash(acta_json: dict) -> str:
    """Deterministic SHA-256 hash of the acta in its current state."""
    canonical = json.dumps(
        acta_json, sort_keys=True, separators=(",", ":"),
        default=str, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _load_latest_categorization(
    session: AsyncSession, system_id: uuid.UUID,
) -> Categorization:
    r = await session.execute(
        select(Categorization)
        .where(Categorization.system_id == system_id)
        .where(Categorization.deleted_at.is_(None))
        .order_by(Categorization.created_at.desc())
        .limit(1)
    )
    cat = r.scalar_one_or_none()
    if cat is None:
        raise SignatureIntegrationError(
            f"Sistema {system_id} no tiene categorizacion emitida. "
            "Genera el acta E-012 primero."
        )
    return cat


async def _load_system(session: AsyncSession, system_id: uuid.UUID) -> System:
    r = await session.execute(
        select(System)
        .where(System.id == system_id)
        .where(System.deleted_at.is_(None))
    )
    system = r.scalar_one_or_none()
    if system is None:
        raise SignatureIntegrationError(f"Sistema {system_id} no existe")
    return system


async def request_acta_signature(
    session: AsyncSession,
    system_id: uuid.UUID,
    recipient_email: str,
    recipient_name: str | None,
    recipient_role: str,
    base_url: str | None = None,
) -> dict:
    """Request signature of acta E-012 via magic link.

    Soft idempotency: if signature_magic_link_id already populated,
    revokes previous link and issues a new one (useful for resends).

    base_url: si None, se lee de ``get_settings().app_base_url``.
    """
    if base_url is None:
        base_url = get_settings().app_base_url
    system = await _load_system(session, system_id)
    categorization = await _load_latest_categorization(session, system_id)

    acta_json = categorization.input_snapshot or {
        "system_id": str(system_id),
        "categorization_id": str(categorization.id),
        "categoria_resultante": categorization.categoria_resultante,
    }
    acta_hash = _compute_acta_snapshot_hash(acta_json)

    ml_service = MagicLinkService(session)

    previous_revoked = False
    if categorization.signature_magic_link_id is not None:
        try:
            await ml_service.revoke_magic_link(
                magic_link_id=categorization.signature_magic_link_id,
                reason="superseded_by_new_signature_request",
            )
            previous_revoked = True
        except MagicLinkNotFoundError:
            pass

    request = MagicLinkGenerateRequest(
        project_id=system.project_id,
        purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
        recipient_email=recipient_email,
        scope={
            "document_type": "acta_e012",
            "system_id": str(system_id),
            "categorization_id": str(categorization.id),
            "acta_snapshot_hash": acta_hash,
            "recipient_name": recipient_name,
            "recipient_role": recipient_role,
        },
    )
    link = await ml_service.generate_magic_link(request, base_url)

    categorization.signature_magic_link_id = link.magic_link_id
    await session.flush()

    return {
        "link_id": link.magic_link_id,
        "magic_link_url": link.url,
        "otp": link.otp,
        "expires_at": link.expires_at,
        "recipient_email": recipient_email,
        "previous_link_revoked": previous_revoked,
        "acta_snapshot_hash": acta_hash,
    }


async def get_signature_status(
    session: AsyncSession, system_id: uuid.UUID,
) -> dict:
    """Current status of the acta E-012 signature request."""
    categorization = await _load_latest_categorization(session, system_id)

    if categorization.signature_magic_link_id is None:
        return {
            "system_id": system_id,
            "has_signature_request": False,
        }

    ml_service = MagicLinkService(session)
    try:
        status = await ml_service.get_magic_link_status(
            categorization.signature_magic_link_id,
        )
    except MagicLinkNotFoundError:
        return {
            "system_id": system_id,
            "has_signature_request": False,
        }

    return {
        "system_id": system_id,
        "has_signature_request": True,
        "link_id": uuid.UUID(status["id"]),
        "state": status["status"],
        "issued_at": status.get("created_at"),
        "expires_at": status.get("expires_at"),
        "consumed_at": None,
        "recipient_email": status.get("recipient_email"),
    }
