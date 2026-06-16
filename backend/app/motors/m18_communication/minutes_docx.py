"""M18 — Acta de Comite de Seguridad (E-005) — DOCX builder programatico.

Genera el DOCX completo desde los datos del modelo CommitteeMeeting.
Aplica el mismo patron de header/footer 3-cell que el resto de
deliverables (mismo look profesional, sin leaks internos al cliente).

El bloque de firmas es DINAMICO: una fila por asistente, con espacio
para nombre, cargo, organizacion, fecha de firma y marca de firma
(rellenado luego por register_signature una vez el asistente firme via
magic link APROBACION_ACTA).
"""
from __future__ import annotations

import io
from datetime import date, datetime

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# Identidad Fulkro · fuente única backend.app.fulkro_identity. Import con alias
# porque este módulo reserva el prefijo FULKRO_* para sentinels de plantilla docx.
from backend.app.fulkro_identity import (
    FULKRO_AUTHOR_NAME as IDENTITY_AUTHOR_NAME,
    FULKRO_AUTHOR_ROLE as IDENTITY_AUTHOR_ROLE,
)


# Sentinels propios (NO usar FULKRO_* — esos sentinels existen en
# scripts/fix_docx_templates.py para los templates legacy y son deuda
# tecnica pendiente). Los nuestros usan prefijo neutro 'FX_'.
HEADER_V2_SENTINEL = "FX_HDR_V2"
FOOTER_V2_SENTINEL = "FX_FTR_V2"
SIGBLOCK_SENTINEL = "FX_SIG_V2"

NAVY = (11, 31, 58)
GRAY = (107, 114, 128)


# ---------------------------------------------------------------------------
# Low-level helpers (mismo patron que scripts/fix_docx_templates.py)
# ---------------------------------------------------------------------------

def _add_field(run, instr: str) -> None:
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr_el)
    run._r.append(fld_end)


def _style_text(run, size=10, bold=False, color=NAVY) -> None:
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)


def _usable_width(section) -> int:
    page = section.page_width
    left = section.left_margin
    right = section.right_margin
    if page is None or left is None or right is None:
        return int(Cm(16))
    return max(int(page - left - right), int(Cm(16)))


def _build_header(doc: Document, codigo: str, titulo: str,
                  cliente_razon: str, version_actual: str) -> None:
    """Header 3-cell: cliente | codigo · titulo + version | consultor."""
    for section in doc.sections:
        # limpiar header existente
        body = section.header._element
        for child in list(body):
            if child.tag.endswith(("}p", "}tbl")):
                body.remove(child)

        usable = _usable_width(section)
        table = section.header.add_table(rows=1, cols=3, width=usable)
        table.autofit = False
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        widths = [0.38, 0.34, 0.28]
        for col, pct in zip(table.columns, widths):
            for cell in col.cells:
                cell.width = int(usable * pct)

        cells = table.rows[0].cells
        p_l = cells[0].paragraphs[0]
        p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _style_text(p_l.add_run(cliente_razon), size=11, bold=True)

        p_c = cells[1].paragraphs[0]
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(
            p_c.add_run(f"{codigo} · {titulo}\nversion {version_actual}"),
            size=9, color=GRAY,
        )

        p_r = cells[2].paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _style_text(
            p_r.add_run(
                f"{IDENTITY_AUTHOR_NAME}\n"
                f"{IDENTITY_AUTHOR_ROLE}"
            ),
            size=9,
        )

        snt = section.header.add_paragraph()
        _style_text(snt.add_run(f"<!--{HEADER_V2_SENTINEL}-->"), size=1)


def _build_footer(doc: Document, codigo: str, cliente_razon: str,
                  version_actual: str) -> None:
    for section in doc.sections:
        body = section.footer._element
        for child in list(body):
            if child.tag.endswith(("}p", "}tbl")):
                body.remove(child)

        usable = _usable_width(section)
        table = section.footer.add_table(rows=1, cols=3, width=usable)
        table.autofit = False
        widths = [0.42, 0.28, 0.30]
        for col, pct in zip(table.columns, widths):
            for cell in col.cells:
                cell.width = int(usable * pct)

        cells = table.rows[0].cells
        _style_text(
            cells[0].paragraphs[0].add_run(
                f"CONFIDENCIAL — {cliente_razon}",
            ),
            size=8, color=GRAY,
        )
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(
            cells[1].paragraphs[0].add_run(f"{codigo} · v{version_actual}"),
            size=8, color=GRAY,
        )
        p_r = cells[2].paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _style_text(p_r.add_run("Pagina "), size=8, color=GRAY)
        run_p = p_r.add_run()
        _style_text(run_p, size=8, color=GRAY)
        _add_field(run_p, "PAGE")
        _style_text(p_r.add_run(" / "), size=8, color=GRAY)
        run_t = p_r.add_run()
        _style_text(run_t, size=8, color=GRAY)
        _add_field(run_t, "NUMPAGES")

        snt = section.footer.add_paragraph()
        _style_text(snt.add_run(f"<!--{FOOTER_V2_SENTINEL}-->"), size=1)


# ---------------------------------------------------------------------------
# Body builders
# ---------------------------------------------------------------------------

def _add_section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    _style_text(p.add_run(text), size=13, bold=True)


def _format_date_es(d) -> str:
    if d is None:
        return ""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except Exception:
            return d
    if isinstance(d, datetime):
        d = d.date()
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre",
             "diciembre")
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def _add_kv_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    """2-column table: label | value."""
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (label, value) in enumerate(rows):
        cells = table.rows[i].cells
        _style_text(
            cells[0].paragraphs[0].add_run(label),
            size=10, bold=True, color=GRAY,
        )
        _style_text(cells[1].paragraphs[0].add_run(value or "—"), size=10)


def _add_attendees_table(doc: Document, asistentes: list[dict]) -> None:
    table = doc.add_table(rows=len(asistentes) + 1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Nombre", "Cargo", "Organizacion", "Email"]
    for col, text in enumerate(headers):
        c = table.rows[0].cells[col]
        _style_text(c.paragraphs[0].add_run(text), size=10, bold=True)
    for i, a in enumerate(asistentes, start=1):
        r = table.rows[i].cells
        _style_text(r[0].paragraphs[0].add_run(a.get("nombre", "")), size=10)
        _style_text(r[1].paragraphs[0].add_run(a.get("cargo", "")), size=10)
        _style_text(r[2].paragraphs[0].add_run(a.get("organizacion", "")), size=10)
        _style_text(r[3].paragraphs[0].add_run(a.get("email", "")), size=9, color=GRAY)


def _add_orden_del_dia(doc: Document, items: list[dict]) -> None:
    if not items:
        doc.add_paragraph("Sin puntos registrados.")
        return
    for it in items:
        punto = it.get("punto", "")
        titulo = it.get("titulo", "")
        ponente = it.get("ponente", "")
        tiempo = it.get("tiempo_min")
        line = f"{punto}. {titulo}"
        if ponente:
            line += f" — Ponente: {ponente}"
        if tiempo:
            line += f" ({tiempo} min)"
        p = doc.add_paragraph(style="List Number")
        _style_text(p.add_run(line), size=10)


def _add_acuerdos_table(doc: Document, acuerdos: list[dict]) -> None:
    if not acuerdos:
        doc.add_paragraph("No se han adoptado acuerdos en esta sesion.")
        return
    table = doc.add_table(rows=len(acuerdos) + 1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Nº", "Acuerdo", "Responsable", "Fecha limite"]
    for col, text in enumerate(headers):
        c = table.rows[0].cells[col]
        _style_text(c.paragraphs[0].add_run(text), size=10, bold=True)
    for i, ac in enumerate(acuerdos, start=1):
        r = table.rows[i].cells
        _style_text(r[0].paragraphs[0].add_run(str(ac.get("numero", i))), size=10)
        _style_text(r[1].paragraphs[0].add_run(ac.get("descripcion", "")), size=10)
        _style_text(r[2].paragraphs[0].add_run(ac.get("owner", "")), size=10)
        _style_text(
            r[3].paragraphs[0].add_run(_format_date_es(ac.get("fecha_limite"))),
            size=10,
        )


def _add_proximos_pasos(doc: Document, items: list[dict]) -> None:
    if not items:
        doc.add_paragraph("Sin proximos pasos definidos.")
        return
    for it in items:
        descripcion = it.get("descripcion", "")
        owner = it.get("owner", "")
        fecha = _format_date_es(it.get("fecha_limite"))
        line = f"{descripcion}"
        meta = []
        if owner:
            meta.append(f"Responsable: {owner}")
        if fecha:
            meta.append(f"Fecha limite: {fecha}")
        if meta:
            line += f"  ({' · '.join(meta)})"
        p = doc.add_paragraph(style="List Bullet")
        _style_text(p.add_run(line), size=10)


def _add_signature_block(doc: Document, asistentes: list[dict],
                         firmas: list[dict] | None) -> None:
    """Bloque de firmas DINAMICO: una fila por asistente.

    Si en ``firmas`` ya hay registros, se rellena la columna 'Firma'
    con el sello de firma + fecha. Si esta vacio, se deja un espacio
    para firma manuscrita o digital.
    """
    doc.add_paragraph()
    _add_section_heading(doc, "Aprobaciones y firmas de los asistentes")

    intro = doc.add_paragraph()
    _style_text(
        intro.add_run(
            "El presente acta se aprueba mediante la firma electronica de "
            "los asistentes que se relacionan a continuacion. Cuando la firma "
            "se realiza a traves del enlace seguro recibido por correo, se "
            "consigna debajo del nombre del firmante el sello de firma "
            "(hash + fecha + IP) que da fe de la voluntad expresa de aprobar "
            "el acta. La trazabilidad completa queda registrada en el "
            "expediente del proyecto."
        ),
        size=10,
    )

    # Mapear firmas por asistente_idx
    firmas_by_idx: dict[int, dict] = {}
    for f in (firmas or []):
        idx = f.get("asistente_idx")
        if isinstance(idx, int):
            firmas_by_idx[idx] = f

    table = doc.add_table(rows=len(asistentes) + 1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Asistente", "Cargo / Organizacion", "Firma"]
    for col, text in enumerate(headers):
        c = table.rows[0].cells[col]
        _style_text(c.paragraphs[0].add_run(text), size=10, bold=True)

    for i, a in enumerate(asistentes):
        r = table.rows[i + 1].cells
        _style_text(r[0].paragraphs[0].add_run(a.get("nombre", "")), size=10, bold=True)
        cargo_org = a.get("cargo", "")
        if a.get("organizacion"):
            cargo_org += f" — {a['organizacion']}"
        _style_text(r[1].paragraphs[0].add_run(cargo_org), size=10, color=GRAY)

        firma = firmas_by_idx.get(i)
        if firma:
            firmado_at = firma.get("firmado_at", "")
            if isinstance(firmado_at, datetime):
                firmado_at = firmado_at.isoformat()
            ip = firma.get("ip", "")
            stamp = "FIRMADO ELECTRONICAMENTE\n"
            stamp += f"Fecha: {firmado_at}\n"
            if ip:
                stamp += f"Origen: {ip}\n"
            magic_link_id = firma.get("magic_link_id", "")
            if magic_link_id:
                stamp += f"Ref. enlace: {str(magic_link_id)[:12]}…"
            _style_text(r[2].paragraphs[0].add_run(stamp), size=9, color=NAVY)
        else:
            _style_text(
                r[2].paragraphs[0].add_run("[Pendiente de firma]"),
                size=9, color=GRAY,
            )

    snt = doc.add_paragraph()
    _style_text(snt.add_run(f"<!--{SIGBLOCK_SENTINEL}-->"), size=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_minutes_docx(
    *,
    codigo: str,
    titulo: str,
    tipo_comite: str,
    fecha,
    lugar: str | None,
    presidente: str,
    secretario: str,
    asistentes: list[dict],
    orden_del_dia: list[dict],
    acuerdos: list[dict],
    proximos_pasos: list[dict],
    notas_libres: str | None,
    firmas: list[dict] | None,
    cliente_razon: str,
    version_actual: str = "1.0",
) -> bytes:
    """Build the E-005 acta DOCX as bytes.

    Devuelve los bytes del DOCX listo para guardarse en disco / firmar /
    convertir a PDF.
    """
    doc = Document()
    _build_header(doc, codigo, titulo, cliente_razon, version_actual)
    _build_footer(doc, codigo, cliente_razon, version_actual)

    # Portada / encabezado
    h = doc.add_paragraph()
    _style_text(h.add_run("Acta del Comite de Seguridad"), size=18, bold=True)
    h2 = doc.add_paragraph()
    _style_text(h2.add_run(titulo), size=14, color=GRAY)

    _add_kv_table(doc, [
        ("Codigo del acta", codigo),
        ("Tipo de comite", tipo_comite.replace("_", " ").capitalize()),
        ("Fecha", _format_date_es(fecha)),
        ("Lugar", lugar or "Telematica"),
        ("Presidente", presidente),
        ("Secretario / a", secretario),
    ])

    doc.add_paragraph()
    _add_section_heading(doc, "1. Asistentes")
    _add_attendees_table(doc, asistentes)

    doc.add_paragraph()
    _add_section_heading(doc, "2. Orden del dia")
    _add_orden_del_dia(doc, orden_del_dia)

    doc.add_paragraph()
    _add_section_heading(doc, "3. Acuerdos adoptados")
    _add_acuerdos_table(doc, acuerdos)

    doc.add_paragraph()
    _add_section_heading(doc, "4. Proximos pasos")
    _add_proximos_pasos(doc, proximos_pasos)

    if notas_libres:
        doc.add_paragraph()
        _add_section_heading(doc, "5. Notas y observaciones")
        p = doc.add_paragraph()
        _style_text(p.add_run(notas_libres), size=10)

    doc.add_page_break()
    _add_signature_block(doc, asistentes, firmas)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
