"""M16 — Mini-LMS — DOCX builders para E-502 y E-503.

E-502: Evidencia de asistencia a curso de formacion. Atestigua que
       la persona ha accedido al contenido completo del curso.
E-503: Evidencia de cuestionario de aprovechamiento. Detalla preguntas,
       respuesta del asistente, respuesta correcta, score y resultado.

Ambas evidencias se generan con la misma calidad visual y de contenido
que los entregables E-* del proyecto: header 3-cell, footer 3-cell,
sin leaks internos, listo para ser presentado al auditor ENAC.
"""
from __future__ import annotations

import io
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


HEADER_V2_SENTINEL = "FX_HDR_V2"
FOOTER_V2_SENTINEL = "FX_FTR_V2"

NAVY = (11, 31, 58)
GRAY = (107, 114, 128)
GREEN = (16, 122, 76)
RED = (180, 35, 35)


# ---------------------------------------------------------------------------
# Low-level helpers (mismo patron que minutes_docx.py / fix_docx_templates.py)
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
    for section in doc.sections:
        body = section.header._element
        for child in list(body):
            if child.tag.endswith(("}p", "}tbl")):
                body.remove(child)
        usable = _usable_width(section)
        table = section.header.add_table(rows=1, cols=3, width=usable)
        table.autofit = False
        for col, pct in zip(table.columns, [0.38, 0.34, 0.28]):
            for cell in col.cells:
                cell.width = int(usable * pct)
        cells = table.rows[0].cells
        _style_text(cells[0].paragraphs[0].add_run(cliente_razon),
                    size=11, bold=True)
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _style_text(
            cells[1].paragraphs[0].add_run(
                f"{codigo} · {titulo}\nversion {version_actual}"
            ),
            size=9, color=GRAY,
        )
        cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _style_text(
            cells[2].paragraphs[0].add_run(
                "Marcos Mata Garcia\n"
                "Consultor independiente en ENS"
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
        for col, pct in zip(table.columns, [0.42, 0.28, 0.30]):
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


def _kv_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (label, value) in enumerate(rows):
        cells = table.rows[i].cells
        _style_text(
            cells[0].paragraphs[0].add_run(label),
            size=10, bold=True, color=GRAY,
        )
        _style_text(cells[1].paragraphs[0].add_run(value or "—"), size=10)


def _section_h(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    _style_text(p.add_run(text), size=13, bold=True)


# ---------------------------------------------------------------------------
# E-502 — Evidencia de asistencia
# ---------------------------------------------------------------------------

def build_e502_attendance_docx(
    *,
    assignment,  # LmsAssignment
    cliente_razon: str,
    version_actual: str = "1.0",
) -> bytes:
    doc = Document()
    titulo = "Evidencia de asistencia a formacion"
    _build_header(doc, "E-502", titulo, cliente_razon, version_actual)
    _build_footer(doc, "E-502", cliente_razon, version_actual)

    h = doc.add_paragraph()
    _style_text(h.add_run("Evidencia de asistencia a accion formativa"),
                size=18, bold=True)
    h2 = doc.add_paragraph()
    _style_text(
        h2.add_run(
            f"{assignment.course_codigo} — {assignment.course_titulo}"
        ),
        size=13, color=GRAY,
    )

    iniciado = (
        assignment.iniciado_at.strftime("%d/%m/%Y %H:%M UTC")
        if assignment.iniciado_at else "Pendiente"
    )

    _kv_table(doc, [
        ("Codigo del curso", assignment.course_codigo),
        ("Titulo del curso", assignment.course_titulo),
        ("Duracion del curso", f"{assignment.course_duracion_minutos} minutos"),
        ("Asistente", assignment.asistente_nombre),
        ("Cargo", assignment.asistente_cargo or "—"),
        ("Organizacion", assignment.asistente_organizacion or cliente_razon),
        ("Email", assignment.asistente_email),
        ("Fecha de asignacion",
         assignment.asignado_at.strftime("%d/%m/%Y %H:%M UTC")),
        ("Fecha de inicio del curso", iniciado),
    ])

    doc.add_paragraph()
    _section_h(doc, "Declaracion")
    p = doc.add_paragraph()
    _style_text(
        p.add_run(
            "El asistente arriba identificado ha accedido al contenido "
            "completo del curso indicado a traves de la plataforma de "
            "formacion del proyecto. La presente evidencia documenta la "
            "fecha y hora de inicio de la formacion y forma parte del "
            "expediente de cumplimiento del Esquema Nacional de Seguridad "
            "(RD 311/2022, medida op.acc.5 — Concienciacion del personal "
            "y, segun el curso, op.exp.10 — Procedimientos operativos)."
        ),
        size=10,
    )

    doc.add_paragraph()
    _section_h(doc, "Verificabilidad")
    p2 = doc.add_paragraph()
    _style_text(
        p2.add_run(
            "Este documento se complementa con la evidencia E-503 "
            "(Cuestionario de aprovechamiento) que se genera al "
            "completar el cuestionario asociado al curso. La trazabilidad "
            "completa del recorrido formativo del asistente queda registrada "
            "en el expediente del proyecto y a disposicion del auditor de "
            "certificacion."
        ),
        size=10,
    )

    return _save(doc)


# ---------------------------------------------------------------------------
# E-503 — Evidencia de cuestionario
# ---------------------------------------------------------------------------

def build_e503_quiz_docx(
    *,
    assignment,
    course: dict[str, Any],
    correcciones: dict[str, dict[str, Any]],
    cliente_razon: str,
    version_actual: str = "1.0",
) -> bytes:
    doc = Document()
    titulo = "Evidencia de cuestionario de aprovechamiento"
    _build_header(doc, "E-503", titulo, cliente_razon, version_actual)
    _build_footer(doc, "E-503", cliente_razon, version_actual)

    h = doc.add_paragraph()
    _style_text(h.add_run("Evidencia de cuestionario de aprovechamiento"),
                size=18, bold=True)
    h2 = doc.add_paragraph()
    _style_text(
        h2.add_run(f"{assignment.course_codigo} — {assignment.course_titulo}"),
        size=13, color=GRAY,
    )

    pass_score = course.get("quiz", {}).get("pass_score", 70)
    score = assignment.quiz_score if assignment.quiz_score is not None else 0.0
    resultado = "APTO" if assignment.quiz_pass else "NO APTO"
    color_resultado = GREEN if assignment.quiz_pass else RED

    _kv_table(doc, [
        ("Codigo del curso", assignment.course_codigo),
        ("Titulo del curso", assignment.course_titulo),
        ("Asistente", assignment.asistente_nombre),
        ("Cargo / Organizacion",
         f"{assignment.asistente_cargo or '—'} — "
         f"{assignment.asistente_organizacion or cliente_razon}"),
        ("Email", assignment.asistente_email),
        ("Fecha de cumplimentacion",
         (assignment.completado_at.strftime("%d/%m/%Y %H:%M UTC")
          if assignment.completado_at else "—")),
        ("Puntuacion obtenida", f"{score:.1f} / 100"),
        ("Puntuacion minima exigida", f"{pass_score:.1f} / 100"),
    ])

    p = doc.add_paragraph()
    _style_text(p.add_run("Resultado: "), size=12, bold=True)
    _style_text(p.add_run(resultado), size=14, bold=True, color=color_resultado)

    doc.add_paragraph()
    _section_h(doc, "Detalle de respuestas")

    preguntas = course.get("quiz", {}).get("preguntas", [])
    table = doc.add_table(rows=len(preguntas) + 1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Nº", "Pregunta", "Respuesta del asistente", "Correcta"]
    for col, text in enumerate(headers):
        c = table.rows[0].cells[col]
        _style_text(c.paragraphs[0].add_run(text), size=10, bold=True)

    for i, q in enumerate(preguntas, start=1):
        r = table.rows[i].cells
        _style_text(r[0].paragraphs[0].add_run(str(i)), size=10)
        _style_text(
            r[1].paragraphs[0].add_run(q.get("enunciado", "")),
            size=10,
        )
        corr = correcciones.get(q["id"], {})
        tu = (corr.get("tu_respuesta") or "—").upper()
        ok = corr.get("ok", False)
        _style_text(
            r[2].paragraphs[0].add_run(tu),
            size=10, bold=True,
            color=GREEN if ok else RED,
        )
        _style_text(
            r[3].paragraphs[0].add_run(corr.get("correcta", "—").upper()),
            size=10,
        )

    doc.add_paragraph()
    _section_h(doc, "Aclaraciones por pregunta")
    for i, q in enumerate(preguntas, start=1):
        corr = correcciones.get(q["id"], {})
        ok = corr.get("ok", False)
        marca = "[CORRECTO]" if ok else "[INCORRECTO]"
        p = doc.add_paragraph()
        _style_text(p.add_run(f"{i}. "), size=10, bold=True)
        _style_text(
            p.add_run(f"{marca} "),
            size=9, bold=True,
            color=GREEN if ok else RED,
        )
        _style_text(p.add_run(q.get("enunciado", "")), size=10)
        if corr.get("explicacion"):
            p2 = doc.add_paragraph()
            _style_text(
                p2.add_run("   Aclaracion: "),
                size=9, bold=True, color=GRAY,
            )
            _style_text(p2.add_run(corr["explicacion"]), size=10)

    doc.add_paragraph()
    _section_h(doc, "Validez de la evidencia")
    p = doc.add_paragraph()
    _style_text(
        p.add_run(
            "El presente documento acredita el resultado del cuestionario "
            "de aprovechamiento asociado al curso indicado. La evidencia "
            "se conserva con hash SHA-256 verificable en el expediente del "
            "proyecto y forma parte de las evidencias exigidas por la "
            "medida op.acc.5 (Concienciacion) del Anexo II del RD 311/2022. "
            "Cuando el resultado es 'NO APTO', el asistente debera repetir "
            "el curso o realizar la formacion presencial complementaria que "
            "el responsable de seguridad considere oportuna."
        ),
        size=10,
    )

    return _save(doc)


def _save(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
