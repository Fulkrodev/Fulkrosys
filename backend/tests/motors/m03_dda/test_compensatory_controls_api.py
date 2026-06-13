"""Tests API compensatorias tipadas (RD 311/2022 Art. 8) · feat/fulkro-100 Ola D."""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.real_auth

_BASE = "/api/v1/dda/projects"


async def _login_owner(async_client) -> str:
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


def _url(project_id: str, suffix: str = "") -> str:
    return f"{_BASE}/{project_id}/compensatory-controls{suffix}"


def _body() -> dict:
    return {
        "measure_code": "op.exp.8",
        "motivo_no_aplica_directa": "El SIEM cloud no soporta el agente on-prem",
        "control_compensatorio": "Reenvío de logs vía syslog cifrado + revisión semanal",
        "riesgo_residual": "Bajo · latencia de detección +15 min",
    }


@pytest.mark.asyncio
async def test_requires_owner(async_client):
    res = await async_client.get(_url(str(uuid.uuid4())))
    assert res.status_code in (401, 403), res.text


@pytest.mark.asyncio
async def test_create_unknown_project_404(async_client):
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        _url(str(uuid.uuid4())), json=_body(),
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_create_list_and_get(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)

    res = await async_client.post(
        _url(project_id), json=_body(), headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201, res.text
    cc = res.json()
    assert cc["estado"] == "pendiente_aprobacion"
    assert cc["measure_code"] == "op.exp.8"
    assert cc["aprobado_por"] is None

    lst = await async_client.get(_url(project_id))
    assert lst.status_code == 200, lst.text
    assert len(lst.json()) == 1

    detail = await async_client.get(_url(project_id, f"/{cc['id']}"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == cc["id"]


@pytest.mark.asyncio
async def test_decide_approve(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    cc = (await async_client.post(
        _url(project_id), json=_body(), headers={"X-CSRF-Token": csrf},
    )).json()

    res = await async_client.post(
        _url(project_id, f"/{cc['id']}/approve"),
        json={"aprobada": True, "aprobado_por": "Dirección · CEO"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    decided = res.json()
    assert decided["estado"] == "aprobada"
    assert decided["aprobado_por"] == "Dirección · CEO"
    assert decided["fecha_aprobacion"] is not None


@pytest.mark.asyncio
async def test_decide_reject(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    cc = (await async_client.post(
        _url(project_id), json=_body(), headers={"X-CSRF-Token": csrf},
    )).json()

    res = await async_client.post(
        _url(project_id, f"/{cc['id']}/approve"),
        json={"aprobada": False, "aprobado_por": "Dirección"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["estado"] == "rechazada"


@pytest.mark.asyncio
async def test_get_unknown_404(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _login_owner(async_client)
    res = await async_client.get(_url(project_id, f"/{uuid.uuid4()}"))
    assert res.status_code == 404, res.text


def test_aplicabilidad_enum_has_compensada():
    """El enum Aplicabilidad expone COMPENSADA (Art. 8)."""
    from backend.app.motors.m03_dda.enums import Aplicabilidad

    assert Aplicabilidad.COMPENSADA.value == "compensada"
