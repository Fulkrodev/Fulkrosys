"""Tests ENS_REQUIRED roles · SAN-E v3.MB-5.0.bis.

ADR-020 v5 Q5.3 (Marcos 2026-05-10): roles ENS_REQUIRED como M30 contactos
INVISIBLE al cliente · admin-managed.

8 tests cubren:
  1. test_role_ens_required_field_persists
  2. test_ens_required_roles_status_endpoint
  3. test_assign_ens_required_role_method
  4. test_validator_blocks_when_roles_missing_e040
  5. test_validator_passes_when_roles_complete_e040
  6. test_validator_skips_when_doc_not_in_required_set
  7. test_admin_can_reassign_role_to_different_contact
  8. test_constraint_enforces_valid_role_values
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.ens_required import (
    ENS_REQUIRED_ROLES,
)
from backend.app.motors.m30_client_contacts.schemas import ClientContactCreate
from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
)
from backend.app.motors.m06_document_factory.stakeholders_helper import (
    validate_ens_required_roles_assigned,
)
from backend.tests.conftest import setup_test_project


def _payload(
    full_name: str,
    email: str,
    role_title: str = "CISO",
    role_category: str = "ciso",
    **overrides,
) -> ClientContactCreate:
    base = {
        "full_name": full_name,
        "email": email,
        "role_title": role_title,
        "role_category": role_category,
    }
    base.update(overrides)
    return ClientContactCreate(**base)


async def _assign_all_six_roles(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    """Helper · crea 6 contactos y asigna los 6 roles ENS_REQUIRED."""
    svc = ClientContactService(db)
    contact_ids: dict[str, uuid.UUID] = {}
    for idx, role in enumerate(ENS_REQUIRED_ROLES):
        contact = await svc.create_contact(
            client_id,
            _payload(
                full_name=f"Persona {role}",
                email=f"persona{idx}@ejemplo.es",
                role_title="ENS Role",
            ),
        )
        await svc.assign_ens_required_role(contact.id, role)
        contact_ids[role] = contact.id
    return contact_ids


# ====================================================================
# Test 1 · field persists
# ====================================================================


@pytest.mark.asyncio
async def test_role_ens_required_field_persists(db: AsyncSession):
    """role_ens_required + contact_role_notes persisten correctamente."""
    client_id, _project_id = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id)
    svc = ClientContactService(db)

    contact = await svc.create_contact(
        client_uuid,
        _payload(full_name="CEO Test", email="ceo@test.es"),
    )
    # P3 · el metodo devuelve ahora (contacto, desplazados): lo que la
    # asignacion se lleva por delante deja de desaparecer en silencio.
    updated, desplazados = await svc.assign_ens_required_role(
        contact.id,
        "sponsor",
        notes="Decision-maker proyecto · firma E-028",
    )

    assert desplazados == {}, "no habia nada que desplazar en este caso"
    assert updated.role_ens_required == "sponsor"
    assert updated.contact_role_notes == "Decision-maker proyecto · firma E-028"


# ====================================================================
# Test 2 · status endpoint
# ====================================================================


@pytest.mark.asyncio
async def test_ens_required_roles_status_endpoint(db: AsyncSession):
    """get_ens_required_roles_status · 3/6 assigned · missing list correcta."""
    client_id, project_id = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id)
    svc = ClientContactService(db)

    # Asignar 3/6 roles
    for idx, role in enumerate([
        "sponsor",
        "responsable_seguridad",
        "responsable_sistema",
    ]):
        contact = await svc.create_contact(
            client_uuid,
            _payload(
                full_name=f"Persona {role}",
                email=f"p{idx}@test.es",
            ),
        )
        await svc.assign_ens_required_role(contact.id, role)

    status = await svc.get_ens_required_roles_status(uuid.UUID(project_id))

    assert status["total_required"] == 6
    assert status["total_assigned"] == 3
    assert status["all_assigned"] is False
    assert "responsable_informacion" in status["missing"]
    assert "responsable_servicio" in status["missing"]
    assert "administrador_seguridad" in status["missing"]
    assert status["roles"]["sponsor"] is not None
    assert status["roles"]["sponsor"]["full_name"] == "Persona sponsor"


# ====================================================================
# Test 3 · assign method
# ====================================================================


@pytest.mark.asyncio
async def test_assign_ens_required_role_method(db: AsyncSession):
    """assign + vacate methods funcionales."""
    client_id, _project_id = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id)
    svc = ClientContactService(db)

    contact = await svc.create_contact(
        client_uuid,
        _payload(full_name="X", email="x@test.es"),
    )

    # Assign role
    await svc.assign_ens_required_role(contact.id, "responsable_seguridad")
    after_assign = await db.execute(
        text(
            "SELECT role_ens_required FROM client_contacts WHERE id = :cid"
        ),
        {"cid": str(contact.id)},
    )
    assert after_assign.scalar() == "responsable_seguridad"

    # Vacate
    await svc.vacate_ens_required_role(contact.id)
    after_vacate = await db.execute(
        text(
            "SELECT role_ens_required, contact_role_notes "
            "FROM client_contacts WHERE id = :cid"
        ),
        {"cid": str(contact.id)},
    )
    row = after_vacate.first()
    assert row[0] is None
    assert row[1] is None


# ====================================================================
# Test 4 · validator blocks E-040 when missing
# ====================================================================


@pytest.mark.asyncio
async def test_validator_blocks_when_roles_missing_e040(db: AsyncSession):
    """Validator E-040 blocks · recoverable=true · blockers list per role."""
    _client_id, project_id = await setup_test_project(db)

    result = await validate_ens_required_roles_assigned(
        db, uuid.UUID(project_id), document_type="E-040"
    )
    assert result.valid is False
    assert result.recoverable is True
    assert len(result.blockers) == 6
    assert any("Sponsor" in b for b in result.blockers)
    assert any("Responsable de la Seguridad" in b for b in result.blockers)


# ====================================================================
# Test 5 · validator passes when complete
# ====================================================================


@pytest.mark.asyncio
async def test_validator_passes_when_roles_complete_e040(db: AsyncSession):
    """Validator passes cuando 6/6 ENS_REQUIRED roles asignados."""
    client_id, project_id = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id)

    await _assign_all_six_roles(db, client_uuid)

    result = await validate_ens_required_roles_assigned(
        db, uuid.UUID(project_id), document_type="E-040"
    )
    assert result.valid is True
    assert result.blockers == []


# ====================================================================
# Test 6 · validator skips non-ENS docs
# ====================================================================


@pytest.mark.asyncio
async def test_validator_skips_when_doc_not_in_required_set(db: AsyncSession):
    """Validator skips si doc no esta en DOCUMENTS_REQUIRE_ENS_ROLES (ej E-001)."""
    _client_id, project_id = await setup_test_project(db)

    # E-001 ficha resumen NO requiere stakeholders
    result = await validate_ens_required_roles_assigned(
        db, uuid.UUID(project_id), document_type="E-001"
    )
    assert result.valid is True
    assert result.blockers == []


# ====================================================================
# Test 7 · reassign role to different contact (auto-vacate previous)
# ====================================================================


@pytest.mark.asyncio
async def test_admin_can_reassign_role_to_different_contact(db: AsyncSession):
    """Reassign role · contact previo se vacate automáticamente."""
    client_id, _project_id = await setup_test_project(db)
    client_uuid = uuid.UUID(client_id)
    svc = ClientContactService(db)

    contact_a = await svc.create_contact(
        client_uuid,
        _payload(full_name="Marcos A", email="a@test.es"),
    )
    contact_b = await svc.create_contact(
        client_uuid,
        _payload(full_name="Lucia B", email="b@test.es"),
    )

    await svc.assign_ens_required_role(contact_a.id, "responsable_seguridad")
    await svc.assign_ens_required_role(contact_b.id, "responsable_seguridad")

    # contact_a should be auto-vacated
    after = await db.execute(
        text(
            "SELECT id, role_ens_required FROM client_contacts "
            "WHERE id IN (:a, :b)"
        ),
        {"a": str(contact_a.id), "b": str(contact_b.id)},
    )
    rows = {str(r[0]): r[1] for r in after.all()}
    assert rows[str(contact_a.id)] is None
    assert rows[str(contact_b.id)] == "responsable_seguridad"


# ====================================================================
# Test 8 · constraint enforces enum
# ====================================================================


@pytest.mark.asyncio
async def test_constraint_enforces_valid_role_values(db: AsyncSession):
    """CHECK constraint rechaza valores fuera del enum 6 roles."""
    client_id, _project_id = await setup_test_project(db)

    with pytest.raises(IntegrityError) as exc:
        await db.execute(
            text(
                "INSERT INTO client_contacts "
                "(id, client_id, full_name, email, role_title, "
                " role_category, role_ens_required, created_at) "
                "VALUES (gen_random_uuid(), :cid, 'Test Bad', "
                " 'bad@test.es', 'CEO', 'sponsor', 'INVALID_ROLE', now())"
            ),
            {"cid": client_id},
        )
        await db.flush()

    err_str = str(exc.value).lower()
    assert "ck_client_contacts_role_ens_required" in err_str or "check" in err_str


# ====================================================================
# Sub-atom 1.C.F.4 v3.10 · API PATCH/DELETE endpoints + priority per category
# ====================================================================


async def _set_project_category(
    db: AsyncSession, project_id: str, category: str,
) -> None:
    from backend.tests.conftest import _admin_setup
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :cat "
                "WHERE id = :pid"
            ),
            {"cat": category, "pid": project_id},
        )


@pytest.mark.asyncio
async def test_status_includes_priority_per_category(async_client, db):
    """GET status incluye project_category + priority + critical_missing."""
    _, project_id = await setup_test_project(db)
    await _set_project_category(db, project_id, "MEDIA")

    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_category"] == "MEDIA"
    assert "priority" in body
    # En MEDIA, sponsor + RI + RS + RSEG + RSIS = critical
    assert body["priority"]["sponsor"] == "critical"
    assert body["priority"]["responsable_seguridad"] == "critical"
    assert body["priority"]["administrador_seguridad"] == "recommended"
    # 0 asignados · 5 críticos missing
    assert body["total_assigned"] == 0
    assert len(body["critical_missing"]) == 5


@pytest.mark.asyncio
async def test_priority_basica_vs_alta(async_client, db):
    """BASICA: 3 critical · ALTA: 6 critical."""
    _, project_basica = await setup_test_project(db)
    await _set_project_category(db, project_basica, "BASICA")

    r1 = await async_client.get(
        f"/api/v1/admin/projects/{project_basica}/ens-required-roles",
    )
    body1 = r1.json()
    critical_basica = [
        r for r, p in body1["priority"].items() if p == "critical"
    ]
    assert set(critical_basica) == {
        "sponsor",
        "responsable_informacion",
        "responsable_seguridad",
    }


@pytest.mark.asyncio
async def test_patch_assign_contact_to_role(async_client, db):
    """PATCH endpoint: asigna contact a role."""
    client_id, project_id = await setup_test_project(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        uuid.UUID(client_id),
        _payload(full_name="Alicia RSEG", email="alicia@test.es"),
    )
    await db.commit()

    r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles/"
        f"responsable_seguridad",
        json={
            "contact_id": str(contact.id),
            "notes": "Firma DdA + declaración conformidad",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["contact_id"] == str(contact.id)

    # Verify status reflects assignment
    status = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles",
    )
    assert status.json()["roles"]["responsable_seguridad"] is not None
    assert status.json()["total_assigned"] == 1


@pytest.mark.asyncio
async def test_patch_invalid_role_400(async_client, db):
    """PATCH con role no canónico devuelve 400."""
    _, project_id = await setup_test_project(db)
    r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles/foo_bar",
        json={"contact_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_vacates_role(async_client, db):
    """DELETE vacates role · idempotent."""
    client_id, project_id = await setup_test_project(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        uuid.UUID(client_id),
        _payload(full_name="Bob Sponsor", email="bob@test.es"),
    )
    await svc.assign_ens_required_role(contact.id, "sponsor")
    await db.commit()

    r = await async_client.delete(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles/sponsor",
    )
    assert r.status_code == 204

    # Idempotente: segunda llamada también 204
    r2 = await async_client.delete(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles/sponsor",
    )
    assert r2.status_code == 204

    status = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/ens-required-roles",
    )
    assert status.json()["roles"]["sponsor"] is None
