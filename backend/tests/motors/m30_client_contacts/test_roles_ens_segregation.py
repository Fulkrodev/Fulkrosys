"""Tests segregación funcional roles ENS (CCN-STIC 801) · SAN-C.MB-9.5.

5 cases cubren:

1. ``test_compliant_minimal_basica`` — 4 contactos distintos en RI/RS/RSEG/RSIS
   → compliant=True para BÁSICA.
2. ``test_violation_rseg_equals_rsis_same_email`` — mismo email en RSEG y
   RSIS → violación severity ``mayor`` rule ``CCN-STIC-801``.
3. ``test_missing_required_role_basica`` — falta RSIS → violación menor
   ``CCN-STIC-801-ROL-AUSENTE``.
4. ``test_legacy_alias_rseg_aceptado`` — categoría legacy ``rseg`` cuenta
   como Responsable Seguridad para validación.
5. ``test_alta_requires_comite_seguridad`` — categoría ALTA exige miembro
   comité; sin él, missing_roles incluye ``miembro_comite_seguridad``.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.models import ClientContact
from backend.app.motors.m30_client_contacts.roles_ens import (
    RolEns,
    validate_role_segregation,
)
from backend.tests.conftest import _admin_setup


async def _create_test_client(db: AsyncSession) -> uuid.UUID:
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:id, :nombre, :cif, 'publico', now())"
            ),
            {"id": str(client_id), "nombre": f"Cliente Test {cif}", "cif": cif},
        )
    await db.flush()
    return client_id


async def _add_contact(
    db: AsyncSession,
    client_id: uuid.UUID,
    full_name: str,
    email: str,
    role_category: str,
) -> ClientContact:
    contact = ClientContact(
        client_id=client_id,
        full_name=full_name,
        email=email,
        role_title=role_category.replace("_", " ").title(),
        role_category=role_category,
    )
    async with _admin_setup(db):
        db.add(contact)
        await db.flush()
    return contact


@pytest.mark.asyncio
async def test_compliant_minimal_basica(db):
    """4 contactos distintos en RI/RS/RSEG/RSIS → compliant=True para BÁSICA."""
    client_id = await _create_test_client(db)
    await _add_contact(db, client_id, "Ana RI", "ana@x.com", RolEns.RI.value)
    await _add_contact(db, client_id, "Bob RS", "bob@x.com", RolEns.RS.value)
    await _add_contact(db, client_id, "Carla RSEG", "carla@x.com", RolEns.RSEG.value)
    await _add_contact(db, client_id, "Dario RSIS", "dario@x.com", RolEns.RSIS.value)

    report = await validate_role_segregation(db, client_id, "BASICA")
    assert report.compliant is True, f"Expected compliant, got violations: {report.violations}"
    assert not report.missing_roles
    assert not report.violations


@pytest.mark.asyncio
async def test_violation_rseg_equals_rsis_same_person(db):
    """Misma persona en RSEG+RSIS → violación CCN-STIC-801 con severidad
    CATEGORY-AWARE (P10-F03 · Ejecutable 8 Pasada 16):

    - BÁSICA: roles acumulables con medida compensatoria → severidad MENOR.
    - MEDIA/ALTA: separación obligatoria → no-conformidad MAYOR.

    El unique constraint (client_id, email) prohíbe duplicar email; el caso
    realista es la misma persona con emails personal/corporativo distintos.
    """
    client_id = await _create_test_client(db)
    await _add_contact(db, client_id, "Ana RI", "ana@x.com", RolEns.RI.value)
    await _add_contact(db, client_id, "Bob RS", "bob@x.com", RolEns.RS.value)
    # Misma persona "Carla Ruiz" con 2 contactos de email distinto, ambos roles
    await _add_contact(db, client_id, "Carla Ruiz", "carla.ruiz@x.com", RolEns.RSEG.value)
    await _add_contact(db, client_id, "Carla Ruiz", "carla.ruiz.it@x.com", RolEns.RSIS.value)

    # BÁSICA → separación admisible con compensatoria → severidad MENOR
    report_basica = await validate_role_segregation(db, client_id, "BASICA")
    assert report_basica.compliant is False
    sep_basica = [v for v in report_basica.violations if v.rule == "CCN-STIC-801"]
    assert len(sep_basica) >= 1
    assert all(v.severity == "menor" for v in sep_basica), (
        "BÁSICA: acumulación RSEG/RSIS admisible con compensatoria (P10-F03)"
    )

    # MEDIA → separación obligatoria → MAYOR
    report_media = await validate_role_segregation(db, client_id, "MEDIA")
    assert any(
        v.rule == "CCN-STIC-801" and v.severity == "mayor"
        for v in report_media.violations
    ), "MEDIA: separación RSEG≠RSIS obligatoria → no-conformidad mayor"

    # ALTA → separación obligatoria → MAYOR
    report_alta = await validate_role_segregation(db, client_id, "ALTA")
    assert any(
        v.rule == "CCN-STIC-801" and v.severity == "mayor"
        for v in report_alta.violations
    ), "ALTA: separación RSEG≠RSIS obligatoria → no-conformidad mayor"


@pytest.mark.asyncio
async def test_missing_required_role_basica(db):
    """Falta RSIS en BÁSICA → violación menor ROL-AUSENTE."""
    client_id = await _create_test_client(db)
    await _add_contact(db, client_id, "Ana RI", "ana@x.com", RolEns.RI.value)
    await _add_contact(db, client_id, "Bob RS", "bob@x.com", RolEns.RS.value)
    await _add_contact(db, client_id, "Carla", "carla@x.com", RolEns.RSEG.value)
    # Sin RSIS asignado

    report = await validate_role_segregation(db, client_id, "BASICA")
    assert report.compliant is False
    assert RolEns.RSIS.value in report.missing_roles


@pytest.mark.asyncio
async def test_legacy_alias_rseg_aceptado(db):
    """Categoría legacy ``rseg`` cuenta como Responsable Seguridad ENS."""
    client_id = await _create_test_client(db)
    await _add_contact(db, client_id, "Ana RI", "ana@x.com", RolEns.RI.value)
    await _add_contact(db, client_id, "Bob RS", "bob@x.com", RolEns.RS.value)
    # Legacy alias "rseg" (Bloque 1 RoleCategory) en lugar de "responsable_seguridad"
    await _add_contact(db, client_id, "Carla", "carla@x.com", "rseg")
    await _add_contact(db, client_id, "Dario RSIS", "dario@x.com", RolEns.RSIS.value)

    report = await validate_role_segregation(db, client_id, "BASICA")
    assert RolEns.RSEG.value not in report.missing_roles
    assert report.compliant is True


@pytest.mark.asyncio
async def test_alta_requires_comite_seguridad(db):
    """Categoría ALTA requiere miembro comité seguridad."""
    client_id = await _create_test_client(db)
    await _add_contact(db, client_id, "Ana RI", "ana@x.com", RolEns.RI.value)
    await _add_contact(db, client_id, "Bob RS", "bob@x.com", RolEns.RS.value)
    await _add_contact(db, client_id, "Carla", "carla@x.com", RolEns.RSEG.value)
    await _add_contact(db, client_id, "Dario RSIS", "dario@x.com", RolEns.RSIS.value)
    await _add_contact(db, client_id, "Eva POC", "eva@x.com", RolEns.POC.value)
    # Sin miembro_comite_seguridad

    report = await validate_role_segregation(db, client_id, "ALTA")
    assert report.compliant is False
    assert RolEns.MIEMBRO_COMITE.value in report.missing_roles
