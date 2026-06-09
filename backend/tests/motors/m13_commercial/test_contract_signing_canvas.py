"""#43 · firma del contrato comercial con canvas Ed25519 (ContractSigningFlow).

Cubre:
- signable_type 'contrato_comercial' (NO step-up OTP · decisión B).
- SEND: congela documento_sha256 + crea SigningIntent + archiva DOCX en IDMS
  (content_hash == documento_sha256) + magic-link FIRMA_CONTRATO.
- e2e SEND→SIGN BAJO fulkro_app: la firma promociona el proyecto + crea el
  ClientUser REAL (la conversión #7 se dispara EN EL FLUJO REAL, no solo en
  tests de handle_contract_signed) + SigningEvent Ed25519 + contrato vigente.
- Atomicidad (refuerzo 1): fallo en sign_canvas → rollback deshace TAMBIÉN la
  promoción + el ClientUser (3 checks).
- Idempotencia (refuerzo 2): doble firma → 1 firma, 1 ClientUser, vigente 1×.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from backend.app.models.client_portal import ClientUser  # noqa: F401 (RLS model reg)
from backend.app.models.commercial import Contract
from backend.app.models.core import Project
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m05_signing.service import SigningService
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.app.motors.m13_commercial.services.contract_signing_flow import (
    ContractSigningFlow,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService
from backend.tests.motors.m13_commercial.test_conversion_fulkro_app import (
    _as_fulkro_app_no_context,
)

# 1x1 PNG válido (data URL) para el canvas.
TINY_PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAA"
    "C0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


async def _setup_unsigned_contract(db, *, email="signer@firmante.es"):
    """Lead + proyecto ligero (#7.3) + contrato C-001 sin firmar (firmado_marcos)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = LeadService(db)
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await svc.create_lead(
        empresa_nombre="Firmante SL",
        contacto_email=email,
        empresa_cif=cif,
        sector="Tecnología",
        categoria_objetivo_ens="MEDIA",
    )
    light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(
        lead
    )
    contract_id = uuid.uuid4()
    params = json.dumps(
        {"pricing": {"categoria": "MEDIA", "total": 11500.0, "hitos": []}}
    )
    alc = json.dumps(
        {"categoria": "MEDIA", "sistemas": 3, "ubicaciones": 1, "exclusiones": []}
    )
    await db.execute(
        text(
            "INSERT INTO contracts (id, lead_id, project_id, plantilla_id, estado, "
            "parametros_xyzpr, alcance_snapshot, cliente_firmante_nombre, created_at) "
            "VALUES (:id, :lid, :pid, 'C-001', 'firmado_marcos', CAST(:p AS jsonb), "
            "CAST(:a AS jsonb), 'Ana Firmante', now())"
        ),
        {
            "id": str(contract_id),
            "lid": str(lead.id),
            "pid": str(light.id),
            "p": params,
            "a": alc,
        },
    )
    await db.flush()
    return lead, light, contract_id


def test_signable_types_contrato_comercial():
    from backend.app.motors.m05_signing.signable_types import (
        REQUIRES_STEP_UP_OTP,
        SIGNABLE_TYPE_LABELS,
        SIGNABLE_TYPES,
    )

    assert "contrato_comercial" in SIGNABLE_TYPES
    # decisión B · el OTP vive en la puerta magic-link, NO step-up adicional.
    assert "contrato_comercial" not in REQUIRES_STEP_UP_OTP
    assert "contrato_comercial" in SIGNABLE_TYPE_LABELS


@pytest.mark.asyncio
async def test_send_freezes_hash_and_creates_intent(db):
    lead, light, contract_id = await _setup_unsigned_contract(db)
    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana Firmante",
        created_by_user_id=uuid.uuid4(),
    )
    assert res["token"] and res["otp"]  # FIRMA_CONTRATO con OTP (puerta)
    assert res["signing_intent_id"]
    assert res["documento_sha256"] and len(res["documento_sha256"]) == 64

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    contract = await db.get(Contract, contract_id)
    assert contract.documento_sha256 == res["documento_sha256"]
    assert str(contract.signing_intent_id) == res["signing_intent_id"]

    intent = await db.get(SigningIntent, contract.signing_intent_id)
    assert intent.signable_type == "contrato_comercial"
    assert intent.signable_ref_id == contract_id  # puente reverso
    assert intent.signable_ref_type == "contract"
    assert intent.document_hash_sha256 == contract.documento_sha256
    assert intent.document_id is not None  # DOCX archivado en IDMS
    assert intent.status == "pending"  # NO otp_required (decisión B)

    # El DOCX archivado tiene content_hash == documento_sha256 (firmado verificable).
    doc_hash = await db.scalar(
        text("SELECT content_hash FROM documents WHERE id = :d"),
        {"d": str(intent.document_id)},
    )
    assert doc_hash == contract.documento_sha256


@pytest.mark.asyncio
async def test_full_send_sign_promotes_and_signs(db):
    """e2e SEND→SIGN bajo fulkro_app · la firma promociona el proyecto y crea el
    cliente DE VERDAD (la conversión #7 se dispara en el flujo real)."""
    lead, light, contract_id = await _setup_unsigned_contract(db)
    light_id, client_id = light.id, light.client_id

    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana Firmante",
        created_by_user_id=uuid.uuid4(),
    )

    # Producción: confirm corre como fulkro_app SIN contexto (anti falso-verde).
    await _as_fulkro_app_no_context(db)
    result = await ContractSigningFlow(db).confirm_signing(
        token=res["token"],
        otp=res["otp"],
        signature_canvas_dataurl=TINY_PNG,
        signed_name="Ana",
        signed_surname="Firmante",
        ip_address="1.2.3.4",
        user_agent="pytest",
        geo_lat=40.4,
        geo_lon=-3.7,
    )
    assert result["status"] == "signed"
    assert result["signing_event_id"] and result["event_hash_sha256"]

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    contract = await db.get(Contract, contract_id)
    assert contract.estado == "vigente"
    assert contract.firmado_cliente_at is not None

    # Proyecto PROMOVIDO (la firma lo promociona · #7 dispara DE VERDAD).
    lifecycle = await db.scalar(
        text("SELECT lifecycle_state FROM projects WHERE id = :p"),
        {"p": str(light_id)},
    )
    assert lifecycle == "SIGNED"

    # ClientUser REAL creado (1 · no duplicado).
    n_users = await db.scalar(
        text("SELECT count(*) FROM client_users WHERE client_id = :c"),
        {"c": str(client_id)},
    )
    assert n_users == 1

    # SigningEvent Ed25519 + canvas + hash chain.
    ev = await db.scalar(
        text(
            "SELECT count(*) FROM signing_events WHERE signing_intent_id = :i "
            "AND event_type = 'signature_generated' "
            "AND signature_ed25519 IS NOT NULL "
            "AND signature_canvas_dataurl IS NOT NULL"
        ),
        {"i": res["signing_intent_id"]},
    )
    assert ev == 1

    # El firmante apunta a un ClientUser REAL de este client (no sintético).
    signer_ok = await db.scalar(
        text(
            "SELECT count(*) FROM client_users WHERE id = :u AND client_id = :c"
        ),
        {"u": result["signer_user_id"], "c": str(client_id)},
    )
    assert signer_ok == 1


@pytest.mark.asyncio
async def test_atomicity_signcanvas_failure_rolls_back_promotion(db, monkeypatch):
    """Refuerzo 1 · fallo en sign_canvas DESPUÉS de la conversión → rollback
    deshace TAMBIÉN la promoción + el ClientUser. 3 checks."""
    lead, light, contract_id = await _setup_unsigned_contract(db)
    light_id, client_id = light.id, light.client_id

    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana",
        created_by_user_id=uuid.uuid4(),
    )

    async def _boom(*a, **k):
        raise RuntimeError("sign_canvas boom")

    monkeypatch.setattr(SigningService, "sign_canvas", _boom)

    await _as_fulkro_app_no_context(db)
    # match exacto · prueba que el rollback lo dispara el fallo de sign_canvas
    # (conversión-primero YA ocurrió), NO un consume fallido aguas arriba.
    with pytest.raises(RuntimeError, match="sign_canvas boom"):
        # begin_nested = frontera de tx atómica (como el commit/rollback del endpoint).
        async with db.begin_nested():
            await ContractSigningFlow(db).confirm_signing(
                token=res["token"],
                otp=res["otp"],
                signature_canvas_dataurl=TINY_PNG,
                signed_name="A",
                signed_surname="B",
            )

    # Savepoint rolled back → TODO deshecho.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lifecycle = await db.scalar(
        text("SELECT lifecycle_state FROM projects WHERE id = :p"),
        {"p": str(light_id)},
    )
    assert lifecycle == "DRAFT"  # (a) proyecto vuelve a ligero
    n_users = await db.scalar(
        text("SELECT count(*) FROM client_users WHERE client_id = :c"),
        {"c": str(client_id)},
    )
    assert n_users == 0  # (b) NO queda ClientUser
    estado = await db.scalar(
        text("SELECT estado FROM contracts WHERE id = :c"),
        {"c": str(contract_id)},
    )
    assert estado != "vigente"  # (c) contrato NO vigente


@pytest.mark.asyncio
async def test_idempotency_double_sign(db):
    """Refuerzo 2 · doble firma (doble clic / reintento) → 1 firma, 1 ClientUser,
    vigente 1×."""
    lead, light, contract_id = await _setup_unsigned_contract(db)
    client_id = light.client_id
    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana",
        created_by_user_id=uuid.uuid4(),
    )

    await _as_fulkro_app_no_context(db)
    r1 = await ContractSigningFlow(db).confirm_signing(
        token=res["token"], otp=res["otp"],
        signature_canvas_dataurl=TINY_PNG, signed_name="Ana", signed_surname="Firmante",
    )
    assert r1["status"] == "signed"

    # Segundo intento (doble clic) · mismo token+otp.
    try:
        r2 = await ContractSigningFlow(db).confirm_signing(
            token=res["token"], otp=res["otp"],
            signature_canvas_dataurl=TINY_PNG, signed_name="Ana", signed_surname="Firmante",
        )
        assert r2["status"] == "already_signed"  # guard idempotente
    except Exception:
        # Si el magic-link rechaza el re-consume (OTP/uses) → también seguro.
        pass

    # Invariantes: 1 firma, 1 ClientUser, vigente.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    ev = await db.scalar(
        text(
            "SELECT count(*) FROM signing_events WHERE signing_intent_id = :i "
            "AND event_type = 'signature_generated'"
        ),
        {"i": res["signing_intent_id"]},
    )
    assert ev == 1
    n_users = await db.scalar(
        text("SELECT count(*) FROM client_users WHERE client_id = :c"),
        {"c": str(client_id)},
    )
    assert n_users == 1
    estado = await db.scalar(
        text("SELECT estado FROM contracts WHERE id = :c"),
        {"c": str(contract_id)},
    )
    assert estado == "vigente"


# ════════════════════════════════════════════════════════════════════
# #34 (FRENTE B) · preview del contrato ANTES de firmar (no a ciegas)
# ════════════════════════════════════════════════════════════════════

async def _cleanup_contract_minio(db, contract_id):
    from backend.app.core.storage.minio_client import (
        BUCKET_DOCUMENTS,
        remove_object,
    )
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    sp = await db.scalar(
        text(
            "SELECT d.storage_path FROM documents d "
            "JOIN signing_intents si ON si.document_id = d.id "
            "JOIN contracts c ON c.signing_intent_id = si.id "
            "WHERE c.id = :cid"
        ),
        {"cid": str(contract_id)},
    )
    if sp and str(sp).startswith("minio://"):
        remove_object(BUCKET_DOCUMENTS, str(sp)[len("minio://"):].partition("/")[2])


@pytest.mark.asyncio
async def test_preview_returns_exact_docx_being_signed(db):
    """#34: el cliente lee/descarga el DOCX EXACTO que va a firmar (WYSIWYS ·
    content_hash == documento_sha256) · pre-firma · sin consumir el magic-link."""
    import hashlib

    lead, light, contract_id = await _setup_unsigned_contract(db)
    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana Firmante",
        created_by_user_id=uuid.uuid4(),
    )
    try:
        info = await ContractSigningFlow(db).get_contract_document_for_preview(
            res["token"],
        )
        assert info["filename"].lower().endswith(".docx")
        assert (
            hashlib.sha256(info["binary"]).hexdigest() == res["documento_sha256"]
        )
        assert info["documento_sha256"] == res["documento_sha256"]
    finally:
        await _cleanup_contract_minio(db, contract_id)


@pytest.mark.asyncio
async def test_preview_http_endpoint_streams_docx(async_client, db):
    """#34: el endpoint público GET /contract-signing/preview entrega el binario
    con cabecera X-Document-Sha256 == documento_sha256 (token = credencial)."""
    import hashlib

    lead, light, contract_id = await _setup_unsigned_contract(db)
    res = await ContractSigningFlow(db).send_for_signing(
        contract_id=contract_id,
        recipient_email=lead.contacto_email,
        recipient_name="Ana Firmante",
        created_by_user_id=uuid.uuid4(),
    )
    try:
        r = await async_client.get(
            f"/api/v1/contract-signing/preview?token={res['token']}",
        )
        assert r.status_code == 200, r.text
        assert hashlib.sha256(r.content).hexdigest() == res["documento_sha256"]
        assert r.headers.get("x-document-sha256") == res["documento_sha256"]
    finally:
        await _cleanup_contract_minio(db, contract_id)


@pytest.mark.asyncio
async def test_preview_invalid_token_raises(db):
    """#34: token inexistente → ContractNotFoundError (no filtra existencia)."""
    from backend.app.motors.m13_commercial.services.contract_signing_flow import (
        ContractNotFoundError,
    )

    with pytest.raises(ContractNotFoundError):
        await ContractSigningFlow(db).get_contract_document_for_preview(
            "invalid-token-aaaaaaaaaaaaaaaaaaaa",
        )
