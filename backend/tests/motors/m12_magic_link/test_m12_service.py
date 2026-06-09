"""Tests del service core Motor 12 — Magic Link Engine.

Enfoque: validar logica criptografica + flujos normales + casos hostiles.
Los tests HTTP via endpoints se haran en test_m12_api.py (13.3).

Estos tests operan directamente sobre MagicLinkService con sesion DB
para verificar la logica sin pasar por la capa HTTP.
"""
import hashlib
import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkNotFoundError,
    MagicLinkExpiredError,
    MagicLinkRevokedError,
    MagicLinkExhaustedError,
    MagicLinkInvalidOTPError,
    MagicLinkOTPBlockedError,
    OTP_FAILURE_THRESHOLD,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import (
    MagicLinkGenerateRequest,
    MagicLinkConsumeRequest,
)
from backend.app.models.operations import MagicLink
from backend.tests.conftest import setup_test_project

BASE_URL = "https://test.fulkro.es"


# ================================================================
# HELPER
# ================================================================

async def _setup_and_generate(db, purpose=MagicLinkPurpose.PORTAL_REMEDIACION):
    """Create client+project, set tenant context, generate a magic link.

    Returns (service, response, project_id).

    Default purpose post-MB-4.bis2 ADR-020: PORTAL_REMEDIACION (legitimate
    tercero · IT cliente sin cuenta portal · NO requires OTP). Anteriormente
    usaba APORTE_EVIDENCIA (deprecated v3 · hard-rejected).

    Override ttl_hours=168 (7 days) + max_uses=3 SOLO cuando purpose es
    el default PORTAL_REMEDIACION (mantiene semantics tests originales que
    asumían APORTE_EVIDENCIA config 7d/3uses). Otros purposes usan su
    PURPOSE_CONFIG default sin override.
    """
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = MagicLinkService(db)
    is_default = purpose == MagicLinkPurpose.PORTAL_REMEDIACION
    req = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=purpose,
        recipient_email="cliente@example.com",
        ttl_hours=168 if is_default else None,
        max_uses=3 if is_default else None,
    )
    resp = await svc.generate_magic_link(req, base_url=BASE_URL)
    await db.flush()
    return svc, resp, project_id


# ================================================================
# HAPPY PATH TESTS (Tests 1-6)
# ================================================================

class TestHappyPath:
    """Tests que verifican que los flujos normales funcionan correctamente."""

    @pytest.mark.asyncio
    async def test_generate_simple_purpose_no_otp(self, db):
        """Test 1: Genera link APORTE_EVIDENCIA (no requiere OTP).

        Verifica: token no vacio, otp es None, url contiene token,
        expires_at ~ 7 dias en el futuro.
        DB: token_hash no nulo, otp_hash NULL, tipo_operacion correcto.
        """
        svc, resp, _ = await _setup_and_generate(db)

        assert resp.token, "Token debe ser no vacio"
        assert resp.otp is None, "PORTAL_REMEDIACION no requiere OTP"
        assert resp.token in resp.url, "URL debe contener el token"
        assert resp.purpose == MagicLinkPurpose.PORTAL_REMEDIACION
        assert resp.action_label == "Acceder al portal de remediacion"

        # TTL ~ 7 dias
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)
        delta = abs((resp.expires_at - expected_exp).total_seconds())
        assert delta < 60, f"Expiration should be ~7 days, delta={delta}s"

        # DB verification
        link = await db.get(MagicLink, resp.magic_link_id)
        assert link is not None
        assert link.token_hash, "token_hash must be set"
        assert link.otp_hash is None, "No OTP for aporte_evidencia"
        assert link.tipo_operacion == "portal_remediacion"
        assert link.usos == 0
        assert link.revocado is False

    @pytest.mark.asyncio
    async def test_generate_purpose_with_otp(self, db):
        """Test 2: Genera link FIRMA_DOCUMENTO (requiere OTP).

        Verifica: response contiene otp de 6 digitos, token presente.
        DB: otp_hash no nulo.
        """
        svc, resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )

        assert resp.token, "Token debe existir"
        assert resp.otp is not None, "FIRMA_DOCUMENTO requiere OTP"
        assert len(resp.otp) == 6, f"OTP debe ser 6 digitos, got {len(resp.otp)}"
        assert resp.otp.isdigit(), "OTP debe ser numerico"

        link = await db.get(MagicLink, resp.magic_link_id)
        assert link.otp_hash is not None, "otp_hash debe guardarse en DB"
        assert link.tipo_operacion == "firma_documento"

    @pytest.mark.asyncio
    async def test_consume_simple_link_success(self, db):
        """Test 3: Genera link APORTE_EVIDENCIA y lo consume exitosamente.

        Verifica: response OK, remaining_uses decrementado, DB usos=1.
        """
        svc, gen_resp, _ = await _setup_and_generate(db)

        consume_req = MagicLinkConsumeRequest(
            token=gen_resp.token,
            client_ip="1.2.3.4",
            user_agent="TestAgent/1.0",
        )
        consume_resp = await svc.consume_magic_link(consume_req)
        await db.flush()

        assert consume_resp.magic_link_id == gen_resp.magic_link_id
        assert consume_resp.purpose == MagicLinkPurpose.PORTAL_REMEDIACION
        assert consume_resp.remaining_uses == 2  # max_uses=3 for aporte_evidencia

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        assert link.usos == 1

    @pytest.mark.asyncio
    async def test_consume_link_with_correct_otp(self, db):
        """Test 4: Genera link FIRMA_DOCUMENTO con OTP y consume con OTP correcto."""
        svc, gen_resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )

        consume_req = MagicLinkConsumeRequest(
            token=gen_resp.token,
            otp=gen_resp.otp,
            client_ip="5.6.7.8",
        )
        consume_resp = await svc.consume_magic_link(consume_req)
        await db.flush()

        assert consume_resp.magic_link_id == gen_resp.magic_link_id
        assert consume_resp.remaining_uses == 0  # max_uses=1 for firma_documento

    @pytest.mark.asyncio
    async def test_revoke_active_link(self, db):
        """Test 5: Genera link, lo revoca, verifica DB."""
        svc, gen_resp, _ = await _setup_and_generate(db)

        await svc.revoke_magic_link(gen_resp.magic_link_id, reason="Test revocation")
        await db.flush()

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        assert link.revocado is True
        assert link.revoked_at is not None

    @pytest.mark.asyncio
    async def test_get_status_returns_active(self, db):
        """Test 6: Status de link recien creado es 'active'."""
        svc, gen_resp, _ = await _setup_and_generate(db)

        status = await svc.get_magic_link_status(gen_resp.magic_link_id)

        assert status["status"] == "active"
        assert status["uses"] == 0
        assert status["purpose"] == "portal_remediacion"
        assert status["recipient_email"] == "cliente@example.com"


# ================================================================
# HOSTILE / SECURITY TESTS (Tests 7-15)
# ================================================================

class TestHostileCases:
    """Tests que verifican que ataques conocidos NO funcionan."""

    @pytest.mark.asyncio
    async def test_consume_expired_link_rejected(self, db):
        """Test 7: Link expirado es rechazado.

        Manipula expira_at directamente en DB para simular paso del tiempo.
        """
        svc, gen_resp, _ = await _setup_and_generate(db)

        # Forzar expiracion en DB
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            text("UPDATE magic_links SET expira_at = :exp WHERE id = :id"),
            {"exp": past, "id": str(gen_resp.magic_link_id)},
        )
        await db.flush()

        consume_req = MagicLinkConsumeRequest(token=gen_resp.token)

        with pytest.raises(MagicLinkExpiredError):
            await svc.consume_magic_link(consume_req)

        # usos NO incrementado
        link = await db.get(MagicLink, gen_resp.magic_link_id)
        await db.refresh(link)
        assert link.usos == 0

    @pytest.mark.asyncio
    async def test_consume_revoked_link_rejected(self, db):
        """Test 8: Link revocado es rechazado."""
        svc, gen_resp, _ = await _setup_and_generate(db)

        await svc.revoke_magic_link(gen_resp.magic_link_id)
        await db.flush()

        consume_req = MagicLinkConsumeRequest(token=gen_resp.token)

        with pytest.raises(MagicLinkRevokedError):
            await svc.consume_magic_link(consume_req)

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        await db.refresh(link)
        assert link.usos == 0

    @pytest.mark.asyncio
    async def test_consume_wrong_otp_increments_failures(self, db):
        """Test 9: OTP incorrecto incrementa otp_failures, NO consume."""
        svc, gen_resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )

        consume_req = MagicLinkConsumeRequest(
            token=gen_resp.token,
            otp="000000",  # OTP incorrecto
        )

        with pytest.raises(MagicLinkInvalidOTPError):
            await svc.consume_magic_link(consume_req)

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        await db.refresh(link)
        assert link.otp_failures == 1
        assert link.usos == 0, "Link NO debe consumirse con OTP incorrecto"

    @pytest.mark.asyncio
    async def test_otp_failures_block_after_threshold(self, db):
        """Test 10 — CRITICO: 3 fallos OTP bloquean el link permanentemente.

        Despues de 3 fallos, ni siquiera el OTP correcto funciona.
        Protege contra fuerza bruta del OTP de 6 digitos.
        """
        svc, gen_resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )
        correct_otp = gen_resp.otp

        # 3 intentos fallidos
        for i in range(OTP_FAILURE_THRESHOLD):
            bad_req = MagicLinkConsumeRequest(
                token=gen_resp.token,
                otp=f"{i:06d}",  # OTPs falsos
            )
            with pytest.raises(MagicLinkInvalidOTPError):
                await svc.consume_magic_link(bad_req)
            await db.flush()

        # Ahora intenta con el OTP correcto — debe estar BLOQUEADO
        correct_req = MagicLinkConsumeRequest(
            token=gen_resp.token,
            otp=correct_otp,
        )
        with pytest.raises(MagicLinkOTPBlockedError):
            await svc.consume_magic_link(correct_req)

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        await db.refresh(link)
        assert link.otp_failures == OTP_FAILURE_THRESHOLD
        assert link.usos == 0, "Link JAMAS consumido tras bloqueo OTP"

    @pytest.mark.asyncio
    async def test_consume_beyond_max_uses_rejected(self, db):
        """Test 11: Link APORTE_EVIDENCIA (max_uses=3) rechazado en 4to uso."""
        svc, gen_resp, _ = await _setup_and_generate(db)

        # Consumir 3 veces (max_uses=3 para aporte_evidencia)
        for i in range(3):
            req = MagicLinkConsumeRequest(token=gen_resp.token)
            resp = await svc.consume_magic_link(req)
            await db.flush()
            assert resp.remaining_uses == 2 - i

        # 4to intento — rechazado
        req = MagicLinkConsumeRequest(token=gen_resp.token)
        with pytest.raises(MagicLinkExhaustedError):
            await svc.consume_magic_link(req)

        link = await db.get(MagicLink, gen_resp.magic_link_id)
        await db.refresh(link)
        assert link.usos == 3

    @pytest.mark.asyncio
    async def test_consume_nonexistent_token_rejected(self, db):
        """Test 12: Token inventado es rechazado.

        Fabrica un token sin pasar por generate. Debe fallar.
        """
        client_id, project_id = await setup_test_project(db)
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        svc = MagicLinkService(db)

        fake_req = MagicLinkConsumeRequest(
            token="eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJmYWtlIjoidG9rZW4ifQ.fakesignature",
        )

        with pytest.raises(MagicLinkNotFoundError):
            await svc.consume_magic_link(fake_req)

    @pytest.mark.asyncio
    async def test_tampered_jwt_signature_rejected(self, db):
        """Test 13 — CRITICO: JWT con firma manipulada es rechazado.

        Cambia un caracter en la parte del payload (entre los dos puntos)
        para simular un ataque de tampering realista.
        """
        svc, gen_resp, _ = await _setup_and_generate(db)
        original_token = gen_resp.token

        # Manipular un caracter en el payload (parte entre primer y segundo punto)
        parts = original_token.split(".")
        assert len(parts) == 3, "JWT debe tener 3 partes"
        payload_chars = list(parts[1])
        # Flip a character in the middle of the payload
        idx = len(payload_chars) // 2
        old_char = payload_chars[idx]
        payload_chars[idx] = "A" if old_char != "A" else "B"
        parts[1] = "".join(payload_chars)
        tampered_token = ".".join(parts)

        consume_req = MagicLinkConsumeRequest(token=tampered_token)

        with pytest.raises(MagicLinkNotFoundError):
            await svc.consume_magic_link(consume_req)

        # Original link usos unchanged
        link = await db.get(MagicLink, gen_resp.magic_link_id)
        assert link.usos == 0

    @pytest.mark.asyncio
    async def test_token_plain_not_stored_in_db(self, db):
        """Test 14: Token plano NUNCA se guarda en DB. Solo el hash SHA-256."""
        svc, gen_resp, _ = await _setup_and_generate(db)
        token_plain = gen_resp.token

        link = await db.get(MagicLink, gen_resp.magic_link_id)

        # token_hash != token_plain
        assert link.token_hash != token_plain, \
            "Token plano NUNCA debe estar en DB"

        # token_hash == sha256(token_plain)
        expected_hash = hashlib.sha256(token_plain.encode("utf-8")).hexdigest()
        assert link.token_hash == expected_hash, \
            "token_hash debe ser SHA-256 del token plano"

    @pytest.mark.asyncio
    async def test_get_status_exhausted(self, db):
        """Test 14b: Status returns 'exhausted' after all uses consumed."""
        svc, gen_resp, _ = await _setup_and_generate(db)

        # Consume all 3 uses (aporte_evidencia max_uses=3)
        for _ in range(3):
            req = MagicLinkConsumeRequest(token=gen_resp.token)
            await svc.consume_magic_link(req)
            await db.flush()

        status = await svc.get_magic_link_status(gen_resp.magic_link_id)
        assert status["status"] == "exhausted"

    @pytest.mark.asyncio
    async def test_get_status_blocked_otp(self, db):
        """Test 14c: Status returns 'blocked_otp' after OTP threshold."""
        svc, gen_resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )

        for i in range(OTP_FAILURE_THRESHOLD):
            bad_req = MagicLinkConsumeRequest(token=gen_resp.token, otp=f"{i:06d}")
            with pytest.raises(MagicLinkInvalidOTPError):
                await svc.consume_magic_link(bad_req)
            await db.flush()

        status = await svc.get_magic_link_status(gen_resp.magic_link_id)
        assert status["status"] == "blocked_otp"

    @pytest.mark.asyncio
    async def test_generate_with_allowed_countries(self, db):
        """Test 14d: Generate with allowed_countries stores in DB."""
        from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest

        client_id, project_id = await setup_test_project(db)
        from backend.app.database import set_tenant_context
        await set_tenant_context(db, client_id=client_id, project_id=project_id)

        svc = MagicLinkService(db)
        req = MagicLinkGenerateRequest(
            project_id=project_id,
            purpose=MagicLinkPurpose.AUTORIZACION_ACCION_REMOTA,
            recipient_email="admin@example.com",
            allowed_countries=["ES", "PT"],
        )
        resp = await svc.generate_magic_link(req, base_url="https://test.fulkro.es")
        await db.flush()

        link = await db.get(MagicLink, resp.magic_link_id)
        assert link.allowed_countries == ["ES", "PT"]
        assert link.recipient_email == "admin@example.com"

    @pytest.mark.asyncio
    async def test_otp_plain_not_stored_in_db(self, db):
        """Test 15: OTP plano NUNCA se guarda en DB. Solo el hash SHA-256."""
        svc, gen_resp, _ = await _setup_and_generate(
            db, purpose=MagicLinkPurpose.FIRMA_DOCUMENTO
        )
        otp_plain = gen_resp.otp

        link = await db.get(MagicLink, gen_resp.magic_link_id)

        # otp_hash != otp_plain
        assert link.otp_hash != otp_plain, \
            "OTP plano NUNCA debe estar en DB"

        # otp_hash == sha256(otp_plain)
        expected_hash = hashlib.sha256(otp_plain.encode("utf-8")).hexdigest()
        assert link.otp_hash == expected_hash, \
            "otp_hash debe ser SHA-256 del OTP plano"
