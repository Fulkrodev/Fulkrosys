"""P3 · asignar un rol ENS borraba el anterior devolviendo 200 en los dos casos.

EL DEFECTO
    ``role_ens_required`` es UNA columna escalar del contacto
    (``m30_client_contacts/models.py:127``, ``String(30)``): no hay tabla
    puente, asi que un contacto no puede sostener dos roles a la vez. Asignarle
    un segundo PISABA el primero, y la operacion respondia 200 en ambos casos.

    La docstring anterior lo describia como si fuera el disenyo -- "1 contact
    puede tener varios roles via re-asignacion sucesiva -> solo el ultimo queda
    activo" -- y no lo es: es perdida de dato sin aviso.

    Y no es un dato cualquiera. El art. 13 del RD 311/2022 exige designar
    responsable de la informacion, del servicio y de seguridad, diferenciados.
    Borrar una designacion en silencio deja al proyecto sin un responsable que
    alguien creia designado, y nadie se entera hasta la auditoria.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
    RolEnsYaAsignadoError,
)
from backend.tests.conftest import setup_test_project


def _payload(**kw):
    from backend.app.motors.m30_client_contacts.schemas import (
        ClientContactCreate,
    )

    base = {
        "full_name": "Contacto P3",
        "email": "p3@test.es",
        "role_title": "Responsable",
        "role_category": "ciso",
    }
    base.update(kw)
    return ClientContactCreate(**base)


async def _contacto(db, client_uuid, nombre, email):
    svc = ClientContactService(db)
    return await svc.create_contact(
        client_uuid, _payload(full_name=nombre, email=email),
    )


@pytest.mark.asyncio
async def test_asignar_un_segundo_rol_se_niega_en_vez_de_pisar(db: AsyncSession):
    client_id, _ = await setup_test_project(db)
    svc = ClientContactService(db)
    c = await _contacto(db, uuid.UUID(client_id), "Elena", "elena@test.es")

    await svc.assign_ens_required_role(c.id, "responsable_seguridad")

    with pytest.raises(RolEnsYaAsignadoError) as exc:
        await svc.assign_ens_required_role(c.id, "sponsor")

    assert "responsable_seguridad" in str(exc.value), (
        "el mensaje tiene que decir QUE rol se perderia"
    )
    # create_contact devuelve el esquema de salida, no la fila: se relee.
    from sqlalchemy import text as sa_text
    actual = (await db.execute(sa_text(
        "SELECT role_ens_required FROM client_contacts WHERE id = :cid"
    ), {"cid": str(c.id)})).scalar()
    assert actual == "responsable_seguridad", (
        "el rol anterior se perdio pese a haberse negado la operacion"
    )


@pytest.mark.asyncio
async def test_con_el_reemplazo_confirmado_si_se_hace_y_se_cuenta(
    db: AsyncSession,
):
    """Confirmado no significa silencioso: la respuesta dice que se desplazo."""
    client_id, _ = await setup_test_project(db)
    svc = ClientContactService(db)
    c = await _contacto(db, uuid.UUID(client_id), "Elena", "elena2@test.es")

    await svc.assign_ens_required_role(c.id, "responsable_seguridad")
    actualizado, desplazados = await svc.assign_ens_required_role(
        c.id, "sponsor", reemplazar_rol_actual=True,
    )

    assert actualizado.role_ens_required == "sponsor"
    assert desplazados["rol_anterior_del_contacto"] == "responsable_seguridad"


@pytest.mark.asyncio
async def test_quitarle_el_rol_a_otro_tambien_se_cuenta(db: AsyncSession):
    """Un rol solo lo sostiene un contacto; cambiarlo de manos se reporta."""
    client_id, _ = await setup_test_project(db)
    svc = ClientContactService(db)
    a = await _contacto(db, uuid.UUID(client_id), "Ana", "ana@test.es")
    b = await _contacto(db, uuid.UUID(client_id), "Bruno", "bruno@test.es")

    await svc.assign_ens_required_role(a.id, "responsable_seguridad")
    _, desplazados = await svc.assign_ens_required_role(
        b.id, "responsable_seguridad",
    )

    assert "Ana" in desplazados.get("contacto_vaciado", ""), desplazados
    from sqlalchemy import text as sa_text
    rol_de_ana = (await db.execute(sa_text(
        "SELECT role_ens_required FROM client_contacts WHERE id = :cid"
    ), {"cid": str(a.id)})).scalar()
    assert rol_de_ana is None


@pytest.mark.asyncio
async def test_por_http_responde_409_y_no_200(db: AsyncSession, async_client):
    client_id, project_id = await setup_test_project(db)
    svc = ClientContactService(db)
    c = await _contacto(db, uuid.UUID(client_id), "Elena", "elena3@test.es")
    await svc.assign_ens_required_role(c.id, "responsable_seguridad")
    await db.commit()

    base = f"/api/v1/admin/projects/{project_id}/ens-required-roles"
    r = await async_client.patch(
        f"{base}/sponsor", json={"contact_id": str(c.id)},
    )
    assert r.status_code == 409, (
        f"se piso la designacion anterior devolviendo {r.status_code}"
    )

    r2 = await async_client.patch(
        f"{base}/sponsor",
        json={"contact_id": str(c.id), "reemplazar_rol_actual": True},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["desplazados"]["rol_anterior_del_contacto"] == (
        "responsable_seguridad"
    )
