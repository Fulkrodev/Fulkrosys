"""X-001 · Inventario de activos MAGERIT (9 categorías canónicas)."""
from __future__ import annotations

import uuid

from openpyxl import Workbook
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from ._common import CanonicalSpec, build_canonical_workbook
from .registry import get_template_info


SPEC = CanonicalSpec(
    info=get_template_info("inventario_activos"),
    sheet_title="Inventario MAGERIT",
    headers=[
        "Código",
        "Nombre",
        "Tipo MAGERIT",
        "Categoría",
        "Propietario",
        "Ubicación",
        "Dependencias",
        "C", "I", "D", "A", "T",
    ],
    notes=[
        "Tipos MAGERIT (Libro II): [I] Información · [S] Servicio · "
        "[SW] Aplicación · [HW] Hardware · [COM] Comunicaciones · "
        "[SI] Soportes · [AUX] Auxiliares · [L] Instalaciones · [P] Personal",
        "C/I/D/A/T = niveles BAJO/MEDIO/ALTO por dimensión CIDAT",
    ],
    sample_rows=[
        ["[SW].001", "ERP corporativo", "[SW]", "software", "TI", "CPD principal",
         "[HW].001, [COM].001", "MEDIO", "ALTO", "ALTO", "ALTO", "MEDIO"],
        ["[HW].001", "Servidor BBDD", "[HW]", "hardware", "TI", "CPD principal",
         "[L].001", "BAJO", "ALTO", "ALTO", "ALTO", "MEDIO"],
        ["[I].001", "BBDD clientes", "[I]", "informacion", "Negocio",
         "Servidor BBDD", "[SW].001", "ALTO", "ALTO", "MEDIO", "ALTO", "ALTO"],
    ],
)


async def _load(project_id: uuid.UUID, db: AsyncSession) -> list[list[object]]:
    """Carga activos reales desde M22 magerit_assets si existen."""
    try:
        rows = await db.execute(
            sa_text(
                "SELECT a.codigo, a.nombre, a.tipo_magerit, a.categoria, "
                "       COALESCE(a.propietario, ''), COALESCE(a.ubicacion, ''), "
                "       COALESCE(array_to_string(a.dependencias, ', '), ''), "
                "       COALESCE(a.dim_c, ''), COALESCE(a.dim_i, ''), "
                "       COALESCE(a.dim_d, ''), COALESCE(a.dim_a, ''), "
                "       COALESCE(a.dim_t, '') "
                "FROM magerit_assets a "
                "JOIN magerit_analysis ma ON ma.id = a.analysis_id "
                "WHERE ma.project_id = :pid AND a.deleted_at IS NULL "
                "ORDER BY a.codigo LIMIT 200"
            ),
            {"pid": str(project_id)},
        )
        return [list(r) for r in rows.fetchall()]
    except Exception:
        return []


async def generate(project_id: uuid.UUID, db: AsyncSession) -> Workbook:
    return await build_canonical_workbook(project_id, db, SPEC, _load)
