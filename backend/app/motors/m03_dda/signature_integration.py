"""Re-integration M3 + M12 Magic Link Engine for DdA E-040 RSEG signing.

Implements M3-G2. Allows requesting an eIDAS advanced electronic
signature of the Declaracion de Aplicabilidad (E-040) from the
Responsable de Seguridad (RSEG) via magic link.

Prerequisite: the DdA must be frozen (aprobado_por IS NOT NULL on
all entries, set by POST /dda/projects/{id}/freeze).

Pattern cloned from M-REINT-2 (m02_magerit/signature_integration.py).
"""
from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.ens import DdaEntry, DdaProjectSignature, EnsMeasure
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkNotFoundError,
)


class E040SignatureIntegrationError(ValueError):
    """Validation errors in the E-040 signature flow."""


def _compute_dda_snapshot_hash(
    project_id: uuid.UUID,
    frozen_at: str,
    entries_data: list[dict],
) -> str:
    """Deterministic SHA-256 hash of the complete DdA.

    entries_data must already be sorted by measure_code.
    """
    snapshot = {
        "project_id": str(project_id),
        "frozen_at": frozen_at,
        "total_entries": len(entries_data),
        "entries": entries_data,
    }
    canonical = json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"),
        default=str, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _load_dda_entries_with_codes(
    session: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    """Load DdA entries joined with measure codes, sorted by codigo."""
    r = await session.execute(
        select(
            DdaEntry.id,
            DdaEntry.aplicabilidad,
            DdaEntry.estado_implementacion,
            DdaEntry.justificacion_no_aplica,
            DdaEntry.aprobado_por,
            DdaEntry.fecha_aprobacion,
            EnsMeasure.codigo.label("measure_code"),
        )
        .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
        .where(DdaEntry.project_id == project_id)
        .where(DdaEntry.deleted_at.is_(None))
        .order_by(EnsMeasure.codigo)
    )
    return [dict(row._mapping) for row in r.all()]


async def _check_frozen(entries: list[dict]) -> tuple[bool, str | None]:
    """Check if DdA is frozen (all entries have aprobado_por set).

    Returns (is_frozen, first_fecha_aprobacion as ISO string).
    """
    if not entries:
        return False, None

    frozen_count = sum(1 for e in entries if e.get("aprobado_por"))
    is_frozen = frozen_count == len(entries)

    if is_frozen:
        dates = [str(e["fecha_aprobacion"]) for e in entries if e.get("fecha_aprobacion")]
        frozen_at = min(dates) if dates else None
        return True, frozen_at

    return False, None


async def _get_or_create_sig_state(
    session: AsyncSession, project_id: uuid.UUID,
) -> DdaProjectSignature:
    """Get or create the signature state row for a project."""
    state = await session.get(DdaProjectSignature, project_id)
    if state is None:
        state = DdaProjectSignature(project_id=project_id)
        session.add(state)
        await session.flush()
    return state


async def request_e040_signature(
    session: AsyncSession,
    project_id: uuid.UUID,
    recipient_email: str,
    recipient_name: str | None,
    recipient_role: str,
    base_url: str | None = None,
) -> dict:
    """Request signature of DdA E-040 via magic link.

    Requires the DdA to be frozen (all entries approved).
    Soft idempotency: revokes previous link if one exists.

    base_url: si None, se lee de ``get_settings().app_base_url``.
    """
    if base_url is None:
        base_url = get_settings().app_base_url
    entries = await _load_dda_entries_with_codes(session, project_id)

    if not entries:
        raise E040SignatureIntegrationError(
            f"La DdA del proyecto {project_id} no ha sido generada. "
            "Ejecuta POST /api/v1/dda/generate antes de solicitar firma."
        )

    is_frozen, frozen_at = await _check_frozen(entries)
    if not is_frozen:
        raise E040SignatureIntegrationError(
            f"La DdA del proyecto {project_id} no esta congelada. "
            f"Ejecuta POST /api/v1/dda/projects/{project_id}/freeze antes de solicitar firma."
        )

    entries_for_hash = [
        {
            "measure_code": e["measure_code"],
            "aplicabilidad": e.get("aplicabilidad"),
            "estado_implementacion": e.get("estado_implementacion"),
        }
        for e in entries
    ]
    dda_hash = _compute_dda_snapshot_hash(project_id, frozen_at, entries_for_hash)

    state = await _get_or_create_sig_state(session, project_id)
    ml_service = MagicLinkService(session)

    previous_revoked = False
    if state.signature_magic_link_id is not None:
        try:
            await ml_service.revoke_magic_link(
                magic_link_id=state.signature_magic_link_id,
                reason="superseded_by_new_signature_request",
            )
            previous_revoked = True
        except MagicLinkNotFoundError:
            pass

    request = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
        recipient_email=recipient_email,
        scope={
            "document_type": "dda_e040_rseg",
            "project_id": str(project_id),
            "dda_snapshot_hash": dda_hash,
            "frozen_at": frozen_at,
            "total_entries": len(entries),
            "recipient_name": recipient_name,
            "recipient_role": recipient_role,
        },
    )
    link = await ml_service.generate_magic_link(request, base_url)

    state.signature_magic_link_id = link.magic_link_id
    await session.flush()

    return {
        "link_id": link.magic_link_id,
        "magic_link_url": link.url,
        "otp": link.otp,
        "expires_at": link.expires_at,
        "recipient_email": recipient_email,
        "previous_link_revoked": previous_revoked,
        "dda_snapshot_hash": dda_hash,
        "frozen_at": frozen_at,
        "total_entries": len(entries),
    }


async def get_e040_signature_status(
    session: AsyncSession, project_id: uuid.UUID,
) -> dict:
    """Current status of the E-040 signature request."""
    entries = await _load_dda_entries_with_codes(session, project_id)

    if not entries:
        return {
            "project_id": project_id,
            "has_signature_request": False,
            "is_frozen": False,
            "total_entries": 0,
        }

    is_frozen, _ = await _check_frozen(entries)
    state = await session.get(DdaProjectSignature, project_id)

    if state is None or state.signature_magic_link_id is None:
        return {
            "project_id": project_id,
            "has_signature_request": False,
            "is_frozen": is_frozen,
            "total_entries": len(entries),
        }

    ml_service = MagicLinkService(session)
    try:
        status = await ml_service.get_magic_link_status(
            state.signature_magic_link_id,
        )
    except MagicLinkNotFoundError:
        return {
            "project_id": project_id,
            "has_signature_request": False,
            "is_frozen": is_frozen,
            "total_entries": len(entries),
        }

    return {
        "project_id": project_id,
        "has_signature_request": True,
        "is_frozen": is_frozen,
        "total_entries": len(entries),
        "link_id": uuid.UUID(status["id"]),
        "state": status["status"],
        "issued_at": status.get("created_at"),
        "expires_at": status.get("expires_at"),
        "consumed_at": None,
        "recipient_email": status.get("recipient_email"),
    }
