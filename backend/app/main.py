"""FULKRO platform — FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.auth.global_dep import authenticate_request
from backend.app.config import get_settings
from backend.app.middleware import BodySizeLimitMiddleware, CSPMiddleware
from backend.app.middleware.marcos_timesheet_middleware import (
    MarcosTimesheetMiddleware,
)
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.public_contact import router as public_contact_router
from backend.app.api.v1.corpus import router as corpus_router
from backend.app.api.v1.projects import router as projects_composer_router
from backend.app.api.v1.audit_search import router as audit_search_router
from backend.app.api.v1.operations import router as operations_router
from backend.app.agents.agent_21_api import router as agent_21_router
from backend.app.agents.agent_11_wrapper import router as agent_11_wrapper_router
from backend.app.api.v1.workflow import router as workflow_router
from backend.app.api.v1.portal_workflow import router as portal_workflow_router
from backend.app.api.v1.workflows_simple import router as workflows_simple_router
from backend.app.api.v1.dashboard import router as admin_dashboard_router
from backend.app.motors.m_observability.api import router as llm_observability_router
from backend.app.motors.m_observability.transparency_api import (
    admin_router as transparency_admin_router,
    client_router as transparency_client_router,
)
from backend.app.motors.m_observability.golden_eval_runs_api import (
    router as golden_eval_runs_router,
)
from backend.app.motors.m_legal.api import router as legal_obligations_router
from backend.app.motors.m11_copiloto.portal_api import router as m11_portal_copiloto_router
from backend.app.motors.m11_copiloto.inline_agents_api import router as m11_inline_agents_router
from backend.app.motors.m23_retainer.timesheet_api import router as m23_timesheet_router
from backend.app.motors.m31_whatsapp.api import (
    admin_router as m31_admin_router,
    portal_router as m31_portal_router,
    webhook_router as m31_webhook_router,
)
from backend.app.motors.m31_whatsapp.sse_endpoint import sse_router as m31_sse_router
from backend.app.motors.m21_portal_cliente.admin_branding_api import (
    router as admin_branding_router,
)
from backend.app.api.v1.mcps import router as mcps_router
from backend.app.api.v1.mcps_execute import router as mcps_execute_router
from backend.app.api.v1.admin_diagnostico_wizard import (
    router as admin_diagnostico_wizard_router,
)
from backend.app.motors.m26_backup.api import router as backup_router
from backend.app.motors.m_compliance_monitor.api import (
    router as compliance_monitor_router,
)
from backend.app.motors.m_compliance_monitor.public_api import (
    router as compliance_public_router,
)
from backend.app.motors.m_compliance.dpa_api import (
    dpa_admin_router,
    dpa_public_router,
)
from backend.app.motors.m_compliance.ropa_api import (
    router as ropa_admin_router,
)
from backend.app.motors.m_compliance.rgpd_api import (
    router as cliente_rgpd_router,
)
from backend.app.motors.m_compliance.compliance_admin_api import (
    router as compliance_admin_router,
)
from backend.app.motors.m_compliance.cookies_api import (
    router as cookies_consent_router,
)
from backend.app.motors.m_compliance_monitor.norma_reports_api import (
    router as norma_reports_router,
)
from backend.app.motors.m02_magerit.api import router as magerit_router
# feat/fulkro-100 Ola D · MAGERIT capa cuantitativa (económica · Libro III 2.3)
from backend.app.motors.m02_magerit.quantitative_api import (
    router as magerit_quantitative_router,
)
from backend.app.motors.m01_categorization.api import router as categorization_router
from backend.app.motors.m01_categorization.archetype_api import router as archetype_router
from backend.app.motors.m01_categorization.dimensions_api import (
    admin_router as dimensions_admin_router,
    reader_router as dimensions_reader_router,
)
from backend.app.motors.m_workflow_engine.api import (
    admin_router as workflow_engine_admin_router,
    reader_router as workflow_engine_reader_router,
)
from backend.app.api.v1.action_plans import router as action_plans_router
from backend.app.api.v1.admin_copilot_stub import router as admin_copilot_stub_router
from backend.app.api.v1.client_copilot_stub import router as client_copilot_stub_router
from backend.app.motors.m19_risk.bia_api import router as bia_router
from backend.app.motors.m19_risk.cliente_continuidad_api import (
    router as cliente_continuidad_router,
)
# feat/fulkro-100 Ola A · continuidad admin buzón + notify draft ready
from backend.app.motors.m19_risk.continuidad_admin_api import (
    router as continuidad_admin_router,
)
# feat/fulkro-100 Ola D · op.cont.3 registro de pruebas de continuidad
from backend.app.motors.m19_risk.continuity_test_execution_api import (
    router as continuity_test_router,
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3A · Evidence request workflow state machine
from backend.app.motors.m07_evidence.request_api import (
    router_admin as evidence_request_admin_router,
    router_cliente as evidence_request_cliente_router,
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3B · Control status compute (false-green prevent)
from backend.app.motors.m04_gap.control_status_api import (
    router_admin as control_status_admin_router,
    router_cliente as control_status_cliente_router,
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3C · Measure translation cliente-friendly
from backend.app.motors.m_compliance.measure_translation_api import (
    router_admin as measure_translation_admin_router,
    router_cliente as measure_translation_cliente_router,
)
from backend.app.motors.m26_backup.backup_policy_321_api import router as backup_321_router
from backend.app.motors.m24_idms.awareness_api import router as awareness_router
from backend.app.motors.m18_communication.aepd_api import router as aepd_router
from backend.app.motors.m15_billing.invoices_aapp_api import router as invoices_aapp_router
from backend.app.motors.m02_magerit.pilar_import_api import router as pilar_import_router
from backend.app.motors.m12_magic_link.api import router as magic_link_router
from backend.app.motors.m03_dda.api import router as dda_router
# feat/fulkro-100 Ola D · medidas compensatorias tipadas (RD 311/2022 Art. 8)
from backend.app.motors.m03_dda.compensatory_api import (
    router as dda_compensatory_router,
)
from backend.app.motors.m19_risk.api import router as risk_router
from backend.app.motors.m04_gap.api import router as gap_router
from backend.app.motors.m06_document_factory.api import router as doc_factory_router
from backend.app.motors.m06_document_factory.portal_api import router as m06_policies_portal_router
from backend.app.core.clients.api import router as clients_router
from backend.app.motors.m11_copiloto.api import router as copilot_router
from backend.app.motors.m05_obligations.api import router as obligations_router
from backend.app.motors.m05_signing.api import (
    admin_router as m05_signing_admin_router,
    client_router as m05_signing_client_router,
)
# feat/fulkro-100 Ola D · sellado de tiempo RFC 3161 (admin)
from backend.app.motors.m05_signing.timestamp_api import (
    router as m05_timestamp_router,
)
from backend.app.motors.m03_dda.portal_api import router as m03_dda_portal_router
from backend.app.motors.m02_magerit.portal_api import router as m02_magerit_portal_router
from backend.app.motors.m08_verification.portal_api import router as m08_pentest_portal_router
from backend.app.motors.m27_conformity.portal_api import router as m27_conformidad_portal_router
from backend.app.motors.m27_conformity.portal_api_dpc import router as m27_dpc_anual_portal_router
from backend.app.motors.m19_risk.incident_portal_api import router as m19_incidents_portal_router
from backend.app.motors.m23_retainer.retainer_checkin_portal_api import router as m23_retainer_checkin_router
from backend.app.motors.m23_retainer.retainer_checkin_admin_api import router as m23_retainer_checkin_admin_router
from backend.app.motors.m_meetings.actas_portal_api import router as m_meetings_actas_portal_router
from backend.app.motors.m07_evidence.antivirus_admin_api import router as m07_antivirus_admin_router
from backend.app.motors.m19_risk.incident_admin_api import router as m19_incident_admin_router
from backend.app.motors.m07_evidence.api import router as evidence_router
from backend.app.motors.m07_evidence.public_router import (
    public_router as evidence_public_router,
)
from backend.app.motors.m16_onboarding.api import router as onboarding_router
from backend.app.motors.m16_onboarding.portal_api import (
    router as m16_portal_router,
)
from backend.app.motors.m21_diagnosis.api import router as m21_diagnosis_router
from backend.app.motors.m21_diagnosis.dashboard_api import (
    router as m21_dashboard_router,
)
from backend.app.core.feature_flags.api import router as feature_flags_router
from backend.app.core.workflow_blocking_api import (
    router as workflow_blocking_router,
)
from backend.app.agents.dry_run_api import (
    router as audit_dry_run_router,
)
from backend.app.motors.m09_audit_prep.simulacro_pre_enac_api import (
    router as simulacro_pre_enac_router,
)
from backend.app.motors.m02_magerit.threat_auto_mapper_api import (
    router as threat_auto_mapper_router,
)
from backend.app.motors.m08_verification.pentest_auto_trigger_api import (
    router as pentest_auto_trigger_router,
)
from backend.app.motors.m21_portal_cliente.audit_api import (
    router as client_audit_router,
)
from backend.app.motors.m21_portal_cliente.task_api import (
    admin_tasks_router,
    client_tasks_router,
)
from backend.app.motors.m21_portal_cliente.chat_api import (
    admin_chat_router,
    client_chat_router,
)
from backend.app.motors.m21_portal_cliente.evidencias_upload_api import (
    router as client_evidencias_router,
)
# SAN-D MB-19.16 cosecha · DEC-MB13-RECENT-ACTIVITY-CARD (ADR-035 deepening)
from backend.app.motors.m21_portal_cliente.recent_activity_api import (
    router as recent_activity_router,
)
# Side-effect: registra SQLAlchemy event listener Project.fase →
# SSE pentest_check_required (MB-15.3 · ADR-037).
from backend.app.motors.m08_verification import pentest_auto_trigger_events  # noqa: F401
from backend.app.api.v1.sse_api import router as sse_events_router
from backend.app.api.v1.sse_client_api import router as sse_client_events_router
from backend.app.motors.m18_communication.alerts_api import (
    router as m18_alerts_router,
)

# Side-effect import: registra SQLAlchemy event listeners → SSE dispatch
# para Asset/DdaEntry/Evidence/Project.fase (MB-13.3 · ADR-035).
from backend.app.core import dashboard_events  # noqa: F401
from backend.app.core.workflow_gates import WorkflowGateError
from backend.app.motors.m22_discovery.api import router as m22_discovery_router
from backend.app.motors.m08_verification.api import router as m08_verification_router
from backend.app.motors.m08_verification.public_api import router as m08_public_router
from backend.app.motors.m25_lifecycle.public_api import router as m25_public_download_router
from backend.app.motors.m13_commercial.contract_signing_public_api import (
    public_router as contract_signing_public_router,
)
from backend.app.motors.m13_commercial.api import router as m13_commercial_router
from backend.app.motors.m27_conformity.public_api import (
    public_router as m27_conformity_public_router,
)
from backend.app.motors.m09_audit_prep.api import router as m09_audit_prep_router
from backend.app.motors.m09_audit_prep.public_api import router as m09_auditor_portal_router
from backend.app.motors.m09_audit_prep.auditor_annotations_api import (
    router_public as m09_auditor_annotations_public_router,
    router_admin as m09_auditor_annotations_admin_router,
)
from backend.app.motors.m09_audit_prep.auditor_clarifications_api import (
    router_public as m09_auditor_clarifications_public_router,
    router_admin as m09_auditor_clarifications_admin_router,
)
from backend.app.motors.m09_audit_prep.dda_evidence_gap_api import (
    router_public as m09_dda_gap_public_router,
    router_admin as m09_dda_gap_admin_router,
)
from backend.app.motors.m09_audit_prep.draft_report_api import (
    router_public as m09_draft_report_public_router,
    router_admin as m09_draft_report_admin_router,
)
from backend.app.motors.m17_planning.api import router as m17_planning_router
from backend.app.motors.m17_planning.portal_api import (
    router as m17_planning_portal_router,
)
from backend.app.motors.m14_contracts.api import router as m14_contracts_router
from backend.app.motors.m15_billing.api import router as m15_billing_router
from backend.app.motors.m10_audit_sim.api import router as m10_audit_sim_router
from backend.app.motors.m20_workspace.api import router as m20_workspace_router
from backend.app.motors.m18_communication.api import router as m18_communication_router
from backend.app.motors.m23_retainer.api import router as m23_retainer_router
from backend.app.motors.m23_retainer.api_paso2 import (
    router as m23_retainer_paso2_router,
)
from backend.app.motors.m21_portal_cliente.notifications_inbox_api import (
    router as client_inbox_router,
)
from backend.app.motors.m21_portal_cliente.mfa_api import (
    mfa_router as client_portal_mfa_router,
)
from backend.app.motors.m21_portal_cliente.api import (
    auth_router as client_portal_auth_router,
    cockpit_router as client_portal_cockpit_router,
    portal_router as client_portal_portal_router,
    support_router as client_portal_support_router,
)
from backend.app.motors.m24_idms.api import router as m24_idms_router
from backend.app.motors.m25_lifecycle.api import router as m25_lifecycle_router
from backend.app.motors.m25_lifecycle.api_paso4 import router as m25_paso4_router
from backend.app.motors.m25_lifecycle.exit_checklist_api import (
    router as m25_exit_checklist_router,
)
from backend.app.motors.m14_contracts.providers_api import (
    router as m14_providers_router,
)
from backend.app.motors.m30_client_contacts.project_scope_api import (
    router as m30_project_scope_router,
)
from backend.app.motors.m30_client_contacts.portal_user_api import (
    router as m30_portal_user_router,
)
from backend.app.motors.m30_client_contacts.department_api import (
    router as m30_departments_router,
    contacts_assign_router as m30_contacts_assign_router,
)
from backend.app.motors.m27_conformity.renewal_extensions_api import (
    router as m27_renewal_ext_router,
)
from backend.app.motors.m28_change_governance.role_topology_extensions_api import (
    router as m28_role_topology_ext_router,
)
from backend.app.motors.m15_billing.financial_extensions_api import (
    router as m15_financial_ext_router,
)
from backend.app.motors.m27_conformity.api import router as m27_conformity_router
from backend.app.motors.m27_conformity.api_paso5 import (
    router as m27_paso5_router,
)
from backend.app.motors.m28_change_governance.api import router as m28_change_router
from backend.app.agents.api import router as agents_router
from backend.app.auth.api import router as auth_router
from backend.app.motors.m30_client_contacts.api import (
    router as m30_client_contacts_router,
)
from backend.app.motors.m30_client_contacts.ens_required_api import (
    router as m30_ens_required_router,
)
from backend.app.motors.m29_client_messaging.api_client import (
    router as m29_client_router,
)
from backend.app.motors.m29_client_messaging.api_admin import (
    router as m29_admin_router,
)
from backend.app.motors.m_meetings.api import (
    router as m_meetings_router,
)
from backend.app.motors.m_cloud_connectors.api import (
    router as cloud_connectors_admin_router,
    catalog_router as cloud_connectors_catalog_router,
    gaps_router as cloud_connectors_gaps_router,
    diagnosis_router as cloud_connectors_diagnosis_router,
    integrations_router as cloud_connectors_integrations_router,
    monitoring_router as cloud_connectors_monitoring_router,
)
from backend.app.motors.m_cloud_connectors.api_cliente import (
    router as cloud_connectors_client_router,
    digest_router as cloud_connectors_client_digest_router,
)
from backend.app.motors.m_cloud_connectors.remediation_api import (
    admin_router as cloud_remediation_admin_router,
    client_router as cloud_remediation_client_router,
)
from backend.app.api.v1.client_compliance_summary import (
    router as client_compliance_summary_router,
)
from backend.app.api.v1.admin_cross_project_compliance import (
    router as admin_cross_project_compliance_router,
)
from backend.app.api.v1.admin_system_health import (
    router as admin_system_health_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FULKRO starting — env={}", settings.app_env)
    # FASE 9.D · hardening LECCIÓN-OPS-004: falla fast si claves Ed25519
    # M06+M07 ausentes o env vars críticas no cargadas (uvicorn sin
    # --env-file .env). Skip automático en tests (FULKRO_TESTING=1).
    from backend.app.startup_checks import run_startup_checks
    run_startup_checks()
    # FIX P4-1: cargar la fuente única editable de precios (pricing_config) en el
    # override en memoria · best-effort (no bloquea el arranque si falla).
    try:
        from backend.app.core.pricing.repository import refresh_pricing_from_db
        from backend.app.database import async_session
        async with async_session() as _s:
            await refresh_pricing_from_db(_s)
    except Exception as _exc:  # pragma: no cover — arranque resiliente
        logger.warning("pricing refresh en arranque falló: {}", _exc)
    yield
    logger.info("FULKRO shutting down")


# Seguridad (auditoría 2026-06-07): en producción se deshabilita la superficie de
# documentación (/docs · /redoc · /openapi.json) para no exponer el mapa de la API.
_prod_docs_off = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if settings.is_production
    else {}
)

app = FastAPI(
    title="FULKRO",
    description="Plataforma de implantacion ENS (RD 311/2022)",
    version="0.1.0",
    lifespan=lifespan,
    # Sub-fase 4.D ADR-021: global dependency cubre 284 endpoints con
    # auth dispatcher dual + CSRF + set_config audit user. Whitelist
    # centralizada en auth.global_dep.WHITELIST_EXACT/PREFIX.
    dependencies=[Depends(authenticate_request)],
    **_prod_docs_off,
)

# Host header validation en producción (anti host-header injection / cache poison).
if settings.is_production:
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list,
    )

# CORS — restrictive in production
if not settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Anti-DoS OOM · límite global de body por Content-Length (auditoría 2026-06-07)
app.add_middleware(BodySizeLimitMiddleware)
# CSP + hardening headers (SAN-B.MB-7.3 · ADR-033)
app.add_middleware(CSPMiddleware)
# SAN-E MB-7.bis closure Q6.C · auto-track Marcos requests into timesheet
app.add_middleware(MarcosTimesheetMiddleware)


# Global handler · los gates de workflow (precondiciones ENS no cumplidas, p.ej.
# generar la DdA sin categorización firmada) deben devolver 409 Conflict con su
# mensaje amistoso · NO 500. Antes solo los endpoints que capturaban
# WorkflowGateError explícitamente lo hacían (la mayoría no) → 500 espurio.
@app.exception_handler(WorkflowGateError)
async def _workflow_gate_handler(_request, exc: WorkflowGateError):  # noqa: ANN001
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "gate": exc.gate},
    )


# Routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(public_contact_router, prefix="/api/v1", tags=["Public — Contacto landing"])
app.include_router(corpus_router, prefix="/api/v1", tags=["Corpus & RAG"])
app.include_router(projects_composer_router, prefix="/api/v1", tags=["Project Composer (FASE 9.B)"])
app.include_router(audit_search_router, prefix="/api/v1", tags=["Audit Search (FASE 9.B)"])
app.include_router(operations_router, prefix="/api/v1", tags=["Operations Overview (FASE 9.B)"])
# FRENTE N · SIEM · consola admin de eventos de seguridad (correlación pentest)
from backend.app.motors.m_siem.api import router as siem_router  # noqa: E402
app.include_router(siem_router, prefix="/api/v1", tags=["SIEM (FRENTE N)"])
app.include_router(agent_21_router, prefix="/api/v1", tags=["Agent 21 - Detector Discrepancias"])
app.include_router(agent_11_wrapper_router, prefix="/api/v1", tags=["Agent 11 - Auditor Virtual (wrapper)"])
app.include_router(workflow_router, prefix="/api/v1", tags=["Workflow guidance (FASE 8)"])
app.include_router(portal_workflow_router, prefix="/api/v1", tags=["Portal cliente - Workflow"])
app.include_router(workflows_simple_router)
app.include_router(admin_dashboard_router, prefix="/api/v1", tags=["Admin Dashboard (Marcos cockpit)"])
app.include_router(llm_observability_router, prefix="/api/v1")
# 1.E.1.B.2 · AI Act art.50 transparency events (admin + cliente portal).
app.include_router(transparency_admin_router, prefix="/api/v1")
app.include_router(transparency_client_router, prefix="/api/v1")
# 1.E.1.B.3.E · Golden eval runs admin (trigger + history + drill-down).
app.include_router(golden_eval_runs_router, prefix="/api/v1")
app.include_router(legal_obligations_router, prefix="/api/v1")
app.include_router(m11_portal_copiloto_router, prefix="/api/v1")
app.include_router(m11_inline_agents_router, prefix="/api/v1")
app.include_router(m23_timesheet_router, prefix="/api/v1")
app.include_router(m31_admin_router, prefix="/api/v1")
app.include_router(m31_portal_router, prefix="/api/v1")
app.include_router(m31_webhook_router, prefix="/api/v1")
app.include_router(m31_sse_router, prefix="/api/v1")
app.include_router(admin_branding_router, prefix="/api/v1")
app.include_router(mcps_router, prefix="/api/v1", tags=["MCPs - Servers Status (9.B)"])
# Sub-atom 1.D.E.A v3.11 · MCP execution endpoints project-scoped (mcps_execute
# ya define prefix="/api/v1" en el router · evita duplicar).
app.include_router(mcps_execute_router)
# Sub-atom 1.D.F.0.A v3.11 · Diagnóstico ENS unificado wizard 6 steps
# (admin-only · prefix `/api/v1/admin/diagnostico-wizard` ya definido en
# el router · NO duplicar).
app.include_router(admin_diagnostico_wizard_router)
app.include_router(backup_router, prefix="/api/v1", tags=["Motor 26 - Backup & DR"])
app.include_router(
    compliance_monitor_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 6 - Self-Monitoring"],
)
app.include_router(
    compliance_public_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 5 - Public Legal/Trust"],
)
app.include_router(
    dpa_public_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 3 - DPA"],
)
app.include_router(
    dpa_admin_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 3 - DPA admin"],
)
app.include_router(
    ropa_admin_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 3 - RoPA admin"],
)
app.include_router(
    cliente_rgpd_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 2 - Cliente RGPD rights"],
)
app.include_router(
    compliance_admin_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 2 - Admin RGPD + Breach"],
)
app.include_router(
    cookies_consent_router,
    prefix="/api/v1",
    tags=["MB-9.bis atom 1 - Cookies consent"],
)
app.include_router(
    norma_reports_router,
    prefix="/api/v1",
    tags=["MB-9.bis mini-atom 3 - Norma reports"],
)
app.include_router(magerit_router, prefix="/api/v1", tags=["Motor 2 - MAGERIT v3"])
# feat/fulkro-100 Ola D · MAGERIT cuantitativo (require_owner · ALE económico)
app.include_router(
    magerit_quantitative_router, prefix="/api/v1",
    tags=["Motor 2 - MAGERIT · Cuantitativo (Libro III 2.3)"],
)
app.include_router(categorization_router, prefix="/api/v1", tags=["Motor 1 - Categorization"])
app.include_router(archetype_router, prefix="/api/v1", tags=["M01 - Pyme Archetypes (MB-11.6)"])
# Sub-atom 1.C.D.A.0 v3.8 · 19 dimensiones adaptación · canonical source of truth
app.include_router(dimensions_reader_router, prefix="/api/v1", tags=["M01 - Dimensions (read · admin + cliente)"])
app.include_router(dimensions_admin_router, prefix="/api/v1", tags=["M01 - Dimensions (admin · Marcos only)"])
# Sub-atom 1.C.D.A v3.8 · m_workflow_engine view composer · enriched workflow
app.include_router(workflow_engine_admin_router, prefix="/api/v1", tags=["m_workflow_engine · Admin Command Center"])
app.include_router(workflow_engine_reader_router, prefix="/api/v1", tags=["m_workflow_engine · reader (admin + cliente)"])
# Sub-atom 1.D.C.A v3.11 · Action Plans Dashboard K.3 cross-motor (M04 + M09 + A21)
app.include_router(action_plans_router, prefix="/api/v1", tags=["Action Plans · Dashboard K.3"])
# Sub-atom 1.C.D.B.3 v3.8 · Admin Copiloto stub endpoint (LLM swap-in 1.D.B.2)
app.include_router(admin_copilot_stub_router, prefix="/api/v1", tags=["Admin Copiloto · stub"])
# Sub-atom 1.C.D.C.3 v3.8 · Client Copiloto stub endpoint (LLM swap-in 1.D.B.1)
app.include_router(client_copilot_stub_router, prefix="/api/v1", tags=["Client Copiloto · stub"])
app.include_router(bia_router, prefix="/api/v1", tags=["M19 - BIA (MB-11.5)"])
# Sesión 3B-2B.8 CLUSTER 2 Phase 2F · cliente continuidad questionnaire+approve
app.include_router(
    cliente_continuidad_router, prefix="/api/v1",
    tags=["Portal Cliente - Continuidad"],
)
# feat/fulkro-100 Ola A · continuidad admin buzón (require_owner) cierra el loop sync
app.include_router(
    continuidad_admin_router, prefix="/api/v1",
    tags=["M19 - Continuidad (admin buzón)"],
)
# feat/fulkro-100 Ola D · op.cont.3 registro de pruebas periódicas de continuidad
app.include_router(
    continuity_test_router, prefix="/api/v1",
    tags=["M19 - Continuidad (op.cont.3 pruebas)"],
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3A · Evidence request workflow state machine
app.include_router(
    evidence_request_admin_router, prefix="/api/v1",
    tags=["Admin - Evidence Requests (M07 · CLUSTER 3 Phase 3A)"],
)
app.include_router(
    evidence_request_cliente_router, prefix="/api/v1",
    tags=["Portal Cliente - Evidence Requests (CLUSTER 3 Phase 3A)"],
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3B · Control status compute endpoints
app.include_router(
    control_status_admin_router, prefix="/api/v1",
    tags=["Admin - Control Status (M04 · CLUSTER 3 Phase 3B)"],
)
app.include_router(
    control_status_cliente_router, prefix="/api/v1",
    tags=["Portal Cliente - Control Status (CLUSTER 3 Phase 3B)"],
)
# Sesión 3B-2B.8 CLUSTER 3 Phase 3C · Measure translation endpoints
app.include_router(
    measure_translation_admin_router, prefix="/api/v1",
    tags=["Admin - Measure Translation (m_compliance · CLUSTER 3 Phase 3C)"],
)
app.include_router(
    measure_translation_cliente_router, prefix="/api/v1",
    tags=["Portal Cliente - Measure Translation (CLUSTER 3 Phase 3C)"],
)
app.include_router(backup_321_router, prefix="/api/v1", tags=["M26 - 3-2-1 Policy (MB-11.5)"])
app.include_router(awareness_router, prefix="/api/v1", tags=["M24 - Awareness training (MB-11.5)"])
app.include_router(aepd_router, prefix="/api/v1", tags=["M18 - AEPD (MB-11.2)"])
app.include_router(invoices_aapp_router, prefix="/api/v1", tags=["M15 - AAPP Billing (MB-11.3)"])
app.include_router(pilar_import_router, prefix="/api/v1", tags=["M02 - PILAR XML import (MB-11.4)"])
app.include_router(magic_link_router, prefix="/api/v1", tags=["Motor 12 - Magic Links"])
app.include_router(dda_router, prefix="/api/v1", tags=["Motor 3 - DdA Engine"])
# feat/fulkro-100 Ola D · compensatorias tipadas (require_owner · Art. 8)
app.include_router(
    dda_compensatory_router, prefix="/api/v1",
    tags=["Motor 3 - DdA · Compensatorias (Art. 8)"],
)
app.include_router(risk_router, prefix="/api/v1", tags=["Motor 19 - Project Risks"])
app.include_router(gap_router, prefix="/api/v1", tags=["Motor 4 - Gap Analysis"])
app.include_router(doc_factory_router, prefix="/api/v1", tags=["Motor 6 - Document Factory"])
app.include_router(clients_router, prefix="/api/v1", tags=["Core - Clients & Projects"])
app.include_router(copilot_router, prefix="/api/v1", tags=["Motor 11 - Copiloto ENS"])
app.include_router(obligations_router, prefix="/api/v1", tags=["Motor 5 - Obligations"])
app.include_router(evidence_router, prefix="/api/v1", tags=["Motor 7 - Evidence"])
app.include_router(
    evidence_public_router,
    prefix="/api/v1",
    tags=["Motor 7 - Evidence (public)"],
)
app.include_router(onboarding_router, prefix="/api/v1", tags=["Motor 16 - Onboarding"])
app.include_router(m16_portal_router)
app.include_router(m21_diagnosis_router, prefix="/api/v1", tags=["Motor 21 - Diagnosis"])
app.include_router(
    m21_dashboard_router,
    prefix="/api/v1",
    tags=["MB-13.1 - Dashboard agregado admin"],
)
app.include_router(
    feature_flags_router,
    prefix="/api/v1",
    tags=["MB-17 - Feature Flags catalog"],
)
app.include_router(
    workflow_blocking_router,
    prefix="/api/v1",
    tags=["MB-17 - Workflow blocking rules"],
)
app.include_router(
    audit_dry_run_router,
    prefix="/api/v1",
    tags=["MB-15 - Audit Dry-Run (A11+M10)"],
)
app.include_router(
    simulacro_pre_enac_router,
    prefix="/api/v1",
    tags=["Simulacro Pre-ENAC (Sesión 3B-2B.10)"],
)
app.include_router(
    threat_auto_mapper_router,
    prefix="/api/v1",
    tags=["MB-15 - Magerit Threat Auto-Mapper"],
)
app.include_router(
    pentest_auto_trigger_router,
    prefix="/api/v1",
    tags=["MB-15 - Pentest Auto-Trigger (CPSTIC)"],
)
app.include_router(
    client_audit_router,
    prefix="/api/v1",
    tags=["MB-14 - Client Audit Log (hash chain)"],
)
app.include_router(
    client_tasks_router,
    prefix="/api/v1",
    tags=["MB-14 - Client Tasks (workspace continuo)"],
)
app.include_router(
    admin_tasks_router,
    prefix="/api/v1/admin",
    tags=["MB-14 - Admin Tasks Regenerate"],
)
app.include_router(
    client_chat_router,
    prefix="/api/v1",
    tags=["MB-14 - Client Chat"],
)
app.include_router(
    admin_chat_router,
    prefix="/api/v1/admin",
    tags=["MB-14 - Admin Chat"],
)
app.include_router(
    client_evidencias_router,
    prefix="/api/v1",
    tags=["MB-14 - Client Evidencias Upload"],
)
app.include_router(
    recent_activity_router,
    prefix="/api/v1",
    tags=["MB-19.16 - Recent Activity (admin home cosecha)"],
)
app.include_router(
    sse_events_router,
    prefix="/api/v1",
    tags=["MB-13.3 - SSE events"],
)
app.include_router(
    sse_client_events_router,
    prefix="/api/v1",
    tags=["1.D.G.C - SSE cliente filtered per audience"],
)
app.include_router(
    m18_alerts_router,
    prefix="/api/v1",
    tags=["MB-13.4 - Alertas proactivas"],
)
app.include_router(m22_discovery_router, prefix="/api/v1", tags=["Motor 22 - Technical Discovery"])
app.include_router(m08_verification_router, prefix="/api/v1", tags=["Motor 8 - Verificacion Tecnica"])
app.include_router(m08_public_router, prefix="/api/v1", tags=["Public Portals (Motor 8 v5.1)"])
# M8 Autopilot v2.0 · pentesting hiper-automatizado (docs/spec/M8_AUTOPILOT_ARCHITECTURE_v2.md)
from backend.app.motors.m08_verification.autopilot_api import router as m08_autopilot_router  # noqa: E402
app.include_router(m08_autopilot_router, prefix="/api/v1", tags=["Motor 8 - Autopilot Pentesting v2.0"])
app.include_router(m25_public_download_router, prefix="/api/v1", tags=["Public Download Portal (M25)"])
app.include_router(
    m27_conformity_public_router,
    prefix="/api/v1",
    tags=["Public Conformity Badge (M27 · CCN-STIC 809)"],
)
app.include_router(m09_audit_prep_router, prefix="/api/v1", tags=["Motor 9 - Audit Preparation"])
app.include_router(
    m09_auditor_portal_router,
    prefix="/api/v1",
    tags=["Public Portal · Auditor ENAC (M9 CLUSTER 2)"],
)
app.include_router(
    m09_auditor_annotations_public_router,
    prefix="/api/v1",
)
app.include_router(
    m09_auditor_annotations_admin_router,
    prefix="/api/v1",
)
app.include_router(
    m09_auditor_clarifications_public_router,
    prefix="/api/v1",
)
app.include_router(
    m09_auditor_clarifications_admin_router,
    prefix="/api/v1",
)
app.include_router(
    m09_dda_gap_public_router,
    prefix="/api/v1",
)
app.include_router(
    m09_dda_gap_admin_router,
    prefix="/api/v1",
)
app.include_router(
    m09_draft_report_public_router,
    prefix="/api/v1",
)
app.include_router(
    m09_draft_report_admin_router,
    prefix="/api/v1",
)
app.include_router(m17_planning_router, prefix="/api/v1", tags=["Motor 17 - Planning"])
app.include_router(
    m17_planning_portal_router, prefix="/api/v1",
    tags=["Motor 17 - Plan Cliente READ-ONLY"],
)
app.include_router(m14_contracts_router, prefix="/api/v1", tags=["Motor 14 - Contracts"])
# #43 · firma del contrato comercial con canvas Ed25519 (público · magic-link
# FIRMA_CONTRATO). Flujo autoritativo: extiende m13 ContractSigningFlow.
app.include_router(contract_signing_public_router, prefix="/api/v1")
# BUG3 fix · CRM router (propuestas + pricing-models + pipeline leads). Marcos-only
# (require_owner). Sin deps externas. prefix interno /commercial → /api/v1/commercial/*.
app.include_router(m13_commercial_router, prefix="/api/v1", tags=["Motor 13 - Commercial"])
app.include_router(m15_billing_router, prefix="/api/v1", tags=["Motor 15 - Billing"])
app.include_router(m10_audit_sim_router, prefix="/api/v1", tags=["Motor 10 - Audit Simulation"])
app.include_router(m20_workspace_router, prefix="/api/v1", tags=["Motor 20 - Workspace"])
app.include_router(m18_communication_router, prefix="/api/v1", tags=["Motor 18 - Communication"])
app.include_router(m23_retainer_router, prefix="/api/v1", tags=["Motor 23 - Retainer"])
app.include_router(m23_retainer_paso2_router, prefix="/api/v1", tags=["Motor 23 - Retainer Paso 2"])
app.include_router(client_portal_auth_router, prefix="/api/v1", tags=["Portal Cliente Auth"])
app.include_router(client_portal_portal_router, prefix="/api/v1", tags=["Portal Cliente"])
app.include_router(client_portal_cockpit_router, prefix="/api/v1", tags=["Cockpit - Usuarios cliente"])
app.include_router(client_portal_support_router, prefix="/api/v1", tags=["Cockpit - Acceso de soporte"])
app.include_router(client_inbox_router)
app.include_router(client_portal_mfa_router, prefix="/api/v1", tags=["Portal Cliente MFA"])
app.include_router(m24_idms_router, prefix="/api/v1", tags=["Motor 24 - IDMS"])
app.include_router(m25_lifecycle_router, prefix="/api/v1", tags=["Motor 25 - Lifecycle"])
app.include_router(m25_paso4_router, prefix="/api/v1", tags=["Motor 25 - Lifecycle Paso 4"])
app.include_router(m25_exit_checklist_router, prefix="/api/v1", tags=["Motor 25 - Exit Checklist"])
app.include_router(m14_providers_router, prefix="/api/v1", tags=["Motor 14 - Providers / C-002"])
app.include_router(m30_project_scope_router, prefix="/api/v1", tags=["Motor 30 - Project-scoped Contacts"])
app.include_router(m30_portal_user_router, prefix="/api/v1", tags=["Motor 30 - Project Portal User (1.C.F)"])
app.include_router(m30_departments_router, prefix="/api/v1", tags=["Motor 30 - Departments (1.C.F.2)"])
app.include_router(m30_contacts_assign_router, prefix="/api/v1", tags=["Motor 30 - Departments (1.C.F.3)"])
app.include_router(m27_renewal_ext_router, prefix="/api/v1", tags=["Motor 27 - Renewal Extensions"])
app.include_router(m28_role_topology_ext_router, prefix="/api/v1", tags=["Motor 28 - Role Topology + Drift"])
app.include_router(m15_financial_ext_router, prefix="/api/v1", tags=["Motor 15 - Financial Extensions"])
app.include_router(m27_conformity_router, tags=["Motor 27 - Conformity Lifecycle"])
app.include_router(m27_paso5_router, prefix="/api/v1", tags=["Motor 27 - Conformity Paso 5"])
app.include_router(m28_change_router, tags=["Motor 28 - Change Governance"])
app.include_router(agents_router, tags=["13 Agentes IA"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(
    m30_client_contacts_router, prefix="/api/v1",
    tags=["Motor 30 - Client Contacts"],
)
app.include_router(
    m30_ens_required_router, prefix="/api/v1",
    tags=["Motor 30 - ENS_REQUIRED stakeholders"],
)
app.include_router(
    m05_signing_client_router, prefix="/api/v1",
    tags=["Motor 05 - In-portal signing (cliente)"],
)
app.include_router(
    m05_signing_admin_router, prefix="/api/v1",
    tags=["Motor 05 - In-portal signing (admin)"],
)
# feat/fulkro-100 Ola D · sellado de tiempo RFC 3161 (require_owner)
app.include_router(
    m05_timestamp_router, prefix="/api/v1",
    tags=["Motor 5 - Firma · Sellado RFC 3161"],
)
app.include_router(
    m03_dda_portal_router, prefix="/api/v1",
    tags=["Motor 03 - DdA cliente in-portal"],
)
app.include_router(
    m02_magerit_portal_router, prefix="/api/v1",
    tags=["Motor 02 - MAGERIT cliente in-portal"],
)
app.include_router(
    m08_pentest_portal_router, prefix="/api/v1",
    tags=["Motor 08 - Pentest cliente in-portal"],
)
app.include_router(
    m27_conformidad_portal_router, prefix="/api/v1",
    tags=["Motor 27 - Conformidad cliente in-portal"],
)
app.include_router(
    m06_policies_portal_router, prefix="/api/v1",
    tags=["Motor 06 - Policies cliente in-portal"],
)
app.include_router(
    m27_dpc_anual_portal_router, prefix="/api/v1",
    tags=["Motor 27 - DPC anual cliente in-portal"],
)
app.include_router(
    m19_incidents_portal_router, prefix="/api/v1",
    tags=["Motor 19 - Incidents cliente in-portal"],
)
app.include_router(
    m23_retainer_checkin_router, prefix="/api/v1",
    tags=["Motor 23 - Retainer checkin cliente in-portal"],
)
app.include_router(
    m23_retainer_checkin_admin_router, prefix="/api/v1",
    tags=["Motor 23 - Retainer checkin admin curación"],
)
app.include_router(
    m_meetings_actas_portal_router, prefix="/api/v1",
    tags=["Motor meetings - Actas cliente in-portal"],
)
app.include_router(
    m07_antivirus_admin_router, prefix="/api/v1",
    tags=["Motor 07 - Evidence antivirus admin"],
)
app.include_router(
    m19_incident_admin_router, prefix="/api/v1",
    tags=["Motor 19 - Incidents admin (workflow + classify)"],
)
app.include_router(
    m29_client_router, prefix="/api/v1",
    tags=["Motor 29 - Mensajería Cliente"],
)
app.include_router(
    m29_admin_router, prefix="/api/v1",
    tags=["Motor 29 - Mensajería Admin"],
)
app.include_router(
    m_meetings_router, prefix="/api/v1",
    tags=["Meetings (FASE 7) - Reuniones externas"],
)

# /api/v1/admin/settings/* — panel admin configuración (FASE 4 4.A.2.c).
from backend.app.admin_settings.api import router as admin_settings_router
app.include_router(admin_settings_router, prefix="/api/v1", tags=["admin-settings"])

# SAN-D MB-16.5 · NotificationOrchestrator API endpoints (ADR-039).
from backend.app.notifications.api import (
    admin_router as notifications_admin_router,
    portal_router as notifications_portal_router,
)
app.include_router(notifications_portal_router, prefix="/api/v1")
app.include_router(notifications_admin_router, prefix="/api/v1")

# Sesión 3B-2B.11 Phase 11.3 · DLQ minimal admin endpoints.
from backend.app.notifications.dlq_api import router as notifications_dlq_router
app.include_router(notifications_dlq_router, prefix="/api/v1")

# Sesión 3B-4 Ejecutable 7.5 · audit accompaniment cycle post-implantación.
from backend.app.motors.m_audit_accompaniment.api import (
    router as audit_accompaniment_router,
)
app.include_router(audit_accompaniment_router, prefix="/api/v1")

# SAN-D MB-18.3 · Auto-billing + reconciliation manual API (ADR-040).
from backend.app.billing.api import (
    admin_finance_router,
    admin_contracts_router as billing_admin_contracts_router,
    client_billing_router,
)
app.include_router(admin_finance_router, prefix="/api/v1")
app.include_router(billing_admin_contracts_router, prefix="/api/v1")
app.include_router(client_billing_router, prefix="/api/v1")

# SAN-D MB-18.4 · RetainerStateMachine + ChurnPredictor API (ADR-040).
from backend.app.retainer.api import (
    admin_retainer_router as billing_admin_retainer_router,
)
app.include_router(billing_admin_retainer_router, prefix="/api/v1")

# 1.C.B sub-lote · Registros vivos E-300..E-325 (audit v4 sub-fase 1.5).
from backend.app.motors.m_live_records.api import router as live_records_router
from backend.app.motors.m_live_records.listeners import (
    register_listeners as register_live_records_listeners,
)
app.include_router(live_records_router, tags=["live_records"])
# 1.C.B fase 3c · auto-population non-invasive M19/M28/M14 → E-305/E-308/E-312.
register_live_records_listeners()

# 1.D.X.B · Cloud Connectors unified layer (admin + cliente + gaps + catalog).
app.include_router(
    cloud_connectors_admin_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.B) - Admin"],
)
app.include_router(
    cloud_connectors_catalog_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.B) - Catalog"],
)
app.include_router(
    cloud_connectors_gaps_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.B) - Gaps"],
)
app.include_router(
    cloud_connectors_client_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.B) - Cliente"],
)
app.include_router(
    cloud_connectors_diagnosis_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.H) - Diagnosis"],
)
app.include_router(
    cloud_connectors_integrations_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.K) - Integrations"],
)
app.include_router(
    cloud_connectors_monitoring_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.VERIFY 2a) - Monitoring"],
)
app.include_router(
    cloud_connectors_client_digest_router, prefix="/api/v1",
    tags=["Cloud Connectors (1.D.X.VERIFY 2b) - Cliente Digest"],
)
# Bloque 3+5 · Cloud Remediation Orchestrator (admin + cliente endpoints)
app.include_router(
    cloud_remediation_admin_router, prefix="/api/v1",
    tags=["Cloud Remediation (Bloque 3+5) - Admin"],
)
app.include_router(
    cloud_remediation_client_router, prefix="/api/v1",
    tags=["Cloud Remediation (Bloque 3+5) - Cliente"],
)
# Bloque 4 · Cliente Compliance Summary aggregator
app.include_router(
    client_compliance_summary_router, prefix="/api/v1",
    tags=["Client Portal · Compliance Summary (Bloque 4)"],
)
# Bloque 4 · Admin Cross-Project Compliance aggregator
app.include_router(
    admin_cross_project_compliance_router, prefix="/api/v1",
    tags=["Admin · Cross-Project Compliance (Bloque 4)"],
)
# Bloque 4 · Admin System Health propio aggregator
app.include_router(
    admin_system_health_router, prefix="/api/v1",
    tags=["Admin · System Health (Bloque 4)"],
)

# /api/v1/_dev/* — endpoints auxiliares dev/test (SUB-FASE 3.F).
# Doble defensa: gate aquí + gate por endpoint en el router.
if not get_settings().is_production:
    from backend.app.dev.router import router as dev_router
    app.include_router(dev_router, prefix="/api/v1", tags=["_dev (non-prod)"])
