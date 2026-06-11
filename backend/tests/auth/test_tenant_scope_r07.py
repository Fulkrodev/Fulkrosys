"""R07 · test del helper central de tenant-scope (ensure_client_project_scope).

Self-contained (mocks · sin BD): valida la lógica de autorización + fijado de
contexto. 404 si el proyecto no existe; 403 si no pertenece al cliente; fija el
contexto RLS (project_id + client_id) cuando es válido.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.auth.tenant_scope import ensure_client_project_scope


def _fake_db(first_row):
    """AsyncSession mock cuyo db.execute(...).first() devuelve first_row."""
    db = MagicMock()
    result = MagicMock()
    result.first.return_value = first_row
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_scope_404_cuando_proyecto_no_existe():
    db = _fake_db(None)
    with pytest.raises(HTTPException) as exc:
        await ensure_client_project_scope(db, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_scope_403_cuando_cliente_no_es_dueno():
    otro_cliente = uuid.uuid4()
    db = _fake_db((otro_cliente,))
    with pytest.raises(HTTPException) as exc:
        await ensure_client_project_scope(db, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_scope_fija_contexto_cuando_valido():
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    db = _fake_db((client_id,))
    with patch(
        "backend.app.auth.tenant_scope.set_tenant_context", new=AsyncMock()
    ) as mock_ctx:
        ret = await ensure_client_project_scope(db, project_id, client_id)
    assert ret == client_id
    mock_ctx.assert_awaited_once()
    _, kwargs = mock_ctx.await_args
    assert kwargs["client_id"] == client_id
    assert kwargs["project_id"] == project_id
