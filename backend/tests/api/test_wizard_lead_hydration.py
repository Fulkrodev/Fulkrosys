"""#7.5 · hidratación del wizard desde lead + persistencia de campos.

- POST create-project persiste domicilio_fiscal/web/persona_contacto (clients) +
  cargo (client_users) que antes se tiraban.
- GET /prefill mapea el lead a los campos del wizard (+ 404 si no existe).
- create-project con lead_id: promueve el proyecto LIGERO (no duplica · 2-A) o
  crea fresco enlazando convertido_a_proyecto_id.
- lead_id ausente → comportamiento idéntico (equivalencia · cubierta además por
  test_admin_diagnostico_wizard).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService
from backend.tests.api.test_admin_diagnostico_wizard import _build_valid_payload
from backend.tests.conftest import _admin_setup


WIZARD_URL = "/api/v1/admin/diagnostico-wizard/create-project"
PREFILL_URL = "/api/v1/admin/diagnostico-wizard/prefill"


async def _make_lead(db, *, cif, papel="alojamos_tratamos_datos", categoria="MEDIA"):
    """Crea un lead (bypass RLS para el setup) en la sesión compartida."""
    async with _admin_setup(db):
        lead = await LeadService(db).create_lead(
            empresa_nombre="Hidratada SL", contacto_email="lead@hidratada.es",
            empresa_cif=cif, sector="consultoría TIC",
            categoria_objetivo_ens=categoria,
        )
        lead.papel_aapp = papel
        await db.flush()
    return lead


# ─────────────────────────── persistencia 4 campos ───────────────────────────

@pytest.mark.asyncio
async def test_create_project_persists_dropped_fields(async_client, db):
    """Los 4 campos que antes se tiraban ahora se persisten."""
    payload = _build_valid_payload()
    cif = payload["step1_datos_cliente"]["cif"]

    r = await async_client.post(WIZARD_URL, json=payload)
    assert r.status_code == 201, r.text

    async with _admin_setup(db):
        row = (await db.execute(text(
            "SELECT domicilio_fiscal, web, persona_contacto FROM clients WHERE cif = :cif"
        ), {"cif": cif})).first()
        cargo = await db.scalar(text(
            "SELECT cargo FROM client_users WHERE email = :e"
        ), {"e": payload["step5_first_user"]["email"]})

    assert row is not None
    assert row[0] == "Calle Mayor 1, Madrid"        # domicilio_fiscal
    assert row[1] == "https://test-diagnostico.es"  # web
    assert row[2] == "Ana García"                   # persona_contacto
    assert cargo == "CISO"                           # client_users.cargo


# ───────────────────────────────── prefill ───────────────────────────────────

@pytest.mark.asyncio
async def test_prefill_maps_lead_fields(async_client, db):
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await _make_lead(db, cif=cif)

    r = await async_client.get(PREFILL_URL, params={"lead_id": str(lead.id)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["razon_social"] == "Hidratada SL"
    assert body["cif"] == cif
    assert body["sector_industrial"] == "consultoría TIC"
    assert body["contacto_email"] == "lead@hidratada.es"
    assert body["categoria_preliminar"] == "MEDIA"
    assert body["papel_aapp"] == "alojamos_tratamos_datos"
    assert body["has_lightweight_project"] is False  # aún sin proyecto


@pytest.mark.asyncio
async def test_prefill_404_when_lead_missing(async_client):
    r = await async_client.get(PREFILL_URL, params={"lead_id": str(uuid.uuid4())})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_prefill_detects_lightweight_project(async_client, db):
    """has_lightweight_project=True cuando el lead SÍ tiene proyecto ligero.

    Regresión del bug de RLS: leer projects sin fijar contexto daba siempre False.
    """
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await _make_lead(db, cif=cif)
    async with _admin_setup(db):
        await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)

    r = await async_client.get(PREFILL_URL, params={"lead_id": str(lead.id)})
    assert r.status_code == 200, r.text
    assert r.json()["has_lightweight_project"] is True


# ───────────────────── edge: lead sin CIF (placeholder) ──────────────────────

@pytest.mark.asyncio
async def test_create_from_lead_placeholder_cif_reuses_by_email(async_client, db):
    """Lead SIN CIF (cliente ligero con CIF placeholder) → el wizard con CIF real
    REUSA el ligero (matchea por email del lead, no por CIF) y promueve el CIF."""
    email = f"sincif-{uuid.uuid4().hex[:8]}@hidratada.es"
    async with _admin_setup(db):
        lead = await LeadService(db).create_lead(
            empresa_nombre="SinCif SL", contacto_email=email,
            empresa_cif=None, categoria_objetivo_ens="MEDIA",
        )
        lead.papel_aapp = "alojamos_tratamos_datos"
        await db.flush()
        light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)
        light_id = light.id
        light_client_id = light.client_id

    real_cif = f"B{uuid.uuid4().hex[:8].upper()}"
    payload = _build_valid_payload(cif=real_cif)
    payload["step1_datos_cliente"]["contacto_email"] = email  # match por email del lead
    payload["lead_id"] = str(lead.id)

    r = await async_client.post(WIZARD_URL, json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["project_id"] == str(light_id)  # MISMO proyecto (reuse vía email)

    async with _admin_setup(db):
        n = await db.scalar(text(
            "SELECT count(*) FROM projects WHERE client_id = :cid"
        ), {"cid": str(light_client_id)})
        cif_now = await db.scalar(text(
            "SELECT cif FROM clients WHERE id = :cid"
        ), {"cid": str(light_client_id)})
    assert n == 1              # NO duplica
    assert cif_now == real_cif  # CIF placeholder promovido al real


# ─────────────────────── create desde lead: 2 ramas ──────────────────────────

@pytest.mark.asyncio
async def test_create_from_lead_promotes_lightweight_no_duplicate(async_client, db):
    """Rama A · lead con proyecto ligero → promueve el MISMO (no duplica)."""
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await _make_lead(db, cif=cif)
    async with _admin_setup(db):
        light = await CommercialWorkflowService(db).create_lightweight_project_for_lead(lead)
        light_id = light.id
        client_id = light.client_id

    payload = _build_valid_payload(cif=cif)  # MISMO CIF que el lead/ligero
    payload["lead_id"] = str(lead.id)

    r = await async_client.post(WIZARD_URL, json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["project_id"] == str(light_id)  # MISMO proyecto

    async with _admin_setup(db):
        n = await db.scalar(text(
            "SELECT count(*) FROM projects WHERE client_id = :cid"
        ), {"cid": str(client_id)})
        fase = await db.scalar(text(
            "SELECT fase FROM projects WHERE id = :id"
        ), {"id": str(light_id)})
        papel = await db.scalar(text(
            "SELECT papel_aapp FROM projects WHERE id = :id"
        ), {"id": str(light_id)})
        domicilio = await db.scalar(text(
            "SELECT domicilio_fiscal FROM clients WHERE id = :cid"
        ), {"cid": str(client_id)})

    assert n == 1                               # NO duplica
    assert fase == "onboarding"                 # promovido (ya no ligero)
    assert papel == "alojamos_tratamos_datos"   # papel_aapp del lead
    assert domicilio == "Calle Mayor 1, Madrid"  # 4 campos persistidos en reuse


@pytest.mark.asyncio
async def test_create_from_lead_without_lightweight_links(async_client, db):
    """Rama B · lead sin proyecto ligero → crea fresco + enlaza el lead."""
    lead_cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await _make_lead(db, cif=lead_cif)

    payload = _build_valid_payload()  # CIF fresco distinto (no existe cliente)
    payload["lead_id"] = str(lead.id)

    r = await async_client.post(WIZARD_URL, json=payload)
    assert r.status_code == 201, r.text
    project_id = r.json()["project_id"]

    async with _admin_setup(db):
        convertido = await db.scalar(text(
            "SELECT convertido_a_proyecto_id FROM leads WHERE id = :id"
        ), {"id": str(lead.id)})
        audit = await db.scalar(text(
            "SELECT count(*) FROM audit_log WHERE accion = 'lead.converted_to_project' "
            "AND project_id = :pid AND payload_new->>'source' = 'wizard'"
        ), {"pid": project_id})
    assert str(convertido) == project_id  # lead enlazado al proyecto creado
    assert audit == 1  # #7.6 · audit_log R6 conversión wizard
