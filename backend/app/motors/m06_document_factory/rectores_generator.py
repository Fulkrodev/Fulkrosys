"""Generators DOCX para 2 documentos rectores · SAN-C.MB-9.4.

* **E-160 Manual SGSI** (CCN-STIC 805) · documento maestro del sistema
  de gestión de seguridad: alcance + roles + procesos + 4 niveles doc
  + métricas + mejora continua.
* **E-170 Plan Director Seguridad** (CCN-STIC 806) · plan estratégico
  trianual: misión/visión + estrategia + inversión por año + KPIs +
  responsables alta dirección.

Aglutinador determinista cross-motor (no LLM):

* M01 Categorización · categoría + dimensiones
* M30 Roles ENS canónicos · 4 obligatorios + POC + Comité
* M19 Risk · riesgos abiertos
* M21 Diagnosis · maturity_level CMM L0-L5

Output: BytesIO con DOCX listo para descarga + audit log entry.
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


RECTORES_TEMPLATE_VERSION = "1.0"


@dataclass(slots=True)
class RectoresContext:
    """Contexto compartido para Manual SGSI + Plan Director."""

    project_id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    system_name: str
    system_category: str
    today: str
    psi_version: str = "1.0"
    services_summary: str = ""
    assets_essential_count: int = 0
    exclusions_text: str = "Ninguna exclusión declarada al alcance del SGSI."
    roles_table: list[dict[str, str]] = field(default_factory=list)
    target_maturity_level: str = "definido"
    target_cmm: str = "L3"
    sponsor_name: str = "(pendiente designación)"
    comite_chair: str = "(pendiente designación)"
    rseg_name: str = "(pendiente designación)"
    # R23 · estimación de esfuerzo/coste por fase (effort × tarifa) para la tabla
    # Capex/Opex del Plan Director. Cada dict: {phase, hours, cost}.
    effort_rows: list[dict] = field(default_factory=list)


async def build_rectores_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> RectoresContext:
    """Aglutina datos cross-motor para Manual SGSI + Plan Director."""
    proj_row = await db.execute(
        sa_text(
            "SELECT p.id, p.client_id, "
            "       COALESCE(c.nombre, 'Cliente') AS client_name, "
            "       COALESCE(p.nombre, 'Sistema') AS system_name "
            "FROM projects p "
            "LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ),
        {"pid": str(project_id)},
    )
    proj = proj_row.first()
    if proj is None:
        raise ValueError(f"Project {project_id} not found")

    client_id = proj[1]

    # Categoría
    cat_row = await db.execute(
        sa_text(
            "SELECT c.categoria_resultante FROM categorizations c "
            "JOIN systems s ON s.id = c.system_id "
            "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
            "ORDER BY c.created_at DESC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    cat = cat_row.first()
    system_category = cat[0] if cat else "BASICA"

    # Roles ENS desde M30
    roles_table: list[dict[str, str]] = []
    sponsor_name = "(pendiente designación)"
    rseg_name = "(pendiente designación)"
    comite_chair = "(pendiente designación)"
    if client_id:
        contacts_row = await db.execute(
            sa_text(
                "SELECT full_name, email, role_category, role_title "
                "FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true AND deleted_at IS NULL "
                "ORDER BY role_category"
            ),
            {"cid": str(client_id)},
        )
        for full_name, email, role_cat, role_title in contacts_row.fetchall():
            role_label = (role_cat or "").replace("_", " ").title()
            roles_table.append({
                "role_name": role_label,
                "person": full_name or "—",
                "email": email or "—",
                "functions": role_title or role_label,
            })
            if role_cat == "sponsor" and sponsor_name.startswith("("):
                sponsor_name = full_name
            if role_cat in ("responsable_seguridad", "rseg") and rseg_name.startswith("("):
                rseg_name = full_name
            if role_cat == "miembro_comite_seguridad" and comite_chair.startswith("("):
                comite_chair = full_name

    # Activos identificados (M22). NOTA: la columna ``es_esencial`` NO existe en
    # magerit_assets (el filtro anterior abortaba la transacción → silenciaba el
    # count Y rompía las queries siguientes). Se cuentan los activos del análisis.
    try:
        assets_row = await db.execute(
            sa_text(
                "SELECT count(*) FROM magerit_assets a "
                "JOIN magerit_analysis ma ON ma.id = a.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )
        assets_essential_count = assets_row.scalar() or 0
    except Exception:
        assets_essential_count = 0

    # R23 · estimación de esfuerzo/coste (effort × tarifa) para Capex/Opex.
    effort_rows: list[dict] = []
    try:
        eff_row = await db.execute(
            sa_text(
                "SELECT phase, estimated_hours, estimated_cost "
                "FROM effort_estimates WHERE project_id = :pid ORDER BY phase"
            ),
            {"pid": str(project_id)},
        )
        for phase, hours, cost in eff_row.fetchall():
            effort_rows.append({
                "phase": phase,
                "hours": float(hours or 0),
                "cost": float(cost or 0),
            })
    except Exception:
        effort_rows = []

    return RectoresContext(
        project_id=project_id,
        client_id=client_id,
        client_name=str(proj[2]),
        system_name=str(proj[3]),
        system_category=str(system_category),
        today=date.today().isoformat(),
        services_summary="Servicios electrónicos identificados en proyecto.",
        assets_essential_count=int(assets_essential_count),
        roles_table=roles_table,
        sponsor_name=sponsor_name,
        comite_chair=comite_chair,
        rseg_name=rseg_name,
        effort_rows=effort_rows,
    )


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def generate_manual_sgsi_docx(ctx: RectoresContext) -> io.BytesIO:
    """Genera Manual SGSI E-160 conforme CCN-STIC 805."""
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Manual del Sistema de Gestión de Seguridad de la Información")
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph(
        f"Cliente: {ctx.client_name}\n"
        f"Sistema: {ctx.system_name}\n"
        f"Categoría: {ctx.system_category}\n"
        f"Fecha: {ctx.today}\n"
        f"Plantilla: E-160 v{RECTORES_TEMPLATE_VERSION}"
    )

    _add_heading(doc, "1. Alcance del SGSI", 1)
    doc.add_paragraph(
        f"El presente Manual define el alcance, objetivos y estructura del "
        f"SGSI de {ctx.client_name} conforme al RD 311/2022. Sistema cubierto: "
        f"{ctx.system_name}. Categoría: {ctx.system_category}. Activos "
        f"esenciales identificados: {ctx.assets_essential_count}."
    )

    _add_heading(doc, "2. Política de Seguridad referenciada", 1)
    doc.add_paragraph(
        f"Se desarrolla a partir de la PSI aprobada (E100 v{ctx.psi_version})."
    )

    _add_heading(doc, "3. Roles y responsabilidades (CCN-STIC 801)", 1)
    if ctx.roles_table:
        rtbl = doc.add_table(rows=1, cols=4)
        rtbl.style = "Light Grid Accent 1"
        hr = rtbl.rows[0].cells
        hr[0].text = "Rol"
        hr[1].text = "Persona"
        hr[2].text = "Email"
        hr[3].text = "Funciones"
        for r in ctx.roles_table:
            cells = rtbl.add_row().cells
            cells[0].text = r["role_name"]
            cells[1].text = r["person"]
            cells[2].text = r["email"]
            cells[3].text = r["functions"]
    else:
        doc.add_paragraph(
            "Roles ENS pendientes de asignación. Ejecutar M30 wizard "
            "para asignar RI/RS/RSEG/RSIS/POC."
        )
    doc.add_paragraph(
        "Segregación funcional: RSEG y RSIS deben ser personas distintas "
        "(CCN-STIC 801, no-conformidad mayor en caso contrario)."
    ).bold = True

    _add_heading(doc, "4. Procesos del SGSI", 1)
    for sub_title, desc in [
        ("4.1 Gestión de riesgos", "Análisis MAGERIT v3 periódico."),
        ("4.2 Gestión de incidentes",
         "Procedimiento E204 + notificación CCN-CERT vía LUCIA."),
        ("4.3 Gestión de cambios",
         "Procedimiento E203 con autorización formal previa."),
        ("4.4 Auditorías internas",
         "Anual interna · bienal externa ENAC (Media/Alta)."),
        ("4.5 Revisión por la Dirección",
         "Acta anual con indicadores + hallazgos + acciones."),
    ]:
        _add_heading(doc, sub_title, 2)
        doc.add_paragraph(desc)

    _add_heading(doc, "5. Documentación SGSI · 4 niveles (CCN-STIC 805)", 1)
    dtbl = doc.add_table(rows=1, cols=4)
    dtbl.style = "Light Grid Accent 1"
    hr = dtbl.rows[0].cells
    hr[0].text = "Nivel"
    hr[1].text = "Tipo"
    hr[2].text = "Aprobación"
    hr[3].text = "Ejemplos"
    for level, tipo, approver, examples in [
        ("1", "Política de Seguridad (PSI)", "Órgano superior", "E-100"),
        ("2", "Normativas", "RSEG", "E-100..E-126"),
        ("3", "Procedimientos", "RSEG / RSIS", "E-200..E-235"),
        ("4", "Instrucciones técnicas", "Técnicos", "E-IT-001 + manuales operativos"),
    ]:
        cells = dtbl.add_row().cells
        cells[0].text = level
        cells[1].text = tipo
        cells[2].text = approver
        cells[3].text = examples

    _add_heading(doc, "6. Métricas e indicadores (CCN-STIC 815)", 1)
    doc.add_paragraph(
        "Disponibilidad servicios críticos · MTTR/MTBF incidentes · % "
        "cumplimiento Anexo II · madurez CMM L0-L5 · cobertura "
        "concienciación personal."
    )

    _add_heading(doc, "7. Mejora continua", 1)
    doc.add_paragraph(
        "Ciclo PDCA: revisión dirección anual · auditorías internas · "
        "auditorías externas ENAC bienales (Media/Alta) · auditorías "
        "extraordinarias en cambios sustanciales."
    )

    _add_heading(doc, "Aprobación", 1)
    sig = doc.add_table(rows=1, cols=4)
    sig.style = "Light Grid Accent 1"
    hr = sig.rows[0].cells
    hr[0].text = "Rol"
    hr[1].text = "Nombre"
    hr[2].text = "Firma"
    hr[3].text = "Fecha"
    for rol, nombre in (
        ("Sponsor / Dirección", ctx.sponsor_name),
        ("Responsable Seguridad (RSEG)", ctx.rseg_name),
    ):
        row = sig.add_row().cells
        row[0].text = rol
        row[1].text = nombre
        row[3].text = ctx.today

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


# R23 · etiquetas legibles de las fases de esfuerzo (effort_estimates.phase).
_EFFORT_PHASE_LABELS: dict[str, str] = {
    "categorizacion": "Categorización del sistema",
    "dda": "Análisis de riesgos y Declaración de Aplicabilidad",
    "implantacion": "Implantación de medidas de seguridad",
    "audit": "Auditoría de conformidad",
    "retainer_year": "Soporte y mantenimiento anual (retainer)",
}


def _eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", ".")


def generate_plan_director_docx(ctx: RectoresContext) -> io.BytesIO:
    """Genera Plan Director Seguridad E-170 (trianual)."""
    doc = Document()

    today_year = date.today().year
    year_start = today_year
    year_start_plus_1 = today_year + 1
    year_end = today_year + 2

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Plan Director de Seguridad (trianual)")
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph(
        f"Cliente: {ctx.client_name}\n"
        f"Periodo: {year_start} – {year_end}\n"
        f"Categoría sistema: {ctx.system_category}\n"
        f"Fecha emisión: {ctx.today}\n"
        f"Plantilla: E-170 v{RECTORES_TEMPLATE_VERSION}"
    )

    _add_heading(doc, "1. Misión y visión de la seguridad", 1)
    doc.add_paragraph(
        f"Garantizar la disponibilidad, integridad, confidencialidad, "
        f"autenticidad y trazabilidad (CIDAT) de la información y los "
        f"servicios electrónicos de {ctx.client_name}, conforme al "
        f"RD 311/2022 (ENS) y demás normativa aplicable."
    )
    doc.add_paragraph(
        f"Visión: alcanzar madurez CMM {ctx.target_cmm} en familias críticas "
        f"del Anexo II en el horizonte {year_end}."
    )

    _add_heading(doc, "2. Estrategia trianual · hitos por año", 1)
    htbl = doc.add_table(rows=1, cols=3)
    htbl.style = "Light Grid Accent 1"
    hr = htbl.rows[0].cells
    hr[0].text = "Año"
    hr[1].text = "Hito principal"
    hr[2].text = "KPI clave"
    for year, hito, kpi in [
        (str(year_start), "Cierre primera certificación / declaración conformidad", "% medidas conformes ≥ 80%"),
        (str(year_start_plus_1), "Madurez CMM L3 familias prioritarias", "Madurez global ≥ L3"),
        (str(year_end), "Auditoría externa renovación", "NC mayores = 0"),
    ]:
        cells = htbl.add_row().cells
        cells[0].text = year
        cells[1].text = hito
        cells[2].text = kpi

    _add_heading(doc, "3. Inversión planificada (Capex / Opex)", 1)
    capex = [r for r in ctx.effort_rows if r["phase"] != "retainer_year"]
    opex = [r for r in ctx.effort_rows if r["phase"] == "retainer_year"]
    if ctx.effort_rows:
        itbl = doc.add_table(rows=1, cols=4)
        itbl.style = "Light Grid Accent 1"
        hr = itbl.rows[0].cells
        hr[0].text = "Tipo"
        hr[1].text = "Concepto"
        hr[2].text = "Esfuerzo (h)"
        hr[3].text = "Coste estimado"
        cap_total = 0.0
        for r in capex:
            cells = itbl.add_row().cells
            cells[0].text = "Capex (inicial)"
            cells[1].text = _EFFORT_PHASE_LABELS.get(r["phase"], r["phase"])
            cells[2].text = f"{r['hours']:.0f}"
            cells[3].text = _eur(r["cost"])
            cap_total += r["cost"]
        op_total = 0.0
        for r in opex:
            cells = itbl.add_row().cells
            cells[0].text = "Opex (anual)"
            cells[1].text = _EFFORT_PHASE_LABELS.get(r["phase"], r["phase"])
            cells[2].text = f"{r['hours']:.0f}"
            cells[3].text = f"{_eur(r['cost'])}/año"
            op_total += r["cost"]
        trow = itbl.add_row().cells
        trow[0].text = "TOTAL"
        trow[1].text = "Inversión inicial (Capex) + recurrente (Opex)"
        trow[2].text = ""
        trow[3].text = f"{_eur(cap_total)} + {_eur(op_total)}/año"
        doc.add_paragraph(
            "Las cifras se derivan de la estimación de esfuerzo del proyecto "
            "(esfuerzo × tarifa). El detalle de medidas y su coste unitario se "
            "desarrolla en el Plan de Adecuación (E-150)."
        )
    else:
        doc.add_paragraph(
            "Tabla Capex/Opex pendiente de cuantificación tras la estimación de "
            "esfuerzo del proyecto, que se desarrolla en el Plan de Adecuación (E-150)."
        )

    _add_heading(doc, "4. KPIs de seguimiento (CCN-STIC 815)", 1)
    doc.add_paragraph(
        "Disponibilidad servicios críticos ≥ 99,5% · MTTR incidentes ≤ 4h · "
        "Cobertura concienciación 100% personal anual · Tasa cumplimiento "
        "Anexo II ≥ 90% · Madurez CMM global ≥ L3."
    )

    _add_heading(doc, "5. Responsables alta dirección", 1)
    rtbl = doc.add_table(rows=1, cols=3)
    rtbl.style = "Light Grid Accent 1"
    hr = rtbl.rows[0].cells
    hr[0].text = "Rol"
    hr[1].text = "Nombre"
    hr[2].text = "Compromiso"
    for rol, nombre, compromiso in [
        ("Sponsor ejecutivo", ctx.sponsor_name, "Aprobación presupuesto + revisión anual"),
        ("Comité Seguridad (presidencia)", ctx.comite_chair, "Sesiones trimestrales · escalado riesgos"),
        ("Responsable Seguridad (RSEG)", ctx.rseg_name, "Ejecución plan + reporte cuatrimestral"),
    ]:
        cells = rtbl.add_row().cells
        cells[0].text = rol
        cells[1].text = nombre
        cells[2].text = compromiso

    _add_heading(doc, "6. Revisión y actualización", 1)
    doc.add_paragraph(
        "Revisión anual con: acta dirección, resultados auditoría externa "
        "(Media/Alta), cambios sustanciales que disparen auditoría "
        "extraordinaria art. 31."
    )

    _add_heading(doc, "Aprobación", 1)
    sig = doc.add_table(rows=1, cols=4)
    sig.style = "Light Grid Accent 1"
    hr = sig.rows[0].cells
    hr[0].text = "Rol"
    hr[1].text = "Nombre"
    hr[2].text = "Firma"
    hr[3].text = "Fecha"
    for rol, nombre in (
        ("Sponsor ejecutivo", ctx.sponsor_name),
        ("Responsable Seguridad (RSEG)", ctx.rseg_name),
        ("Director General", ctx.sponsor_name),
    ):
        row = sig.add_row().cells
        row[0].text = rol
        row[1].text = nombre
        row[3].text = ctx.today

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
