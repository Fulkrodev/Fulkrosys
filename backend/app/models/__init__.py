"""FULKRO models - import all to register with SQLAlchemy metadata."""
from backend.app.models.base import Base  # noqa: F401
from backend.app.models.core import *  # noqa: F401, F403
from backend.app.models.ens import *  # noqa: F401, F403
from backend.app.models.documents import *  # noqa: F401, F403
from backend.app.models.document_factory import *  # noqa: F401, F403
from backend.app.models.findings import *  # noqa: F401, F403
from backend.app.models.governance import *  # noqa: F401, F403
from backend.app.models.operations import *  # noqa: F401, F403
# pentesting models DEMOLIDOS Sesion 7 (M8 v4.2 → v5.1).
# Las 5 tablas v5.1 viven en el motor (m08_verification/models.py)
# y se importan aqui para registrarlas en la metadata global.
from backend.app.motors.m08_verification.models import *  # noqa: F401, F403
from backend.app.models.knowledge import *  # noqa: F401, F403
from backend.app.models.ens_extensions import *  # noqa: F401, F403
from backend.app.models.audit_log import *  # noqa: F401, F403
from backend.app.models.commercial import *  # noqa: F401, F403
from backend.app.models.onboarding import *  # noqa: F401, F403
# #7 · registra los event listeners que pueblan cif_norm on-write (Lead+Client).
from backend.app.models import cif_norm_events  # noqa: F401
# Batch A diagnóstico previo · registro dedicado consentimiento del lead.
from backend.app.models.precliente_consent import *  # noqa: F401, F403
from backend.app.models.planning import *  # noqa: F401, F403
from backend.app.models.collaboration import *  # noqa: F401, F403
from backend.app.models.retainer import *  # noqa: F401, F403
from backend.app.models.backup import *  # noqa: F401, F403
from backend.app.models.lifecycle import *  # noqa: F401, F403
# SAN-E MB-3.A · M25 exit checklist (capa validacion pre-cierre lifecycle).
from backend.app.models.m25_exit_checklist import *  # noqa: F401, F403
# SAN-E MB-3.B · M14 providers + C-002 cross-compliance.
from backend.app.models.m14_providers import *  # noqa: F401, F403
# SAN-E MB-3.D · M27 renewal_campaign_milestones (sub-tabla campaigns).
from backend.app.models.m27_renewal_milestone import *  # noqa: F401, F403
# SAN-E MB-3.E · M28 project_role_assignments granular per project.
from backend.app.models.m28_role_assignment import *  # noqa: F401, F403
from backend.app.motors.m02_magerit.models import *  # noqa: F401, F403
from backend.app.models.pkg import *  # noqa: F401, F403
from backend.app.models.diagnosis import *  # noqa: F401, F403
from backend.app.models.discovery import *  # noqa: F401, F403
from backend.app.models.audit_prep import *  # noqa: F401, F403
from backend.app.models.audit_sim import *  # noqa: F401, F403
from backend.app.models.communication import *  # noqa: F401, F403
from backend.app.models.lms import *  # noqa: F401, F403
from backend.app.models.idms import *  # noqa: F401, F403
from backend.app.models.copilot import *  # noqa: F401, F403
from backend.app.models.auth import *  # noqa: F401, F403
from backend.app.models.client_portal import *  # noqa: F401, F403
from backend.app.models.client_notification import ClientNotification  # noqa: F401
from backend.app.models.conformity_lifecycle import *  # noqa: F401, F403
from backend.app.models.operations_paso7 import *  # noqa: F401, F403
from backend.app.models.commercial_paso7 import *  # noqa: F401, F403
from backend.app.motors.m30_client_contacts.models import *  # noqa: F401, F403
# Ejecutable 8 Pasada 16 (DB-DRIFT-01): registrar en Base.metadata módulos de modelos de
# motor que faltaban — resuelve FK client_contacts.department_id -> departments en alembic
# check, y hace visibles m_audit_accompaniment (3 tablas creadas por DDL en Ejecutable 7.5
# sin migración) + m_cloud_connectors para autogenerate/check.
from backend.app.motors.m30_client_contacts.department_models import *  # noqa: F401, F403
from backend.app.motors.m_cloud_connectors.models import *  # noqa: F401, F403
from backend.app.motors.m_audit_accompaniment.models import *  # noqa: F401, F403
from backend.app.motors.m29_client_messaging.models import *  # noqa: F401, F403
# SAN-E v3.MB-7.0 drift cleanup · 6 motor models antes no importados
# (signing_intents/events/otp · magic_link_migration_log · chat_threads/messages ·
# client_tasks · a21_scan_runs/discrepancies · alert_queue · audit_dry_run_results).
# Antes: alembic check los detectaba como "removed table" porque NO estaban en
# Base.metadata. Ahora declarative source aligned con BD reality.
from backend.app.motors.m05_signing.models import *  # noqa: F401, F403
from backend.app.motors.m12_magic_link.models_migration_log import *  # noqa: F401, F403
from backend.app.motors.m21_portal_cliente.models_chat import *  # noqa: F401, F403
from backend.app.motors.m21_portal_cliente.models_tasks import *  # noqa: F401, F403
from backend.app.models.alerts import *  # noqa: F401, F403
from backend.app.models.a21_discrepancies import *  # noqa: F401, F403
# SAN-E v3.MB-7.bis · marcos_timesheet_entries (atom 7.bis.5 Q6.C)
from backend.app.motors.m23_retainer.timesheet_models import *  # noqa: F401, F403
# SAN-E v3.MB-8 atom 8.1 · M31 WhatsApp Business motor models
from backend.app.motors.m31_whatsapp.models import *  # noqa: F401, F403
# SAN-D MB-15.1 · AuditDryRunResult model · normalmente importado vía agents/api
# en main.py runtime. Para alembic check (env.py NO importa main) registramos
# aquí también · circular import seguro por orden de imports (Base ya cargado).
from backend.app.agents.models.dry_run import *  # noqa: F401, F403
from backend.app.models.change_governance import *  # noqa: F401, F403
from backend.app.models.admin import *  # noqa: F401, F403
# SAN-C MB-11.5 · BIA + awareness training tracking.
from backend.app.models.bia import *  # noqa: F401, F403
from backend.app.models.awareness import *  # noqa: F401, F403
# Sesión 3B-2B.8 CLUSTER 2 Phase 2F · cliente continuidad questionnaire+approve
from backend.app.models.cliente_continuidad import *  # noqa: F401, F403
# feat/fulkro-100 Ola D · op.cont.3 registro de pruebas periódicas de continuidad
from backend.app.models.continuity_test_execution import *  # noqa: F401, F403
# feat/fulkro-100 Ola D · medidas compensatorias tipadas (RD 311/2022 Art. 8)
from backend.app.models.compensatory_control import *  # noqa: F401, F403
# Sesión 3B-2B.8 CLUSTER 3 Phase 3A · Evidence request workflow state machine
from backend.app.models.evidence_request import *  # noqa: F401, F403
# SAN-C MB-11.2 · AEPD notifications RGPD art.33-34.
from backend.app.models.aepd import *  # noqa: F401, F403
# SAN-C MB-11.3 · Facturas AAPP Facturae 3.2.x + Ley 3/2004 morosidad.
from backend.app.models.invoices_aapp import *  # noqa: F401, F403
# SAN-D MB-16.1 · NotificationOrchestrator events + preferences (ADR-039).
from backend.app.models.notifications import *  # noqa: F401, F403
# SAN-D MB-18.1 · ContractMilestone + RetainerHealthSignal (ADR-040).
from backend.app.models.billing_milestones import *  # noqa: F401, F403
# SAN-E v3.MB-9.bis atom 9.bis.6 · FULKRO Self-Monitoring (3 platform tables).
from backend.app.models.compliance_monitor import *  # noqa: F401, F403
# SAN-E v3.MB-9.bis atom 9.bis.5 · Sub-processor subscribers (Trust Center).
# Star import (module side-effect registration) avoids circular import when
# the submodule's own `from backend.app.models.base import ...` re-enters
# this __init__ during a fresh load (e.g. pytest collecting a test that
# imports SubProcessorSubscriber directly from the motor module).
from backend.app.motors.m_compliance_monitor import sub_processor_subscribers as _sps  # noqa: F401, E501
# SAN-E v3.MB-9.bis atom 9.bis.3 · RoPA Art. 30 GDPR (fulkro_ropa_treatments).
from backend.app.models.ropa_treatments import *  # noqa: F401, F403
# SAN-E v3.MB-9.bis atom 9.bis.2 · Breach (Art. 33) + Erasure (Art. 17) tables.
from backend.app.models.compliance_breach_erasure import *  # noqa: F401, F403
# SAN-E v3.MB-9.bis atom 9.bis.1 · Cookie consent audit log (Art. 7 GDPR).
from backend.app.models.consent_audit import *  # noqa: F401, F403
# SAN-E v3.MB-9.bis mini-atom 3 · per-norma compliance reports.
from backend.app.models.compliance_norma_reports import *  # noqa: F401, F403
# SAN-E v3.MB-10 Atom 10.2 · feature_flag_overrides (ADR-046 materializa
# ADR-036 deferred · M32 LOGICAL · NO motor m32_capabilities/ separate).
# ADR-046 renamed post-audit B1.2 · was ADR-037 MB-10 (collision fix).
# Star import (m08 pattern) evita circular import: módulo parcial OK con
# star (lista names empty), named import raise ImportError.
from backend.app.core.feature_flags.models import *  # noqa: F401, F403
# SAN-D MB-15.1 · AuditDryRunResult model lives in agents/models/dry_run
# Importado transitivamente vía agents/api/dry_run_api en main.py · evita
# circular import models/base ← models/__init__ ← agents.models.dry_run.
# 1.C.B sub-lote · LiveRecord registros vivos E-300..E-325 (motor m_live_records).
from backend.app.models.live_record import LiveRecord  # noqa: F401
# 1.E.1.B.2 · AI Act art.50 transparency events (motor m_observability).
# Star import (m08 pattern) evita circular import: módulo parcial OK con
# star (lista names empty), named import raise ImportError.
from backend.app.motors.m_observability.models import *  # noqa: F401, F403
# CLUSTER 3 Phase C1.1 · auditor portal annotations cross-motor inspection.
from backend.app.models.auditor_annotations import AuditorAnnotation  # noqa: F401
# CLUSTER 3 Phase C2.1 · auditor portal clarification requests + admin SSE.
from backend.app.models.auditor_clarifications import (  # noqa: F401
    AuditorClarificationRequest,
)
