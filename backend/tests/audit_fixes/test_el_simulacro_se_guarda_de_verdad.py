"""La ejecución del simulacro de auditoría se guarda: sobrevive a la petición.

EL FALLO
    ``dry_run_api.execute_dry_run`` devolvía el resultado del servicio y nunca
    llamaba a ``db.commit()``. El servicio hacía ``flush()`` —suficiente para
    que el propio endpoint lo vea y lo devuelva— y al cerrarse la sesión de la
    petición la transacción se revertía entera.

    Consecuencia: la ejecución se veía en pantalla y desaparecía. La tabla
    ``audit_dry_run_results`` estaba SIEMPRE vacía, el histórico del panel no
    tenía nada que comparar y no había forma de enseñarle progreso a un
    auditor. Tampoco quedaba la alerta de no conformidades mayores.

POR QUÉ NO LO CAZÓ NADA DE LO QUE HABÍA — y esto es el hallazgo de verdad
    1. ``test_execute_dry_run_persists_result`` dice «row persistido» y
       comprueba la fila **con la misma sesión** que la escribió. Con un
       ``flush()`` basta. Nunca pudo distinguir «guardado» de «visible dentro
       de mi propia transacción».
    2. Y tampoco lo cazaría un test por HTTP con el cliente de pruebas: el
       fixture ``async_client`` sustituye ``get_db`` por la sesión transaccional
       del test, atada a una transacción externa que se revierte al final. Ahí
       ``commit()`` no es un commit. Comprobado: con el arreglo puesto, la
       llamada por HTTP devuelve 200 y la fila sigue sin estar en la base.

    Es decir: el arnés era incapaz de observar la diferencia, en los dos
    caminos. Por eso este test llama a la función del endpoint con una sesión
    de verdad —como la que sirve una petición real— y comprueba el resultado
    desde OTRA conexión, que es lo que significa «guardado».
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings

pytestmark = pytest.mark.requires_db


@pytest.fixture
async def motor_independiente():
    engine = create_async_engine(get_settings().database_url, echo=False)
    yield engine
    await engine.dispose()


async def _sembrar_proyecto(engine) -> tuple[uuid.UUID, uuid.UUID]:
    client_id, project_id = uuid.uuid4(), uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await conn.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Cliente simulacro', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await conn.execute(text(
            "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
            "created_at) VALUES (:id, :cid, 'Proyecto simulacro', 'MEDIA', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    return client_id, project_id


async def _limpiar(engine, client_id, project_id) -> None:
    sentencias = (
        "DELETE FROM audit_dry_run_results WHERE project_id = :pid",
        "DELETE FROM audit_sim_findings WHERE run_id IN "
        "  (SELECT id FROM audit_sim_runs WHERE project_id = :pid)",
        "DELETE FROM audit_sim_runs WHERE project_id = :pid",
        "DELETE FROM alerts WHERE project_id = :pid",
        "DELETE FROM audit_log WHERE project_id = :pid",
        "DELETE FROM projects WHERE id = :pid",
    )
    # Cada borrado en su propia transaccion: si una tabla no existe en esta
    # variante del esquema, el fallo no aborta los demas.
    for sql in sentencias:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
                await conn.execute(text(sql), {"pid": str(project_id)})
        except Exception:  # noqa: BLE001
            pass
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            await conn.execute(text("DELETE FROM clients WHERE id = :cid"),
                               {"cid": str(client_id)})
    except Exception:  # noqa: BLE001 — la limpieza no decide el veredicto
        pass


@pytest.mark.asyncio
async def test_la_ejecucion_sobrevive_al_cierre_de_la_peticion(motor_independiente):
    from backend.app.agents.dry_run_api import execute_dry_run
    from backend.tests.agents.test_audit_dry_run_service import _mock_m10_run

    client_id, project_id = await _sembrar_proyecto(motor_independiente)
    try:
        mock_m10 = _mock_m10_run(project_id, "MEDIA", score=75)

        async def _fake_run_simulation(db_arg, *, project_id, categoria):
            db_arg.add(mock_m10)
            await db_arg.flush()
            return mock_m10

        a11_payload = {
            "veredicto": "favorable_con_remediacion",
            "probabilidad_certificacion_primera": 0.7,
            "narrativa_md": "## Conclusión\n...",
            "pac": [], "preguntas_contextuales": [],
        }

        sesion = AsyncSession(bind=motor_independiente, expire_on_commit=False)
        try:
            with patch(
                "backend.app.motors.m10_audit_sim.audit_simulator."
                "AuditSimulatorService.run_simulation",
                side_effect=_fake_run_simulation,
            ), patch(
                "backend.app.agents.agent_11_auditor_virtual."
                "Agent11AuditorVirtual.generate_supplementary_audit",
                AsyncMock(return_value=a11_payload),
            ):
                await execute_dry_run(
                    project_id=project_id,
                    db=sesion,
                    current_user=SimpleNamespace(id=uuid.uuid4()),
                )
        finally:
            await sesion.close()

        # La prueba de fuego: OTRA conexión.
        async with motor_independiente.begin() as conn:
            # bypassrls: aqui se comprueba que la fila EXISTE, no si RLS la
            # deja ver a un inquilino sin contexto (eso es otro test).
            await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            n = await conn.scalar(
                text("SELECT count(*) FROM audit_dry_run_results "
                     "WHERE project_id = :pid"),
                {"pid": str(project_id)},
            )
        assert n == 1, (
            "la ejecución del simulacro no está en la base: el endpoint no hizo "
            "commit y el histórico se queda vacío para siempre"
        )
    finally:
        await _limpiar(motor_independiente, client_id, project_id)
