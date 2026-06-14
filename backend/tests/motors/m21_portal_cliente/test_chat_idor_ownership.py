"""Regresión IDOR cross-tenant en el chat del portal cliente.

El portal cliente corre bajo ``fulkro_app_bypassrls`` durante todo el request
(verify_session lo fija para poder leer client_sessions), lo que DESACTIVA la
RLS. Antes de este blindaje un cliente podía leer/escribir en el hilo de OTRO
cliente pasando su ``thread_id`` directamente (cross-tenant read+write
confirmado empíricamente en el roleplay). El helper ``_assert_thread_in_project``
valida explícitamente la propiedad del hilo independientemente del estado de RLS.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.chat_api import (
    _assert_thread_in_project,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _make_thread(db: AsyncSession, project_id: uuid.UUID) -> uuid.UUID:
    tid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO chat_threads (id, project_id, status, "
                "messages_count) VALUES (:t, :p, 'open', 0)"
            ),
            {"t": str(tid), "p": str(project_id)},
        )
    return tid


@pytest.mark.asyncio
async def test_assert_thread_in_project_rejects_foreign_tenant(db: AsyncSession):
    # Dos proyectos REALES (FK projects) · B dueño del hilo, A intruso.
    _cb, pb = await setup_test_project(db)
    _ca, pa = await setup_test_project(db)
    project_b = uuid.UUID(pb)
    project_a = uuid.UUID(pa)
    thread_b = await _make_thread(db, project_b)

    # El portal cliente corre bajo bypassrls en runtime (verify_session); el
    # helper se apoya en su WHERE explícito. Replicamos ese contexto para que el
    # test refleje el comportamiento real (sin bypassrls la RLS del rol de test
    # ocultaría el hilo incluso al dueño).
    async with _admin_setup(db):
        # Owner (B) → passes
        await _assert_thread_in_project(db, thread_b, project_b)

        # Foreign tenant (A) → 404 (no filtra existencia · IDOR bloqueado)
        with pytest.raises(HTTPException) as exc:
            await _assert_thread_in_project(db, thread_b, project_a)
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_assert_thread_in_project_404_when_missing(db: AsyncSession):
    async with _admin_setup(db):
        with pytest.raises(HTTPException) as exc:
            await _assert_thread_in_project(db, uuid.uuid4(), uuid.uuid4())
        assert exc.value.status_code == 404
