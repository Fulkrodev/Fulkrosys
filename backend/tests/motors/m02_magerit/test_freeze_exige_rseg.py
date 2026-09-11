"""N4 (2/2) · congelar el analisis de riesgos exige RSEG nombrado y lo atribuye.

EL DEFECTO, DISTINTO DEL DE LA DdA
    `POST /magerit/analysis/{id}/freeze` no recibia aprobador NINGUNO. No es que
    validara mal un nombre: es que el acto no quedaba atribuido a nadie. El
    analisis de riesgos se congelaba y nadie constaba como responsable.

    RD 311/2022 Anexo III punto 1.d, literal, sobre lo que la auditoria debe
    constatar: "Que se ha realizado un analisis de riesgos, con revision y
    aprobacion anual." Una aprobacion sin aprobador no se puede constatar.

POR QUE NO SE ANYADE UN CAMPO DE TEXTO
    Se podria haber copiado el patron de la DdA (`aprobado_por` por query) y
    validarlo. Se hace al reves y mejor: el backend RESUELVE quien es el
    Responsable de la Seguridad del proyecto y lo escribe el. Asi no hay grafia
    que teclear mal, no hay contrato de API que romper, no hay selector que
    anyadir en la interfaz, y es imposible atribuir el acto a quien no toca.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, asigna_rseg, setup_test_project

BASE = "/api/v1/magerit"


async def _analisis_congelable(db, project_id: str) -> str:
    """Analisis con al menos un calculo de riesgo (requisito para congelar)."""
    analysis_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO magerit_analysis "
            "(id, project_id, name, version, status, methodology_version, "
            " calculation_mode, created_at) "
            "VALUES (:id, :pid, 'Analisis test N4', 1, 'draft', 'v3', "
            "        'qualitative', now())"
        ), {"id": str(analysis_id), "pid": project_id})
    await db.flush()
    return str(analysis_id)


@pytest.mark.asyncio
async def test_freeze_sin_rseg_nombrado_devuelve_403(async_client, db):
    _, project_id = await setup_test_project(db)
    analysis_id = await _analisis_congelable(db, project_id)

    r = await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")
    assert r.status_code == 403, (
        f"sin Responsable de la Seguridad nombrado no se puede aprobar el "
        f"analisis de riesgos · recibido {r.status_code}: {r.text[:300]}"
    )
    assert "responsable_seguridad" in r.text or "Responsable de la Seguridad" in r.text


@pytest.mark.asyncio
async def test_con_rseg_nombrado_no_es_403(async_client, db):
    """Con RSEG asignado el control de rol pasa.

    Puede fallar despues por la regla de negocio (no hay calculos de riesgo),
    que es precisamente lo que demuestra que el control de rol quedo atras.
    """
    _, project_id = await setup_test_project(db)
    await asigna_rseg(db, project_id, "Ana RSEG Real")
    analysis_id = await _analisis_congelable(db, project_id)

    r = await async_client.post(f"{BASE}/analysis/{analysis_id}/freeze")
    assert r.status_code != 403, f"recibido {r.status_code}: {r.text[:300]}"
