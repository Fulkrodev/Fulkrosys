"""El contexto RLS sobrevive al commit, y por eso el refresh ya no revienta.

EL FALLO
    El contexto de inquilino se fija con ``set_config(..., true)``: alcance
    TRANSACCIÓN. ``commit()`` la termina y borra el GUC. La siguiente consulta
    abre transacción nueva sin contexto, las políticas RLS no reconocen a nadie
    y la sesión no ve **ni su propia fila recién escrita**.

    El síntoma típico: ``db.refresh(obj)`` detrás de ``db.commit()`` levanta
    "Could not refresh instance", FastAPI responde 500 — y la operación YA está
    guardada. El usuario reintenta y duplica. La huella quedó en la base del
    demo: un proyecto ``DUPLICADO-CLAUDE``, creado dos veces por esta vía.

    Hay 30 parejas ``commit() -> refresh()`` en ``backend/app``. Este test no
    persigue las 30: comprueba la propiedad de la que dependen todas.

POR QUÉ ESTE TEST NO USA EL FIXTURE `db`
    Y esto es lo más importante del módulo. El fixture `db` de `conftest.py`
    ata la sesión a una transacción de CONEXIÓN abierta a mano
    (``conn.begin()``) para poder revertirla al terminar. Dentro de ese montaje
    ``session.commit()`` **no es un commit**: cierra una subtransacción y deja
    viva la de fuera, así que el GUC transaccional no se borra nunca.

    Es decir: el arnés hacía IMPOSIBLE observar este fallo. Un test escrito con
    el fixture pasa igual antes y después del arreglo — comprobado —, que es la
    peor clase de test verde. Por eso aquí se abre una sesión propia, como la
    que sirve una petición real, y se limpia a mano.

POR QUÉ NO VALE is_local=false
    Porque el GUC viviría lo que viva la CONEXIÓN, y las conexiones se reciclan
    en el pool: la petición siguiente, de otro cliente, heredaría el contexto
    del anterior. Eso ya no es un 500, es una fuga entre inquilinos. El último
    test lo congela.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.database import set_tenant_context

pytestmark = pytest.mark.requires_db


class _Escenario:
    """Cliente + proyecto reales en la base, y su limpieza."""

    def __init__(self) -> None:
        self.client_id = uuid.uuid4()
        self.project_id = uuid.uuid4()
        self.cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async def sembrar(self, engine) -> None:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            await conn.execute(text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Cliente RLS Q2', :cif, now())"
            ), {"id": str(self.client_id), "cif": self.cif})
            await conn.execute(text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proyecto RLS Q2', now())"
            ), {"id": str(self.project_id), "cid": str(self.client_id)})

    async def limpiar(self, engine) -> None:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            await conn.execute(text("DELETE FROM projects WHERE id = :id"),
                               {"id": str(self.project_id)})
            await conn.execute(text("DELETE FROM clients WHERE id = :id"),
                               {"id": str(self.client_id)})


@pytest.fixture
async def sesion_de_verdad():
    """Una sesión cuyo ``commit()`` es un commit, como en producción."""
    engine = create_async_engine(get_settings().database_url, echo=False)
    escenario = _Escenario()
    await escenario.sembrar(engine)
    session = AsyncSession(bind=engine, expire_on_commit=False)
    try:
        yield session, escenario
    finally:
        await session.close()
        await escenario.limpiar(engine)
        await engine.dispose()


@pytest.mark.asyncio
async def test_la_sesion_ve_su_propia_fila_despues_de_hacer_commit(sesion_de_verdad):
    session, esc = sesion_de_verdad
    await set_tenant_context(session, client_id=esc.client_id,
                             project_id=esc.project_id)
    await session.commit()

    visto = await session.scalar(
        text("SELECT nombre FROM projects WHERE id = :pid"),
        {"pid": str(esc.project_id)},
    )
    assert visto == "Proyecto RLS Q2", (
        "tras el commit la sesión no ve su propio proyecto: el contexto RLS se "
        "perdió y cualquier refresh posterior devuelve 500 con la operación ya "
        "guardada — que es como se fabricó el DUPLICADO-CLAUDE del demo"
    )


@pytest.mark.asyncio
async def test_db_refresh_tras_commit_no_revienta(sesion_de_verdad):
    """El síntoma exacto que producía el 500 y los duplicados."""
    from backend.app.models.core import Project

    session, esc = sesion_de_verdad
    await set_tenant_context(session, client_id=esc.client_id,
                             project_id=esc.project_id)
    proyecto = await session.get(Project, esc.project_id)
    assert proyecto is not None
    await session.commit()
    await session.refresh(proyecto)  # <- "Could not refresh instance"
    assert proyecto.nombre == "Proyecto RLS Q2"


@pytest.mark.asyncio
async def test_el_contexto_se_acumula_y_no_se_pisa(sesion_de_verdad):
    """Fijar sólo el proyecto no puede borrar el cliente ya fijado."""
    session, esc = sesion_de_verdad
    await set_tenant_context(session, client_id=esc.client_id)
    await set_tenant_context(session, project_id=esc.project_id)
    await session.commit()

    cid = await session.scalar(
        text("SELECT current_setting('app.current_client_id', true)"))
    pid = await session.scalar(
        text("SELECT current_setting('app.current_project_id', true)"))
    assert cid == str(esc.client_id)
    assert pid == str(esc.project_id)


@pytest.mark.asyncio
async def test_olvidar_el_inquilino_es_explicito(sesion_de_verdad):
    """Una tarea de fondo que reusa sesión tiene que poder soltar el contexto."""
    from backend.app.database import clear_tenant_context

    session, esc = sesion_de_verdad
    await set_tenant_context(session, client_id=esc.client_id,
                             project_id=esc.project_id)
    await session.commit()
    await clear_tenant_context(session)
    await session.commit()

    visto = await session.scalar(
        text("SELECT nombre FROM projects WHERE id = :pid"),
        {"pid": str(esc.project_id)},
    )
    assert visto is None, "tras olvidar el inquilino, RLS vuelve a esconderlo"


def test_el_guc_sigue_siendo_transaccional_y_no_de_conexion():
    """La garantía que impide que el arreglo se convierta en una fuga."""
    fuente = (Path(__file__).resolve().parents[3]
              / "backend" / "app" / "database.py").read_text(encoding="utf-8")
    assert "set_config('app.current_client_id', :cid, true)" in fuente
    assert "set_config('app.current_project_id', :pid, true)" in fuente
    assert "', false)" not in fuente, (
        "algún set_config pasó a ser de conexión: el contexto de un inquilino "
        "puede filtrarse a la petición siguiente al reciclarse el pool"
    )
