"""Regresión bug auditoría 2026-06-12 · /client-portal/compliance-summary 500.

Causa raíz: ``_conformity_status_raw`` consultaba ``conformity_declarations``
(tabla INEXISTENTE). El ``except`` tragaba el error SIN rollback → la
transacción asyncpg quedaba *aborted* y la siguiente query no envuelta
(``cloud_gaps``) moría con ``InFailedSQLTransactionError`` → el endpoint
devolvía **500** al cliente en su panel de cumplimiento.

Fix: cada query best-effort corre dentro de un SAVEPOINT (``_safe_scalar`` /
``begin_nested``) — un fallo se aísla y NO envenena la transacción externa —
y conformity lee de la tabla real ``conformity_routes``.
"""
from __future__ import annotations

import inspect

import pytest
from sqlalchemy import text

import backend.app.api.v1.client_compliance_summary as M


@pytest.mark.asyncio
async def test_safe_scalar_failure_does_not_poison_transaction(db):
    """Una query a tabla inexistente devuelve default y NO aborta la tx."""
    bad = await M._safe_scalar(
        db,
        "SELECT COUNT(*) FROM tabla_inexistente_zzz WHERE x = :p",
        {"p": 1},
    )
    assert bad == 0

    # Si la tx hubiera quedado *aborted* esto lanzaría
    # InFailedSQLTransactionError (el bug original).
    ok = await db.execute(text("SELECT 1"))
    assert ok.scalar() == 1


@pytest.mark.asyncio
async def test_conformity_reads_existing_table_and_keeps_tx_alive(db):
    """conformity lee de tabla existente; la tx sigue usable después."""
    status, pending = await M._conformity_status_raw(
        db, "00000000-0000-0000-0000-000000000000",
    )
    assert status in ("ok", "warning", "critical", "unknown")
    assert isinstance(pending, int)

    ok = await db.execute(text("SELECT 1"))
    assert ok.scalar() == 1


def test_module_no_longer_references_missing_table():
    """Blindaje: la tabla fantasma no puede reintroducirse."""
    src = inspect.getsource(M)
    # No debe CONSULTARSE la tabla fantasma (mención en comentarios es ok).
    assert "FROM conformity_declarations" not in src, (
        "query contra tabla inexistente conformity_declarations reintroducida"
    )
    assert "FROM conformity_routes" in src
