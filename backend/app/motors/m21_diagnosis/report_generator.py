"""Generador del informe de diagnostico Fase 1.

Toma un DiagnosisRun completado, construye un report_data JSON estructurado
con todas las secciones del informe, y renderiza a DOCX via docxtpl.

El informe es el entregable que Marcos presenta al Comite del cliente.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import DiagnosisRun

from .quickwins import generate_quick_wins


REPO_ROOT = Path(__file__).resolve().parents[4]
REPORTS_DIR = REPO_ROOT / "var" / "reports"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "informe_fase1_template.docx"


class ReportGeneratorError(ValueError):
    pass


def _ensure_reports_dir(project_id: uuid.UUID) -> Path:
    d = REPORTS_DIR / str(project_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _load_run(session: AsyncSession, run_id: uuid.UUID) -> DiagnosisRun:
    r = await session.execute(select(DiagnosisRun).where(DiagnosisRun.id == run_id))
    run = r.scalar_one_or_none()
    if run is None:
        raise ReportGeneratorError(f"DiagnosisRun {run_id} no existe")
    return run


async def generate_report(session: AsyncSession, run_id: uuid.UUID) -> dict:
    """Genera report_data estructurado desde un diagnosis_run completado."""
    run = await _load_run(session, run_id)
    if run.status != "completed":
        raise ReportGeneratorError(
            f"DiagnosisRun {run_id} no esta completado (status: {run.status})"
        )

    diagnosis_data = {
        "stakeholder_analysis": run.stakeholder_analysis or {},
        "process_inventory": run.process_inventory or {},
        "compliance_detection": run.compliance_detection or {},
        "maturity_scoring": run.maturity_scoring or {},
    }

    quick_wins = generate_quick_wins(diagnosis_data)

    stakeholders = run.stakeholder_analysis or {}
    processes = run.process_inventory or {}
    compliance = run.compliance_detection or {}
    maturity = run.maturity_scoring or {}
    overall = maturity.get("overall", {}) or {}

    report_data = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "diagnosis_run_id": str(run.id),
            "project_id": str(run.project_id),
        },
        "resumen_ejecutivo": {
            "maturity_level": overall.get("level", 0),
            "maturity_label": overall.get("label", "L0 - Inexistente"),
            "critical_gaps": stakeholders.get("critical_gaps", 0),
            "total_people": stakeholders.get("total_people", 0),
            "total_processes": processes.get("total_processes", 0),
            "normativas_aplicables": compliance.get("total_applicable", 0),
            "quick_wins_count": len(quick_wins),
        },
        "stakeholders": stakeholders,
        "processes": processes,
        "compliance": compliance,
        "maturity": maturity,
        "quick_wins": quick_wins,
        "recomendaciones_fase_2": _generate_recommendations(diagnosis_data, quick_wins),
    }

    run.report_data = report_data
    await session.commit()

    return {
        "run_id": str(run.id),
        "project_id": str(run.project_id),
        "report_data": report_data,
        "quick_wins_count": len(quick_wins),
        "status": "generated",
    }


async def generate_report_docx(
    session: AsyncSession, run_id: uuid.UUID
) -> Optional[str]:
    """Genera DOCX del informe. Devuelve path o None si docxtpl no disponible.

    Sesión 3B-2B.4 Phase 4 · inyecta ClientBranding (logo + colors + footer)
    desde DB · cliente piloto recibe DOCX con SU branding (audit Phase 0 D3
    finding · "PDF reports NO branding" resolved).
    """
    run = await _load_run(session, run_id)
    if run.report_data is None:
        raise ReportGeneratorError(
            "Genera el report_data primero (POST /generate-report)"
        )

    try:
        from docxtpl import DocxTemplate, InlineImage
        from docx.shared import Mm
    except ImportError:
        return None

    if not TEMPLATE_PATH.exists():
        _generate_provisional_template(TEMPLATE_PATH)

    # Phase 4 · fetch cliente branding (logo + colors + footer) ANTES render.
    from backend.app.core.branding import build_branding_pdf_context

    branding = await build_branding_pdf_context(session, run.project_id)

    doc = DocxTemplate(str(TEMPLATE_PATH))
    context = _build_docx_context(run.report_data)
    context["branding"] = branding.template_dict()
    if branding.logo_path and branding.logo_path.exists():
        context["branding"]["logo_image"] = InlineImage(
            doc, str(branding.logo_path), height=Mm(12),
        )
    doc.render(context)

    output_dir = _ensure_reports_dir(run.project_id)
    output_path = output_dir / f"informe_fase1_{run.id}.docx"
    doc.save(str(output_path))

    # Cleanup temp logo file · non-fatal si falla.
    if branding.logo_path and branding.logo_path.exists():
        try:
            branding.logo_path.unlink()
        except OSError:
            pass

    run.report_docx_path = str(output_path)
    await session.commit()

    return str(output_path)


def _generate_recommendations(
    diagnosis_data: dict, quick_wins: list[dict]
) -> list[dict]:
    """Recomendaciones deterministas para Fase 2."""
    recs: list[dict] = []

    maturity = diagnosis_data.get("maturity_scoring", {}) or {}
    overall_level = (maturity.get("overall", {}) or {}).get("level", 0)

    if overall_level <= 1:
        recs.append({
            "prioridad": "alta",
            "area": "general",
            "recomendacion": (
                "La organizacion tiene madurez L0-L1. Empezar por marco organizativo: "
                "nombrar roles, aprobar politica de seguridad, constituir comite."
            ),
            "esfuerzo_estimado_horas": 20,
        })

    stakeholders = diagnosis_data.get("stakeholder_analysis", {}) or {}
    critical_gaps = stakeholders.get("critical_gaps", 0)
    if critical_gaps > 0:
        recs.append({
            "prioridad": "critica",
            "area": "organizacion",
            "recomendacion": (
                f"Faltan {critical_gaps} roles ENS obligatorios. "
                "Nombrar antes de cualquier otra accion."
            ),
            "esfuerzo_estimado_horas": 2,
        })

    compliance = diagnosis_data.get("compliance_detection", {}) or {}
    if compliance.get("total_applicable", 0) > 2:
        recs.append({
            "prioridad": "media",
            "area": "compliance",
            "recomendacion": (
                f"Se aplican {compliance['total_applicable']} normativas. "
                "Aprovechar cross-compliance para reducir esfuerzo duplicado."
            ),
            "esfuerzo_estimado_horas": 8,
        })

    for qw in quick_wins[:3]:
        recs.append({
            "prioridad": "alta",
            "area": "quick_win",
            "recomendacion": qw["titulo"],
            "esfuerzo_estimado_horas": qw["horas_estimadas"],
            "medida_ens": qw.get("medida_ens"),
        })

    return recs


def _build_docx_context(report_data: dict) -> dict:
    """Mapea report_data a contexto Jinja2 para el template DOCX."""
    resumen = report_data.get("resumen_ejecutivo", {}) or {}
    maturity = report_data.get("maturity", {}) or {}
    domains = maturity.get("domains", {}) or {}

    return {
        "fecha_generacion": (report_data.get("meta", {}) or {}).get("generated_at", ""),
        "project_id": (report_data.get("meta", {}) or {}).get("project_id", ""),
        "maturity_level": resumen.get("maturity_level", 0),
        "maturity_label": resumen.get("maturity_label", ""),
        "critical_gaps": resumen.get("critical_gaps", 0),
        "total_people": resumen.get("total_people", 0),
        "total_processes": resumen.get("total_processes", 0),
        "normativas_count": resumen.get("normativas_aplicables", 0),
        "quick_wins_count": resumen.get("quick_wins_count", 0),
        "domains": [
            {
                "key": k,
                "name": (v or {}).get("name", k) if isinstance(v, dict) else k,
                "level": (v or {}).get("level", 0) if isinstance(v, dict) else 0,
                "label": (v or {}).get("label", "") if isinstance(v, dict) else "",
                "percentage": (v or {}).get("percentage", 0) if isinstance(v, dict) else 0,
            }
            for k, v in domains.items()
        ],
        "quick_wins": report_data.get("quick_wins", []),
        "recommendations": report_data.get("recomendaciones_fase_2", []),
        "stakeholders": report_data.get("stakeholders", {}),
        "processes": report_data.get("processes", {}),
        "compliance": report_data.get("compliance", {}),
    }


def _generate_provisional_template(path: Path) -> None:
    """Crea el template DOCX provisional con python-docx.

    Sesión 3B-2B.4 Phase 4 · header includes optional cliente logo InlineImage
    + footer includes branding.footer_text. Templates con branding NULL caen
    gracefully a text fallback (M06 pattern reused).
    """
    from docx import Document

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    # Phase 4 · header con logo cliente (InlineImage si has_logo · text fallback)
    doc.add_paragraph("{% if branding.has_logo %}{{ branding.logo_image }}{% else %}{{ branding.client_name|upper }}{% endif %}")

    doc.add_heading("Informe de Diagnostico ENS - Fase 1", level=0)
    doc.add_paragraph("Fecha: {{ fecha_generacion }}")
    doc.add_paragraph("Proyecto: {{ project_id }}")

    doc.add_heading("Resumen Ejecutivo", level=1)
    doc.add_paragraph("Nivel de madurez global: {{ maturity_label }} (L{{ maturity_level }})")
    doc.add_paragraph("Gaps criticos (roles ENS): {{ critical_gaps }}")
    doc.add_paragraph("Personas identificadas: {{ total_people }}")
    doc.add_paragraph("Procesos inventariados: {{ total_processes }}")
    doc.add_paragraph("Normativas aplicables: {{ normativas_count }}")
    doc.add_paragraph("Quick wins identificados: {{ quick_wins_count }}")

    doc.add_heading("Madurez por dominio", level=1)
    doc.add_paragraph(
        "{% for d in domains %}- {{ d.name }}: {{ d.label }} ({{ d.percentage }}%)\n{% endfor %}"
    )

    doc.add_heading("Quick Wins", level=1)
    doc.add_paragraph(
        "{% for qw in quick_wins %}* {{ qw.titulo }} "
        "[{{ qw.impacto }}/{{ qw.esfuerzo }}, {{ qw.horas_estimadas }}h] - {{ qw.medida_ens }}\n"
        "  {{ qw.descripcion }}\n{% endfor %}"
    )

    doc.add_heading("Recomendaciones Fase 2", level=1)
    doc.add_paragraph(
        "{% for r in recommendations %}[{{ r.prioridad|upper }}] {{ r.recomendacion }} "
        "({{ r.esfuerzo_estimado_horas }}h)\n{% endfor %}"
    )

    # Phase 4 · footer cliente branding · graceful empty si NO set
    doc.add_paragraph("{{ branding.footer_text }}")

    doc.save(str(path))
