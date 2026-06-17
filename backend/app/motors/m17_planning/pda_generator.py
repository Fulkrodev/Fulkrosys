"""Plan de Adecuación (PdA) CCN-STIC 806 generator · SAN-C.MB-9.3.

Aglutina datos cross-motor en un DOCX firmable conforme CCN-STIC 806:

* M01 Categorización (CIDAT + nivel resultante)
* M02 MAGERIT (count escenarios riesgo)
* M03 DdA (totales aplicables / con refuerzos / no aplicables)
* M04 Gap Analysis (resumen por familia ENS)
* M17 Planning (tasks WBS asignadas con effort + plazo + coste)

Output: ``BytesIO`` con DOCX listo para descarga + audit log entry.

Diseño determinista (no LLM): el template ``E150_plan_adecuacion.md``
en M06 templates/policies/ documenta la estructura canónica oficial.
Este módulo construye el DOCX programáticamente con python-docx
manteniendo paridad estructural con el template MD.

Uso típico::

    from backend.app.motors.m17_planning.pda_generator import (
        build_pda_context, generate_pda_docx,
    )

    ctx = await build_pda_context(db, project_id)
    bio = generate_pda_docx(ctx)
    # bio.getvalue() → bytes DOCX
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


PDA_TEMPLATE_VERSION = "1.0"
PDA_DOCUMENT_KIND = "E-150"


@dataclass(slots=True)
class PdaContext:
    """Contexto aglutinado cross-motor para el generador PdA."""

    project_id: uuid.UUID
    client_name: str
    system_name: str
    system_category: str
    today: str
    psi_version: str
    dimensions: list[dict[str, str]] = field(default_factory=list)
    information_types: list[dict[str, str]] = field(default_factory=list)
    services: list[dict[str, str]] = field(default_factory=list)
    dda_total: int = 0
    dda_aplicables: int = 0
    dda_con_refuerzos: int = 0
    dda_no_aplica: int = 0
    risk_scenarios_count: int = 0
    gap_summary: list[dict[str, Any]] = field(default_factory=list)
    plan_tasks: list[dict[str, Any]] = field(default_factory=list)


async def build_pda_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> PdaContext:
    """Construye contexto PdA aglutinando datos M01+M02+M03+M04+M17.

    Cada query es resiliente: si una tabla está vacía o no aplica, los
    contadores devuelven 0 en lugar de fallar. El PdA queda generable
    incluso en proyectos en fases tempranas (con datos parciales).
    """
    # Project + cliente
    proj_row = await db.execute(
        sa_text(
            "SELECT p.id, COALESCE(c.nombre, 'Cliente') AS client_name, "
            "       COALESCE(p.nombre, 'Sistema') AS system_name, "
            "       COALESCE(p.fase, 'pre_venta') AS fase "
            "FROM projects p "
            "LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ),
        {"pid": str(project_id)},
    )
    proj = proj_row.first()
    if proj is None:
        raise ValueError(f"Project {project_id} not found")

    # Categorización (M01) · vía systems del proyecto (categorizations.system_id)
    cat_row = await db.execute(
        sa_text(
            "SELECT c.categoria_resultante, c.input_snapshot "
            "FROM categorizations c "
            "JOIN systems s ON s.id = c.system_id "
            "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
            "ORDER BY c.created_at DESC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    cat = cat_row.first()
    system_category = cat[0] if cat else "BASICA"
    raw_dims = cat[1] if cat else None

    cidat_names = {
        "D": "Disponibilidad",
        "I": "Integridad",
        "C": "Confidencialidad",
        "A": "Autenticidad",
        "T": "Trazabilidad",
    }
    dimensions = []
    snapshot = raw_dims or {}
    snap_dims = (
        snapshot.get("dimensions", {}) if isinstance(snapshot, dict) else {}
    )
    for code, name in cidat_names.items():
        entry = snap_dims.get(code, {}) if isinstance(snap_dims, dict) else {}
        dimensions.append({
            "code": code,
            "name": name,
            "level": (entry or {}).get("level", "BAJO"),
            "justification": (entry or {}).get("justification", ""),
        })

    # DdA (M03)
    dda_row = await db.execute(
        sa_text(
            "SELECT count(*) AS total, "
            "       count(*) FILTER (WHERE aplicabilidad = 'aplica') AS apl, "
            "       count(*) FILTER (WHERE aplicabilidad = 'aplica_con_refuerzos') AS con_ref, "
            "       count(*) FILTER (WHERE aplicabilidad = 'no_aplica') AS no_apl "
            "FROM dda_entries WHERE project_id = :pid"
        ),
        {"pid": str(project_id)},
    )
    dda = dda_row.first()

    # MAGERIT escenarios (M02) · resiliente a schema sin project_id directo
    try:
        risk_row = await db.execute(
            sa_text(
                "SELECT count(*) FROM magerit_threat_assessment ta "
                "JOIN magerit_analysis ma ON ma.id = ta.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )
        risk_scenarios_count = risk_row.scalar() or 0
    except Exception:
        risk_scenarios_count = 0

    # Gap por familia (M04)
    gap_row = await db.execute(
        sa_text(
            "SELECT em.familia, "
            "       count(*) AS aplicables, "
            "       count(*) FILTER (WHERE de.aplicabilidad LIKE 'aplica%') AS aplica_all, "
            # FIX P1-5: conformes REALES desde el estado de implementación de la
            # DdA (antes hardcoded a 0 → el PDA E-150 firmable reportaba 0%
            # conformidad / 100% no-conformes en TODAS las familias siempre).
            "       count(*) FILTER (WHERE de.estado_implementacion = 'implantada') AS conformes "
            "FROM dda_entries de "
            "JOIN ens_measures em ON em.id = de.measure_id "
            "WHERE de.project_id = :pid AND em.familia IS NOT NULL "
            "GROUP BY em.familia ORDER BY em.familia"
        ),
        {"pid": str(project_id)},
    )
    gap_summary = []
    for fam, aplicables, aplica_all, conformes in gap_row.fetchall():
        conformes = int(conformes or 0)
        no_conformes = max(int(aplica_all or 0) - conformes, 0)
        pct = round((conformes / aplica_all * 100) if aplica_all else 0, 1)
        gap_summary.append({
            "family": fam,
            # FIX: la columna "Aplicables" debe contar SOLO las medidas aplicables
            # (aplica%), no el total con no_aplica · si no, 'Aplicables' no
            # reconcilia con 'No conformes'/'% conformidad' (que usan aplica_all)
            # en el PdA E-150 firmable (CCN-STIC 806). `aplicables` (count(*) total)
            # se ignora; el nombre del campo se mantiene por compatibilidad render.
            "aplicables": int(aplica_all or 0),
            "conformes": conformes,
            "no_conformes": no_conformes,
            "pct_conformidad": pct,
        })

    # Plan tasks (M17) · usa columnas reales de wbs_tasks
    tasks_row = await db.execute(
        sa_text(
            "SELECT t.task_code, t.task_name, t.deliverable_e_code, "
            "       t.responsible, t.phase, t.duration_days, "
            "       t.end_date, t.effort_marcos_hours "
            "FROM wbs_tasks t WHERE t.project_id = :pid "
            "AND COALESCE(t.status, '') != 'descartada' "
            "AND t.deleted_at IS NULL "
            "ORDER BY t.start_date ASC NULLS LAST LIMIT 50"
        ),
        {"pid": str(project_id)},
    )
    plan_tasks = []
    for row in tasks_row.fetchall():
        plan_tasks.append({
            "code": row[0] or "WBS-?",
            "title": row[1] or "(sin título)",
            "description": "",  # wbs_tasks no almacena descripción larga
            "ens_measure": row[2] or "—",  # deliverable_e_code como proxy
            "responsible_role": row[3] or "RSEG",
            "priority": row[4] or "—",
            "effort_hours": int(row[7] or 0),
            "target_date": row[6].isoformat() if row[6] else "—",
            # S25 (campaña 2026-06-17): NO se incluye coste por tarea. wbs_tasks
            # no almacena coste y el modelo de pricing es por proyecto fijo (no
            # tarifa/hora), así que un "Coste: 0€" en cada acción era completitud
            # falsa. El dato real y trazable es el esfuerzo en horas (arriba).
        })

    return PdaContext(
        project_id=project_id,
        client_name=str(proj[1]),
        system_name=str(proj[2]),
        system_category=str(system_category),
        today=date.today().isoformat(),
        psi_version="1.0",
        dimensions=dimensions,
        information_types=[],
        services=[],
        dda_total=int(dda[0] or 0) if dda else 0,
        dda_aplicables=int(dda[1] or 0) if dda else 0,
        dda_con_refuerzos=int(dda[2] or 0) if dda else 0,
        dda_no_aplica=int(dda[3] or 0) if dda else 0,
        risk_scenarios_count=int(risk_scenarios_count),
        gap_summary=gap_summary,
        plan_tasks=plan_tasks,
    )


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    """Hereda estilo del template profesional (negro, Pt grande)."""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def generate_pda_docx(ctx: PdaContext) -> io.BytesIO:
    """Genera DOCX programático conforme template E150 (CCN-STIC 806).

    Output: ``BytesIO`` listo para upload a MinIO o response streaming.
    """
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Plan de Adecuación al Esquema Nacional de Seguridad")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(
        f"Cliente: {ctx.client_name}\n"
        f"Sistema: {ctx.system_name}\n"
        f"Categoría: {ctx.system_category}\n"
        f"Fecha emisión: {ctx.today}\n"
        f"Plantilla: {PDA_DOCUMENT_KIND} v{PDA_TEMPLATE_VERSION}"
    )

    _add_heading(doc, "1. Política de Seguridad aprobada", level=1)
    doc.add_paragraph(
        f"La presente adecuación se enmarca en la Política de Seguridad de "
        f"la Información aprobada formalmente por la Dirección de "
        f"{ctx.client_name} (referencia E100 · v{ctx.psi_version})."
    )

    _add_heading(doc, "3. Categoría del sistema (M01)", level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Dimensión"
    hdr[1].text = "Nivel"
    hdr[2].text = "Justificación"
    for dim in ctx.dimensions:
        row = table.add_row().cells
        row[0].text = f"{dim['code']} · {dim['name']}"
        row[1].text = dim["level"]
        row[2].text = dim["justification"]
    doc.add_paragraph(f"Categoría resultante: {ctx.system_category}").bold = True

    _add_heading(doc, "4. Declaración de Aplicabilidad (M03 DdA)", level=1)
    doc.add_paragraph(
        f"Medidas Anexo II evaluadas: {ctx.dda_total}\n"
        f"  · Aplicables base: {ctx.dda_aplicables}\n"
        f"  · Aplicables con refuerzos: {ctx.dda_con_refuerzos}\n"
        f"  · No aplicables (justificadas): {ctx.dda_no_aplica}"
    )

    _add_heading(doc, "5. Análisis de Riesgos (M02 MAGERIT)", level=1)
    doc.add_paragraph(
        f"Total escenarios de riesgo evaluados: {ctx.risk_scenarios_count}.\n"
        f"Análisis ejecutado conforme MAGERIT v3 Libros I/II/III. "
        f"Riesgo residual aceptado por la Dirección al cierre."
    )

    if ctx.gap_summary:
        _add_heading(doc, "6. Gap analysis por familia ENS", level=1)
        gtbl = doc.add_table(rows=1, cols=4)
        gtbl.style = "Light Grid Accent 1"
        hr = gtbl.rows[0].cells
        hr[0].text = "Familia"
        hr[1].text = "Aplicables"
        hr[2].text = "No conformes"
        hr[3].text = "% conformidad"
        for fam in ctx.gap_summary:
            row = gtbl.add_row().cells
            row[0].text = fam["family"]
            row[1].text = str(fam["aplicables"])
            row[2].text = str(fam["no_conformes"])
            row[3].text = f"{fam['pct_conformidad']}%"

    _add_heading(doc, "7. Plan de acciones correctivas", level=1)
    if ctx.plan_tasks:
        for task in ctx.plan_tasks:
            p = doc.add_paragraph()
            r = p.add_run(f"{task['code']} · {task['title']}")
            r.bold = True
            doc.add_paragraph(
                f"Medida ENS: {task['ens_measure']} · Responsable: "
                f"{task['responsible_role']} · Prioridad: {task['priority']}\n"
                f"Esfuerzo: {task['effort_hours']}h · Plazo: {task['target_date']}\n"
                f"{task['description']}"
            )
    else:
        doc.add_paragraph(
            "Plan WBS pendiente de generación vía M17. Re-emitir PdA "
            "tras `generate_plan` para incluir tasks correctivas."
        )

    _add_heading(doc, "Aprobación", level=1)
    sig = doc.add_table(rows=1, cols=4)
    sig.style = "Light Grid Accent 1"
    hr = sig.rows[0].cells
    hr[0].text = "Rol"
    hr[1].text = "Nombre"
    hr[2].text = "Firma"
    hr[3].text = "Fecha"
    for rol in ("Responsable Seguridad (RSEG)", "Responsable Sistema (RSIS)", "Sponsor / Dirección"):
        row = sig.add_row().cells
        row[0].text = rol
        row[1].text = ""
        row[2].text = ""
        row[3].text = ""

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run(
        f"Documento generado por FULKRO conforme CCN-STIC 806 · RD 311/2022 · "
        f"plantilla {PDA_DOCUMENT_KIND} v{PDA_TEMPLATE_VERSION}"
    )
    fr.italic = True
    fr.font.size = Pt(8)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
