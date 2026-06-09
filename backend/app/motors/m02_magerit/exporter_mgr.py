"""MAGERIT v3 → PILAR ``.mgr`` exporter (best-effort).

Produces a ``.mgr`` bundle that an auditor can import into CCN's PILAR
tool. The file is a ZIP archive containing two members:

* ``analisis.xml`` — full dump of the risk analysis in MAGERIT v3 XML
  shape (activos, dependencias, amenazas, salvaguardas, riesgo,
  plan de tratamiento) with explicit DICAT dimension mapping. Column
  names and nesting follow the public MAGERIT v3 methodology
  ("Método", Libro 1 §4; "Catálogo", Libro 2).

* ``manifest.json`` — metadata header identifying the generator, the
  analysis id, and the FULKRO schema version.

PILAR's internal binary format is proprietary and not published by
CCN; the public MAGERIT methodology is the recognised standard for
ENS risk analysis evidence. This bundle provides the full MAGERIT
content — the auditor can either import the XML into PILAR via its
"importar análisis" menu or read it directly as MAGERIT-compliant
evidence.
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.dom import minidom

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritAssetDependency,
    MageritRiskCalculation,
    MageritSafeguardDeployment,
    MageritThreatAssessment,
    MageritTreatmentPlan,
)


MGR_SCHEMA_VERSION = "fulkro-mgr-1.0"


def _pretty(tree: ET.Element) -> str:
    raw = ET.tostring(tree, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def _leaf(parent: ET.Element, tag: str, value) -> None:
    if value is None or value == "":
        return
    el = ET.SubElement(parent, tag)
    el.text = str(value)


async def build_mgr_xml(
    session: AsyncSession, analysis_id: uuid.UUID
) -> str:
    """Build the ``analisis.xml`` payload of the ``.mgr`` bundle."""
    analysis = (
        await session.execute(
            select(MageritAnalysis).where(MageritAnalysis.id == analysis_id)
        )
    ).scalar_one_or_none()
    if analysis is None:
        raise ValueError(f"MAGERIT analysis not found: {analysis_id}")

    root = ET.Element(
        "magerit",
        attrib={
            "version": "3.0",
            "tool": "fulkro",
            "schema": MGR_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    header = ET.SubElement(root, "analisis")
    _leaf(header, "id", analysis.id)
    _leaf(header, "project_id", analysis.project_id)
    _leaf(header, "nombre", analysis.name)
    _leaf(header, "estado", analysis.status)
    _leaf(header, "version", analysis.version)
    _leaf(header, "metodologia", analysis.methodology_version)
    _leaf(header, "modo_calculo", analysis.calculation_mode)
    _leaf(header, "aprobado_por", analysis.approved_by)
    _leaf(header, "aprobado_at", analysis.approved_at)

    # --- activos + dependencias ---
    activos_el = ET.SubElement(root, "activos")
    assets = (await session.execute(
        select(MageritAsset).where(
            MageritAsset.analysis_id == analysis_id,
            MageritAsset.deleted_at.is_(None),
        )
    )).scalars().all()
    for a in assets:
        a_el = ET.SubElement(activos_el, "activo", attrib={"id": str(a.id)})
        _leaf(a_el, "codigo", a.code)
        _leaf(a_el, "nombre", a.name)
        _leaf(a_el, "tipo", a.asset_type_code)
        _leaf(a_el, "descripcion", a.description)
        _leaf(a_el, "propietario", a.owner)
        val = ET.SubElement(a_el, "valoracion_DICAT")
        _leaf(val, "D", a.value_d)
        _leaf(val, "I", a.value_i)
        _leaf(val, "C", a.value_c)
        _leaf(val, "A", a.value_a)
        _leaf(val, "T", a.value_t)
        if any(v is not None for v in (
            a.accumulated_d, a.accumulated_i, a.accumulated_c,
            a.accumulated_a, a.accumulated_t,
        )):
            acc = ET.SubElement(a_el, "acumulado_DICAT")
            _leaf(acc, "D", a.accumulated_d)
            _leaf(acc, "I", a.accumulated_i)
            _leaf(acc, "C", a.accumulated_c)
            _leaf(acc, "A", a.accumulated_a)
            _leaf(acc, "T", a.accumulated_t)

    deps_el = ET.SubElement(root, "dependencias")
    deps = (await session.execute(
        select(MageritAssetDependency).where(
            MageritAssetDependency.analysis_id == analysis_id
        )
    )).scalars().all()
    for d in deps:
        dep_el = ET.SubElement(deps_el, "dependencia", attrib={
            "superior": str(d.superior_asset_id),
            "inferior": str(d.inferior_asset_id),
            "grado": f"{float(d.dependency_degree):.4f}"
                     if d.dependency_degree is not None else "1.0000",
        })
        if d.reason:
            _leaf(dep_el, "motivo", d.reason)

    # --- amenazas ---
    thr_el = ET.SubElement(root, "amenazas")
    threats = (await session.execute(
        select(MageritThreatAssessment).where(
            MageritThreatAssessment.analysis_id == analysis_id
        )
    )).scalars().all()
    for t in threats:
        t_el = ET.SubElement(thr_el, "amenaza")
        _leaf(t_el, "asset_id", t.asset_id)
        _leaf(t_el, "threat_code", t.threat_code)
        _leaf(t_el, "probabilidad", t.probability)
        deg = ET.SubElement(t_el, "degradacion_DICAT")
        _leaf(deg, "D", t.degradation_d)
        _leaf(deg, "I", t.degradation_i)
        _leaf(deg, "C", t.degradation_c)
        _leaf(deg, "A", t.degradation_a)
        _leaf(deg, "T", t.degradation_t)

    # --- salvaguardas ---
    sg_el = ET.SubElement(root, "salvaguardas")
    safeguards = (await session.execute(
        select(MageritSafeguardDeployment).where(
            MageritSafeguardDeployment.analysis_id == analysis_id
        )
    )).scalars().all()
    for s in safeguards:
        s_el = ET.SubElement(sg_el, "salvaguarda")
        _leaf(s_el, "safeguard_code", s.safeguard_code)
        _leaf(s_el, "estado", s.status)
        _leaf(s_el, "eficacia", s.efficacy)
        _leaf(s_el, "tipo_efecto", s.effect_type)
        _leaf(s_el, "responsable", s.responsible)
        _leaf(s_el, "notas", s.notes)

    # --- riesgo ---
    r_el = ET.SubElement(root, "riesgos")
    risks = (await session.execute(
        select(MageritRiskCalculation).where(
            MageritRiskCalculation.analysis_id == analysis_id
        )
    )).scalars().all()
    for r in risks:
        rw = ET.SubElement(r_el, "riesgo")
        _leaf(rw, "asset_id", r.asset_id)
        _leaf(rw, "threat_code", r.threat_code)
        _leaf(rw, "dimension", r.dimension)
        _leaf(rw, "impacto_intrinseco", r.impact_intrinsic)
        _leaf(rw, "riesgo_intrinseco_acumulado", r.risk_intrinsic_accumulated)
        _leaf(rw, "riesgo_intrinseco_repercutido", r.risk_intrinsic_repercuted)
        _leaf(rw, "impacto_efectivo", r.impact_effective)
        _leaf(rw, "riesgo_efectivo", r.risk_effective)
        _leaf(rw, "riesgo_residual", r.risk_residual)
        _leaf(rw, "nivel_riesgo", r.risk_level)

    # --- plan de tratamiento ---
    tp_el = ET.SubElement(root, "tratamiento")
    plans = (await session.execute(
        select(MageritTreatmentPlan).where(
            MageritTreatmentPlan.analysis_id == analysis_id,
            MageritTreatmentPlan.deleted_at.is_(None),
        )
    )).scalars().all()
    for p in plans:
        pp = ET.SubElement(tp_el, "accion")
        _leaf(pp, "asset_id", p.asset_id)
        _leaf(pp, "threat_code", p.threat_code)
        _leaf(pp, "dimension", p.dimension)
        _leaf(pp, "nivel_riesgo_actual", p.current_risk_level)
        _leaf(pp, "riesgo_actual", p.current_risk_value)
        _leaf(pp, "decision", p.treatment)
        _leaf(pp, "accion", p.action_description)
        _leaf(pp, "salvaguardas_propuestas",
              ",".join(p.proposed_safeguards) if p.proposed_safeguards else None)
        _leaf(pp, "nivel_riesgo_objetivo", p.target_risk_level)
        _leaf(pp, "responsable", p.responsible)
        _leaf(pp, "plazo", p.deadline)

    return _pretty(root)


async def export_to_mgr(
    session: AsyncSession, analysis_id: uuid.UUID
) -> bytes:
    """Package the analysis as a ``.mgr`` ZIP bundle (XML + manifest)."""
    xml = await build_mgr_xml(session, analysis_id)
    manifest = {
        "generator": "FULKRO Motor 2",
        "schema": MGR_SCHEMA_VERSION,
        "analysis_id": str(analysis_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Bundle MAGERIT v3 generado por el consultor. El XML incluido "
            "es conforme a la metodología pública del CCN y puede "
            "importarse en PILAR (menú 'Importar análisis'). El formato "
            "binario propietario de PILAR no está publicado por el CCN; "
            "este bundle implementa el equivalente documental público."
        ),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("analisis.xml", xml)
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return buf.getvalue()
