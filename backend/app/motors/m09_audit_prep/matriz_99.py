"""Matriz cruzada 99 — medida × evidencia × documento × estado (M9-B).

XLSX con openpyxl. Una fila por medida aplicable del Anexo II con sus
evidencias, DdA status, documentos asociados, hallazgos pentest y gaps.
"""
from __future__ import annotations

import io
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Document, Evidence
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.models.findings import Finding
from backend.app.motors.m08_verification.integrations.m3_dda_updater import (
    get_findings_by_measure as get_verif_findings_by_measure,
)


# Columnas de la matriz
HEADERS = [
    "Código medida",
    "Nombre medida",
    "Familia",
    "Nivel ENS",
    "Estado DdA",
    "Aplicabilidad",
    "Documento(s)",
    "Evidencia(s)",
    "Vigente",
    "Fecha última evidencia",
    "Finding pentest",
    "Gap detectado",
    "Observaciones",
    "Carpeta dossier",
]


# Mapeo familia -> carpeta dossier con evidencias
_FAMILIA_TO_FOLDER = {
    "org": "09_EVIDENCIAS_POR_MEDIDA",
    "op.acc": "09_EVIDENCIAS_POR_MEDIDA",
    "op.exp": "09_EVIDENCIAS_POR_MEDIDA",
    "op.mon": "09_EVIDENCIAS_POR_MEDIDA",
    "op.ext": "09_EVIDENCIAS_POR_MEDIDA",
    "op.cont": "10_PLAN_CONTINUIDAD",
    "op.pl": "03_ANALISIS_RIESGOS",
    "mp.info": "09_EVIDENCIAS_POR_MEDIDA",
    "mp.com": "09_EVIDENCIAS_POR_MEDIDA",
    "mp.sw": "09_EVIDENCIAS_POR_MEDIDA",
    "mp.if": "09_EVIDENCIAS_POR_MEDIDA",
    "mp.s": "09_EVIDENCIAS_POR_MEDIDA",
    "mp.per": "11_FORMACION",
}


def _classify_folder(codigo: str) -> str:
    code = (codigo or "").lower()
    for prefix, folder in _FAMILIA_TO_FOLDER.items():
        if code.startswith(prefix):
            return folder
    return "09_EVIDENCIAS_POR_MEDIDA"


def _derive_nivel_ens(m: EnsMeasure) -> str:
    niveles = []
    if getattr(m, "aplica_basica", True):
        niveles.append("B")
    if getattr(m, "aplica_media", True):
        niveles.append("M")
    if getattr(m, "aplica_alta", True):
        niveles.append("A")
    return "/".join(niveles) if niveles else "-"


def _applies_to_categoria(m: EnsMeasure, cat: str) -> bool:
    c = (cat or "").upper()
    if c == "BASICA":
        return bool(getattr(m, "aplica_basica", True))
    if c == "MEDIA":
        return bool(getattr(m, "aplica_media", True))
    if c == "ALTA":
        return bool(getattr(m, "aplica_alta", True))
    return True


async def _get_measures_for_categoria(
    db: AsyncSession, categoria: str,
) -> list[EnsMeasure]:
    r = await db.execute(select(EnsMeasure).order_by(EnsMeasure.codigo.asc()))
    all_m = list(r.scalars().all())
    return [m for m in all_m if _applies_to_categoria(m, categoria)]


async def _build_rows(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> list[dict]:
    measures = await _get_measures_for_categoria(db, categoria)

    # DdA entries indexado por codigo
    r = await db.execute(
        select(DdaEntry, EnsMeasure.codigo).join(
            EnsMeasure, EnsMeasure.id == DdaEntry.measure_id,
        ).where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
        )
    )
    dda_by_code: dict[str, DdaEntry] = {}
    for entry, codigo in r.all():
        dda_by_code[codigo] = entry

    # Evidencias por codigo
    r = await db.execute(
        select(Evidence).where(
            Evidence.project_id == project_id,
            Evidence.deleted_at.is_(None),
        )
    )
    ev_by_code: dict[str, list[Evidence]] = {}
    for ev in r.scalars().all():
        if ev.measure_code:
            ev_by_code.setdefault(ev.measure_code, []).append(ev)

    # Documentos con template_codigo
    r = await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        )
    )
    documents = list(r.scalars().all())

    # Findings gap por medida_afectada
    r = await db.execute(
        select(Finding).where(
            Finding.project_id == project_id,
            Finding.deleted_at.is_(None),
            Finding.medida_afectada.isnot(None),
        )
    )
    gaps_by_code: dict[str, list[Finding]] = {}
    for f in r.scalars().all():
        gaps_by_code.setdefault(f.medida_afectada, []).append(f)

    # Hallazgos de verificacion tecnica v5.1 indexados por medida ENS.
    pentest_by_code: dict[str, list] = await get_verif_findings_by_measure(
        db, project_id,
    )

    today = date.today()
    rows: list[dict] = []
    for m in measures:
        codigo = m.codigo
        dda = dda_by_code.get(codigo)
        ev_list = ev_by_code.get(codigo, [])
        gap_list = gaps_by_code.get(codigo, [])
        pt_list = pentest_by_code.get(codigo, [])

        vigente = "Sin evidencia"
        fecha_ultima = ""
        evidencias_str = ""
        if ev_list:
            newest = max(
                ev_list,
                key=lambda e: (e.fecha_evidencia or date.min),
            )
            fecha_ultima = (
                newest.fecha_evidencia.isoformat()
                if newest.fecha_evidencia else ""
            )
            if newest.vigente and (
                newest.fecha_caducidad is None
                or newest.fecha_caducidad >= today
            ):
                vigente = "Sí"
            elif newest.fecha_caducidad and newest.fecha_caducidad < today:
                vigente = "Caducada"
            else:
                vigente = "No"
            evidencias_str = "; ".join(
                f"{e.tipo or 'evidencia'}:{(e.hash_sha256 or '')[:8]}"
                for e in ev_list[:3]
            )
            if len(ev_list) > 3:
                evidencias_str += f" (+{len(ev_list) - 3} mas)"
        # Enlaces de descarga de evidencias (max 3) — hipervinculos XLSX
        evidencia_links: list[dict] = [
            {
                "evidence_id": str(e.id),
                "label": f"{e.tipo or 'evidencia'} {(e.hash_sha256 or '')[:8]}",
                "url": f"/api/v1/evidence/{e.id}/download",
            }
            for e in ev_list[:3]
        ]

        # Documentos relacionados (basico: matchea por medida via measure_code
        # en ens_evidence vault o via template_codigo heuristico)
        docs_str = ""
        related_docs = [
            d for d in documents
            if d.template_codigo and (
                # Documento que contiene el codigo de medida en el nombre
                codigo.replace(".", "") in (d.template_codigo or "").lower()
                or codigo in (d.nombre or "")
            )
        ]
        if related_docs:
            docs_str = "; ".join(
                d.template_codigo or d.nombre for d in related_docs[:3]
            )

        pentest_str = ""
        if pt_list:
            pentest_str = "; ".join(
                f"{(getattr(pf, 'cve_id', None) or getattr(pf, 'title', None) or 'finding')}"
                f"({(getattr(pf, 'severity', None) or 'n/d')})"
                for pf in pt_list[:3]
            )
            if len(pt_list) > 3:
                pentest_str += f" (+{len(pt_list) - 3})"

        gap_str = ""
        if gap_list:
            gap_str = "; ".join(
                f"{(f.fuente or 'gap')}:{(f.severidad or 'n/d')}"
                for f in gap_list[:3]
            )

        observaciones = ""
        if dda and dda.observaciones:
            observaciones = dda.observaciones[:200]

        rows.append({
            "codigo": codigo,
            "nombre": m.nombre or "",
            "familia": m.familia or "",
            "nivel_ens": _derive_nivel_ens(m),
            "estado_dda": (
                dda.estado_implementacion if dda else "sin_dda"
            ),
            "aplicabilidad": (
                dda.aplicabilidad if dda else "pendiente"
            ),
            "documentos": docs_str,
            "evidencias": evidencias_str,
            "evidencia_links": evidencia_links,
            "vigente": vigente,
            "fecha_ultima_evidencia": fecha_ultima,
            "finding_pentest": pentest_str,
            "gap": gap_str,
            "observaciones": observaciones,
            "carpeta_dossier": _classify_folder(codigo),
        })

    # Anadir medidas no aplicables como filas informativas — el auditor
    # ENAC espera ver las 73 medidas del Anexo II completas con su
    # justificacion cuando no aplican a la categoria. Si hay hallazgos
    # tecnicos (pentest) contra una medida no aplicable, se muestran
    # tambien — los hallazgos son reales independientemente de si la
    # medida se exige para esta categoria.
    all_measures = list((await db.execute(
        select(EnsMeasure).order_by(EnsMeasure.codigo.asc())
    )).scalars().all())
    applied_codes = {r["codigo"] for r in rows}
    for m in all_measures:
        if m.codigo in applied_codes:
            continue
        pt_list = pentest_by_code.get(m.codigo, [])
        pentest_str = ""
        if pt_list:
            pentest_str = "; ".join(
                f"{(getattr(pf, 'cve_id', None) or getattr(pf, 'title', None) or 'finding')}"
                f"({(getattr(pf, 'severity', None) or 'n/d')})"
                for pf in pt_list[:3]
            )
        rows.append({
            "codigo": m.codigo,
            "nombre": m.nombre or "",
            "familia": m.familia or "",
            "nivel_ens": _derive_nivel_ens(m),
            "estado_dda": "no_aplica",
            "aplicabilidad": "no_aplica",
            "documentos": "",
            "evidencias": "—",
            "evidencia_links": [],
            "vigente": "—",
            "fecha_ultima_evidencia": "",
            "finding_pentest": pentest_str,
            "gap": "",
            "observaciones": (
                f"Medida no aplicable a categoria {categoria.upper()}"
            ),
            "carpeta_dossier": "—",
        })
    rows.sort(key=lambda r: r["codigo"])
    return rows


def _format_xlsx(rows: list[dict]) -> bytes:
    """Genera XLSX con openpyxl: header azul, filas alternas, format condicional."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Matriz 99"

    # Header
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True,
        )

    # Fills para filas
    zebra_fill = PatternFill("solid", fgColor="F2F2F2")
    vigente_fill = PatternFill("solid", fgColor="C6EFCE")
    caducada_fill = PatternFill("solid", fgColor="FFC7CE")
    no_fill = PatternFill("solid", fgColor="FFEB9C")

    row_keys = [
        "codigo", "nombre", "familia", "nivel_ens", "estado_dda",
        "aplicabilidad", "documentos", "evidencias", "vigente",
        "fecha_ultima_evidencia", "finding_pentest", "gap",
        "observaciones", "carpeta_dossier",
    ]

    link_font = Font(color="1F4E78", underline="single")

    for i, row in enumerate(rows, start=2):
        zebra = (i % 2 == 0)
        for col_idx, key in enumerate(row_keys, start=1):
            value = row.get(key, "")
            cell = ws.cell(row=i, column=col_idx, value=str(value))
            if zebra:
                cell.fill = zebra_fill
            cell.alignment = Alignment(
                vertical="center", wrap_text=True,
            )
        # Hipervinculo en columna Evidencia(s) (index 8) si hay links
        links = row.get("evidencia_links") or []
        if links:
            ev_cell = ws.cell(row=i, column=8)
            # Solo se puede asignar 1 hyperlink por celda; usamos el mas
            # reciente y dejamos el resto en el tooltip (comment).
            ev_cell.hyperlink = links[0]["url"]
            ev_cell.font = link_font
            if len(links) > 1:
                try:
                    from openpyxl.comments import Comment
                    comment = "Evidencias adicionales:\n" + "\n".join(
                        f"- {l['label']} → {l['url']}" for l in links[1:]
                    )
                    ev_cell.comment = Comment(comment, "Consultor ENS")
                except Exception:  # pragma: no cover
                    pass
        # Formato condicional columna "Vigente" (index 9)
        vigente_cell = ws.cell(row=i, column=9)
        v_val = (row.get("vigente") or "").lower()
        if v_val == "sí" or v_val == "si":
            vigente_cell.fill = vigente_fill
        elif v_val == "caducada":
            vigente_cell.fill = caducada_fill
        elif v_val in {"no", "sin evidencia"}:
            vigente_cell.fill = no_fill

    # Anchos aproximados por columna
    widths = [15, 40, 12, 10, 16, 14, 25, 30, 12, 18, 30, 25, 30, 20]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    # Freeze panes en la fila 2
    ws.freeze_panes = "A2"

    # Ancho de fila 1
    ws.row_dimensions[1].height = 30

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# =============== Public API ===============

async def generate_matriz_99(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> bytes:
    rows = await _build_rows(db, project_id, categoria)
    return _format_xlsx(rows)


async def generate_matriz_99_data(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> list[dict]:
    """Misma matriz como list[dict] (para JSON APIs y tests)."""
    return await _build_rows(db, project_id, categoria)
