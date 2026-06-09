"""C#55 (FRENTE C) · recategorización REAL cross-motor.

Verifica que recategorize_project:
- N1 (sin borradores ni contratos) → APLICA · cambia categoria_objetivo.
- N3 (contrato firmado) → BLOQUEA (blocked_signed) · categoria_objetivo INTACTA +
  constancia en adendas (lo firmado no se toca).
Reutiliza el orquestador floor_elevation_service (OPS-026).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m28_change_governance.recategorization_service import (
    recategorize_project,
)
from backend.tests.conftest import setup_test_project, _admin_setup

pytestmark = pytest.mark.asyncio


async def _set_categoria(db, project_id: str, categoria: str) -> None:
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo=:c WHERE id=:p"),
            {"c": categoria, "p": project_id},
        )


async def _categoria_actual(db, project_id: str) -> str:
    async with _admin_setup(db):
        return (await db.execute(
            text("SELECT categoria_objetivo FROM projects WHERE id=:p"),
            {"p": project_id},
        )).scalar()


async def test_n1_recat_applies_changes_category(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "BASICA")

    async with _admin_setup(db):
        result = await recategorize_project(
            db, uuid.UUID(project_id), uuid.uuid4(), "ALTA",
            "Reanálisis de impacto: datos especialmente protegidos.",
        )

    assert result.state == "applied", result
    assert result.level == "N1"
    assert result.old_category == "BASICA"
    assert result.new_category == "ALTA"
    assert await _categoria_actual(db, project_id) == "ALTA"


async def test_n3_signed_contract_blocks_and_keeps_category(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "BASICA")
    sha = "b" * 64
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, "
                "firmado_cliente_at, documento_sha256, hash_sha256, created_at) "
                "VALUES (:id, :pid, 'vigente', now(), :sha, :sha, now())"
            ),
            {"id": str(uuid.uuid4()), "pid": project_id, "sha": sha},
        )

    async with _admin_setup(db):
        result = await recategorize_project(
            db, uuid.UUID(project_id), uuid.uuid4(), "ALTA",
            "Intento de elevar con contrato firmado.",
        )

    assert result.state == "blocked_signed", result
    assert result.level == "N3"
    # La categoría NO cambia (lo firmado no se toca).
    assert await _categoria_actual(db, project_id) == "BASICA"
    # Constancia del intento bloqueado en adendas del contrato firmado.
    async with _admin_setup(db):
        adendas = (await db.execute(
            text("SELECT adendas FROM contracts WHERE project_id=:p"),
            {"p": project_id},
        )).scalar()
    assert adendas and "intentos_elevacion_bloqueados" in adendas


async def test_no_op_same_category_applied(db):
    _, project_id = await setup_test_project(db)
    await _set_categoria(db, project_id, "MEDIA")
    async with _admin_setup(db):
        result = await recategorize_project(
            db, uuid.UUID(project_id), uuid.uuid4(), "MEDIA", "sin cambio",
        )
    assert result.state == "applied"
    assert result.old_category == "MEDIA" and result.new_category == "MEDIA"


async def test_invalid_category_raises(db):
    _, project_id = await setup_test_project(db)
    with pytest.raises(ValueError):
        async with _admin_setup(db):
            await recategorize_project(
                db, uuid.UUID(project_id), uuid.uuid4(), "SUPREMA", "x",
            )
