"""P2 · el checklist sabia que faltaba y no habia forma de pedirselo.

EL DEFECTO
    `check_deliverables` calcula desde la version 1 que entregables exige la
    categoria y cuales faltan. Pero de esa cuenta solo salia publicada la
    CIFRA -- `readiness_quick` devuelve `entregables_presentes: 1` y
    `entregables_total: 28` -- nunca la LISTA.

    Sin lista, la interfaz no podia ofrecer generarlos. Y sin esa oferta, el
    generador generico `POST /projects/{id}/documents/generate` no tenia quien
    lo llamara: `grep -rn "documents/generate" frontend/` devolvia CERO
    resultados. El motor estaba entero -- saca 63 de los 65 entregables en una
    pasada -- y le faltaba el cable hasta la pantalla.

QUE SE COMPRUEBA
    Que la lista publicada es LA MISMA que usa el checklist, no una copia. Una
    segunda lista de entregables exigidos seria el patron que llevamos toda la
    sesion cerrando: la misma regla escrita dos veces, divergiendo.
"""
from __future__ import annotations


import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_publica_la_misma_lista_que_usa_el_checklist(db, async_client):
    from backend.app.motors.m09_audit_prep import checklist_service

    _, project_id = await setup_test_project(db)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/audit-prep/projects/{project_id}"
        f"/entregables-requeridos?categoria=BASICA"
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()

    assert cuerpo["requeridos"] == checklist_service.get_required_deliverables(
        "BASICA"
    ), "la lista publicada no es la del checklist: hay una segunda copia"
    assert cuerpo["total"] == len(cuerpo["requeridos"])


@pytest.mark.asyncio
async def test_lo_que_ya_esta_generado_no_sale_como_pendiente(db, async_client):
    _, project_id = await setup_test_project(db)
    await db.execute(sa_text(
        "INSERT INTO documents (id, project_id, nombre, template_codigo, "
        "  estado, created_at) VALUES (gen_random_uuid(), :pid, "
        "  'E-012 acta', 'E-012', 'generado', now())"
    ), {"pid": str(project_id)})
    await db.commit()

    cuerpo = (await async_client.get(
        f"/api/v1/audit-prep/projects/{project_id}"
        f"/entregables-requeridos?categoria=BASICA"
    )).json()

    assert "E-012" in cuerpo["presentes"]
    assert "E-012" not in cuerpo["faltan"]
    assert cuerpo["presentes_count"] == 1


@pytest.mark.asyncio
async def test_separa_lo_generable_de_lo_que_no_tiene_plantilla(
    db, async_client,
):
    """Informacion que el operador necesita ANTES de pulsar nada.

    Un entregable exigido sin plantilla en el catalogo no se puede generar; que
    el boton lo intente y falle 27 veces no ayuda a nadie.
    """
    _, project_id = await setup_test_project(db)
    await db.commit()

    cuerpo = (await async_client.get(
        f"/api/v1/audit-prep/projects/{project_id}"
        f"/entregables-requeridos?categoria=BASICA"
    )).json()

    generables = set(cuerpo["faltan"])
    sin_plantilla = set(cuerpo["faltan_sin_plantilla"])
    assert not (generables & sin_plantilla), (
        "un codigo no puede estar a la vez en las dos listas"
    )
    assert generables | sin_plantilla == (
        set(cuerpo["requeridos"]) - set(cuerpo["presentes"])
    ), "las dos listas juntas tienen que ser todo lo que falta"


@pytest.mark.asyncio
async def test_la_categoria_se_deriva_del_proyecto_si_no_se_da(db, async_client):
    """La pantalla no tiene por que saber la categoria para preguntar."""
    _, project_id = await setup_test_project(db)
    await db.execute(sa_text(
        "UPDATE projects SET categoria_objetivo = 'MEDIA' WHERE id = :pid"
    ), {"pid": str(project_id)})
    await db.commit()

    cuerpo = (await async_client.get(
        f"/api/v1/audit-prep/projects/{project_id}/entregables-requeridos"
    )).json()
    assert cuerpo["categoria"] == "MEDIA"
    assert cuerpo["total"] > 28, "MEDIA exige mas entregables que BASICA"


def test_el_frontend_llama_al_generador_generico():
    """El cable existe · era exactamente esto lo que faltaba.

    `grep -rn "documents/generate" frontend/` devolvia cero resultados: el
    generador estaba entero y sin quien lo llamara.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[4]
    cliente = (raiz / "frontend/lib/api/documents.ts").read_text("utf-8")
    assert "documents/generate" in cliente
    assert "getEntregablesRequeridos" in cliente

    panel = (
        raiz / "frontend/components/documents/EntregablesGeneratorPanel.tsx"
    ).read_text("utf-8")
    assert "generateDocumentoPorCodigo" in panel

    pagina = (
        raiz
        / "frontend/app/(admin)/admin/projects/[id]/documents/page.tsx"
    ).read_text("utf-8")
    assert "EntregablesGeneratorPanel" in pagina, (
        "el panel existe pero no esta montado en ninguna pagina"
    )


@pytest.mark.asyncio
async def test_el_generador_no_pide_al_navegador_el_NIF_del_cliente(db):
    """P2 · la identidad del cliente la pone el backend, no el llamante.

    Las plantillas declaran `cliente.razon_social`, `cliente.nif` y
    `cliente.domicilio_social` como obligatorios, y el generador generico
    rechazaba con 422 "Missing required placeholders" cualquier llamada que no
    los trajera a mano. Eso hacia el endpoint inservible desde una pantalla.

    Y ademas era una mala idea: dejar que el llamante ponga el NIF que quiera
    en un documento firmable es lo contrario de lo que hace falta. El dato lo
    tiene la base.
    """
    from backend.app.motors.m06_document_factory.governance_context import (
        build_governance_context,
    )

    _, project_id = await setup_test_project(db)
    await db.execute(sa_text(
        "UPDATE clients SET domicilio_fiscal = 'Plaza Mayor 1, Madrid' "
        "WHERE id = (SELECT client_id FROM projects WHERE id = :pid)"
    ), {"pid": str(project_id)})
    await db.flush()

    ctx = await build_governance_context(db, project_id)
    cliente = ctx.get("cliente", {})

    assert cliente.get("razon_social"), "falta la razon social en el contexto base"
    assert cliente.get("nif"), "falta el NIF en el contexto base"
    assert cliente.get("domicilio_social") == "Plaza Mayor 1, Madrid"


def test_el_domicilio_del_cliente_se_puede_escribir_desde_el_producto():
    """Un dato que los documentos exigen y no habia forma de rellenar.

    Los 9 clientes del demo tenian `domicilio_fiscal` a NULL y el esquema de
    edicion no aceptaba el campo (`extra="forbid"` -> 422), asi que el
    generador rechazaba todo entregable de cualquiera de ellos.
    """
    from backend.app.core.clients.schemas import ClientUpdate

    assert "domicilio_fiscal" in ClientUpdate.model_fields, (
        "el domicilio social vuelve a no ser editable: sin el, el generador "
        "documental rechaza los entregables con 422"
    )
