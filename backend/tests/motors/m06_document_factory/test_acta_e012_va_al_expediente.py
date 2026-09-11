"""O2 · el acta de categorizacion no llegaba al expediente del auditor.

EL DEFECTO
    ``GET /systems/{id}/acta-e012.pdf`` y ``.docx`` renderizaban el acta en un
    directorio temporal, la mandaban al navegador y borraban el directorio. No
    quedaba fichero, ni fila en ``documents``, ni huella, ni firma.

    Y el expediente que se entrega al auditor del ENAC se arma leyendo
    EXACTAMENTE esa tabla:

        m09_audit_prep/dossier_generator._collect_documents
            select(Document).where(Document.project_id == project_id, ...)

    Asi que el acta de aprobacion de la categorizacion -- el documento
    fundacional del ciclo, el de la doble firma competente del art. 40.2 del
    RD 311/2022 -- no viajaba en el expediente. En el proyecto del demo que
    recorrio el ciclo entero habia 3 documentos registrados (E-155 y E-808 x2)
    y ningun E-012, habiendose descargado el acta.

    Ademas cada descarga volvia a renderizar. Dos descargas del "mismo" acta
    daban dos ficheros distintos -- el DOCX lleva sellos de tiempo dentro del
    zip; las dos filas E-808 del demo tienen huellas distintas -- y ninguno
    quedaba guardado, de modo que no habia forma de decir que bytes firmo el
    cliente.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import setup_test_project


async def _sistema_categorizado(db) -> tuple[uuid.UUID, uuid.UUID]:
    """Un sistema con su categorizacion, que es lo que el acta declara."""
    _, project_id = await setup_test_project(db)
    system_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO systems (id, project_id, nombre, created_at) "
        "VALUES (:sid, :pid, 'Sistema del acta', now())"
    ), {"sid": str(system_id), "pid": str(project_id)})
    await db.execute(sa_text(
        "INSERT INTO services (id, system_id, nombre, valoracion_c, "
        "  valoracion_i, valoracion_d, valoracion_a, valoracion_t, created_at) "
        "VALUES (gen_random_uuid(), :sid, 'Servicio', 'MEDIO', 'MEDIO', "
        "  'BAJO', 'BAJO', 'BAJO', now())"
    ), {"sid": str(system_id)})
    await db.execute(sa_text(
        "INSERT INTO categorizations (id, system_id, categoria_resultante, "
        "  version, fecha_acta, created_at) "
        "VALUES (gen_random_uuid(), :sid, 'MEDIA', 1, current_date, now())"
    ), {"sid": str(system_id)})
    await db.flush()
    return system_id, uuid.UUID(str(project_id))


async def _codigos_en_el_expediente(db, project_id) -> list[str]:
    """Lo que el generador del expediente ve, por su propio camino."""
    from backend.app.motors.m09_audit_prep.dossier_generator import (
        _collect_documents,
    )

    docs = await _collect_documents(db, project_id)
    return [d["template_codigo"] for d in docs]


@pytest.mark.asyncio
async def test_el_acta_queda_registrada_y_entra_en_el_expediente(db):
    from backend.app.motors.m06_document_factory.acta_e012_generator import (
        generar_o_recuperar_acta_e012,
    )

    system_id, project_id = await _sistema_categorizado(db)

    assert "E-012" not in await _codigos_en_el_expediente(db, project_id)

    doc, resultado = await generar_o_recuperar_acta_e012(db, system_id)

    assert doc is not None
    assert doc.template_codigo == "E-012"
    assert doc.rendered_hash, "el acta registrada sin huella no es comprobable"
    assert resultado["reutilizado"] is False

    assert "E-012" in await _codigos_en_el_expediente(db, project_id), (
        "el acta sigue sin viajar en el expediente del auditor"
    )


@pytest.mark.asyncio
async def test_descargarla_dos_veces_no_crea_dos_actas(db):
    """Un acta registra UNA decision de categorizacion.

    Sin idempotencia cada descarga dejaria una fila nueva y el expediente
    llevaria N copias del mismo documento con huellas distintas -- que es
    justo lo que un auditor no puede leer.
    """
    from backend.app.motors.m06_document_factory.acta_e012_generator import (
        generar_o_recuperar_acta_e012,
    )

    system_id, project_id = await _sistema_categorizado(db)

    doc1, r1 = await generar_o_recuperar_acta_e012(db, system_id)
    doc2, r2 = await generar_o_recuperar_acta_e012(db, system_id)

    assert r1["reutilizado"] is False
    assert r2["reutilizado"] is True
    assert doc1.id == doc2.id
    assert doc1.rendered_hash == doc2.rendered_hash

    codigos = await _codigos_en_el_expediente(db, project_id)
    assert codigos.count("E-012") == 1, f"actas duplicadas: {codigos}"


@pytest.mark.asyncio
async def test_una_categorizacion_nueva_genera_su_propia_acta(db):
    """La idempotencia no congela el acta: si la decision cambia, hay acta
    nueva. Es lo contrario de reutilizar a ciegas."""
    from backend.app.motors.m06_document_factory.acta_e012_generator import (
        generar_o_recuperar_acta_e012,
    )

    system_id, project_id = await _sistema_categorizado(db)
    doc1, _ = await generar_o_recuperar_acta_e012(db, system_id)

    await db.execute(sa_text(
        "INSERT INTO categorizations (id, system_id, categoria_resultante, "
        "  version, fecha_acta, created_at) "
        "VALUES (gen_random_uuid(), :sid, 'ALTA', 2, current_date, now())"
    ), {"sid": str(system_id)})
    await db.flush()

    doc2, r2 = await generar_o_recuperar_acta_e012(db, system_id)

    assert r2["reutilizado"] is False
    assert doc2.id != doc1.id
    codigos = await _codigos_en_el_expediente(db, project_id)
    assert codigos.count("E-012") == 2


@pytest.mark.asyncio
async def test_los_endpoints_no_renderizan_por_su_cuenta(db):
    """El acta sale por la fabrica documental, no por un render suelto.

    Guard contra la reaparicion del camino paralelo: si alguien vuelve a
    renderizar el acta a mano en el endpoint, el documento deja de
    registrarse y el defecto vuelve entero.
    """
    from pathlib import Path

    fuente = Path(
        "backend/app/motors/m01_categorization/api.py"
    ).resolve()
    if not fuente.exists():  # pragma: no cover — ejecutado fuera de la raiz
        fuente = Path(__file__).resolve().parents[4] / (
            "backend/app/motors/m01_categorization/api.py"
        )
    texto = fuente.read_text("utf-8")

    assert "generar_o_recuperar_acta_e012" in texto
    assert "TemporaryDirectory(prefix=\"fulkro_acta_e012_\")" not in texto, (
        "el endpoint volvio a renderizar el acta en un temporal que se borra"
    )
