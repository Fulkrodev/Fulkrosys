"""cif_norm (#7 · Fase 7.1): normalización + populate-on-write + dedup.

- normalize_cif limpia/uppercasea; is_valid_cif valida formato ES.
- event listeners pueblan cif_norm en CADA escritura (Lead + Client).
- find_or_create_client dedup por cif_norm (mismo CIF, formato distinto → 1 cliente).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.core.cif_norm import is_valid_cif, normalize_cif
from backend.app.models.core import Client
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)
from backend.app.motors.m13_commercial.services.lead_service import LeadService


def test_normalize_cif_cleans_and_uppercases():
    assert normalize_cif(" b-1234 5678 ") == "B12345678"
    assert normalize_cif("b1234.5678") == "B12345678"
    assert normalize_cif("B12345678") == "B12345678"
    assert normalize_cif(None) is None
    assert normalize_cif("") is None
    assert normalize_cif("   ") is None


def test_is_valid_cif():
    assert is_valid_cif("B12345678") is True    # CIF
    assert is_valid_cif("12345678Z") is True    # NIF
    assert is_valid_cif("X1234567L") is True     # NIE
    assert is_valid_cif("b-1234 5678") is True   # normaliza antes de validar
    assert is_valid_cif("nope") is False
    assert is_valid_cif(None) is False


@pytest.mark.asyncio
async def test_client_cif_norm_populated_on_write(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    c = Client(nombre="Acme", cif="B-1234 5678")
    db.add(c)
    await db.flush()
    assert c.cif_norm == "B12345678"


@pytest.mark.asyncio
async def test_lead_cif_norm_populated_on_write(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    lead = await LeadService(db).create_lead(
        empresa_nombre="Acme SL", contacto_email="a@acme.es", empresa_cif="b1234.5678",
    )
    assert lead.cif_norm == "B12345678"


@pytest.mark.asyncio
async def test_find_or_create_client_dedups_by_normalized_cif(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    # Cliente existente con un formato de CIF.
    existing = Client(nombre="Acme", cif="B-1234 5678")  # cif_norm = B12345678
    db.add(existing)
    await db.flush()
    # Lead con el MISMO CIF en OTRO formato.
    lead = await LeadService(db).create_lead(
        empresa_nombre="Acme SL", contacto_email="a@acme.es", empresa_cif="b1234.5678",
    )
    found = await CommercialWorkflowService(db)._find_or_create_client(lead)
    assert found.id == existing.id   # dedup: NO crea un segundo cliente


@pytest.mark.asyncio
async def test_find_or_create_client_creates_when_no_match(db):
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    lead = await LeadService(db).create_lead(
        empresa_nombre="NewCo SL", contacto_email="new@co.es", empresa_cif=cif,
    )
    created = await CommercialWorkflowService(db)._find_or_create_client(lead)
    assert created.cif_norm == normalize_cif(cif)   # nuevo cliente con cif_norm poblado
