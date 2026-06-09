"""Tests M18 Communication & Reporting Engine.

Cubre:
- Plan (defaults + activar + 3 escalations default)
- Reports (5 tipos, RAG determinista, lifecycle draft→reviewed→sent)
- Escalations (5 triggers precargados, publicación en feed M20)
- DOCX
- API + RLS
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m18_communication.escalation_service import (
    EscalationError,
    EscalationService,
    TRIGGERS,
)
from backend.app.motors.m18_communication.plan_service import (
    DEFAULT_ESCALATIONS,
    CommunicationPlanService,
    PlanError,
)
from backend.app.motors.m18_communication.report_generator import (
    REPORT_TEMPLATES,
    ReportError,
    ReportGeneratorService,
)
from backend.app.motors.m20_workspace.workspace_service import WorkspaceService
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/communication"
BASE_WS = "/api/v1/workspace"


async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


# ─────────── Catálogo ───────────

def test_report_templates_has_5_types():
    assert len(REPORT_TEMPLATES) == 5
    expected = {"weekly_sponsor", "monthly_comite", "quarterly_direccion",
                "compliance_resources", "quick_wins"}
    assert set(REPORT_TEMPLATES.keys()) == expected


def test_triggers_has_7_types():
    # C#35 (FRENTE C): +incidente_deadline_notificacion_lucia (reloj Art.33).
    # H#54 (FRENTE H · DEC-5): +aepd_deadline_notificacion_72h (reloj RGPD Art.33).
    assert len(TRIGGERS) == 7
    expected = {"riesgo_materializado_alto", "paron_por_cliente_5_dias",
                "hallazgo_critico_auditoria", "evidencia_critica_caducada",
                "nc_mayor_detectada", "incidente_deadline_notificacion_lucia",
                "aepd_deadline_notificacion_72h"}
    assert set(TRIGGERS.keys()) == expected


def test_default_escalations_has_3_rules():
    assert len(DEFAULT_ESCALATIONS) == 3


# ─────────── Plan ───────────

@pytest.mark.asyncio
async def test_create_plan_with_defaults(db):
    _, project_id = await _setup_tenant(db)
    plan = await CommunicationPlanService().create_plan(
        db, project_id=uuid.UUID(project_id),
    )
    assert plan.estado == "draft"
    assert "sponsor" in plan.destinatarios
    assert "weekly" in plan.frecuencias
    assert len(plan.escalations) == 3


@pytest.mark.asyncio
async def test_create_plan_duplicate_rejected(db):
    _, project_id = await _setup_tenant(db)
    await CommunicationPlanService().create_plan(db, project_id=uuid.UUID(project_id))
    with pytest.raises(PlanError):
        await CommunicationPlanService().create_plan(db, project_id=uuid.UUID(project_id))


@pytest.mark.asyncio
async def test_activate_plan(db):
    _, project_id = await _setup_tenant(db)
    await CommunicationPlanService().create_plan(db, project_id=uuid.UUID(project_id))
    plan = await CommunicationPlanService().activate_plan(db, uuid.UUID(project_id))
    assert plan.estado == "active"
    assert plan.activado_at is not None


# ─────────── Reports ───────────

@pytest.mark.asyncio
async def test_generate_weekly_sponsor(db):
    _, project_id = await _setup_tenant(db)
    report = await ReportGeneratorService().generate_report(
        db, uuid.UUID(project_id), tipo="weekly_sponsor",
    )
    assert report.tipo == "weekly_sponsor"
    assert report.destinatario_rol == "sponsor"
    assert report.estado == "generated"
    assert report.contenido_jsonb is not None
    assert "tareas_completadas_count" in report.contenido_jsonb


@pytest.mark.asyncio
async def test_generate_monthly_comite(db):
    _, project_id = await _setup_tenant(db)
    report = await ReportGeneratorService().generate_report(
        db, uuid.UUID(project_id), tipo="monthly_comite",
    )
    assert report.tipo == "monthly_comite"
    assert report.destinatario_rol == "comite_seguridad"
    assert "progreso_pct" in report.contenido_jsonb


@pytest.mark.asyncio
async def test_generate_quarterly_rag_green_when_empty(db):
    _, project_id = await _setup_tenant(db)
    report = await ReportGeneratorService().generate_report(
        db, uuid.UUID(project_id), tipo="quarterly_direccion",
    )
    # Proyecto vacío: progreso=0, nc_mayores=0, riesgos_criticos=0, retraso=0
    # → rule RED por progreso<70
    assert report.semaforo_rag == "red"


@pytest.mark.asyncio
async def test_rag_determinista_green_conditions():
    rag = ReportGeneratorService._calculate_rag(
        progreso_pct=95, nc_mayores=0, riesgos_criticos=0, retraso_semanas=0,
    )
    assert rag == "green"


@pytest.mark.asyncio
async def test_rag_determinista_amber_when_progreso_85():
    rag = ReportGeneratorService._calculate_rag(
        progreso_pct=85, nc_mayores=0, riesgos_criticos=0, retraso_semanas=0,
    )
    assert rag == "amber"


@pytest.mark.asyncio
async def test_rag_determinista_red_when_nc_mayores():
    rag = ReportGeneratorService._calculate_rag(
        progreso_pct=95, nc_mayores=1, riesgos_criticos=0, retraso_semanas=0,
    )
    assert rag == "red"


@pytest.mark.asyncio
async def test_rag_determinista_red_when_retraso():
    rag = ReportGeneratorService._calculate_rag(
        progreso_pct=95, nc_mayores=0, riesgos_criticos=0, retraso_semanas=3,
    )
    assert rag == "red"


@pytest.mark.asyncio
async def test_mark_reviewed_then_sent(db):
    _, project_id = await _setup_tenant(db)
    svc = ReportGeneratorService()
    report = await svc.generate_report(
        db, uuid.UUID(project_id), tipo="weekly_sponsor",
    )
    reviewed = await svc.mark_reviewed(db, report.id)
    assert reviewed.estado == "reviewed"
    sent = await svc.mark_sent(db, report.id)
    assert sent.estado == "sent"
    assert sent.enviado_at is not None


@pytest.mark.asyncio
async def test_cannot_send_without_review(db):
    _, project_id = await _setup_tenant(db)
    svc = ReportGeneratorService()
    report = await svc.generate_report(
        db, uuid.UUID(project_id), tipo="weekly_sponsor",
    )
    with pytest.raises(ReportError):
        await svc.mark_sent(db, report.id)


@pytest.mark.asyncio
async def test_generate_invalid_tipo_rejected(db):
    _, project_id = await _setup_tenant(db)
    with pytest.raises(ReportError):
        await ReportGeneratorService().generate_report(
            db, uuid.UUID(project_id), tipo="invalid_type",
        )


@pytest.mark.asyncio
async def test_generate_docx_returns_bytes(db):
    _, project_id = await _setup_tenant(db)
    svc = ReportGeneratorService()
    report = await svc.generate_report(
        db, uuid.UUID(project_id), tipo="weekly_sponsor",
    )
    content = await svc.generate_docx(db, report.id)
    assert content[:2] == b"PK"
    assert len(content) > 1500


# ─────────── Escalations ───────────

@pytest.mark.asyncio
async def test_create_escalation_riesgo_materializado(db):
    _, project_id = await _setup_tenant(db)
    event = await EscalationService().create_escalation(
        db, project_id=uuid.UUID(project_id),
        trigger="riesgo_materializado_alto",
    )
    assert event.trigger == "riesgo_materializado_alto"
    assert "sponsor" in event.notificados
    assert "direccion" in event.notificados
    assert event.canal == "email_urgente"
    assert event.resuelto is False


@pytest.mark.asyncio
async def test_create_escalation_invalid_trigger(db):
    _, project_id = await _setup_tenant(db)
    with pytest.raises(EscalationError):
        await EscalationService().create_escalation(
            db, project_id=uuid.UUID(project_id),
            trigger="invalid_trigger",
        )


@pytest.mark.asyncio
async def test_resolve_escalation(db):
    _, project_id = await _setup_tenant(db)
    svc = EscalationService()
    event = await svc.create_escalation(
        db, project_id=uuid.UUID(project_id),
        trigger="paron_por_cliente_5_dias",
    )
    resolved = await svc.resolve_escalation(db, event.id)
    assert resolved.resuelto is True
    assert resolved.resuelto_at is not None


@pytest.mark.asyncio
async def test_active_count(db):
    _, project_id = await _setup_tenant(db)
    svc = EscalationService()
    await svc.create_escalation(
        db, project_id=uuid.UUID(project_id), trigger="nc_mayor_detectada",
    )
    await svc.create_escalation(
        db, project_id=uuid.UUID(project_id), trigger="evidencia_critica_caducada",
    )
    count = await svc.get_active_count(db, uuid.UUID(project_id))
    assert count == 2


@pytest.mark.asyncio
async def test_escalation_publishes_to_feed_m20(db):
    _, project_id = await _setup_tenant(db)
    ws = await WorkspaceService().create_workspace(
        db, project_id=uuid.UUID(project_id), nombre="Test WS",
    )
    event = await EscalationService().create_escalation(
        db, project_id=uuid.UUID(project_id),
        trigger="hallazgo_critico_auditoria",
    )
    assert event.feed_item_id is not None

    feed = await WorkspaceService().list_feed(db, ws.id, tipo="alerta")
    assert len(feed) >= 1
    assert feed[0].tipo == "alerta"


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_list_report_templates(async_client):
    r = await async_client.get(f"{BASE}/report-templates")
    assert r.status_code == 200
    assert len(r.json()["templates"]) == 5


@pytest.mark.asyncio
async def test_api_list_escalation_triggers(async_client):
    r = await async_client.get(f"{BASE}/escalation-triggers")
    assert r.status_code == 200
    assert len(r.json()["triggers"]) == 7  # C#35 lucia + H#54 aepd (Art.33 ENS+RGPD)


@pytest.mark.asyncio
async def test_api_create_plan(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/communication/plan", json={},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "draft"
    assert len(data["escalations"]) == 3


@pytest.mark.asyncio
async def test_api_generate_report(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/communication/reports/generate",
        json={"tipo": "weekly_sponsor"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "weekly_sponsor"


@pytest.mark.asyncio
async def test_api_create_escalation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/communication/escalations",
        json={"trigger": "nc_mayor_detectada"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["resuelto"] is False


# ─────────── M17/M18 task linkage (Sesión 6 GAP 2) ───────────


@pytest.mark.asyncio
async def test_count_tasks_resolves_via_project_plan_join(db):
    """M18 _count_tasks debe contar tareas via JOIN con ProjectPlan, sin
    necesidad de que WbsTask.project_id este poblado.

    Reproduce el bug que requeria backfill manual en la demo.
    """
    from datetime import date
    from backend.app.motors.m17_planning import planning_service

    _, project_id = await _setup_tenant(db)
    project_uuid = uuid.UUID(project_id)

    # Generar plan via M17 — crea WbsTask con project_plan_id pero sin
    # poblar project_id directo en algunas instalaciones.
    plan = await planning_service.generate_plan(
        db, project_uuid,
        categoria="MEDIA", start_date=date.today(),
        client_size="mediana", complexity="media",
        marcos_weekly_hours=20.0, client_weekly_hours=8.0,
    )
    assert plan is not None

    # Marcamos explicitamente project_id a NULL en TODAS las tareas
    # para simular el escenario que rompia el report.
    from sqlalchemy import update
    from backend.app.models.planning import WbsTask
    await db.execute(
        update(WbsTask)
        .where(WbsTask.project_plan_id == plan.id)
        .values(project_id=None)
    )
    await db.flush()

    # Ahora _count_tasks debe contar via JOIN, no via project_id directo.
    svc = ReportGeneratorService()
    total = await svc._count_tasks(db, project_uuid)
    assert total > 0, (
        "M18 _count_tasks devolvio 0 tareas; el JOIN ProjectPlan "
        "no esta funcionando correctamente"
    )

    # Marcar 2 como completed y validar el filtro status_in
    tasks = await planning_service.get_tasks(db, plan.id)
    for t in tasks[:2]:
        t.status = "completed"
    await db.flush()
    completed = await svc._count_tasks(
        db, project_uuid, status_in=("completed", "done"),
    )
    assert completed == 2


@pytest.mark.asyncio
async def test_weekly_sponsor_counts_real_progress_no_backfill(db):
    """Status weekly_sponsor refleja avance real sin necesidad de backfill."""
    from datetime import date
    from backend.app.motors.m17_planning import planning_service

    _, project_id = await _setup_tenant(db)
    project_uuid = uuid.UUID(project_id)

    plan = await planning_service.generate_plan(
        db, project_uuid,
        categoria="BASICA", start_date=date.today(),
        client_size="micro", complexity="baja",
        marcos_weekly_hours=10.0, client_weekly_hours=4.0,
    )
    # NO hacemos backfill de project_id en wbs_tasks. Marcamos 3 tareas.
    tasks = await planning_service.get_tasks(db, plan.id)
    assert len(tasks) >= 3
    for t in tasks[:3]:
        t.status = "completed"
    await db.flush()

    report = await ReportGeneratorService().generate_report(
        db, project_uuid, tipo="weekly_sponsor",
    )
    contenido = report.contenido_jsonb or {}
    assert contenido.get("tareas_completadas_count", 0) == 3, (
        f"Esperaba 3 tareas completadas, conteo={contenido.get('tareas_completadas_count')}"
    )
