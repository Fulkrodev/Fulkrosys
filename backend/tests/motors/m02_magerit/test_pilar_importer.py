"""Tests PILAR XML importer + endpoint · SAN-C MB-11.4."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
)
from backend.app.motors.m02_magerit.pilar_importer import (
    PilarImportError,
    import_to_analysis,
    parse_xml,
)


_FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _read_fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


# ============================================================
# Parser unit tests
# ============================================================


def test_parse_pilar_compat_sample_detects_format():
    xml = _read_fixture("pilar_compat_sample.xml")
    parsed = parse_xml(xml)
    assert parsed.detected_format == "pilar_compat"
    assert len(parsed.assets) == 3
    assert len(parsed.threat_assessments) == 2
    assert len(parsed.safeguards) == 2


def test_parse_pilar_compat_extracts_dimensions():
    xml = _read_fixture("pilar_compat_sample.xml")
    parsed = parse_xml(xml)
    a002 = next(a for a in parsed.assets if a.code == "A-002")
    assert a002.value_d == 9
    assert a002.value_i == 9
    assert a002.value_c == 9
    assert a002.asset_type_code == "SW"


def test_parse_fulkro_native_detects_format():
    xml = _read_fixture("fulkro_native_sample.xml")
    parsed = parse_xml(xml)
    assert parsed.detected_format == "fulkro_native"
    assert len(parsed.assets) == 2
    assert parsed.assets[0].code == "FN-A-001"


def test_parse_invalid_xml_raises_clear_error():
    with pytest.raises(PilarImportError, match="mal formado"):
        parse_xml(b"<not-closed-xml>")


def test_parse_unknown_root_raises_clear_error():
    xml = b'<?xml version="1.0"?><other_root><foo/></other_root>'
    with pytest.raises(PilarImportError, match="no soportado"):
        parse_xml(xml)


def test_parse_empty_xml_raises():
    with pytest.raises(PilarImportError, match="vac"):
        parse_xml(b"")


def test_parse_missing_dimensions_returns_none():
    xml = b'''<?xml version="1.0"?>
    <magerit_analysis>
      <assets>
        <asset code="X-1" name="Sin dimensions" type="HW"/>
      </assets>
    </magerit_analysis>'''
    parsed = parse_xml(xml)
    assert parsed.assets[0].value_d is None
    assert parsed.assets[0].value_c is None


def test_parse_skips_malformed_assets_without_code_or_name():
    xml = b'''<?xml version="1.0"?>
    <magerit_analysis>
      <assets>
        <asset code="OK-1" name="Bien" type="HW"/>
        <asset name="Sin code" type="HW"/>
        <asset code="Sin name"/>
      </assets>
    </magerit_analysis>'''
    parsed = parse_xml(xml)
    assert len(parsed.assets) == 1


# ============================================================
# Import to BD tests (requires DB)
# ============================================================


async def _create_test_analysis(db) -> uuid.UUID:
    """Crea project + analysis para tests import. Usa setup_test_project."""
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    analysis = MageritAnalysis(
        project_id=project_id,
        name="Test analysis MB-11.4",
        version=1,
    )
    db.add(analysis)
    await db.flush()
    return analysis.id


@pytest.mark.asyncio
async def test_import_pilar_compat_creates_rows(db):
    analysis_id = await _create_test_analysis(db)
    parsed = parse_xml(_read_fixture("pilar_compat_sample.xml"))
    summary = await import_to_analysis(db, analysis_id, parsed)
    await db.commit()

    assert summary.assets_created == 3
    assert summary.threat_assessments_created == 2
    assert summary.safeguards_created == 2
    assert summary.detected_format == "pilar_compat"

    # Verify in DB
    assets = (await db.execute(
        select(MageritAsset).where(MageritAsset.analysis_id == analysis_id),
    )).scalars().all()
    assert len(assets) == 3
    codes = sorted(a.code for a in assets)
    assert codes == ["A-001", "A-002", "A-003"]


@pytest.mark.asyncio
async def test_import_threat_with_unknown_asset_skipped(db):
    analysis_id = await _create_test_analysis(db)
    xml = b'''<?xml version="1.0"?>
    <magerit_analysis>
      <assets>
        <asset code="OK-1" name="OK" type="HW"/>
      </assets>
      <threats>
        <threat code="E.1" asset="OK-1"><probability>M</probability></threat>
        <threat code="E.2" asset="UNKNOWN"><probability>A</probability></threat>
      </threats>
    </magerit_analysis>'''
    parsed = parse_xml(xml)
    summary = await import_to_analysis(db, analysis_id, parsed)
    assert summary.assets_created == 1
    assert summary.threat_assessments_created == 1  # UNKNOWN skipped


# ============================================================
# HTTP endpoint integration
# ============================================================


@pytest.mark.asyncio
async def test_endpoint_import_xml_returns_summary(async_client, db):
    analysis_id = await _create_test_analysis(db)
    await db.commit()

    files = {
        "file": (
            "sample.xml",
            _read_fixture("pilar_compat_sample.xml"),
            "application/xml",
        ),
    }
    response = await async_client.post(
        f"/api/v1/magerit/analysis/{analysis_id}/import-xml",
        files=files,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["detected_format"] == "pilar_compat"
    assert data["assets_created"] == 3
    assert data["threat_assessments_created"] == 2


@pytest.mark.asyncio
async def test_endpoint_preview_does_not_persist(async_client, db):
    analysis_id = await _create_test_analysis(db)
    await db.commit()

    files = {
        "file": (
            "sample.xml",
            _read_fixture("fulkro_native_sample.xml"),
            "application/xml",
        ),
    }
    response = await async_client.post(
        f"/api/v1/magerit/analysis/{analysis_id}/import-xml/preview",
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["detected_format"] == "fulkro_native"
    assert data["assets_count"] == 2
    assert "FN-A-001" in data["sample_asset_codes"]

    # Verify nothing persisted
    count = (await db.execute(
        sa_text("SELECT count(*) FROM magerit_assets WHERE analysis_id = :aid"),
        {"aid": str(analysis_id)},
    )).scalar()
    assert count == 0


@pytest.mark.asyncio
async def test_endpoint_import_unknown_root_returns_422(async_client, db):
    analysis_id = await _create_test_analysis(db)
    await db.commit()

    files = {
        "file": (
            "bad.xml",
            b'<?xml version="1.0"?><wrong_root><foo/></wrong_root>',
            "application/xml",
        ),
    }
    response = await async_client.post(
        f"/api/v1/magerit/analysis/{analysis_id}/import-xml",
        files=files,
    )
    assert response.status_code == 422
    assert "no soportado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_endpoint_import_unknown_analysis_returns_404(async_client):
    files = {
        "file": ("x.xml", b"<magerit_analysis/>", "application/xml"),
    }
    fake = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    response = await async_client.post(
        f"/api/v1/magerit/analysis/{fake}/import-xml",
        files=files,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_import_empty_file_returns_422(async_client, db):
    analysis_id = await _create_test_analysis(db)
    await db.commit()

    files = {"file": ("empty.xml", b"", "application/xml")}
    response = await async_client.post(
        f"/api/v1/magerit/analysis/{analysis_id}/import-xml",
        files=files,
    )
    assert response.status_code == 422
