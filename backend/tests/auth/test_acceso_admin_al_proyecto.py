"""O2 · Marcos recibia 403 en sus propias rutas por preguntar por un atributo
que no existe.

EL DEFECTO
    Dos motores resolvian el acceso a un proyecto con el mismo bloque copiado:

        m01_categorization/dimensions_api._ensure_access
        m_workflow_engine/api._ensure_project_access

    y los dos decidian asi:

        pool = getattr(subject, "pool", None) or getattr(subject.user, "pool", None)
        if pool == "auth_users" or getattr(subject.user, "is_marcos", False):
            ...  # rama de administracion

    ``AuthSubject`` declara ``__slots__ = ("user", "role_pool", "email")``: no
    hay ``pool``, ni en el sujeto ni en el ``User``. Y ``is_marcos`` no existe en
    ningun modelo -- el unico ``_is_marcos`` del repositorio es una funcion
    privada del middleware de fichajes. Los dos ``getattr`` devolvian siempre
    ``None``/``False``: la rama de administracion era codigo inalcanzable y toda
    peticion de Marcos caia en la rama de cliente, se quedaba sin ``client_id``
    y respondia 403.

POR QUE NO LO CAZO NADIE ANTES
    ``test_dimensions.py`` anuncia en su cabecera "HTTP endpoints (GET reader ·
    PATCH admin)" y no hace una sola llamada HTTP: sus 14 tests entran por el
    service. El control de acceso vivia en el endpoint, asi que nunca se
    ejecuto. Estos tests entran por HTTP, que es por donde entra el navegador.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.tests.conftest import setup_test_project

RAIZ = Path(__file__).resolve().parents[3]


# ================================================================
# Por HTTP · el camino que recorre el navegador
# ================================================================


@pytest.mark.asyncio
async def test_admin_lee_las_dimensiones_del_proyecto(db, async_client):
    """GET /api/v1/projects/{id}/dimensions como Marcos -> 200, no 403."""
    _, project_id = await setup_test_project(db)

    r = await async_client.get(f"/api/v1/projects/{project_id}/dimensions")

    assert r.status_code != 403, (
        "Marcos no alcanza su propio proyecto: la rama de administracion del "
        f"control de acceso no se ejecuta. Cuerpo: {r.text[:200]}"
    )
    assert r.status_code == 200, r.text
    assert "madurez_ens_actual" in r.json()


@pytest.mark.asyncio
async def test_admin_escribe_las_dimensiones_del_proyecto(db, async_client):
    """PATCH como Marcos -> 200. Sin esto el asistente no puede guardar."""
    _, project_id = await setup_test_project(db)

    r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/dimensions",
        json={"madurez_ens_actual": "L2"},
    )
    assert r.status_code != 403, (
        f"PATCH admin rechazado con 403: {r.text[:200]}"
    )
    assert r.status_code == 200, r.text
    assert r.json()["madurez_ens_actual"] == "L2"


@pytest.mark.asyncio
async def test_proyecto_inexistente_sigue_dando_404(db, async_client):
    """El arreglo abre la puerta a Marcos, no la quita: un proyecto que no
    existe sigue respondiendo 404 y no 200."""
    r = await async_client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/dimensions"
    )
    assert r.status_code == 404, r.text


# ================================================================
# Que no vuelva a escribirse
# ================================================================


def test_nadie_pregunta_por_atributos_que_no_existen():
    """``subject.pool`` e ``is_marcos`` no vuelven al codigo de autorizacion.

    Un ``getattr`` con valor por defecto sobre un nombre que no existe no falla:
    devuelve el valor por defecto y convierte un error de autorizacion en un
    silencio. Ese silencio es lo que dejo la rama admin muerta durante meses.
    """
    ficheros = list((RAIZ / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500, f"solo {len(ficheros)} ficheros barridos"

    patron = re.compile(
        r'getattr\(\s*subject(?:\.user)?\s*,\s*"(?:pool|is_marcos)"'
    )
    malos = []
    for py in ficheros:
        for i, linea in enumerate(
            py.read_text("utf-8", errors="ignore").splitlines(), 1
        ):
            if patron.search(linea.split("#", 1)[0]):
                malos.append(f"{py.relative_to(RAIZ)}:{i}: {linea.strip()[:80]}")
    assert not malos, (
        "vuelve a decidirse el acceso con atributos inexistentes; el campo "
        "real es `role_pool` (auth/global_dep.py):\n  " + "\n  ".join(malos)
    )


def test_el_atributo_que_se_usa_existe_de_verdad():
    """Anti-vacuidad del guard anterior: comprueba contra el modelo real."""
    from backend.app.auth.global_dep import AuthSubject
    from backend.app.auth.acceso_proyecto import POOL_MARCOS, es_marcos

    assert "role_pool" in AuthSubject.__slots__
    assert "pool" not in AuthSubject.__slots__

    class _Sujeto:
        role_pool = POOL_MARCOS

    class _Cliente:
        role_pool = "cliente"

    assert es_marcos(_Sujeto()) is True
    assert es_marcos(_Cliente()) is False
    assert es_marcos(object()) is False


def test_los_dos_motores_llaman_a_la_fuente_unica():
    for rel in (
        "backend/app/motors/m01_categorization/dimensions_api.py",
        "backend/app/motors/m_workflow_engine/api.py",
    ):
        texto = (RAIZ / rel).read_text("utf-8")
        assert "asegurar_acceso_al_proyecto" in texto, (
            f"{rel} volvio a tener su propia copia del control de acceso"
        )
