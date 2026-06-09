"""Helper común que construye un workbook canónico desde definición declarativa.

Cada uno de los 16 generators define solo:

* Sheet title
* Headers (lista de strings canónicos)
* Sample placeholder rows (1-3 ejemplos para guiar al cliente)
* Optional async data loader cross-motor (DdA · inventario · etc.)

Y llama a ``build_canonical_workbook`` para producir el ``.xlsx`` con
estilo corporativo coherente. Esto reduce el tamaño per generator y
garantiza visual consistency en las 16 plantillas.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Awaitable, Callable, Sequence

from openpyxl import Workbook
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import (
    auto_size_columns,
    new_workbook,
    write_data_rows,
    write_headers,
    write_metadata_block,
)
from .registry import ExcelTemplateInfo


@dataclass(slots=True)
class CanonicalSpec:
    """Especificación declarativa de una plantilla Excel."""

    info: ExcelTemplateInfo
    sheet_title: str
    headers: Sequence[str]
    sample_rows: Sequence[Sequence[object]] = field(default_factory=list)
    notes: Sequence[str] = field(default_factory=list)


DataLoader = Callable[[uuid.UUID, AsyncSession], Awaitable[Sequence[Sequence[object]]]]


async def _resolve_project_name(project_id: uuid.UUID, db: AsyncSession) -> str:
    """Best-effort: nombre del proyecto sin RLS (lectura simple)."""
    try:
        row = await db.execute(
            sa_text("SELECT COALESCE(nombre, 'Proyecto') FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )
        result = row.scalar()
        return str(result) if result else "Proyecto"
    except Exception:
        return "Proyecto"


async def build_canonical_workbook(
    project_id: uuid.UUID,
    db: AsyncSession,
    spec: CanonicalSpec,
    data_loader: DataLoader | None = None,
) -> Workbook:
    """Construye workbook canónico con metadata + headers + datos.

    Si ``data_loader`` resuelve datos cross-motor, se usan; si no, se
    rellena con ``spec.sample_rows`` (placeholder UX para guía cliente).
    """
    project_name = await _resolve_project_name(project_id, db)

    wb = new_workbook(spec.sheet_title)
    ws = wb.active
    next_row = write_metadata_block(
        ws,
        title=spec.info.title,
        project_name=project_name,
        today=date.today().isoformat(),
        template_code=spec.info.code,
        start_row=1,
    )

    # Notas/instrucciones
    for note in spec.notes:
        ws.cell(row=next_row, column=1, value=f"• {note}")
        ws.merge_cells(
            start_row=next_row, start_column=1, end_row=next_row, end_column=6
        )
        next_row += 1
    if spec.notes:
        next_row += 1

    write_headers(ws, spec.headers, row=next_row)

    rows: Sequence[Sequence[object]] = []
    if data_loader is not None:
        try:
            rows = await data_loader(project_id, db)
        except Exception:
            rows = []
    if not rows:
        rows = spec.sample_rows

    write_data_rows(ws, rows, start_row=next_row + 1)
    auto_size_columns(ws)

    return wb
