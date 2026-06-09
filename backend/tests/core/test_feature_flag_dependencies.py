"""Tests feature flag FastAPI dependencies (ADR-036 SAN-D MB-17.2)."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from backend.app.core.feature_flags.dependencies import (
    require_archetype,
    require_category,
    require_feature,
)
from backend.tests.conftest import _admin_setup


async def _create_project(
    db,
    *,
    categoria_objetivo: str | None = None,
    archetype: str | None = None,
):
    """Insert client + project con categoría/arquetipo personalizados."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, archetype, created_at) "
                "VALUES (:id, :cid, 'TestProj', :cat, :arch, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria_objetivo,
                "arch": archetype,
            },
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return project_id


@pytest.mark.asyncio
async def test_require_category_alta_blocks_basica(db):
    """require_category(['ALTA']) · proyecto BASICA → 403."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    dep = require_category(["ALTA"])
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=project_id, db=db)
    assert exc.value.status_code == 403
    assert "ALTA" in exc.value.detail


@pytest.mark.asyncio
async def test_require_category_alta_allows_alta(db):
    """require_category(['ALTA']) · proyecto ALTA → no raise."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    dep = require_category(["ALTA"])
    # No raise = success
    await dep(project_id=project_id, db=db)


@pytest.mark.asyncio
async def test_require_category_media_in_list_allows(db):
    """require_category(['MEDIA','ALTA']) · MEDIA pasa."""
    project_id = await _create_project(db, categoria_objetivo="MEDIA")
    dep = require_category(["MEDIA", "ALTA"])
    await dep(project_id=project_id, db=db)


@pytest.mark.asyncio
async def test_require_category_basica_blocked_by_media_alta_list(db):
    """require_category(['MEDIA','ALTA']) · BASICA bloqueada."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    dep = require_category(["MEDIA", "ALTA"])
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=project_id, db=db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_category_default_basica_when_null(db):
    """require_category · categoria_objetivo NULL trata como BASICA."""
    project_id = await _create_project(db, categoria_objetivo=None)
    dep = require_category(["BASICA"])
    await dep(project_id=project_id, db=db)


@pytest.mark.asyncio
async def test_require_archetype_sector_salud_blocks_saas(db):
    """require_archetype(['sector_salud']) · saas_only → 403."""
    project_id = await _create_project(
        db, categoria_objetivo="MEDIA", archetype="saas_only",
    )
    dep = require_archetype(["sector_salud"])
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=project_id, db=db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_archetype_allows_match(db):
    """require_archetype(['sector_salud']) · proyecto sector_salud → ok."""
    project_id = await _create_project(
        db, categoria_objetivo="MEDIA", archetype="sector_salud",
    )
    dep = require_archetype(["sector_salud"])
    await dep(project_id=project_id, db=db)


@pytest.mark.asyncio
async def test_require_archetype_blocks_null_archetype(db):
    """require_archetype · archetype NULL → 403."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    dep = require_archetype(["saas_only"])
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=project_id, db=db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_feature_alta_pentest_blocks_basica(db):
    """require_feature('alta_pentest_cpstic') · BASICA → 403."""
    project_id = await _create_project(db, categoria_objetivo="BASICA")
    dep = require_feature("alta_pentest_cpstic")
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=project_id, db=db)
    assert exc.value.status_code == 403
    assert "alta_pentest_cpstic" in exc.value.detail


@pytest.mark.asyncio
async def test_require_feature_alta_pentest_allows_alta(db):
    """require_feature('alta_pentest_cpstic') · ALTA → ok."""
    project_id = await _create_project(db, categoria_objetivo="ALTA")
    dep = require_feature("alta_pentest_cpstic")
    await dep(project_id=project_id, db=db)


@pytest.mark.asyncio
async def test_require_feature_404_when_project_missing(db):
    """require_feature · project_id inexistente → 404."""
    dep = require_feature("alta_pentest_cpstic")
    with pytest.raises(HTTPException) as exc:
        await dep(project_id=uuid.uuid4(), db=db)
    assert exc.value.status_code == 404
