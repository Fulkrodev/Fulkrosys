"""M6 DOCX template normalizer (idempotent, v2).

Two phases executed on every non-commercial template under
``var/templates_docx/``:

1. ``LEAK_FIXES`` — per-template textual substitutions that remove any
   ``FULKRO`` / ``Motor N`` / ``Agente N`` / ``Document Factory`` /
   ``Copiloto`` references from the rendered body. Commercial
   templates (``C-*``, ``P-*``) keep the brand.

2. Normalised header / footer / signature block:
   - Header as a 3-cell table: ``{{ cliente.header_brand }}`` on the
     left (rendered at document-generation time as an image if the
     client has a logo, or stylised text otherwise), the document code
     + title in the centre, ``{{ consultor.header_brand }}`` on the
     right (always the consultant wordmark).
   - Footer as a 3-cell table: ``CONFIDENCIAL — {{ cliente.razon_social }}``
     on the left, document code + version in the centre,
     ``Página PAGE / NUMPAGES`` on the right (DOCX field codes).
   - Structured signature block appended to deliverables: 3-column
     table ``ELABORADO POR`` / ``REVISADO POR`` / ``APROBADO POR`` with
     nombre / cargo / fecha / firma fields ready to receive the M12
     digital signature (hash + QR) or a manuscript mark.

The script is idempotent: header/footer are always rebuilt; the
signature block is only appended when not already present (checked via
``FX_SIG_V2`` sentinel).

Sentinels: usan prefijo neutro ``FX_`` (no ``FULKRO_``) para evitar
que la marca interna aparezca dentro del XML del DOCX. Si en algun
template siguen presentes los sentinels antiguos ``FULKRO_*``, el
script los purga automaticamente al regenerar header/footer/sigblock.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "var" / "templates_docx"

# New sentinels (no leak FULKRO inside XML).
HEADER_V2_SENTINEL = "FX_HDR_V2"
FOOTER_V2_SENTINEL = "FX_FTR_V2"
SIGBLOCK_SENTINEL = "FX_SIG_V2"

# Legacy sentinels — purged on regeneration to ensure 0 FULKRO leaks
# in the XML of compiled .docx templates.
LEGACY_SENTINELS = (
    "FULKRO_HEADER_V2", "FULKRO_FOOTER_V2", "FULKRO_SIGBLOCK_V2",
)


HEADER_TITLES = {
    "E-001": "Ficha Resumen Ejecutivo",
    "E-040": "Informe Final de Adecuación",
    "E-050": "Informe de Auditoría Interna del SGSI",
    "E-090": "Informe de Diagnóstico",
    "E-702": "Informe de Verificación Técnica",
    "E-703": "Resumen Ejecutivo de Verificación",
    "E-704": "Informe de Verificación Red Team",
    "E-100": "Política de Seguridad",
    "E-101": "Política de Control de Acceso",
    "E-102": "Política de Criptografía",
    "E-103": "Política de Uso Aceptable",
    "E-104": "Política de Clasificación de la Información",
    "E-105": "Política de Personal",
    "E-106": "Política de Seguridad Física",
    "E-107": "Política Criptográfica",
    "E-108": "Política de Gestión de Incidentes",
    "E-109": "Política de Continuidad",
    "E-110": "Política de Proveedores",
    "E-111": "Política de Gestión de Activos",
    "E-112": "Política de Retención de Registros",
    "E-113": "Política de Protección de Datos",
    "E-114": "Política de Desarrollo Seguro",
    "E-200": "Procedimiento de Gestión de Usuarios",
    "E-205": "Procedimiento de Gestión de Vulnerabilidades",
    "E-218": "Procedimiento de Auditoría Interna",
    "E-400": "Análisis de Impacto en el Negocio",
    "F-001": "Acta de Reunión Exploratoria",
    "F-003": "Acta de Negociación",
    "F-006": "Plan de Comunicación",
    "F-007": "Plan de Riesgos del Proyecto",
    "F-008": "Acta de Kick-off",
}


LEAK_FIXES: dict[str, list[tuple[str, str]]] = {
    "E-040.docx": [
        ("ejecutado por FULKRO entre el", "llevado a cabo entre el"),
        (
            "El proyecto se ha ejecutado siguiendo la metodología FULKRO, alineada con",
            "El proyecto se ha ejecutado siguiendo una metodología alineada con",
        ),
        ("11.3 Compromiso de FULKRO", "11.3 Compromiso del consultor"),
        ("FULKRO se compromete a acompañar", "El consultor se compromete a acompañar"),
        (
            "Elaborado por: Marcos Mata García — FULKRO",
            "Elaborado por: Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad",
        ),
    ],
    "E-001.docx": [
        ("Inversión total contratada (FULKRO)", "Inversión total contratada"),
        ("Honorarios FULKRO contratados", "Honorarios del consultor contratados"),
        ("Honorarios FULKRO consumidos", "Honorarios del consultor consumidos"),
        ("Horas FULKRO contratadas", "Horas del consultor contratadas"),
        ("Horas FULKRO consumidas", "Horas del consultor consumidas"),
    ],
    "E-090.docx": [
        ("3.1 Organizativo (Motor 21)", "3.1 Diagnóstico organizativo"),
        ("3.2 Técnico (Motor 22)", "3.2 Diagnóstico técnico"),
        ("Conforme al Effort Estimator (Motor 17):", "Conforme al estimador de esfuerzo del proyecto:"),
    ],
    "E-114.docx": [
        (
            "conforme al Motor 8 (Pentesting Engine)",
            "conforme al procedimiento de pentesting aplicable",
        ),
    ],
    "F-001.docx": [
        (
            "Consultor: Marcos Mata García — FULKRO",
            "Consultor: Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad",
        ),
    ],
    "F-003.docx": [
        (
            "Si un ajuste queda fuera del rango aceptable, el Agente 20 propone alternativas:",
            "Si un ajuste queda fuera del rango aceptable, se proponen alternativas:",
        ),
    ],
    "F-006.docx": [
        ("Plataforma FULKRO (magic links)", "Portal del proyecto con enlaces seguros"),
        ("Continuo (FULKRO)", "Continuo"),
    ],
    "F-007.docx": [
        ("Motor 24 Regulatory Radar monitorizando BOE", "Monitorización continuada del BOE y avisos CCN"),
    ],
    "F-008.docx": [
        ("Marcos Mata García (FULKRO)", "Marcos Mata García, Consultor independiente en ENS"),
        ("Presentación de FULKRO y de Marcos", "Presentación del consultor"),
    ],
    "P-001.docx": [
        (
            "{# Esta sección la genera el Agente 19 a partir de los bloques A-F de la reunión exploratoria. Es donde el cliente siente que lo hemos escuchado. Debe usar las propias palabras del",
            "{# Esta sección se elabora a partir de los bloques A-F de la reunión exploratoria. Debe usar las propias palabras del",
        ),
        (
            "{# Diagrama Mermaid gantt generado por el Motor 17 y rasterizado a PNG por docxtpl #}",
            "{# Diagrama Mermaid gantt del cronograma del proyecto #}",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _replace_in_paragraph(paragraph, find: str, repl: str) -> bool:
    if find not in paragraph.text:
        return False
    new_text = paragraph.text.replace(find, repl)
    if not paragraph.runs:
        paragraph.add_run(new_text)
        return True
    paragraph.runs[0].text = new_text
    for r in paragraph.runs[1:]:
        r.text = ""
    return True


def apply_leak_fixes(doc: Document, fixes: list[tuple[str, str]]) -> int:
    applied = 0

    def _walk(paragraphs):
        nonlocal applied
        for p in paragraphs:
            for find, repl in fixes:
                if _replace_in_paragraph(p, find, repl):
                    applied += 1

    _walk(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _walk(cell.paragraphs)
    for section in doc.sections:
        _walk(section.header.paragraphs)
        _walk(section.footer.paragraphs)
    return applied


# ---------------------------------------------------------------------------
# Header / footer builders
# ---------------------------------------------------------------------------

def _clear_section_part(part) -> None:
    body = part._element
    for child in list(body):
        if child.tag.endswith(("}p", "}tbl")):
            body.remove(child)


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


def _style_text(run, size=9, bold=False, color=(11, 31, 58)):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)


def _usable_width(section) -> int:
    page = section.page_width
    left = section.left_margin
    right = section.right_margin
    if page is None or left is None or right is None:
        return int(Cm(16))  # A4 21cm - 2.5cm margins x2 fallback
    return max(int(page - left - right), int(Cm(16)))


def build_header(doc: Document, code: str, title: str) -> None:
    for section in doc.sections:
        _clear_section_part(section.header)
        usable = _usable_width(section)
        table = section.header.add_table(rows=1, cols=3, width=usable)
        table.autofit = False
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        widths_pct = [0.38, 0.34, 0.28]
        for col, pct in zip(table.columns, widths_pct):
            for cell in col.cells:
                cell.width = int(usable * pct)

        cells = table.rows[0].cells

        p_left = cells[0].paragraphs[0]
        p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _style_text(p_left.add_run("{{ cliente.header_brand }}"), size=11, bold=True)

        p_ctr = cells[1].paragraphs[0]
        p_ctr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(
            p_ctr.add_run(f"{code} · {title}\nversión {{{{ proyecto.version_actual }}}}"),
            size=9, color=(107, 114, 128),
        )

        p_right = cells[2].paragraphs[0]
        p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _style_text(p_right.add_run("{{ consultor.header_brand }}"), size=9)

        snt = section.header.add_paragraph()
        snt_run = snt.add_run(f"<!--{HEADER_V2_SENTINEL}-->")
        snt_run.font.size = Pt(1)


def build_footer(doc: Document, code: str) -> None:
    for section in doc.sections:
        _clear_section_part(section.footer)
        usable = _usable_width(section)
        table = section.footer.add_table(rows=1, cols=3, width=usable)
        table.autofit = False
        widths_pct = [0.42, 0.28, 0.30]
        for col, pct in zip(table.columns, widths_pct):
            for cell in col.cells:
                cell.width = int(usable * pct)

        cells = table.rows[0].cells

        p_l = cells[0].paragraphs[0]
        p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _style_text(
            p_l.add_run("CONFIDENCIAL — {{ cliente.razon_social }}"),
            size=8, color=(107, 114, 128),
        )

        p_c = cells[1].paragraphs[0]
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(
            p_c.add_run(f"{code} · v{{{{ proyecto.version_actual }}}}"),
            size=8, color=(107, 114, 128),
        )

        p_r = cells[2].paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _style_text(p_r.add_run("Página "), size=8, color=(107, 114, 128))
        run_page = p_r.add_run()
        _style_text(run_page, size=8, color=(107, 114, 128))
        _add_field(run_page, "PAGE")
        _style_text(p_r.add_run(" / "), size=8, color=(107, 114, 128))
        run_total = p_r.add_run()
        _style_text(run_total, size=8, color=(107, 114, 128))
        _add_field(run_total, "NUMPAGES")

        snt = section.footer.add_paragraph()
        snt_run = snt.add_run(f"<!--{FOOTER_V2_SENTINEL}-->")
        snt_run.font.size = Pt(1)


# ---------------------------------------------------------------------------
# Signature block
# ---------------------------------------------------------------------------

SIGBLOCK_TEMPLATES = {
    "E-001.docx", "E-040.docx", "E-050.docx", "E-090.docx", "E-400.docx",
    "E-702.docx", "E-703.docx", "E-704.docx",
}


def _doc_has_sigblock(doc: Document) -> bool:
    for p in doc.paragraphs:
        if SIGBLOCK_SENTINEL in p.text:
            return True
    return False


def _purge_legacy_sentinels(doc: Document) -> int:
    """Remove every paragraph whose text contains a legacy FULKRO_*
    sentinel (header/footer/sigblock). Idempotent.

    Returns the number of paragraphs removed. After calling this function,
    the doc no longer contains any 'FULKRO' substring inside the document
    body / sections that came from old build runs.
    """
    removed = 0

    def _remove_legacy_in_paragraphs(paragraphs) -> int:
        n = 0
        for p in list(paragraphs):
            txt = p.text or ""
            if any(legacy in txt for legacy in LEGACY_SENTINELS):
                el = p._element
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
                    n += 1
        return n

    removed += _remove_legacy_in_paragraphs(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                removed += _remove_legacy_in_paragraphs(cell.paragraphs)
    for section in doc.sections:
        removed += _remove_legacy_in_paragraphs(section.header.paragraphs)
        for tbl in section.header.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    removed += _remove_legacy_in_paragraphs(cell.paragraphs)
        removed += _remove_legacy_in_paragraphs(section.footer.paragraphs)
        for tbl in section.footer.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    removed += _remove_legacy_in_paragraphs(cell.paragraphs)
    return removed


def append_sigblock(doc: Document) -> None:
    doc.add_paragraph()
    heading = doc.add_paragraph()
    _style_text(heading.add_run("APROBACIONES Y FIRMAS"), size=12, bold=True)

    intro = doc.add_paragraph()
    _style_text(
        intro.add_run(
            "El presente documento se aprueba mediante las firmas de los intervinientes "
            "que se relacionan a continuación. Cuando la firma se realiza digitalmente a "
            "través del portal del proyecto, el hash SHA-256 y el código QR de "
            "verificación se consignan bajo el nombre del firmante."
        ),
        size=10,
    )

    table = doc.add_table(rows=5, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["ELABORADO POR", "REVISADO POR", "APROBADO POR"]
    for cell, text in zip(table.rows[0].cells, headers):
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(p.add_run(text), size=10, bold=True)

    roles = ["elaborado", "revisado", "aprobado"]
    labels = [("Nombre", "nombre"), ("Cargo", "cargo"), ("Fecha", "fecha"), ("Firma", "firma_marca")]
    for i, (label, field) in enumerate(labels, start=1):
        for j, role in enumerate(roles):
            cell = table.rows[i].cells[j]
            p = cell.paragraphs[0]
            _style_text(p.add_run(f"{label}: "), size=9, bold=True, color=(107, 114, 128))
            _style_text(p.add_run(f"{{{{ firmas.{role}.{field} }}}}"), size=10)

    sentinel = doc.add_paragraph()
    snt_run = sentinel.add_run(f"<!--{SIGBLOCK_SENTINEL}-->")
    snt_run.font.size = Pt(1)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    files = sorted(TEMPLATES_DIR.glob("*.docx"))
    leak_total = 0
    header_total = 0
    sigblock_total = 0
    legacy_purged_total = 0

    for f in files:
        doc = Document(str(f))
        if f.name in LEAK_FIXES:
            n = apply_leak_fixes(doc, LEAK_FIXES[f.name])
            if n:
                leak_total += n
                print(f"[leak-fix] {f.name}: {n}")

        # Purge legacy FULKRO_* sentinels before regenerating headers/footers.
        # build_header/build_footer rebuild sections from scratch, so legacy
        # sentinels in header/footer disappear automatically; this purge
        # catches the SIGBLOCK sentinel in the body (where it lives) and
        # any stray header/footer remnant.
        n_legacy = _purge_legacy_sentinels(doc)
        if n_legacy:
            legacy_purged_total += n_legacy
            print(f"[purge-legacy] {f.name}: {n_legacy} legacy sentinels removed")

        is_commercial = f.stem.startswith(("C-", "P-"))
        if not is_commercial:
            code = f.stem
            title = HEADER_TITLES.get(code, f"Documento {code}")
            build_header(doc, code, title)
            build_footer(doc, code)
            header_total += 1
        if f.name in SIGBLOCK_TEMPLATES and not _doc_has_sigblock(doc):
            append_sigblock(doc)
            sigblock_total += 1
        doc.save(str(f))

    print(f"\n=== SUMMARY ===")
    print(f"leak replacements: {leak_total}")
    print(f"legacy FULKRO_* sentinels purged: {legacy_purged_total}")
    print(f"header+footer rewritten: {header_total}")
    print(f"signature blocks appended: {sigblock_total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
