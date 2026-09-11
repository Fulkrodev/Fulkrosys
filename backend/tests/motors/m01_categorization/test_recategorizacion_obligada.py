"""Regla 2 · ADR-061 era un hueco funcional disfrazado de decision, y se arregla.

QUE DECIA ADR-061
    "NO se han migrado las categorizaciones existentes. El cambio afecta a
     calculos nuevos. Una categorizacion guardada antes del cambio conserva sus
     cinco dimensiones en BAJO, y nadie la ha revisado."

    Eso no es una contrapartida de una decision: es un dato incorrecto en la
    base con una nota al lado. Una categorizacion es el acto que fija la
    categoria del sistema y de ella cuelga TODO -- que medidas aplican, la DdA,
    el plan, el alcance --. Si se calculo con una regla que la propia norma
    contradice, no vale, y decirlo en un ADR no la arregla.

QUE SE HACE EN VEZ DE DOCUMENTARLO
    NO se recalcula por detras. Una categorizacion es un acto aprobado y
    firmado (`aprobado_por`, `fecha_acta`, `version`): sobrescribirla en una
    migracion seria falsificar un acta. Lo que se hace es MARCARLA: se recomputa
    desde `input_snapshot` con la regla correcta y, si el resultado difiere de
    lo guardado -- o no hay snapshot con el que comprobarlo --, la fila queda
    marcada como que exige recategorizar, con el motivo escrito.
"""
from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


async def _sistema(db, project_id: str) -> str:
    sid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:id, :pid, 'Sistema regla2', now())"
        ), {"id": str(sid), "pid": project_id})
    await db.flush()
    return str(sid)


async def _categorizacion(db, system_id: str, categoria: str, snapshot: dict | None):
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, "
            " fecha_acta, version, input_snapshot, created_at) "
            "VALUES (:id, :sid, :cat, :f, 1, CAST(:snap AS JSONB), now())"
        ), {"id": str(cid), "sid": system_id, "cat": categoria, "f": date.today(),
            "snap": json.dumps(snapshot) if snapshot is not None else None})
    await db.flush()
    return str(cid)


# ── la columna existe y por defecto no molesta ────────────────────────
@pytest.mark.asyncio
async def test_existe_la_marca_de_recategorizacion(db):
    cols = {r[0] for r in (await db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'categorizations'"
    ))).all()}
    assert "requiere_recategorizacion" in cols
    assert "motivo_recategorizacion" in cols


# ── el detector ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_marca_la_que_se_calculo_con_la_regla_vieja(db):
    """Sistema sin una sola valoracion: la regla vieja daba BASICA."""
    from backend.app.motors.m01_categorization.recategorizacion import (
        marcar_categorizaciones_afectadas,
    )

    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)
    # Snapshot de un sistema que nadie valoro: la regla vieja lo hacia BASICA.
    snap = {"information_types": [
        {"id": str(uuid.uuid4()), "nombre": "Datos",
         "valoraciones": {"D": None, "I": None, "C": None, "A": None, "T": None}},
    ], "services": []}
    cat_id = await _categorizacion(db, system_id, "BASICA", snap)

    n = await marcar_categorizaciones_afectadas(db)
    assert n >= 1

    fila = (await db.execute(text(
        "SELECT requiere_recategorizacion, motivo_recategorizacion "
        "FROM categorizations WHERE id = :id"
    ), {"id": cat_id})).first()
    assert fila[0] is True, "no se marco una categorizacion calculada con la regla vieja"
    motivo = fila[1] or ""
    assert "AFECTADA" in motivo.upper(), f"el motivo no explica la causa: {motivo!r}"
    assert "Anexo I" in motivo, "el motivo tiene que citar la norma"
    # El caso concreto: sin una sola dimension valorada no hay categoria, y la
    # regla vieja devolvia BASICA.
    assert "SIN CATEGORIZAR" in motivo.upper() and "BASICA" in motivo.upper()


@pytest.mark.asyncio
async def test_no_marca_la_que_sigue_siendo_correcta(db):
    """Si recomputar da lo mismo, la categorizacion vale y no se toca."""
    from backend.app.motors.m01_categorization.recategorizacion import (
        marcar_categorizaciones_afectadas,
    )

    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)
    snap = {"information_types": [
        {"id": str(uuid.uuid4()), "nombre": "Datos",
         "valoraciones": {"D": "ALTO", "I": None, "C": None, "A": None, "T": None}},
    ], "services": []}
    cat_id = await _categorizacion(db, system_id, "ALTA", snap)

    await marcar_categorizaciones_afectadas(db)
    fila = (await db.execute(text(
        "SELECT requiere_recategorizacion FROM categorizations WHERE id = :id"
    ), {"id": cat_id})).first()
    assert fila[0] is False, "se marco una categorizacion que sigue siendo correcta"


@pytest.mark.asyncio
async def test_marca_la_que_no_tiene_snapshot_con_el_que_comprobar(db):
    """Sin snapshot no se puede verificar: se marca, no se da por buena."""
    from backend.app.motors.m01_categorization.recategorizacion import (
        marcar_categorizaciones_afectadas,
    )

    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)
    cat_id = await _categorizacion(db, system_id, "MEDIA", None)

    await marcar_categorizaciones_afectadas(db)
    fila = (await db.execute(text(
        "SELECT requiere_recategorizacion, motivo_recategorizacion "
        "FROM categorizations WHERE id = :id"
    ), {"id": cat_id})).first()
    assert fila[0] is True
    assert "snapshot" in (fila[1] or "").lower()


@pytest.mark.asyncio
async def test_es_idempotente(db):
    from backend.app.motors.m01_categorization.recategorizacion import (
        marcar_categorizaciones_afectadas,
    )

    _, project_id = await setup_test_project(db)
    system_id = await _sistema(db, project_id)
    await _categorizacion(db, system_id, "MEDIA", None)

    primera = await marcar_categorizaciones_afectadas(db)
    segunda = await marcar_categorizaciones_afectadas(db)
    assert primera >= 1
    assert segunda == 0, "la segunda pasada no puede volver a marcar lo ya marcado"
