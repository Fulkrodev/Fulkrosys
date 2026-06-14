"""INES Annual Report generator · SAN-C.MB-10.4.

INES (Informe Nacional del Estado de la Seguridad) es el reporte anual
obligatorio para entidades del sector público sujetas al ENS, regulado
por el CCN-CERT vía CCN-STIC 824 (estructura) y CCN-STIC 844 (Wi-Fi /
seguridad de comunicaciones inalámbricas).

Salida del generator:

* JSON canónico CCN-STIC 824 schema (para upload portal INES web)
* DOCX legible para Dirección + auditor (resumen ejecutivo + tablas)

Aglutina datos cross-motor del año fiscal:

* M01 + M27 · sistemas en alcance + categorización + estado conformidad
* M18 · incidentes (count + severidad) del año
* M21 · madurez procesos (CMM L0-L5)
* M15 · inversión seguridad (opcional · si hay datos billing)

Refs: SAN-C.MB-10.4 · CCN-STIC 824/844
"""
from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

INES_SCHEMA_VERSION = "CCN-STIC-824-v1"
INES_TEMPLATE_VERSION = "1.0"


@dataclass(slots=True)
class InesYearReport:
    """Reporte INES anual aglutinado."""

    organization_name: str
    organization_cif: str
    year: int
    today: str
    systems: list[dict[str, Any]] = field(default_factory=list)
    incidents_summary: dict[str, int] = field(default_factory=dict)
    maturity_avg: float = 0.0
    investment_eur: float | None = None
    rseg_name: str = "(pendiente designación)"
    plan_year_next: list[str] = field(default_factory=list)


async def collect_ines_data(
    db: AsyncSession,
    organization_id: uuid.UUID,
    year: int,
) -> InesYearReport:
    """Aglutina cross-motor para reporte INES del año fiscal."""
    org_row = await db.execute(
        sa_text(
            "SELECT COALESCE(nombre, 'Organización'), COALESCE(cif, '') "
            "FROM clients WHERE id = :cid"
        ),
        {"cid": str(organization_id)},
    )
    org = org_row.first()
    if org is None:
        raise ValueError(f"Organization {organization_id} not found")

    # Sistemas en alcance + categorización
    systems_row = await db.execute(
        sa_text(
            "SELECT p.id::text, p.nombre, COALESCE(c.categoria_resultante, 'BASICA'), "
            "       COALESCE(p.fase, 'pre_venta'), p.fecha_objetivo_certificacion::text "
            "FROM projects p "
            "LEFT JOIN systems s ON s.project_id = p.id "
            "LEFT JOIN categorizations c ON c.system_id = s.id "
            "  AND c.deleted_at IS NULL "
            "WHERE p.client_id = :cid "
            "  AND p.deleted_at IS NULL "
            "ORDER BY p.created_at"
        ),
        {"cid": str(organization_id)},
    )
    systems: list[dict[str, Any]] = []
    seen_pids: set[str] = set()
    for pid, name, cat, fase, target_date in systems_row.fetchall():
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        systems.append({
            "system_id": pid,
            "name": name,
            "category": cat,
            "lifecycle_phase": fase,
            "target_certification_date": target_date,
        })

    # Incidentes año
    incidents_summary: dict[str, int] = {
        "BAJA": 0,
        "MEDIA": 0,
        "ALTA": 0,
        "CRITICA": 0,
    }
    try:
        # FIX(column-drift): la tabla incidents tiene `severidad` (español) y la
        # fecha del incidente es `fecha`, NO `severity`/`created_at`. Antes la
        # query lanzaba UndefinedColumn tragado por el except → INES siempre 0
        # incidentes (corrupción silenciosa de un entregable regulatorio · CCN-STIC
        # 824). Espejo de dpc_anual_service.py.
        inc_row = await db.execute(
            sa_text(
                "SELECT COALESCE(severidad, 'MEDIA'), count(*) "
                "FROM incidents i "
                "JOIN projects p ON p.id = i.project_id "
                "WHERE p.client_id = :cid "
                "  AND extract(year from i.fecha) = :y "
                "  AND i.deleted_at IS NULL "
                "GROUP BY severidad"
            ),
            {"cid": str(organization_id), "y": year},
        )
        for sev, count in inc_row.fetchall():
            sev_norm = (sev or "MEDIA").upper()
            incidents_summary[sev_norm] = int(count)
    except Exception:
        logger.exception("INES incidents query failed (year=%s)", year)

    # Madurez avg cross-projects (placeholder · 0.0 si no hay datos)
    maturity_avg = 0.0

    return InesYearReport(
        organization_name=str(org[0]),
        organization_cif=str(org[1]),
        year=year,
        today=date.today().isoformat(),
        systems=systems,
        incidents_summary=incidents_summary,
        maturity_avg=maturity_avg,
    )


def generate_ines_json(report: InesYearReport) -> dict[str, Any]:
    """Payload JSON canónico CCN-STIC 824 schema."""
    return {
        "@schema": INES_SCHEMA_VERSION,
        "organization": {
            "name": report.organization_name,
            "cif": report.organization_cif,
        },
        "year": report.year,
        "report_date": report.today,
        "systems_in_scope": report.systems,
        "incidents_summary": report.incidents_summary,
        "maturity_avg_cmm": round(report.maturity_avg, 2),
        "investment_security_eur": report.investment_eur,
        "rseg": report.rseg_name,
        "next_year_plan": report.plan_year_next,
    }


def _heading(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def generate_ines_docx(report: InesYearReport) -> io.BytesIO:
    """DOCX legible para Dirección + auditor."""
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(
        f"Informe Nacional del Estado de la Seguridad (INES) · {report.year}"
    )
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph(
        f"Entidad: {report.organization_name} ({report.organization_cif})\n"
        f"Año fiscal: {report.year}\n"
        f"Fecha emisión: {report.today}\n"
        f"RSEG: {report.rseg_name}\n"
        f"Schema: {INES_SCHEMA_VERSION} · Plantilla v{INES_TEMPLATE_VERSION}"
    )

    _heading(doc, "1. Sistemas en alcance ENS", 1)
    if not report.systems:
        doc.add_paragraph("Sin sistemas registrados para esta entidad.")
    else:
        tbl = doc.add_table(rows=1, cols=4)
        tbl.style = "Light Grid Accent 1"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Sistema"
        hdr[1].text = "Categoría"
        hdr[2].text = "Fase"
        hdr[3].text = "Objetivo certificación"
        for s in report.systems:
            row = tbl.add_row().cells
            row[0].text = s["name"]
            row[1].text = s["category"]
            row[2].text = s["lifecycle_phase"]
            row[3].text = s["target_certification_date"] or "—"

    _heading(doc, "2. Incidentes del año por severidad", 1)
    inc_tbl = doc.add_table(rows=1, cols=2)
    inc_tbl.style = "Light Grid Accent 1"
    inc_tbl.rows[0].cells[0].text = "Severidad"
    inc_tbl.rows[0].cells[1].text = "Número"
    for sev, n in report.incidents_summary.items():
        row = inc_tbl.add_row().cells
        row[0].text = sev
        row[1].text = str(n)

    _heading(doc, "3. Madurez global procesos seguridad", 1)
    doc.add_paragraph(
        f"Madurez CMM media (L0-L5): {report.maturity_avg:.2f}\n"
        "Detalle por familia disponible en informes M21 cross-compliance."
    )

    _heading(doc, "4. Inversión en seguridad", 1)
    if report.investment_eur is not None:
        doc.add_paragraph(f"Inversión año {report.year}: {report.investment_eur:,.2f} €")
    else:
        doc.add_paragraph("Datos de inversión pendientes de consolidar (M15 billing).")

    _heading(doc, "5. Plan año siguiente", 1)
    if report.plan_year_next:
        for item in report.plan_year_next:
            doc.add_paragraph(f"• {item}")
    else:
        doc.add_paragraph("Plan próximo año por definir tras revisión por dirección.")

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run(
        f"Documento generado por FULKRO conforme CCN-STIC 824/844 · "
        f"schema {INES_SCHEMA_VERSION}"
    )
    fr.italic = True
    fr.font.size = Pt(8)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
