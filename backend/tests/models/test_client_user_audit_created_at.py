"""Una fila de ``client_user_audit`` sin ``created_at`` explicito se guarda.

Las descargas del portal de cliente (documento y evidencia) crean la fila de
auditoria sin pasar ``created_at``. Sin default en el modelo, el ORM mandaba
NULL a una columna NOT NULL y la descarga respondia 500 despues de leer el
fichero: el cliente no podia descargar nada. Encontrado el 2026-09-23 barriendo
los GET del portal con identificadores reales.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.client_portal import ClientUserAudit
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.mark.asyncio
async def test_la_auditoria_de_descarga_se_guarda_sin_created_at(db):
    client_id, _ = await setup_test_project(db)
    async with _admin_setup(db):
        fila = ClientUserAudit(
            client_user_id=None,
            client_id=client_id,
            action="portal_document_download",
            metadata_jsonb={"document_id": "x"},
        )
        db.add(fila)
        await db.flush()
        guardada = (await db.execute(
            select(ClientUserAudit).where(ClientUserAudit.id == fila.id)
        )).scalar_one()
    assert guardada.created_at is not None
