"""INES adapter — snapshot anual CCN-STIC 824 en formato XLSX.

Genera hoja Excel con el reporting anual que Marcos sube manualmente
al portal INES del CCN.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any

from openpyxl import Workbook
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


INES_SHEETS = (
    ("01_Identificacion", [
        "Nombre entidad", "CIF", "Sector", "Categoria ENS",
        "RSEG", "Fecha certificacion", "Fecha renovacion prevista",
    ]),
    ("02_Activos", [
        "ID Sistema", "Nombre", "Tipo", "D", "I", "C", "A", "T",
    ]),
    ("03_Cumplimiento", [
        "Medida", "Familia", "Categoria aplicable", "Estado",
        "Evidencia codigo", "Observaciones",
    ]),
    ("04_Incidentes", [
        "Fecha", "Tipo", "Severidad", "Descripcion corta",
        "Categorizacion INCIBE", "Estado",
    ]),
    ("05_Resumen", [
        "Metrica", "Valor", "Unidad",
    ]),
)


async def generate_ines_snapshot(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    year: int | None = None,
) -> dict[str, Any]:
    year = year or datetime.now(timezone.utc).year
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, headers in INES_SHEETS:
        ws = wb.create_sheet(sheet_name)
        ws.append(headers)

    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        ident_row = (await db.execute(sa_text(
            "SELECT c.nombre, c.cif, c.sector, p.categoria_objetivo, "
            "p.certified_at "
            "FROM projects p JOIN clients c ON p.client_id = c.id "
            "WHERE p.id = :pid"
        ), {"pid": str(project_id)})).first()
        if ident_row:
            ws = wb["01_Identificacion"]
            ws.append([
                ident_row.nombre or "",
                ident_row.cif or "",
                ident_row.sector or "",
                ident_row.categoria_objetivo or "",
                "Marcos Mata Garcia (RSEG externo)",
                ident_row.certified_at.isoformat() if ident_row.certified_at else "",
                "",
            ])

        ws = wb["02_Activos"]
        systems = (await db.execute(sa_text(
            "SELECT id::text, nombre FROM systems WHERE project_id = :pid"
        ), {"pid": str(project_id)})).all()
        for s in systems:
            cat = (await db.execute(sa_text(
                "SELECT valoracion_d, valoracion_i, valoracion_c, "
                "valoracion_a, valoracion_t FROM information_types "
                "WHERE system_id = :sid LIMIT 1"
            ), {"sid": s.id})).first()
            ws.append([
                s.id, s.nombre, "Sistema",
                cat.valoracion_d if cat else "",
                cat.valoracion_i if cat else "",
                cat.valoracion_c if cat else "",
                cat.valoracion_a if cat else "",
                cat.valoracion_t if cat else "",
            ])

        ws = wb["03_Cumplimiento"]
        findings_rows = (await db.execute(sa_text(
            "SELECT medida_afectada, estado, descripcion "
            "FROM findings WHERE project_id = :pid "
            "ORDER BY medida_afectada ASC"
        ), {"pid": str(project_id)})).all()
        for f in findings_rows:
            medida = f.medida_afectada or "?"
            familia = medida.split(".")[0] if "." in medida else ""
            ws.append([
                medida, familia, "", f.estado or "open", "", f.descripcion or "",
            ])

        ws = wb["05_Resumen"]
        ws.append(["Sistemas inventariados", len(systems), "unidades"])
        ws.append(["Hallazgos abiertos", len(findings_rows), "unidades"])
        ws.append(["Year reporting", year, "AAAA"])
    finally:
        await db.execute(sa_text("RESET ROLE"))

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()
    artifact_hash = hashlib.sha256(xlsx_bytes).hexdigest()
    return {
        "tool": "INES",
        "project_id": project_id,
        "year": year,
        "artifact_path": (
            f"exports/ines/{project_id}/ines_{year}_{artifact_hash[:8]}.xlsx"
        ),
        "artifact_content": xlsx_bytes,
        "artifact_hash": artifact_hash,
        "sheets": [name for name, _ in INES_SHEETS],
        "checklist": [
            f"Descargar el XLSX y revisarlo para year={year}",
            "Acceder a INES con certificado CCN",
            "Subir el fichero al formulario anual CCN-STIC 824",
            "Adjuntar acuse de recibo como proof",
        ],
    }


def export(project_id: uuid.UUID, params: dict) -> dict:
    """Legacy sync stub — preservado. Usar generate_ines_snapshot para real."""
    import hashlib, json
    payload = {
        "project_id": str(project_id),
        "snapshot_period": params.get("period", "Q4-2026"),
        "controls_status": params.get("controls_status", {}),
    }
    body = json.dumps(payload, sort_keys=True).encode()
    artifact_hash = hashlib.sha256(body).hexdigest()
    return {
        "tool": "INES",
        "project_id": project_id,
        "artifact_path": f"exports/ines/{project_id}/snapshot_{artifact_hash[:8]}.json",
        "artifact_hash": artifact_hash,
        "checklist": [
            "Abrir INES con credenciales del organismo",
            "Cargar snapshot del periodo correspondiente",
            "Revisar mapping de medidas a controles INES",
            "Confirmar carga y descargar acuse",
            "Adjuntar acuse INES como proof",
        ],
    }
