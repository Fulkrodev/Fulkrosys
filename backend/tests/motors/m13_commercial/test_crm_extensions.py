"""Tests SAN-D MB-19.1 · CRM lead extensions migration + models.

Cubre:
- Lead model nuevos campos extension (estado_contacto · primer_contacto_at
  · fecha_perdida · razon_perdida · fecha_conversion · convertido_a_proyecto_id
  · temperature_level · categoria_objetivo_ens · archetype_ens).
- Proposal model nuevos campos extension (feedback_cliente · cambios_desde_anterior
  · superseded · fecha_aceptacion · agent_19_metadata).
- LeadStageHistory model audit trail.
- CheckConstraints estado_contacto + temperature_level + categoria_objetivo_ens.

Refs: ADR-041 · sand_crm_lead_extensions migration.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.models.commercial import Lead, Proposal, LeadStageHistory
from backend.tests.conftest import _admin_setup


# ====================== Lead extension fields ======================

@pytest.mark.asyncio
async def test_lead_extension_fields_persist(db):
    """Lead acepta nuevos campos extension MB-19.1."""
    lead_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Lead Ext Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Lead Ext Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, contacto_email, "
            "estado, estado_contacto, primer_contacto_at, "
            "temperature_level, categoria_objetivo_ens, archetype_ens, "
            "convertido_a_proyecto_id, created_at) "
            "VALUES (:id, 'TestCo SL', 'test@testco.es', 'nuevo', "
            "'reunion_agendada', now(), 6, 'MEDIA', 'pyme_industrial', "
            ":pid, now())"
        ), {"id": str(lead_id), "pid": str(project_id)})
    await db.flush()

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one()
    assert lead.estado_contacto == "reunion_agendada"
    assert lead.primer_contacto_at is not None
    assert lead.temperature_level == 6
    assert lead.categoria_objetivo_ens == "MEDIA"
    assert lead.archetype_ens == "pyme_industrial"
    assert lead.convertido_a_proyecto_id == project_id


@pytest.mark.asyncio
async def test_lead_estado_contacto_check_constraint_rejects_invalid(db):
    """CheckConstraint ck_leads_estado_contacto rechaza valores fuera enum."""
    lead_id = uuid.uuid4()
    # Savepoint pattern · permite recuperar la transacción tras
    # check constraint violation sin abortar el resto del test
    await db.execute(text("SAVEPOINT before_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception) as exc_info:
            await db.execute(text(
                "INSERT INTO leads (id, empresa_nombre, "
                "estado_contacto, created_at) "
                "VALUES (:id, 'Bad Lead', 'INVALID_STATE', now())"
            ), {"id": str(lead_id)})
            await db.flush()
        assert "ck_leads_estado_contacto" in str(exc_info.value).lower() \
            or "check" in str(exc_info.value).lower()
    finally:
        await db.execute(text("ROLLBACK TO SAVEPOINT before_violation"))
        await db.execute(text("RESET ROLE"))


@pytest.mark.asyncio
async def test_lead_temperature_check_constraint_rejects_out_of_range(db):
    """CheckConstraint ck_leads_temperature_range rechaza temperature_level
    fuera 1-7."""
    lead_id = uuid.uuid4()
    await db.execute(text("SAVEPOINT before_temp_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception) as exc_info:
            await db.execute(text(
                "INSERT INTO leads (id, empresa_nombre, "
                "temperature_level, created_at) "
                "VALUES (:id, 'Hot Lead', 99, now())"
            ), {"id": str(lead_id)})
            await db.flush()
        assert "check" in str(exc_info.value).lower()
    finally:
        await db.execute(text("ROLLBACK TO SAVEPOINT before_temp_violation"))
        await db.execute(text("RESET ROLE"))


@pytest.mark.asyncio
async def test_lead_categoria_objetivo_ens_check_constraint(db):
    """CheckConstraint ck_leads_categoria_objetivo_ens valida BASICA/MEDIA/ALTA."""
    lead_id_ok = uuid.uuid4()
    async with _admin_setup(db):
        # Acepta BASICA
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, "
            "categoria_objetivo_ens, created_at) "
            "VALUES (:id, 'Cat OK', 'BASICA', now())"
        ), {"id": str(lead_id_ok)})
        await db.flush()

    # Rechaza valor inválido (savepoint pattern)
    bad_id = uuid.uuid4()
    await db.execute(text("SAVEPOINT before_cat_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception):
            await db.execute(text(
                "INSERT INTO leads (id, empresa_nombre, "
                "categoria_objetivo_ens, created_at) "
                "VALUES (:id, 'Cat BAD', 'CRITICA', now())"
            ), {"id": str(bad_id)})
            await db.flush()
    finally:
        await db.execute(text("ROLLBACK TO SAVEPOINT before_cat_violation"))
        await db.execute(text("RESET ROLE"))


# ====================== Proposal extension fields ======================

@pytest.mark.asyncio
async def test_proposal_extension_fields_persist(db):
    """Proposal acepta nuevos campos revisions MB-19.1."""
    lead_id = uuid.uuid4()
    proposal_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Prop Lead', now())"
        ), {"id": str(lead_id)})
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, version, estado, "
            "feedback_cliente, cambios_desde_anterior, superseded, "
            "fecha_aceptacion, agent_19_metadata, created_at) "
            "VALUES (:id, :lid, 2, 'sent', "
            "'Necesito ajustar precio', 'Reduccion 10% importe', "
            "FALSE, NULL, "
            "'{\"agent_run_id\": \"run-001\", \"tokens_used\": 1234}'::jsonb, "
            "now())"
        ), {"id": str(proposal_id), "lid": str(lead_id)})
    await db.flush()

    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one()
    assert proposal.feedback_cliente == "Necesito ajustar precio"
    assert proposal.cambios_desde_anterior == "Reduccion 10% importe"
    assert proposal.superseded is False
    assert proposal.fecha_aceptacion is None
    assert proposal.agent_19_metadata == {
        "agent_run_id": "run-001",
        "tokens_used": 1234,
    }


@pytest.mark.asyncio
async def test_proposal_superseded_default_false(db):
    """Proposal.superseded default FALSE server_default."""
    lead_id = uuid.uuid4()
    proposal_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Lead Sup', now())"
        ), {"id": str(lead_id)})
        # NO especifica superseded · debe inferir FALSE default
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, version, created_at) "
            "VALUES (:id, :lid, 1, now())"
        ), {"id": str(proposal_id), "lid": str(lead_id)})
    await db.flush()

    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one()
    assert proposal.superseded is False


# ====================== LeadStageHistory audit trail ======================

@pytest.mark.asyncio
async def test_lead_stage_history_persistence(db):
    """LeadStageHistory persiste transición workflow."""
    lead_id = uuid.uuid4()
    history_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Hist Lead', now())"
        ), {"id": str(lead_id)})
        await db.execute(text(
            "INSERT INTO lead_stage_history (id, lead_id, "
            "estado_anterior, estado_nuevo, cambiado_por_user_id, "
            "notas, metadata_jsonb, created_at) "
            "VALUES (:id, :lid, 'respondio', 'reunion_agendada', :uid, "
            "'Cliente confirmó cita', "
            "'{\"meeting_at\": \"2026-05-14T10:00:00Z\"}'::jsonb, now())"
        ), {
            "id": str(history_id), "lid": str(lead_id),
            "uid": str(user_id),
        })
    await db.flush()

    result = await db.execute(
        select(LeadStageHistory).where(LeadStageHistory.id == history_id)
    )
    history = result.scalar_one()
    assert history.estado_anterior == "respondio"
    assert history.estado_nuevo == "reunion_agendada"
    assert history.cambiado_por_user_id == user_id
    assert history.notas == "Cliente confirmó cita"
    assert history.metadata_jsonb == {"meeting_at": "2026-05-14T10:00:00Z"}


@pytest.mark.asyncio
async def test_lead_stage_history_estado_nuevo_check_constraint(db):
    """CheckConstraint ck_lead_stage_history_estado_nuevo rechaza valor inválido."""
    lead_id = uuid.uuid4()
    history_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'BadHist Lead', now())"
        ), {"id": str(lead_id)})

    await db.execute(text("SAVEPOINT before_history_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception) as exc_info:
            await db.execute(text(
                "INSERT INTO lead_stage_history (id, lead_id, "
                "estado_nuevo, created_at) "
                "VALUES (:id, :lid, 'INVALID_STATE', now())"
            ), {"id": str(history_id), "lid": str(lead_id)})
            await db.flush()
        assert "check" in str(exc_info.value).lower()
    finally:
        await db.execute(text(
            "ROLLBACK TO SAVEPOINT before_history_violation"
        ))
        await db.execute(text("RESET ROLE"))


@pytest.mark.asyncio
async def test_lead_stage_history_cascade_on_lead_delete(db):
    """ON DELETE CASCADE · borrar lead borra history rows."""
    lead_id = uuid.uuid4()
    history_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:id, 'Cascade Lead', now())"
        ), {"id": str(lead_id)})
        await db.execute(text(
            "INSERT INTO lead_stage_history (id, lead_id, "
            "estado_nuevo, created_at) "
            "VALUES (:id, :lid, 'nuevo', now())"
        ), {"id": str(history_id), "lid": str(lead_id)})
        await db.flush()

        # Verify exists
        cnt_before = (await db.execute(text(
            "SELECT count(*) FROM lead_stage_history WHERE id = :id"
        ), {"id": str(history_id)})).scalar()
        assert cnt_before == 1

        # Delete lead → cascade
        await db.execute(text("DELETE FROM leads WHERE id = :id"), {
            "id": str(lead_id),
        })
        await db.flush()

        cnt_after = (await db.execute(text(
            "SELECT count(*) FROM lead_stage_history WHERE id = :id"
        ), {"id": str(history_id)})).scalar()
        assert cnt_after == 0
