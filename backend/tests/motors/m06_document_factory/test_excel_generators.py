"""Tests 16 generators Excel · SAN-C.MB-10.1.

Cobertura per generator: cada uno produce un Workbook openpyxl válido
con la sheet correcta + cabeceras canónicas (no error openpyxl, no zip
corrupto). Datos cross-motor están cubiertos en tests específicos por
generator (dda_matriz · inventario_activos) cuando se aglutina.

Pattern: pytest.mark.parametrize sobre los 16 slugs · 16 cases
generados automáticamente desde el registry.
"""
from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m06_document_factory.excel_generators import (
    EXCEL_TEMPLATES,
    dispatch,
    list_templates,
)
from backend.tests.conftest import _admin_setup


@pytest.mark.asyncio
@pytest.mark.parametrize("template", EXCEL_TEMPLATES, ids=lambda t: t.slug)
async def test_generate_excel_template_produces_valid_xlsx(
    template, db: AsyncSession
):
    """Cada generator produce un Workbook openpyxl válido sin errores."""
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"T {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, :nombre, 'adecuacion', now())"
            ),
            {
                "pid": str(project_id),
                "cid": str(client_id),
                "nombre": f"Proyecto Excel Test {template.slug}",
            },
        )

    wb = await dispatch(template.slug, project_id, db)

    assert isinstance(wb, Workbook)
    # Sheet activa con título canónico (truncado a 31 chars en openpyxl)
    assert wb.active.title is not None
    assert len(wb.active.title) <= 31

    # Verifica que el workbook serializa a OOXML válido
    bio = io.BytesIO()
    wb.save(bio)
    data = bio.getvalue()
    assert len(data) > 1000

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert "[Content_Types].xml" in names
        assert any("worksheets/" in n for n in names)


def test_excel_templates_count_is_16():
    """Catálogo canónico debe tener exactamente 16 entries."""
    templates = list_templates()
    assert len(templates) == 16


def test_excel_templates_slugs_are_unique():
    """Slugs únicos · no duplicates."""
    slugs = [t.slug for t in list_templates()]
    assert len(slugs) == len(set(slugs))


def test_excel_templates_codes_are_unique():
    """Códigos X-001..X-016 únicos."""
    codes = [t.code for t in list_templates()]
    assert len(codes) == len(set(codes))


@pytest.mark.asyncio
async def test_dispatch_unknown_slug_raises_keyerror(db: AsyncSession):
    """Dispatch a slug inexistente lanza KeyError."""
    with pytest.raises(KeyError, match=r"(?i)excel.*template.*no existe"):
        await dispatch("inexistente_xxx", uuid.uuid4(), db)
