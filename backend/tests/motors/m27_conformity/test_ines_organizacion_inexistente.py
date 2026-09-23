"""INES de una organizacion que no existe: 404, no 500.

Encontrado el 2026-09-23 barriendo los GET de la API: ``collect_ines_data``
levantaba ValueError y llegaba al usuario como 500 (JSON y DOCX).
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_ines_json_de_organizacion_inexistente_da_404(async_client, db):
    r = await async_client.get(
        f"/api/v1/conformity/organizations/{uuid.uuid4()}/ines/2026/json",
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_ines_docx_de_organizacion_inexistente_da_404(async_client, db):
    r = await async_client.post(
        f"/api/v1/conformity/organizations/{uuid.uuid4()}/ines/2026/docx",
    )
    assert r.status_code == 404, r.text
