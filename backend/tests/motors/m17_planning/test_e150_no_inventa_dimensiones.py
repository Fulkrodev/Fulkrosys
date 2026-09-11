"""O2 · el Plan de Adecuacion E-150 imprimia las cinco dimensiones en BAJO.

EL DEFECTO
    ``pda_generator.build_pda_context`` leia las dimensiones asi:

        snap_dims = snapshot.get("dimensions", {})
        ...
        "level": (entry or {}).get("level", "BAJO")

    La clave ``dimensions`` NO EXISTE ni ha existido nunca en
    ``categorizations.input_snapshot``. El unico escritor canonico del snapshot
    (``m01_categorization/service.py``) emite ``{"information_types": [...],
    "services": [...]}``, con las valoraciones anidadas dentro. No es deuda de
    datos migrados: es una forma que ningun productor genera.

    Consecuencia: ``snap_dims`` era SIEMPRE ``{}``, el ``.get`` caia SIEMPRE en
    su valor por defecto y el plan imprimia las cinco dimensiones en BAJO en
    CUALQUIER proyecto -- tambien en uno de categoria ALTA. Un entregable
    firmable declarando por debajo el nivel de las cinco dimensiones.

    Y al lado, el mismo ``or "BASICA"`` que ya se quito de otros cuatro
    generadores en el bloque N: ``system_category = cat[0] if cat else "BASICA"``.

MISMA FAMILIA QUE EL ACTA
    Es el defecto de ``67c7edf`` en otro documento: un entregable que se firma
    imprimiendo un nivel que nadie ha valorado. Alli el sintoma era 'MEDIO' por
    una plantilla con `else 'MEDIO'`; aqui es 'BAJO' por una clave que no
    existe. El arreglo es el mismo: leer de donde estan los datos, con la MISMA
    funcion que usa la generacion de la DdA.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import setup_test_project


async def _proyecto_con_dimensiones(db, valoraciones: dict[str, str], categoria: str):
    """Proyecto con un sistema valorado y su categorizacion."""
    _, project_id = await setup_test_project(db)
    system_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO systems (id, project_id, nombre, created_at) "
        "VALUES (:sid, :pid, 'Sistema E-150', now())"
    ), {"sid": str(system_id), "pid": str(project_id)})
    await db.execute(sa_text(
        "INSERT INTO information_types (id, system_id, nombre, valoracion_d, "
        "  valoracion_i, valoracion_c, valoracion_a, valoracion_t, created_at) "
        "VALUES (gen_random_uuid(), :sid, 'Datos', :d, :i, :c, :a, :t, now())"
    ), {"sid": str(system_id), **{k.lower(): valoraciones.get(k) for k in "DICAT"}})
    await db.execute(sa_text(
        "INSERT INTO categorizations (id, system_id, categoria_resultante, "
        "  version, fecha_acta, created_at) "
        "VALUES (gen_random_uuid(), :sid, :cat, 1, current_date, now())"
    ), {"sid": str(system_id), "cat": categoria})
    await db.flush()
    return uuid.UUID(str(project_id))


@pytest.mark.asyncio
async def test_el_plan_imprime_los_niveles_reales_no_BAJO(db):
    from backend.app.motors.m17_planning.pda_generator import build_pda_context

    project_id = await _proyecto_con_dimensiones(
        db, {"D": "ALTO", "I": "MEDIO", "C": "ALTO", "A": "BAJO", "T": None},
        "ALTA",
    )

    ctx = await build_pda_context(db, project_id)
    niveles = {d["code"]: d["level"] for d in ctx.dimensions}

    assert niveles["D"] == "ALTO", f"D salio {niveles['D']!r}"
    assert niveles["I"] == "MEDIO"
    assert niveles["C"] == "ALTO"
    assert niveles["A"] == "BAJO"
    assert niveles["T"] == "No afectada", (
        "una dimension que nadie valoro no se adscribe a ningun nivel "
        f"(Anexo I punto 3) · salio {niveles['T']!r}"
    )
    assert set(niveles.values()) != {"BAJO"}, (
        "las cinco en BAJO otra vez: la lectura volvio a caer en su defecto"
    )


@pytest.mark.asyncio
async def test_el_plan_no_inventa_la_categoria(db):
    """Sin categorizacion el plan no se emite declarando BASICA."""
    from backend.app.motors.m06_document_factory.errores import (
        CategoriaNoDeterminadaError,
    )
    from backend.app.motors.m17_planning.pda_generator import build_pda_context

    _, project_id = await setup_test_project(db)

    with pytest.raises(CategoriaNoDeterminadaError):
        await build_pda_context(db, uuid.UUID(str(project_id)))


@pytest.mark.asyncio
async def test_la_categoria_que_imprime_es_la_aprobada(db):
    from backend.app.motors.m17_planning.pda_generator import build_pda_context

    project_id = await _proyecto_con_dimensiones(
        db, {"D": "MEDIO", "I": "MEDIO", "C": "BAJO", "A": "BAJO", "T": "BAJO"},
        "MEDIA",
    )
    ctx = await build_pda_context(db, project_id)
    assert ctx.system_category == "MEDIA"
