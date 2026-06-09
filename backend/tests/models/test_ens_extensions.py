"""Tests for ENS corpus extension tables."""
import uuid

import pytest

from backend.app.models.ens_extensions import (
    ENSMeasureDimension,
    ENSMeasureEvidenciaType,
    ENSMeasureGuiaCCN,
    ENSMeasureRefuerzo,
)


# Sentinel measure_code "test.fixture.X" para evitar colisión con seed canónico
# SAN-C.MB-9.1 (filas reales del Anexo II RD 311/2022).
_TEST_CODE = "test.fixture.x"


@pytest.mark.asyncio
async def test_insert_ens_measure_refuerzo(db):
    r = ENSMeasureRefuerzo(
        measure_code=_TEST_CODE,
        refuerzo_level="+R1",
        applicable_categories={"ALTA": True, "MEDIA": True},
        description="Refuerzo R1 para control de acceso.",
    )
    db.add(r)
    await db.flush()
    assert r.id is not None


@pytest.mark.asyncio
async def test_insert_ens_measure_dimension(db):
    d = ENSMeasureDimension(
        measure_code=_TEST_CODE,
        refuerzo_level=None,
        dimension="C",
    )
    db.add(d)
    await db.flush()
    assert d.id is not None


@pytest.mark.asyncio
async def test_insert_ens_measure_guia_ccn(db):
    g = ENSMeasureGuiaCCN(
        measure_code=_TEST_CODE,
        guia_code="CCN-STIC-804",
        section_ref="4.2.1",
        relevance="develops",
    )
    db.add(g)
    await db.flush()
    assert g.id is not None


@pytest.mark.asyncio
async def test_insert_ens_measure_evidencia_type(db):
    e = ENSMeasureEvidenciaType(
        measure_code=_TEST_CODE,
        evidence_type="screenshot",
        description="Captura de pantalla del panel de control de acceso.",
        freshness_days=90,
        applicable_categories={"ALTA": True},
    )
    db.add(e)
    await db.flush()
    assert e.id is not None
    assert e.is_mandatory is True
