"""N4 · congelar la DdA exige que quien aprueba sea el RSEG nombrado del proyecto.

LA MEDICION QUE PEDIA N4, PRIMERO
    `require_ens_role` NO EXISTIA en el repositorio: cero apariciones en .py,
    .ts, .tsx y .md. Asi que no habia dependencia que borrar ni "sus 13 tests"
    que quitar. Los 13 tests que si existen son
    `m30_client_contacts/test_ens_required_roles.py`, y prueban otra cosa: que
    los 6 roles ENS esten ASIGNADOS antes de generar ciertos documentos. Es una
    comprobacion de completitud de datos, no de autorizacion.

    Rutas para los actos que la norma asigna a un rol: SI EXISTEN.
      POST /api/v1/dda/projects/{project_id}/freeze   <- aprobar la DdA
    Con lo cual aplica la rama "si existen, aplicala ahi".

EL DEFECTO
    `freeze_dda` recibia `aprobado_por: str = Query(..., description="Nombre del
    RSEG que aprueba")` y NO comprobaba nada. Cualquier cadena valia. La DdA
    quedaba congelada y firmada a nombre de quien se escribiera, incluso si esa
    persona no era el Responsable de la Seguridad del proyecto, o no existia.

    RD 311/2022 art. 11.1: "se diferenciara el responsable de la informacion, el
    responsable del servicio, el responsable de la seguridad y el responsable
    del sistema". El art. 11.3 remite a la politica para las atribuciones de
    cada uno. Si el sistema deja aprobar a nombre de cualquiera, esa
    diferenciacion no existe en la practica.

    Nota de alcance: el endpoint YA estaba tras `require_owner` (router
    Marcos-only), asi que esto no era un agujero de autenticacion. Lo que
    faltaba era que el NOMBRE del aprobador correspondiera al rol.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project

RSEG = "responsable_seguridad"


async def _crea_contacto(db, client_id: str, nombre: str, rol: str | None):
    await db.execute(text("SELECT set_config('app.current_client_id', :c, true)"),
                     {"c": client_id})
    await db.execute(text(
        "INSERT INTO client_contacts (id, client_id, full_name, email, "
        "role_title, role_category, role_ens_required, is_active, created_at) "
        "VALUES (:id, :cid, :n, :e, 'Cargo test', 'tecnico', :r, true, now())"
    ), {"id": str(uuid.uuid4()), "cid": client_id, "n": nombre,
        "e": f"{uuid.uuid4().hex[:8]}@test.local", "r": rol})
    await db.flush()


@pytest.mark.asyncio
async def test_freeze_rechaza_403_a_quien_no_es_el_rseg(
    async_client, db,
):
    """EL TEST QUE FALLABA ANTES: pasaba con 200/400, nunca con 403."""
    client_id, project_id = await setup_test_project(db)
    await _crea_contacto(db, client_id, "Ana RSEG Real", RSEG)
    await _crea_contacto(db, client_id, "Pepe Sistemas", "responsable_sistema")

    r = await async_client.post(
        f"/api/v1/dda/projects/{project_id}/freeze",
        params={"aprobado_por": "Pepe Sistemas"},
    )
    assert r.status_code == 403, (
        f"un contacto que NO es el RSEG no puede aprobar la DdA · "
        f"recibido {r.status_code}: {r.text[:300]}"
    )
    assert RSEG in r.text or "Responsable de la Seguridad" in r.text


@pytest.mark.asyncio
async def test_freeze_rechaza_403_a_un_nombre_inventado(
    async_client, db,
):
    client_id, project_id = await setup_test_project(db)
    await _crea_contacto(db, client_id, "Ana RSEG Real", RSEG)

    r = await async_client.post(
        f"/api/v1/dda/projects/{project_id}/freeze",
        params={"aprobado_por": "Cualquiera Que Yo Escriba"},
    )
    assert r.status_code == 403, f"recibido {r.status_code}: {r.text[:300]}"


@pytest.mark.asyncio
async def test_freeze_rechaza_403_si_no_hay_rseg_nombrado(
    async_client, db,
):
    """Sin RSEG asignado no se puede aprobar: no hay a quien atribuirlo."""
    client_id, project_id = await setup_test_project(db)
    await _crea_contacto(db, client_id, "Pepe Sistemas", "responsable_sistema")

    r = await async_client.post(
        f"/api/v1/dda/projects/{project_id}/freeze",
        params={"aprobado_por": "Pepe Sistemas"},
    )
    assert r.status_code == 403, f"recibido {r.status_code}: {r.text[:300]}"


@pytest.mark.asyncio
async def test_el_rseg_nombrado_pasa_el_control_de_rol(
    async_client, db,
):
    """El RSEG correcto NO recibe 403.

    Puede recibir 400 por la regla de negocio (la DdA exige >=80% de medidas
    valoradas para congelarse), que es justo lo que demuestra que el control de
    ROL ya lo paso y el flujo siguio adelante.
    """
    client_id, project_id = await setup_test_project(db)
    await _crea_contacto(db, client_id, "Ana RSEG Real", RSEG)

    r = await async_client.post(
        f"/api/v1/dda/projects/{project_id}/freeze",
        params={"aprobado_por": "Ana RSEG Real"},
    )
    assert r.status_code != 403, (
        f"el RSEG nombrado no puede ser rechazado por rol · {r.text[:300]}"
    )
