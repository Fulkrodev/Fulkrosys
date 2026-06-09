"""Smoke test for MAGERIT → PILAR .mgr exporter."""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from xml.etree import ElementTree as ET

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m02_magerit.exporter_mgr import (
    MGR_SCHEMA_VERSION,
    export_to_mgr,
)
from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritAssetDependency,
    MageritThreatAssessment,
)


@pytest.mark.asyncio
async def test_export_to_mgr_generates_valid_bundle(db):
    """Create a minimal analysis with assets/dependencies/threats → export →
    verify the ``.mgr`` bundle has the expected structure.

    Runs as the ``fulkro`` superuser role so the inserts bypass RLS; the
    rest of the test runs as the normal app role.
    """
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Scratch client + project so the FK on magerit_analysis.project_id holds.
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO clients (id, nombre, cif, sector) "
        "VALUES (:cid, 'MAGERIT Test SL', :cif, 'servicios')"
    ), {"cid": str(client_id), "cif": f"B{uuid.uuid4().int % 10_000_000:07d}0"})
    await db.execute(sa_text(
        "INSERT INTO projects (id, client_id, nombre, estado, lifecycle_state) "
        "VALUES (:pid, :cid, 'Proyecto MAGERIT Test', 'ACTIVO', 'ACTIVE')"
    ), {"pid": str(project_id), "cid": str(client_id)})

    analysis = MageritAnalysis(
        project_id=project_id,
        name="AR Test Exporter .mgr",
        status="draft",
        version=1,
        methodology_version="MAGERIT v3",
        calculation_mode="qualitative",
    )
    db.add(analysis)
    await db.flush()

    asset_a = MageritAsset(
        analysis_id=analysis.id,
        code="SRV-001",
        name="Servidor clínico principal",
        asset_type_code="HW",
        value_d=8, value_i=9, value_c=9, value_a=7, value_t=6,
    )
    asset_b = MageritAsset(
        analysis_id=analysis.id,
        code="DB-001",
        name="Base de datos HCE",
        asset_type_code="D",
        value_d=9, value_i=10, value_c=10, value_a=9, value_t=8,
    )
    db.add_all([asset_a, asset_b])
    await db.flush()

    dep = MageritAssetDependency(
        analysis_id=analysis.id,
        superior_asset_id=asset_a.id,
        inferior_asset_id=asset_b.id,
        dependency_degree=1.0,
        reason="El servidor clínico depende de la BBDD HCE para operar.",
    )
    db.add(dep)

    threat = MageritThreatAssessment(
        analysis_id=analysis.id,
        asset_id=asset_b.id,
        threat_code="A.11",
        probability="M",
        degradation_c=70, degradation_i=50, degradation_a=30,
    )
    db.add(threat)
    await db.flush()

    await db.execute(sa_text("RESET ROLE"))

    # Set tenant context para SELECT bajo fulkro_app · magerit_analysis
    # tiene RLS post-SAN-B.MB-2.1.
    await db.execute(
        sa_text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )

    blob = await export_to_mgr(db, analysis.id)

    # .mgr is a ZIP bundle
    assert blob[:2] == b"PK", "expected ZIP magic header"

    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist()) >= {"analisis.xml", "manifest.json"}
        manifest = json.loads(z.read("manifest.json"))
        assert manifest["schema"] == MGR_SCHEMA_VERSION
        assert manifest["analysis_id"] == str(analysis.id)

        root = ET.fromstring(z.read("analisis.xml").decode("utf-8"))
    assert root.tag == "magerit"
    assert root.attrib["version"] == "3.0"

    header = root.find("analisis")
    assert header.find("id").text == str(analysis.id)
    assert header.find("nombre").text == "AR Test Exporter .mgr"
    assert header.find("metodologia").text == "MAGERIT v3"

    activos = list(root.find("activos").iter("activo"))
    assert len(activos) == 2
    codes = sorted(a.find("codigo").text for a in activos)
    assert codes == ["DB-001", "SRV-001"]
    for a in activos:
        if a.find("codigo").text == "SRV-001":
            dicat = a.find("valoracion_DICAT")
            assert dicat.find("D").text == "8"
            assert dicat.find("I").text == "9"

    deps = list(root.find("dependencias").iter("dependencia"))
    assert len(deps) == 1
    assert deps[0].attrib["grado"].startswith("1.0")

    amenazas = list(root.find("amenazas").iter("amenaza"))
    assert len(amenazas) == 1
    assert amenazas[0].find("threat_code").text == "A.11"
    assert amenazas[0].find("probabilidad").text == "M"

    for tag in ("salvaguardas", "riesgos", "tratamiento"):
        assert root.find(tag) is not None, f"missing {tag}"
