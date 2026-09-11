"""P1 · la Declaracion de Conformidad afirmaba una falsedad en su cara.

EL DEFECTO
    La seccion 4 del E-180 imprimia:

        Conformes 60 · No conformes 0 · Porcentaje conformidad 100,0%

    sobre un proyecto que el propio simulacro Pre-ENAC de la plataforma
    puntuaba 0/100 con 59 contradicciones y UNA sola evidencia subida. Las dos
    cifras convivian en la misma aplicacion contradiciendose de plano.

    El 100% no estaba mal calculado: es el recuento correcto de entradas de la
    DdA con ``estado_implementacion = 'implantada'``
    (``distintivo_generator.py:142``). Lo falso era la ETIQUETA -- llamar
    "conformidad" a una autodeclaracion que nadie cruza con el Vault de
    evidencias. Y el ``max(aplicables - conformes, 0)`` de la linea 143 hacia
    IMPOSIBLE por construccion que el numero delatara la incoherencia.

LA ELECCION, Y POR QUE
    El encargo daba dos salidas: no emitir por debajo de un umbral, o imprimir
    el readiness real en la cara del documento. Se elige la SEGUNDA.

    Un umbral seria una puerta sobre un numero que sale de datos
    autodeclarados: cerrariamos el paso apoyandonos en la misma cifra cuya
    fiabilidad es el problema. Y bloquearia un borrador legitimo a mitad de
    proyecto. Nombrar bien la cifra, en cambio, arregla la falsedad en su
    origen y no se puede sortear: el lector ve en que se apoya lo que lee sin
    abrir otra pantalla.

    Con UNA excepcion, que no es un umbral sino una incoherencia entre dos
    manejadores del mismo documento: la E-180 es la autodeclaracion del art. 38
    para BASICA, y el endpoint hermano ya rechaza con 422 emitirla en ruta de
    CERTIFICACION (MEDIA/ALTA). Este no miraba. En el demo eso produjo una
    autodeclaracion BASICA para un proyecto MEDIA.
"""
from __future__ import annotations

import re
import uuid
import zipfile

import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import setup_test_project


def _texto_del_docx(datos: bytes) -> str:
    with zipfile.ZipFile(__import__("io").BytesIO(datos)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))


async def _proyecto_con_dda_toda_implantada(db) -> uuid.UUID:
    """El escenario del demo: la DdA entera declarada implantada, sin una sola
    evidencia detras."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(str(project_id))
    medidas = (await db.execute(sa_text(
        "SELECT id FROM ens_measures LIMIT 8"
    ))).scalars().all()
    assert medidas, "la BD de test no trae el catalogo de medidas"
    for mid in medidas:
        await db.execute(sa_text(
            "INSERT INTO dda_entries (id, project_id, measure_id, "
            "  aplicabilidad, estado_implementacion, version, created_at) "
            "VALUES (gen_random_uuid(), :pid, :mid, 'aplica', 'implantada', "
            "  1, now())"
        ), {"pid": str(pid), "mid": str(mid)})
    await db.flush()
    return pid


@pytest.mark.asyncio
async def test_el_documento_separa_lo_declarado_de_lo_verificado(db):
    from backend.app.motors.m27_conformity.distintivo_generator import (
        build_distintivo_context,
        generate_declaration_docx,
    )

    pid = await _proyecto_con_dda_toda_implantada(db)
    ctx = await build_distintivo_context(db, pid)
    texto = _texto_del_docx(generate_declaration_docx(ctx).getvalue())

    assert "Porcentaje conformidad" not in texto, (
        "el documento vuelve a llamar 'conformidad' a una autodeclaracion"
    )
    assert "Implantación declarada en la DdA (autodeclarada)" in texto
    assert "CONFORMIDAD VERIFICADA" in texto
    assert "Puntuación de preparación de auditoría" in texto

    # P · el TITULAR es la cifra verificada. El orden de una tabla es una
    # afirmacion sobre que importa: poner la declarada arriba invita a leerla y
    # quedarse ahi, que es lo que hacia que el documento dijera "100%".
    assert texto.index("CONFORMIDAD VERIFICADA") < texto.index(
        "Implantación declarada en la DdA"
    ), "la cifra declarada volvio a encabezar la tabla"


@pytest.mark.asyncio
async def test_dice_cuantas_medidas_declara_sin_evidencia(db):
    """La diferencia entre declarado y verificado no se calla: se nombra."""
    from backend.app.motors.m27_conformity.distintivo_generator import (
        build_distintivo_context,
        generate_declaration_docx,
    )

    pid = await _proyecto_con_dda_toda_implantada(db)
    ctx = await build_distintivo_context(db, pid)

    assert ctx.conformes_count == 8, "el escenario no reproduce el caso"
    assert ctx.pct_conformidad == 100.0, "el escenario no reproduce el caso"
    assert ctx.verificadas_con_evidencia < ctx.conformes_count, (
        "sin una sola evidencia subida, lo verificado no puede igualar a lo "
        "declarado"
    )

    texto = _texto_del_docx(generate_declaration_docx(ctx).getvalue())
    assert "Declaradas SIN evidencia que las sostenga" in texto
    assert "no tienen evidencia vigente que las sostenga" in texto, (
        "el documento afirma implantacion sin avisar de que no esta probada"
    )
    assert "refleja el estado consignado, no un estado verificado" in texto


@pytest.mark.asyncio
async def test_la_resta_ya_no_se_aplana_a_cero(db):
    """`max(..., 0)` tapaba por construccion cualquier incoherencia."""
    from pathlib import Path

    fuente = Path(
        "backend/app/motors/m27_conformity/distintivo_generator.py"
    ).resolve()
    if not fuente.exists():  # pragma: no cover
        fuente = Path(__file__).resolve().parents[4] / (
            "backend/app/motors/m27_conformity/distintivo_generator.py"
        )
    cuerpo = fuente.read_text("utf-8")
    assert "no_conformes_count = max(" not in cuerpo


@pytest.mark.asyncio
async def test_no_se_autodeclara_BASICA_un_proyecto_de_certificacion(
    db, async_client,
):
    """La E-180 es la autodeclaracion del art. 38 para BASICA.

    En ruta de CERTIFICACION la conformidad la acredita una entidad acreditada,
    no el propio sujeto. El endpoint hermano ya lo rechazaba con 422; este
    emitia sin mirar.
    """
    _, project_id = await setup_test_project(db)
    await db.execute(sa_text(
        "INSERT INTO conformity_routes (id, project_id, route_type, status, "
        "  created_at) VALUES (gen_random_uuid(), :pid, 'certificacion_enac', "
        "  'planned', now())"
    ), {"pid": str(project_id)})
    await db.flush()

    r = await async_client.post(
        f"/api/v1/conformity/projects/{project_id}/declaration/generate-docx"
    )
    assert r.status_code == 422, (
        f"se emitio una autodeclaracion BASICA en ruta de certificacion: {r.status_code}"
    )
    assert "CERTIFICACIÓN" in r.text or "certificación" in r.text
