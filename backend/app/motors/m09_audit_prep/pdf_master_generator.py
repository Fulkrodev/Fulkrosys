"""M9 — PDF maestro navegable (indice clickable del dossier ENAC).

Estrategia:
1. Construir un MD (o ODT) con enlaces internos a las 15 secciones
   del dossier.
2. Convertirlo a PDF con LibreOffice headless (mismo pipeline que M6).
3. LibreOffice preserva los enlaces internos como bookmarks navegables.

El PDF se incluye dentro del ZIP del dossier como
``00_INDICE/00_INDICE_MAESTRO.pdf`` y apunta a los nombres de carpeta
(ej. ``04_DECLARACION_APLICABILIDAD``) para que el auditor navegue
rapidamente desde el indice.
"""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m09_audit_prep.dossier_generator import (
    DOSSIER_STRUCTURE, _collect_documents, _collect_evidence,
    _collect_operational_records, _collect_pentest_findings, get_run,
)


class PdfMasterError(RuntimeError):
    pass


def _build_master_markdown(
    run, documents: list[dict], evidence: list[dict],
    records: list[dict], findings: list[dict],
) -> str:
    """Construye el MD del indice maestro con anclas internas."""
    lines: list[str] = []
    lines.append("% INDICE MAESTRO DEL DOSSIER ENS")
    lines.append(f"% Proyecto {run.project_id} · Categoria {run.categoria}")
    lines.append("")
    lines.append("# INDICE MAESTRO DEL DOSSIER")
    lines.append("")
    lines.append(
        "Este documento es la puerta de entrada al dossier. Cada seccion"
        " incluye un enlace directo a la carpeta correspondiente."
    )
    lines.append("")
    if getattr(run, "readiness_score", None) is not None:
        lines.append(
            f"**Puntuacion de preparacion:** {run.readiness_score}/100"
        )
    lines.append(
        f"**Documentos:** {len(documents)} · "
        f"**Evidencias:** {len(evidence)} · "
        f"**Registros:** {len(records)} · "
        f"**Hallazgos tecnicos:** {len(findings)}"
    )
    lines.append("")
    lines.append("## Secciones")
    lines.append("")

    # Indice con enlaces
    for item in DOSSIER_STRUCTURE:
        anchor = item["folder"].lower().replace("_", "-")
        lines.append(
            f"- [{item['folder']}](#{anchor}) — {item['description']}"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Detalle por carpeta
    by_folder: dict[str, list[dict]] = {}
    for d in documents:
        by_folder.setdefault(d["carpeta_destino"], []).append(d)

    for item in DOSSIER_STRUCTURE:
        folder = item["folder"]
        lines.append(f"## {folder}")
        lines.append("")
        lines.append(f"_{item['description']}_")
        lines.append("")
        entries = by_folder.get(folder, [])
        if entries:
            lines.append("| Código | Documento | Estado |")
            lines.append("|---|---|---|")
            for d in sorted(
                entries, key=lambda x: x.get("template_codigo") or "zzz",
            ):
                code = d.get("template_codigo") or "—"
                nombre = (d.get("nombre") or "").replace("|", "/")[:60]
                estado = d.get("estado") or "—"
                lines.append(f"| {code} | {nombre} | {estado} |")
        elif folder == "08_REGISTROS_OPERACION":
            lines.append(f"- {len(records)} registros operativos adjuntos")
        elif folder == "09_EVIDENCIAS_POR_MEDIDA":
            by_measure: dict[str, int] = {}
            for ev in evidence:
                by_measure[ev["measure_code"]] = (
                    by_measure.get(ev["measure_code"], 0) + 1
                )
            lines.append(
                f"- {len(by_measure)} medidas con evidencias "
                f"({len(evidence)} en total)"
            )
        elif folder == "13_INFORMES_TECNICOS":
            lines.append(f"- {len(findings)} hallazgos tecnicos documentados")
            lines.append(
                "- Informes **E-702** (tecnico), **E-703** (ejecutivo) y "
                "**E-704** (Red Team Alta) cuando procede"
            )
        elif folder == "99_MATRIZ_CRUZADA":
            lines.append(
                "- `matriz_medidas_evidencias.xlsx` (73 medidas x 14 columnas)"
            )
        else:
            lines.append("_(sin entregables para esta carpeta)_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "**Elaborado por:** Marcos Mata Garcia, "
        "Consultor independiente en Esquema Nacional de Seguridad"
    )
    lines.append("")
    lines.append("_RD 311/2022 · CCN-STIC 805/806/808_")
    return "\n".join(lines)


def _markdown_to_pdf(markdown: str, out_dir: Path) -> Path:
    """Pipeline MD → PDF usando LibreOffice headless.

    Requiere pandoc y libreoffice disponibles. Falla con
    ``PdfMasterError`` si alguno no esta.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "00_INDICE_MAESTRO.md"
    md_path.write_text(markdown, encoding="utf-8")

    # Pandoc MD → DOCX primero (preserva anchors como bookmarks)
    docx_path = out_dir / "00_INDICE_MAESTRO.docx"
    cmd_pandoc = [
        "pandoc", str(md_path),
        "-o", str(docx_path),
        "--from", "gfm",
        "--to", "docx",
    ]
    try:
        result = subprocess.run(
            cmd_pandoc, capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError as exc:
        raise PdfMasterError(
            "pandoc no encontrado. Instalar con: apt install pandoc",
        ) from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise PdfMasterError("pandoc tardo demasiado (>60s)") from exc
    if result.returncode != 0:  # pragma: no cover
        raise PdfMasterError(
            f"pandoc fallo: {result.stderr}",
        )

    # LibreOffice DOCX → PDF (los enlaces internos se preservan)
    cmd_lo = [
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(out_dir), str(docx_path),
    ]
    try:
        result = subprocess.run(
            cmd_lo, capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError as exc:
        raise PdfMasterError(
            "libreoffice no encontrado. Instalar: apt install libreoffice-writer",
        ) from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise PdfMasterError("libreoffice tardo demasiado (>120s)") from exc
    if result.returncode != 0:  # pragma: no cover
        raise PdfMasterError(
            f"libreoffice fallo: {result.stderr}",
        )

    pdf_path = out_dir / "00_INDICE_MAESTRO.pdf"
    if not pdf_path.exists():  # pragma: no cover
        raise PdfMasterError(
            f"PDF no encontrado en {pdf_path} (libreoffice rc=0 pero sin output)",
        )
    return pdf_path


async def generate_pdf_master(
    db: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
    *, out_dir: Optional[Path] = None,
) -> bytes:
    """Genera el PDF maestro navegable y devuelve sus bytes.

    Si ``out_dir`` no se pasa, se usa un ``tempfile.TemporaryDirectory``
    que se limpia al salir.
    """
    run = await get_run(db, run_id)
    if run is None or run.project_id != project_id:
        raise PdfMasterError(
            f"AuditPreparationRun {run_id} no encontrado",
        )

    documents = await _collect_documents(db, project_id)
    evidence = await _collect_evidence(db, project_id)
    records = await _collect_operational_records(db, project_id)
    findings = await _collect_pentest_findings(db, project_id)

    md = _build_master_markdown(run, documents, evidence, records, findings)

    if out_dir is None:
        with tempfile.TemporaryDirectory(prefix="fulkro_pdf_master_") as tmp:
            pdf_path = _markdown_to_pdf(md, Path(tmp))
            return pdf_path.read_bytes()
    pdf_path = _markdown_to_pdf(md, out_dir)
    return pdf_path.read_bytes()


__all__ = ["generate_pdf_master", "PdfMasterError"]
