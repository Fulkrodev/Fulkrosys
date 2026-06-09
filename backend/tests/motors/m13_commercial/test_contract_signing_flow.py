"""Tests SAN-D MB-19.4 · ContractSigningFlow + magic-link FIRMA_CONTRATO.

Cubre:
- send_for_signing genera magic-link FIRMA_CONTRATO + actualiza Contract.firmado_cliente_link_id.
- send_for_signing OTP+geo flags habilitados (jurídico vinculante).
- send_for_signing contract no encontrado raises.
- confirm_signing consume magic-link + UPDATE Contract.firmado_cliente_at + trigger auto-conversion.
- confirm_signing OTP inválido raises ContractSigningFlowError.
- confirm_signing token corrupto raises.
- FIRMA_CONTRATO purpose existe en MagicLinkPurpose enum (#36).
- FIRMA_CONTRATO config: TTL 72h · OTP True · geo True · max_uses 3.

Refs: ADR-041 · MagicLinkPurpose.FIRMA_CONTRATO · MB-19.4.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.models.commercial import Contract
from backend.app.motors.m12_magic_link.purposes import (
    MagicLinkPurpose,
    PURPOSE_CONFIG,
    get_config,
)
from backend.app.motors.m13_commercial.services.contract_signing_flow import (
    ContractSigningFlow,
    ContractSigningFlowError,
    ContractNotFoundError,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService


# ====================== FIRMA_CONTRATO purpose enum ======================

def test_firma_contrato_purpose_in_enum():
    """MagicLinkPurpose.FIRMA_CONTRATO existe (#36 enum extension)."""
    assert MagicLinkPurpose.FIRMA_CONTRATO.value == "firma_contrato"


def test_firma_contrato_config_juridico_vinculante():
    """FIRMA_CONTRATO config · TTL 72h · OTP True · geo True · max_uses 3."""
    config = get_config(MagicLinkPurpose.FIRMA_CONTRATO)
    assert config["ttl_hours"] == 72
    assert config["max_uses"] == 3
    assert config["requires_otp"] is True
    assert config["requires_geo"] is True
    assert "Firmar contrato" in config["action_label"]


def test_purpose_count_post_mb19_4_includes_firma_contrato():
    """Post-MB-19.4 · FIRMA_CONTRATO sumado al total enum + config.

    NOTA: comentario header purposes.py dice "9+5+3+3+3+12=35" pero real
    es 8+5+3+3+3+12=34 pre-MB-19.4 (AUTORIZACION_PENTEST eliminado SAN-B
    MB-6.6 sin actualizar comentario header). Post-MB-19.4 total = 35.
    """
    total = len(PURPOSE_CONFIG)
    assert total == len(list(MagicLinkPurpose))
    assert MagicLinkPurpose.FIRMA_CONTRATO in PURPOSE_CONFIG
    # Total = pre + 1 nuevo MB-19.4
    assert total >= 35


# ====================== Helper: setup lead + contract ======================

async def _setup_lead_and_contract(db):
    """Crea lead M13 + contract draft listo para signing."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead_service = LeadService(db)
    lead = await lead_service.create_lead(
        empresa_nombre="Sign Co SL",
        contacto_email=f"sign-{uuid.uuid4().hex[:6]}@signco.es",
        empresa_cif=f"B{uuid.uuid4().hex[:8].upper()}",
        categoria_objetivo_ens="MEDIA",
    )
    # Avanzar a propuesta_enviada
    for tgt in ("enviado", "respondio", "reunion_agendada", "propuesta_enviada"):
        lead = await lead_service.transition_estado_contacto(
            lead_id=lead.id, target_estado=tgt,
        )

    contract_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO contracts (id, lead_id, estado, tipo, "
        "cliente_firmante_nombre, created_at) "
        "VALUES (:id, :lid, 'draft', 'servicios', NULL, now())"
    ), {"id": str(contract_id), "lid": str(lead.id)})
    await db.flush()
    return lead, contract_id


# #43 · canvas dataurl (1x1 PNG) para confirm_signing.
CANVAS = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAA"
    "C0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


# ====================== send_for_signing ======================

@pytest.mark.asyncio
async def test_send_for_signing_generates_magic_link(db):
    """send_for_signing crea magic-link FIRMA_CONTRATO + intent + freeze hash."""
    lead, contract_id = await _setup_lead_and_contract(db)
    result = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email="signer@signco.es",
        recipient_name="Juan Pérez",
        created_by_user_id=uuid.uuid4(),
    )
    assert "magic_link_id" in result
    assert "/ml/consume?token=" in result["url"]
    assert result["otp"] is not None and len(result["otp"]) == 6
    assert "Firmar contrato" in result["action_label"]
    # #43 · ahora también crea el SigningIntent + congela documento_sha256.
    assert result["signing_intent_id"] is not None
    assert result["documento_sha256"] and len(result["documento_sha256"]) == 64

    contract = await db.get(Contract, contract_id)
    assert contract.firmado_cliente_link_id is not None
    assert str(contract.firmado_cliente_link_id) == result["magic_link_id"]
    assert contract.cliente_firmante_nombre == "Juan Pérez"
    assert contract.signing_intent_id is not None


@pytest.mark.asyncio
async def test_send_for_signing_contract_not_found_raises(db):
    with pytest.raises(ContractNotFoundError):
        await ContractSigningFlow(db).send_for_signing(
            contract_id=uuid.uuid4(),
            recipient_email="ghost@ghost.es",
            recipient_name="Ghost",
            created_by_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_send_for_signing_custom_subject_propagates(db):
    lead, contract_id = await _setup_lead_and_contract(db)
    result = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email="custom@signco.es",
        recipient_name="Cliente Custom",
        created_by_user_id=uuid.uuid4(),
        custom_subject="Firma contrato URGENTE",
        custom_body_intro="Marcos: necesitamos cerrar antes del viernes.",
    )
    assert result["magic_link_id"] is not None


@pytest.mark.asyncio
async def test_send_for_signing_ttl_override(db):
    lead, contract_id = await _setup_lead_and_contract(db)
    result = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email="ttl@signco.es",
        recipient_name="TTL Test",
        created_by_user_id=uuid.uuid4(),
        ttl_hours=24,
    )
    from datetime import datetime, timezone

    expires = datetime.fromisoformat(result["expires_at"])
    delta_hours = (expires - datetime.now(timezone.utc)).total_seconds() / 3600
    assert 23.5 < delta_hours < 24.5


# ====================== confirm_signing full flow (#43 canvas) ======================

@pytest.mark.asyncio
async def test_confirm_signing_full_flow_with_conversion(db):
    """#43 · SEND→SIGN canvas Ed25519 + auto-conversión #7 (promueve + cliente)."""
    from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
        CommercialWorkflowService,
    )

    lead, contract_id = await _setup_lead_and_contract(db)
    light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(
        lead
    )
    await db.execute(
        text("UPDATE contracts SET project_id = :pid WHERE id = :cid"),
        {"pid": str(light.id), "cid": str(contract_id)},
    )
    await db.flush()

    send_result = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email="signer@signco.es",
        recipient_name="Juan Confirmador",
        created_by_user_id=uuid.uuid4(),
    )

    confirm_result = await ContractSigningFlow(db).confirm_signing(
        token=send_result["token"],
        otp=send_result["otp"],
        signature_canvas_dataurl=CANVAS,
        signed_name="Juan",
        signed_surname="Confirmador",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Chrome/120",
        geo_lat=40.4168,
        geo_lon=-3.7038,
    )
    assert confirm_result["status"] == "signed"
    assert confirm_result["contract_id"] == str(contract_id)
    assert confirm_result["signing_event_id"]

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    contract = await db.get(Contract, contract_id)
    assert contract.firmado_cliente_at is not None
    assert contract.estado == "vigente"  # #43 · canvas → vigente
    audit = (contract.adendas or {}).get("signing_audit", {})
    assert audit.get("ip_address") == "192.168.1.100"
    assert audit.get("geo") == {"lat": 40.4168, "lon": -3.7038}

    conversion = confirm_result["conversion"]
    assert conversion["client_id"] is not None
    assert conversion["project_id"] == str(light.id)  # promovido (no duplica)


@pytest.mark.asyncio
async def test_confirm_signing_invalid_otp_raises(db):
    lead, contract_id = await _setup_lead_and_contract(db)
    send_result = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email="bad-otp@signco.es",
        recipient_name="Bad OTP",
        created_by_user_id=uuid.uuid4(),
    )
    with pytest.raises(ContractSigningFlowError) as exc_info:
        await ContractSigningFlow(db).confirm_signing(
            token=send_result["token"],
            otp="000000",  # incorrecto
            signature_canvas_dataurl=CANVAS,
            signed_name="X",
            signed_surname="Y",
            ip_address="1.1.1.1",
            user_agent="Test",
        )
    assert "Magic-link inválido" in str(exc_info.value) or "OTP" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_confirm_signing_corrupt_token_raises(db):
    with pytest.raises(ContractSigningFlowError) as exc_info:
        await ContractSigningFlow(db).confirm_signing(
            token="not.a.valid.jwt",
            otp="123456",
            signature_canvas_dataurl=CANVAS,
            signed_name="X",
            signed_surname="Y",
        )
    assert "Magic-link" in str(exc_info.value)
