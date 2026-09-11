"""O2 · lo que el sistema genera queda registrado, o no existe para el auditor.

EL DEFECTO
    Seis productores documentales construian su fichero en memoria y lo
    devolvian como ``Response`` sin dejar rastro:

        m02_magerit/api.py            informe E-028 (PDF y DOCX)
        m17_planning/api.py           plan de adecuacion E-150
        m27_conformity/api.py         declaracion E-041 (admin)
        m27_conformity/portal_api.py  la misma, por el portal del cliente
        m06_document_factory/api.py   manual SGSI E-160, plan director E-170

    Y los dos consumidores del expediente leen EXCLUSIVAMENTE ``documents``:
    ``checklist_service.check_deliverables`` marca `missing` con severidad
    `error` lo que no este ahi, y ``dossier_generator._collect_documents`` deja
    la carpeta con solo su `.keep`. El consultor generaba el plan de
    adecuacion, se lo descargaba, y el expediente seguia diciendo que no
    existe.

POR QUE UN REGISTRADOR Y NO LLAMAR A generate_document
    ``generate_document`` RENDERIZA desde la plantilla DOCX del catalogo. Estos
    seis no renderizan plantillas: construyen el documento con python-docx a
    partir de datos del proyecto. Lo que les faltaba no era el render, era la
    mitad de atras -- huella, firma, fila, copia durable, auditoria --, que es
    exactamente lo que hay en ``registro.py`` y lo que ``generate_document``
    hace tambien.
"""
from __future__ import annotations

import uuid

import pytest

from backend.tests.conftest import setup_test_project


def _docx_minimo() -> bytes:
    """Un DOCX de verdad, construido igual que lo hacen los productores."""
    import io

    from docx import Document as Docx

    doc = Docx()
    doc.add_paragraph("Documento de prueba del registro m06.")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


async def _codigos_en_el_expediente(db, project_id) -> list[str]:
    from backend.app.motors.m09_audit_prep.dossier_generator import (
        _collect_documents,
    )

    return [d["template_codigo"] for d in await _collect_documents(db, project_id)]


@pytest.mark.asyncio
async def test_un_entregable_registrado_llega_al_expediente(db):
    from backend.app.motors.m06_document_factory.registro import (
        registrar_documento_generado,
    )

    _, project_id = await setup_test_project(db)
    project_id = uuid.UUID(str(project_id))

    assert "E-150" not in await _codigos_en_el_expediente(db, project_id)

    fila = await registrar_documento_generado(
        db, project_id=project_id, template_codigo="E-150",
        nombre="E-150 - Plan de Adecuacion al ENS",
        docx_bytes=_docx_minimo(), generated_by="test",
    )

    assert fila.rendered_hash, "sin huella el documento no es comprobable"
    assert fila.docx_path
    assert "E-150" in await _codigos_en_el_expediente(db, project_id)


@pytest.mark.asyncio
async def test_descargarlo_n_veces_deja_una_sola_fila(db):
    """Son descargas: el consultor pulsa el boton N veces.

    Sin idempotencia ``documents`` se llena de duplicados y el checklist
    empieza a contar basura.
    """
    from backend.app.motors.m06_document_factory.registro import (
        registrar_documento_generado,
    )

    _, project_id = await setup_test_project(db)
    project_id = uuid.UUID(str(project_id))

    ids = set()
    for _ in range(3):
        fila = await registrar_documento_generado(
            db, project_id=project_id, template_codigo="E-160",
            nombre="E-160 - Manual del SGSI",
            docx_bytes=_docx_minimo(), generated_by="test",
        )
        ids.add(fila.id)

    assert len(ids) == 1, f"{len(ids)} filas para el mismo entregable"
    codigos = await _codigos_en_el_expediente(db, project_id)
    assert codigos.count("E-160") == 1, codigos


@pytest.mark.asyncio
async def test_no_sobrescribe_un_documento_ya_firmado(db):
    """Sobrescribir un documento firmado seria borrar la prueba de que se
    firmo. Si la fila esta firmada, la regeneracion crea otra."""
    from sqlalchemy import text as sa_text

    from backend.app.motors.m06_document_factory.registro import (
        registrar_documento_generado,
    )

    _, project_id = await setup_test_project(db)
    project_id = uuid.UUID(str(project_id))

    primera = await registrar_documento_generado(
        db, project_id=project_id, template_codigo="E-170",
        nombre="E-170 - Plan Director de Seguridad",
        docx_bytes=_docx_minimo(), generated_by="test",
    )
    await db.execute(sa_text(
        "UPDATE documents SET client_signing_intent_id = gen_random_uuid() "
        "WHERE id = :did"
    ), {"did": str(primera.id)})
    await db.flush()

    segunda = await registrar_documento_generado(
        db, project_id=project_id, template_codigo="E-170",
        nombre="E-170 - Plan Director de Seguridad",
        docx_bytes=_docx_minimo(), generated_by="test",
    )

    assert segunda.id != primera.id, (
        "la regeneracion sobrescribio la fila firmada"
    )
    codigos = await _codigos_en_el_expediente(db, project_id)
    assert codigos.count("E-170") == 2


@pytest.mark.asyncio
async def test_sin_bytes_no_se_registra_nada(db):
    from backend.app.motors.m06_document_factory.registro import (
        registrar_documento_generado,
    )

    _, project_id = await setup_test_project(db)
    with pytest.raises(ValueError):
        await registrar_documento_generado(
            db, project_id=uuid.UUID(str(project_id)),
            template_codigo="E-150", generated_by="test",
        )
