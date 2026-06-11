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
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.core import Categorization, System
from backend.app.motors.m05_signing.service import SigningService
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkNotFoundError,
)

# R03 · autoridades competentes de la categorización (art. 40.2 + art. 11 RD 311/2022):
# el Responsable de la Información y el Responsable del Servicio APRUEBAN el acta E-012.
# El acta sólo se considera aprobada cuando constan AMBAS firmas (doble firma).
_ACTA_SIGNER_ROLES: tuple[str, ...] = (
    "responsable_informacion",
    "responsable_servicio",
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


# ----------------------------------------------------------------------------
# R03 · DOBLE FIRMA competente del acta E-012 (RInfo + RServ · art. 40.2)
# Reutiliza m05 (Ed25519 + hash chain R6) · sin tabla nueva · estado derivado de
# los signing_intents (signable_ref_id = categorization.id).
# ----------------------------------------------------------------------------

def _payload_as_dict(payload) -> dict:
    """``intent_payload`` JSONB → dict (asyncpg lo devuelve como str en raw SQL)."""
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return {}


async def _resolve_acta_signers(
    session: AsyncSession, project_id: uuid.UUID,
) -> dict[str, dict]:
    """RInfo + RServ → client_user (project_role_assignments + m30 client_contacts).

    Sólo incluye los roles con contacto asignado y acceso al portal (client_user_id).
    """
    rows = (await session.execute(
        sa_text(
            "SELECT pra.role_code, pra.contact_id, cc.client_user_id, "
            "  cc.full_name, cc.email "
            "FROM project_role_assignments pra "
            "JOIN client_contacts cc ON cc.id = pra.contact_id "
            "WHERE pra.project_id = :pid AND pra.deleted_at IS NULL "
            "  AND cc.deleted_at IS NULL "
            "  AND pra.role_code IN ('responsable_informacion', 'responsable_servicio')"
        ),
        {"pid": str(project_id)},
    )).mappings().all()
    return {
        r["role_code"]: {
            "client_user_id": r["client_user_id"],
            "full_name": r["full_name"],
            "email": r["email"],
            "contact_id": r["contact_id"],
        }
        for r in rows
    }


async def _existing_acta_intents(
    session: AsyncSession, categorization_id: uuid.UUID,
) -> dict[str, dict]:
    """signing_intents del acta E-012 existentes, indexados por role_code."""
    rows = (await session.execute(
        sa_text(
            "SELECT id, intent_payload, status, created_by_user_id "
            "FROM signing_intents "
            "WHERE signable_ref_id = :rid AND signable_ref_type = 'categorization' "
            "  AND signable_type = 'acta_comite'"
        ),
        {"rid": str(categorization_id)},
    )).mappings().all()
    out: dict[str, dict] = {}
    for r in rows:
        role = _payload_as_dict(r["intent_payload"]).get("role_code")
        if role:
            out[role] = dict(r)
    return out


async def request_acta_double_signature(
    session: AsyncSession,
    system_id: uuid.UUID,
) -> dict:
    """Solicita la DOBLE firma competente del acta E-012 (R03).

    Crea de forma idempotente dos signing_intents m05 ``acta_comite`` —uno para el
    Responsable de la Información y otro para el Responsable del Servicio— ambos
    vinculados al mismo hash del acta (freeze) y a la misma categorización. El acta
    se aprueba sólo cuando AMBOS firman (gate en get_acta_double_signature_status).
    """
    system = await _load_system(session, system_id)
    categorization = await _load_latest_categorization(session, system_id)

    acta_json = categorization.input_snapshot or {
        "system_id": str(system_id),
        "categorization_id": str(categorization.id),
        "categoria_resultante": categorization.categoria_resultante,
    }
    acta_hash = _compute_acta_snapshot_hash(acta_json)

    signers = await _resolve_acta_signers(session, system.project_id)
    legibles = {
        "responsable_informacion": "Responsable de la Información",
        "responsable_servicio": "Responsable del Servicio",
    }
    faltan = [
        legibles[role] for role in _ACTA_SIGNER_ROLES
        if not signers.get(role) or not signers[role]["client_user_id"]
    ]
    if faltan:
        raise SignatureIntegrationError(
            "No se puede solicitar la doble firma del acta E-012: falta asignar y dar "
            f"acceso al portal a: {', '.join(faltan)}. La categorización (art. 40.2 RD "
            "311/2022) requiere la aprobación competente de ambos roles."
        )

    existing = await _existing_acta_intents(session, categorization.id)
    svc = SigningService(session)
    result_roles: dict[str, dict] = {}
    for role_code in _ACTA_SIGNER_ROLES:
        prev = existing.get(role_code)
        if prev and prev["status"] not in ("rejected", "expired"):
            result_roles[role_code] = {
                "intent_id": prev["id"], "status": prev["status"], "reused": True,
            }
            continue
        s = signers[role_code]
        intent = await svc.create_intent(
            project_id=system.project_id,
            signable_type="acta_comite",
            document_hash_sha256=acta_hash,
            created_by_user_id=s["client_user_id"],
            signable_ref_id=categorization.id,
            signable_ref_type="categorization",
            intent_payload={
                "role_code": role_code, "ecode": "E-012",
                "signer_name": s["full_name"],
            },
        )
        result_roles[role_code] = {
            "intent_id": intent.id, "status": intent.status, "reused": False,
        }

    return {
        "system_id": system_id,
        "categorization_id": categorization.id,
        "acta_snapshot_hash": acta_hash,
        "signers": result_roles,
        "aprobada": False,
    }


async def get_acta_double_signature_status(
    session: AsyncSession, system_id: uuid.UUID,
) -> dict:
    """Estado de la doble firma del acta E-012 + gate ``aprobada``.

    ``aprobada=True`` SÓLO cuando los dos intents competentes (RInfo y RServ) están
    en estado ``signed``. Mientras falte alguno, el acta NO está aprobada.
    """
    categorization = await _load_latest_categorization(session, system_id)
    existing = await _existing_acta_intents(session, categorization.id)

    roles_status = {
        role: (existing[role]["status"] if existing.get(role) else None)
        for role in _ACTA_SIGNER_ROLES
    }
    aprobada = all(roles_status.get(r) == "signed" for r in _ACTA_SIGNER_ROLES)
    return {
        "system_id": system_id,
        "categorization_id": categorization.id,
        "has_double_signature_request": bool(existing),
        "roles": roles_status,
        "responsable_informacion_firmado": roles_status.get("responsable_informacion") == "signed",
        "responsable_servicio_firmado": roles_status.get("responsable_servicio") == "signed",
        "aprobada": aprobada,
    }
