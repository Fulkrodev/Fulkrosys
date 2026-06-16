"""Tests M27 distintivo público · §2.8/272 keyset scan sin truncación silenciosa.

El endpoint público GET /public/conformity/badge/{cert_id}/badge.svg resuelve el
proyecto cuyo cert_id derivado (uuid5 one-way, no invertible en SQL) coincide.
Antes el scan usaba 'LIMIT 1000' → truncación silenciosa (un cert válido fuera del
top-1000 daba 404). Ahora pagina por keyset hasta agotar.
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m27_conformity.distintivo_generator import derive_cert_id
from backend.tests.conftest import setup_test_project


BADGE = "/api/v1/public/conformity/badge/{cert}/badge.svg"


@pytest.mark.asyncio
async def test_public_badge_resolves_valid_cert(async_client, db):
    """Un cert_id derivado de un proyecto existente devuelve el SVG (200)."""
    _, project_id = await setup_test_project(db)
    cert_id = derive_cert_id(uuid.UUID(project_id))

    r = await async_client.get(BADGE.format(cert=cert_id))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert r.headers["x-cert-id"] == str(cert_id)
    assert "<svg" in r.text


@pytest.mark.asyncio
async def test_public_badge_unknown_cert_returns_404(async_client, db):
    """Un cert_id que no deriva de ningún proyecto activo devuelve 404
    (tras agotar el scan paginado, no por truncación)."""
    await setup_test_project(db)  # hay proyectos, pero ninguno casa
    bogus = uuid.uuid5(uuid.NAMESPACE_OID, "fulkro-conformity:does-not-exist")

    r = await async_client.get(BADGE.format(cert=bogus))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_public_badge_resolves_across_batches(async_client, db, monkeypatch):
    """Con el lote forzado a 1, el scan keyset igual encuentra un cert cuyo
    proyecto NO es el primero por id → demuestra que no hay truncación silenciosa
    (regresión del antiguo LIMIT 1000)."""
    import backend.app.motors.m27_conformity.public_api as public_api

    # Crea varios proyectos; el cert objetivo será de uno de ellos.
    ids = []
    for _ in range(4):
        _, pid = await setup_test_project(db)
        ids.append(pid)
    # Objetivo: el proyecto con el id más alto (lo último que pagina ASC).
    target = max(ids)
    cert_id = derive_cert_id(uuid.UUID(target))

    # Fuerza lotes de tamaño 1 para ejercitar el bucle de paginación.
    monkeypatch.setattr(public_api, "_BADGE_SCAN_BATCH", 1)

    r = await async_client.get(BADGE.format(cert=cert_id))
    assert r.status_code == 200, r.text
    assert r.headers["x-cert-id"] == str(cert_id)
