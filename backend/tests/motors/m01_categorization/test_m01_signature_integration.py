"""Tests for M1 + M12 re-integration: Acta E-012 signature via magic link.

Closes TODO-M12-G1. Tests exercise the full HTTP flow:
  POST /systems/{id}/acta-e012/request-signature
  GET  /systems/{id}/acta-e012/signature-status

Each test seeds data through the M1 API (create system, add info types,
categorize) to produce a real categorization, then exercises the signature
endpoints that consume M12 MagicLinkService.
"""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m01_categorization.signature_integration import (
    SignatureIntegrationError,
    get_acta_double_signature_status,
    request_acta_double_signature,
)
from backend.tests.conftest import setup_test_project


# ================================================================
# HELPER: seed a system with categorization through the M1 API
# ================================================================

async def _seed_categorized_system(async_client, db):
    """Create project -> system -> info types -> categorize. Return system_id."""
    _, project_id = await setup_test_project(db)
    sys_resp = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": "SistemaFirma"},
    )
    assert sys_resp.status_code == 201, sys_resp.text
    system_id = sys_resp.json()["id"]

    await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/information-types",
        json={"items": [
            {"nombre": "Datos test", "valoracion_d": "MEDIO",
             "valoracion_i": "BAJO", "valoracion_c": "BAJO",
             "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
        ]},
    )
    cat_resp = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/categorize",
        json={"aprobado_por": "Test User"},
    )
    assert cat_resp.status_code == 200 or cat_resp.status_code == 201, cat_resp.text
    return system_id


# ================================================================
# REQUEST SIGNATURE TESTS
# ================================================================

class TestRequestSignature:

    @pytest.mark.asyncio
    async def test_request_signature_returns_200_with_link(self, async_client, db):
        """POST request-signature on categorized system returns magic link."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "rsi@example.com", "recipient_name": "Juan Perez"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "http" in body["magic_link_url"]
        assert len(body["otp"]) == 6
        assert body["recipient_email"] == "rsi@example.com"
        assert body["previous_link_revoked"] is False
        assert len(body["acta_snapshot_hash"]) == 64

    @pytest.mark.asyncio
    async def test_request_signature_fails_nonexistent_system(self, async_client, db):
        """POST request-signature on non-existent system returns 404.

        FIX(RLS): el endpoint ahora resuelve el sistema vía _get_system_with_rls
        (get_system_owner SECURITY DEFINER + tenant context) ANTES de operar — sin
        esto un sistema VÁLIDO fallaría bajo RLS en prod. Para un sistema
        inexistente devuelve 404 (Not Found · correcto y consistente con el
        endpoint de doble firma), no el 422 previo.
        """
        fake_id = uuid.uuid4()
        r = await async_client.post(
            f"/api/v1/categorization/systems/{fake_id}/acta-e012/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 404
        assert "no encontrado" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_request_signature_fails_uncategorized_system(self, async_client, db):
        """POST request-signature on system without categorization returns 422."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "SistemaSinCat"},
        )
        system_id = sys_resp.json()["id"]

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "x@example.com"},
        )
        assert r.status_code == 422
        assert "no tiene" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_request_signature_persists_link_id(self, async_client, db):
        """Categorization row gets signature_magic_link_id populated."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "rsi@example.com"},
        )
        assert r.status_code == 200
        link_id = r.json()["link_id"]

        row = await db.execute(text(
            "SELECT signature_magic_link_id FROM categorizations "
            "WHERE system_id = :sid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"sid": system_id})
        persisted = row.scalar_one_or_none()
        assert str(persisted) == link_id

    @pytest.mark.asyncio
    async def test_request_signature_idempotent_revokes_previous(self, async_client, db):
        """Second request-signature revokes the first link."""
        system_id = await _seed_categorized_system(async_client, db)

        r1 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "a@example.com"},
        )
        assert r1.status_code == 200
        link_id_1 = r1.json()["link_id"]

        r2 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "b@example.com"},
        )
        assert r2.status_code == 200
        link_id_2 = r2.json()["link_id"]

        assert link_id_1 != link_id_2
        assert r2.json()["previous_link_revoked"] is True

    @pytest.mark.asyncio
    async def test_request_signature_rejects_invalid_email(self, async_client, db):
        """Invalid email in request body returns 422 (Pydantic validation)."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "not-an-email"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_request_signature_uses_default_role(self, async_client, db):
        """Omitting recipient_role defaults to 'Responsable de la Informacion'."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "rsi@example.com"},
        )
        assert r.status_code == 200
        link_id = r.json()["link_id"]

        row = await db.execute(text(
            "SELECT scope FROM magic_links WHERE id = :lid"
        ), {"lid": link_id})
        scope = row.scalar_one()
        assert scope["recipient_role"] == "Responsable de la Información"


# ================================================================
# SIGNATURE STATUS TESTS
# ================================================================

class TestSignatureStatus:

    @pytest.mark.asyncio
    async def test_status_no_request_yet(self, async_client, db):
        """Status before any signature request returns has_signature_request=False."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/signature-status"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is False
        assert body["link_id"] is None

    @pytest.mark.asyncio
    async def test_status_after_request(self, async_client, db):
        """Status after signature request returns active link details."""
        system_id = await _seed_categorized_system(async_client, db)

        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "rsi@example.com"},
        )

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/signature-status"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_signature_request"] is True
        assert body["link_id"] is not None
        assert body["state"] == "active"
        assert body["recipient_email"] == "rsi@example.com"

    @pytest.mark.asyncio
    async def test_status_404_for_nonexistent_system(self, async_client, db):
        """Status for non-existent system returns 404."""
        fake_id = uuid.uuid4()
        r = await async_client.get(
            f"/api/v1/categorization/systems/{fake_id}/acta-e012/signature-status"
        )
        assert r.status_code == 404


# ================================================================
# HASH DETERMINISM TEST
# ================================================================

class TestActaSnapshotHash:

    @pytest.mark.asyncio
    async def test_hash_is_deterministic(self):
        """Same input produces same SHA-256 hash."""
        from backend.app.motors.m01_categorization.signature_integration import (
            _compute_acta_snapshot_hash,
        )
        acta = {"system_id": "abc", "cat": "MEDIA", "dims": {"D": "M", "I": "M"}}
        h1 = _compute_acta_snapshot_hash(acta)
        h2 = _compute_acta_snapshot_hash(acta)
        assert h1 == h2
        assert len(h1) == 64

    @pytest.mark.asyncio
    async def test_hash_changes_with_different_input(self):
        """Different input produces different hash."""
        from backend.app.motors.m01_categorization.signature_integration import (
            _compute_acta_snapshot_hash,
        )
        h1 = _compute_acta_snapshot_hash({"a": 1})
        h2 = _compute_acta_snapshot_hash({"a": 2})
        assert h1 != h2

    @pytest.mark.asyncio
    async def test_magic_link_scope_contains_expected_fields(self, async_client, db):
        """The magic link scope metadata has the required fields."""
        system_id = await _seed_categorized_system(async_client, db)

        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/acta-e012/request-signature",
            json={"recipient_email": "rsi@example.com", "recipient_name": "Ana Lopez"},
        )
        link_id = r.json()["link_id"]

        row = await db.execute(text(
            "SELECT scope FROM magic_links WHERE id = :lid"
        ), {"lid": link_id})
        scope = row.scalar_one()

        assert scope["document_type"] == "acta_e012"
        assert scope["system_id"] == system_id
        assert "categorization_id" in scope
        assert len(scope["acta_snapshot_hash"]) == 64
        assert scope["recipient_name"] == "Ana Lopez"


# ================================================================
# R03 · DOBLE FIRMA competente del acta E-012 (RInfo + RServ · art. 40.2)
# ================================================================

async def _seed_double_signers(db, client_id, project_id):
    """Siembra RInfo + RServ con client_user + contacto + role assignment."""
    contacts = {}
    for role_code, title in (
        ("responsable_informacion", "Responsable de la Información"),
        ("responsable_servicio", "Responsable del Servicio"),
    ):
        cu_id = uuid.uuid4()
        cc_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, password_hash) "
            "VALUES (:id, :cid, :email, 'x')"
        ), {"id": str(cu_id), "cid": str(client_id), "email": f"{role_code}@dob.test"})
        await db.execute(text(
            "INSERT INTO client_contacts "
            "(id, client_id, full_name, email, role_title, role_category, client_user_id) "
            "VALUES (:id, :cid, :n, :email, :t, 'operativo', :cu)"
        ), {"id": str(cc_id), "cid": str(client_id), "n": f"Firmante {role_code}",
            "email": f"{role_code}@dob.test", "t": title, "cu": str(cu_id)})
        await db.execute(text(
            "INSERT INTO project_role_assignments (id, project_id, role_code, contact_id) "
            "VALUES (:id, :pid, :rc, :cc)"
        ), {"id": str(uuid.uuid4()), "pid": str(project_id), "rc": role_code,
            "cc": str(cc_id)})
        contacts[role_code] = cc_id
    await db.flush()
    return contacts


async def _seed_categorized_with_project(async_client, db):
    """Como _seed_categorized_system pero devuelve (client_id, project_id, system_id)."""
    client_id, project_id = await setup_test_project(db)
    sys_resp = await async_client.post(
        f"/api/v1/categorization/projects/{project_id}/systems",
        json={"nombre": "SistemaDoble"},
    )
    system_id = sys_resp.json()["id"]
    await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/information-types",
        json={"items": [
            {"nombre": "Datos", "valoracion_d": "MEDIO", "valoracion_i": "MEDIO",
             "valoracion_c": "MEDIO", "valoracion_a": "MEDIO", "valoracion_t": "MEDIO"},
        ]},
    )
    cat_resp = await async_client.post(
        f"/api/v1/categorization/systems/{system_id}/categorize",
        json={"aprobado_por": "Test"},
    )
    assert cat_resp.status_code in (200, 201), cat_resp.text
    return client_id, project_id, uuid.UUID(system_id)


class TestActaDoubleSignature:

    @pytest.mark.asyncio
    async def test_request_creates_two_intents(self, async_client, db):
        client_id, project_id, system_id = await _seed_categorized_with_project(
            async_client, db)
        await _seed_double_signers(db, client_id, project_id)

        res = await request_acta_double_signature(db, system_id)
        assert set(res["signers"].keys()) == {
            "responsable_informacion", "responsable_servicio"}
        assert res["aprobada"] is False
        assert len(res["acta_snapshot_hash"]) == 64

        n = (await db.execute(text(
            "SELECT count(*) FROM signing_intents WHERE signable_ref_id = :rid "
            "AND signable_type = 'acta_comite'"
        ), {"rid": str(res["categorization_id"])})).scalar_one()
        assert n == 2

    @pytest.mark.asyncio
    async def test_request_is_idempotent(self, async_client, db):
        client_id, project_id, system_id = await _seed_categorized_with_project(
            async_client, db)
        await _seed_double_signers(db, client_id, project_id)

        r1 = await request_acta_double_signature(db, system_id)
        r2 = await request_acta_double_signature(db, system_id)
        assert all(v["reused"] for v in r2["signers"].values())
        n = (await db.execute(text(
            "SELECT count(*) FROM signing_intents WHERE signable_ref_id = :rid "
            "AND signable_type = 'acta_comite'"
        ), {"rid": str(r1["categorization_id"])})).scalar_one()
        assert n == 2

    @pytest.mark.asyncio
    async def test_aprobada_gate_requires_both(self, async_client, db):
        client_id, project_id, system_id = await _seed_categorized_with_project(
            async_client, db)
        await _seed_double_signers(db, client_id, project_id)
        res = await request_acta_double_signature(db, system_id)
        cat_id = res["categorization_id"]

        assert (await get_acta_double_signature_status(
            db, system_id))["aprobada"] is False

        await db.execute(text(
            "UPDATE signing_intents SET status='signed' WHERE signable_ref_id=:rid "
            "AND intent_payload->>'role_code'='responsable_informacion'"
        ), {"rid": str(cat_id)})
        st1 = await get_acta_double_signature_status(db, system_id)
        assert st1["responsable_informacion_firmado"] is True
        assert st1["responsable_servicio_firmado"] is False
        assert st1["aprobada"] is False

        await db.execute(text(
            "UPDATE signing_intents SET status='signed' WHERE signable_ref_id=:rid "
            "AND intent_payload->>'role_code'='responsable_servicio'"
        ), {"rid": str(cat_id)})
        assert (await get_acta_double_signature_status(
            db, system_id))["aprobada"] is True

    @pytest.mark.asyncio
    async def test_fails_without_competent_signers(self, async_client, db):
        _, _, system_id = await _seed_categorized_with_project(async_client, db)
        with pytest.raises(SignatureIntegrationError) as exc:
            await request_acta_double_signature(db, system_id)
        assert "doble firma" in str(exc.value).lower()
