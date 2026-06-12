"""R15 · el cierre BÁSICA valida la autoevaluación CCN-STIC 808 contra la tabla.

Antes `self_assessment_report_id` era un UUID opcional sin comprobar. Ahora
`process_basic_declaration` exige que apunte a un `documents` REAL de ESTE
proyecto que sea la autoevaluación 808 (plantilla E-808*).
"""
import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m27_conformity.conformity_service_paso5 import (
    ConformityError,
    ConformityServicePaso5,
)
from backend.tests.conftest import setup_test_project


async def _set_ctx(db, client_id, project_id):
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )


async def _mk_doc(db, project_id, template_codigo, nombre="doc"):
    doc_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO documents (id, project_id, nombre, template_codigo, "
        "created_at, updated_at) VALUES (:id, :pid, :nom, :tpl, now(), now())"
    ), {"id": str(doc_id), "pid": str(project_id), "nom": nombre, "tpl": template_codigo})
    await db.flush()
    return doc_id


class TestBasica808Gate:
    @pytest.mark.asyncio
    async def test_valida_documento_808(self, db):
        client_id, project_id = await setup_test_project(db)
        await _set_ctx(db, client_id, project_id)
        doc_id = await _mk_doc(db, project_id, "E-808", "Autoevaluación 808")
        svc = ConformityServicePaso5()
        await svc._validate_self_assessment_808(db, project_id, doc_id)  # no lanza

    @pytest.mark.asyncio
    async def test_acepta_variante_e808c(self, db):
        client_id, project_id = await setup_test_project(db)
        await _set_ctx(db, client_id, project_id)
        doc_id = await _mk_doc(db, project_id, "E-808C", "Autoevaluación 808 cierre")
        svc = ConformityServicePaso5()
        await svc._validate_self_assessment_808(db, project_id, doc_id)  # no lanza

    @pytest.mark.asyncio
    async def test_rechaza_inexistente(self, db):
        client_id, project_id = await setup_test_project(db)
        await _set_ctx(db, client_id, project_id)
        svc = ConformityServicePaso5()
        with pytest.raises(ConformityError, match="no corresponde"):
            await svc._validate_self_assessment_808(db, project_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_rechaza_documento_no_808(self, db):
        client_id, project_id = await setup_test_project(db)
        await _set_ctx(db, client_id, project_id)
        doc_id = await _mk_doc(db, project_id, "E-100", "Política")
        svc = ConformityServicePaso5()
        with pytest.raises(ConformityError, match="E-808"):
            await svc._validate_self_assessment_808(db, project_id, doc_id)

    @pytest.mark.asyncio
    async def test_rechaza_documento_de_otro_proyecto(self, db):
        client_a, project_a = await setup_test_project(db)
        client_b, project_b = await setup_test_project(db)
        await _set_ctx(db, client_a, project_a)
        doc_a = await _mk_doc(db, project_a, "E-808", "Autoeval A")
        # contexto del proyecto B no debe validar un doc del A
        await _set_ctx(db, client_b, project_b)
        svc = ConformityServicePaso5()
        with pytest.raises(ConformityError, match="no corresponde"):
            await svc._validate_self_assessment_808(db, project_b, doc_a)
