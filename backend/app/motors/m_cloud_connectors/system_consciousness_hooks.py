"""System Consciousness Hooks · Bloque 3+5 Enhancement Phase B (Path B refined).

Cross-module propagation when CloudGap reaches terminal VERIFIED state.
Fired graceful por CloudRemediationOrchestrator.mark_verified() · NUNCA bloquea
state transition primaria (try/except outer en orchestrator).

Pattern reuse: `maybe_dispatch_X` canonical de
``backend/app/motors/m14_contracts/workflow_hooks.py`` (FASE C Phase A).

Subscribers cross-system propagation (Path B refined · architecturally coherent):
  1. CloudGap status semantic update (resolved_at + verified_at sostained)
  2. m_compliance_monitor recheck trigger (best-effort)
  3. M9 Dossier evidence file auto-add (best-effort)
  4. M14 AdendaGenerator trigger si material change detected (best-effort)
  5. M22 Events bus emit cross-motor subscribers (best-effort)
  6. Dashboards SSE refresh (best-effort)
  7. NotificationOrchestrator cross-stakeholders (best-effort)

R1 + R23 + R29 + R30 + R31 sostained.
ADR-014 read-only · NO destructive cloud writes (cross-module updates só
metadata + tracking · cloud state unchanged).
ADR-025 sostained · NO new tables · reuse infrastructure existing.
ADR-031 ENAC trazabilidad · audit trail enriquecido per propagation step.

Best-effort dispatch · si CUALQUIER sub-system falla → log exception · OTROS
sub-systems continúan · primary VERIFIED transition NUNCA reverted.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudGap,
    CloudRemediationActorType,
    CloudRemediationApprovalLog,
)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Main entry point Phase B


async def maybe_dispatch_remediation_verified(
    db: AsyncSession,
    *,
    gap: CloudGap,
    admin_user_id: uuid.UUID | None,
    correlation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Dispatch cross-module propagation post VERIFIED · best-effort.

    Returns dict con per-subsystem result · útil para audit trail enrichment.
    """
    correlation_id = correlation_id or uuid.uuid4()
    propagation_result: dict[str, Any] = {
        "correlation_id": str(correlation_id),
        "gap_id": str(gap.id),
        "project_id": str(gap.project_id),
        "verified_at": gap.verified_at.isoformat() if gap.verified_at else None,
        "subsystems": {},
    }

    # 1. m_compliance_monitor recheck (best-effort)
    propagation_result["subsystems"]["compliance_recheck"] = (
        await _maybe_trigger_compliance_recheck(db, gap, correlation_id)
    )

    # 2. M9 Dossier evidence auto-add (best-effort)
    propagation_result["subsystems"]["dossier_evidence"] = (
        await _maybe_add_dossier_evidence(db, gap, admin_user_id, correlation_id)
    )

    # 3. M14 AdendaGenerator trigger si material change (best-effort)
    propagation_result["subsystems"]["adenda_material_check"] = (
        await _maybe_trigger_adenda_if_material(db, gap, correlation_id)
    )

    # 4. SSE dashboard refresh (best-effort)
    propagation_result["subsystems"]["dashboards_refresh"] = (
        await _maybe_refresh_dashboards(gap, correlation_id)
    )

    # 5. NotificationOrchestrator cross-stakeholders (best-effort)
    propagation_result["subsystems"]["notifications"] = (
        await _maybe_notify_stakeholders(db, gap, admin_user_id, correlation_id)
    )

    # 6. Record audit log enriched con propagation summary (best-effort)
    await _maybe_record_propagation_audit(db, gap, propagation_result)

    return propagation_result


# ──────────────────────────────────────────────────────────────────────
# Sub-system: m_compliance_monitor recheck trigger


async def _maybe_trigger_compliance_recheck(
    db: AsyncSession,
    gap: CloudGap,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Best-effort · trigger m_compliance_monitor recheck for affected checks.

    Identifica ENS measure code → affected compliance checks → schedule recheck.
    Graceful fallback si motor NO available o checks NO encontrados.
    """
    try:
        # Reuse public_api m_compliance_monitor existing
        from backend.app.motors.m_compliance_monitor import public_api as compliance_api
    except ImportError:
        logger.debug("m_compliance_monitor NOT available · skip recheck trigger")
        return {"status": "skipped", "reason": "motor_unavailable"}

    try:
        # Best-effort · invoke recheck function if exists · graceful otherwise
        recheck_fn = getattr(compliance_api, "schedule_recheck_for_ens_measure", None)
        if recheck_fn is None:
            logger.debug(
                "compliance public_api lacks schedule_recheck_for_ens_measure · "
                "no-op recheck (Future-1.E.compliance.recheck-api)",
            )
            return {"status": "skipped", "reason": "api_not_exposed"}

        await recheck_fn(
            db=db,
            project_id=gap.project_id,
            ens_measure_code=gap.ens_measure_code,
            correlation_id=correlation_id,
        )
        return {
            "status": "triggered",
            "ens_measure_code": gap.ens_measure_code,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "compliance recheck trigger failed (gap=%s) · %s · best-effort",
            gap.id, exc,
        )
        return {"status": "error", "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────
# Sub-system: M9 Dossier evidence auto-add


async def _maybe_add_dossier_evidence(
    db: AsyncSession,
    gap: CloudGap,
    admin_user_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Best-effort · auto-add evidence file to M9 Dossier folder.

    File metadata only (path · sha256) · NO actual filesystem write (T1 polish
    Future-1.E.remediation.evidence-file-physical-write si demand-driven).
    """
    try:
        # Identify M9 evidence intake function
        from backend.app.motors.m09_audit_prep.dossier_generator import (
            DossierGenerator,
        )
    except ImportError:
        logger.debug("M9 dossier_generator NOT available · skip evidence add")
        return {"status": "skipped", "reason": "motor_unavailable"}

    try:
        # Generate evidence record stub (metadata only)
        evidence_record = {
            "type": "cloud_remediation_evidence",
            "gap_id": str(gap.id),
            "ens_measure_code": gap.ens_measure_code,
            "verified_at": gap.verified_at.isoformat() if gap.verified_at else None,
            "verified_by_user_id": (
                str(gap.verified_by_user_id) if gap.verified_by_user_id else None
            ),
            "correlation_id": str(correlation_id),
            "filename_logical": f"cloud_remediation_{gap.id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
            "folder_logical": "13_Informes_Tecnicos",
        }
        # Best-effort · invoke method si exists (NO concrete API impl required)
        register_fn = getattr(DossierGenerator, "register_external_evidence", None)
        if register_fn is None:
            logger.debug(
                "DossierGenerator lacks register_external_evidence · "
                "evidence stub generated only (Future-1.E.dossier.evidence-register-api)",
            )
            return {
                "status": "metadata_only",
                "evidence_record": evidence_record,
            }
        await register_fn(db, evidence_record)
        return {
            "status": "registered",
            "evidence_record": evidence_record,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "M9 dossier evidence add failed (gap=%s) · %s · best-effort",
            gap.id, exc,
        )
        return {"status": "error", "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────
# Sub-system: M14 AdendaGenerator trigger si material change


async def _maybe_trigger_adenda_if_material(
    db: AsyncSession,
    gap: CloudGap,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Best-effort · trigger M14 AdendaGenerator si gap implica material change.

    Material change heurística:
    - Severity CRITICAL OR HIGH
    - ENS measure de familia op.ext.* (proveedores · supply chain)

    Pattern reuse: ``maybe_dispatch_adenda_on_materiality_assessed`` (M14 FASE C).
    """
    try:
        from backend.app.motors.m14_contracts.workflow_hooks import (
            maybe_dispatch_adenda_on_materiality_assessed,
        )
    except ImportError:
        logger.debug("M14 workflow_hooks NOT available · skip adenda trigger")
        return {"status": "skipped", "reason": "motor_unavailable"}

    # Heurística material change · scope-out NO ENS op.ext.* → NO adenda
    is_material = (
        gap.severity in ("critical", "high")
        and gap.ens_measure_code.startswith("op.ext.")
    )
    if not is_material:
        return {
            "status": "skipped",
            "reason": "not_material_change",
            "severity": gap.severity,
            "ens_measure_code": gap.ens_measure_code,
        }

    try:
        assessment_result = {
            "materiality_level": "MATERIAL",
            "affects_overlay": True,
            "affects_renewal": False,
            "trigger_source": "cloud_remediation_verified",
            "gap_id": str(gap.id),
            "correlation_id": str(correlation_id),
        }
        await maybe_dispatch_adenda_on_materiality_assessed(
            db=db,
            project_id=gap.project_id,
            assessment_result=assessment_result,
        )
        return {
            "status": "triggered",
            "materiality_level": "MATERIAL",
            "ens_measure_code": gap.ens_measure_code,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "M14 adenda trigger failed (gap=%s) · %s · best-effort",
            gap.id, exc,
        )
        return {"status": "error", "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────
# Sub-system: Dashboards SSE refresh


async def _maybe_refresh_dashboards(
    gap: CloudGap,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Best-effort · dispatch SSE events para dashboards refresh real-time.

    Cliente /cumplimiento + Admin /cross-project-compliance subscribers.
    """
    try:
        from backend.app.core.sse_dispatcher import sse_dispatcher
    except ImportError:
        return {"status": "skipped", "reason": "sse_unavailable"}

    try:
        await sse_dispatcher.dispatch(
            channel=f"project:{gap.project_id}",
            event_type="compliance_dashboard_refresh_required",
            data={
                "gap_id": str(gap.id),
                "ens_measure_code": gap.ens_measure_code,
                "reason": "remediation_verified",
                "correlation_id": str(correlation_id),
            },
        )
        # Admin cross-project dashboard channel
        await sse_dispatcher.dispatch(
            channel="admin:cross_project_compliance",
            event_type="cross_project_compliance_refresh_required",
            data={
                "project_id": str(gap.project_id),
                "correlation_id": str(correlation_id),
            },
        )
        return {"status": "dispatched", "channels": 2}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "SSE dashboards refresh failed (gap=%s) · %s · best-effort",
            gap.id, exc,
        )
        return {"status": "error", "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────
# Sub-system: NotificationOrchestrator cross-stakeholders


async def _maybe_notify_stakeholders(
    db: AsyncSession,
    gap: CloudGap,
    admin_user_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    """Best-effort · cliente friendly R29 + admin technical notifications.

    Cliente: ClientNotification inbox · "Sistema X ahora más seguro · alerta resuelta"
    Admin: log-only fallback (admin inbox T1 polish)
    """
    result: dict[str, Any] = {"cliente": "skipped", "admin": "skipped"}

    # Cliente notification (best-effort via m21_portal_cliente)
    try:
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )

        await emit_client_notification(
            db=db,
            project_id=gap.project_id,
            client_user_id=None,  # broadcast to project · resolver picks active users
            type="cloud_remediation_verified",
            title=f"Tu sistema está más seguro · {gap.ens_measure_code}",
            body=(
                "Marcos confirmó que la solución funciona correctamente. "
                "La alerta ha quedado resuelta. ¡Buen trabajo!"
            ),
            target_url=f"/client-portal/cumplimiento",
            priority="normal",
            emitted_by_motor="m_cloud_connectors",
        )
        result["cliente"] = "emitted"
    except (ImportError, AttributeError, TypeError) as exc:
        logger.debug(
            "Cliente notification skipped (gap=%s) · %s",
            gap.id, exc,
        )
        result["cliente"] = "skipped_api_mismatch"
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Cliente notification failed (gap=%s) · %s",
            gap.id, exc,
        )
        result["cliente"] = f"error:{exc}"

    # Admin notification (log-only fallback · admin inbox T1 polish)
    logger.info(
        "Admin notification · remediation verified · gap=%s ens=%s correlation=%s",
        gap.id, gap.ens_measure_code, correlation_id,
    )
    result["admin"] = "logged"

    return result


# ──────────────────────────────────────────────────────────────────────
# Sub-system: Audit log enrichment · propagation summary


async def _maybe_record_propagation_audit(
    db: AsyncSession,
    gap: CloudGap,
    propagation_result: dict[str, Any],
) -> None:
    """Best-effort · enrich audit log con propagation summary.

    Adds new audit log row con action=verified + metadata.propagation_summary
    para ENAC trazabilidad cross-system propagation visible.
    """
    try:
        log_row = CloudRemediationApprovalLog(
            gap_id=gap.id,
            project_id=gap.project_id,
            action="propagation_summary",  # custom action · NOT enum (audit-only)
            actor_user_id=None,
            actor_type=CloudRemediationActorType.SYSTEM.value,
            notes="Cross-module propagation summary post VERIFIED",
            metadata_jsonb=propagation_result,
            correlation_id=(
                uuid.UUID(propagation_result["correlation_id"])
                if propagation_result.get("correlation_id") else None
            ),
        )
        db.add(log_row)
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Propagation audit log failed (gap=%s) · %s · best-effort",
            gap.id, exc,
        )
