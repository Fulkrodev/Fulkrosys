"""Incident workflow service · SAN-E v3.MB-6 atom 3.

CCN-STIC 817 workflow estados (6 · admin Marcos transitions):
  created → triaged → investigated → mitigated → resolved → closed

Cliente VE solo `resolved` + `closed` (Q4 cement).
Cliente review MixinA pattern (revisada_ok / con_pregunta / suggest_change).
Firma `incident_close` linkea state transition resolved → closed.

CCN-CERT routing via ccn_cert_decision_tree + LUCIA opt-in (Q2 cement).
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import and_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.operations import Incident
from backend.app.motors.m19_risk.ccn_cert_decision_tree import (
    IncidentEvaluationInput,
    evaluate_routing,
)


WORKFLOW_STATES: tuple[str, ...] = (
    "created",
    "triaged",
    "investigated",
    "mitigated",
    "resolved",
    "closed",
)

# State machine · transitions válidas (CCN-STIC 817)
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"triaged"}),
    "triaged": frozenset({"investigated", "resolved"}),  # skip si trivial
    "investigated": frozenset({"mitigated", "resolved"}),
    "mitigated": frozenset({"resolved"}),
    "resolved": frozenset({"closed"}),  # solo post-firma cliente
    "closed": frozenset(),  # terminal
}

VALID_SEVERITIES: frozenset[str] = frozenset({"critical", "high", "medium", "low"})

CLIENT_FACING_REVIEW_STATUS: frozenset[str] = frozenset({
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
})

CLIENT_VISIBLE_STATES: frozenset[str] = frozenset({"resolved", "closed"})


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class IncidentWorkflowError(Exception):
    """Base error incident workflow service."""


class IncidentNotFoundError(IncidentWorkflowError):
    """Incident no existe."""


class InvalidWorkflowTransitionError(IncidentWorkflowError):
    """Transition no permitida por state machine."""


class InvalidSeverityError(IncidentWorkflowError):
    """Severity inválida."""


class InvalidReviewActionError(IncidentWorkflowError):
    """Action review inválido."""


class IncidentAlreadyClosedError(IncidentWorkflowError):
    """Incident ya cerrado · NO se puede modificar."""


# ════════════════════════════════════════════════════════════════════
# Data transfer objects
# ════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class IncidentClientView:
    """Vista cliente single incident · filter visible states only."""

    id: uuid.UUID
    project_id: uuid.UUID
    fecha: datetime | None
    severidad: str | None
    descripcion: str | None
    resolucion: str | None
    workflow_state: str | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    ccn_cert_routing: dict | None
    reported_to_ccn_cert_at: datetime | None
    manual_notification_doc_id: uuid.UUID | None
    lucia_submission_id: uuid.UUID | None
    notificado_lucia: bool | None
    created_at: datetime


# ════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════


class IncidentWorkflowService:
    """Service incident workflow + CCN-CERT routing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Admin · create + classify
    # ----------------------------------------------------------------

    async def create_incident(
        self,
        *,
        project_id: uuid.UUID,
        severidad: str,
        descripcion: str,
        fecha: datetime | None = None,
    ) -> Incident:
        """Marcos admin crea incident · ejecuta decision tree + persiste routing."""
        sev_norm = (severidad or "").lower().strip()
        if sev_norm not in VALID_SEVERITIES:
            raise InvalidSeverityError(
                f"Severidad '{severidad}' inválida · esperado {sorted(VALID_SEVERITIES)}"
            )

        # Resolve project lucia_enabled + tier
        proj_row = await self.db.execute(
            sa_text(
                "SELECT lucia_enabled, categoria_objetivo FROM projects WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )
        proj_hit = proj_row.first()
        if proj_hit is None:
            raise IncidentNotFoundError(f"Project {project_id} no existe")
        lucia_enabled = bool(proj_hit[0])
        project_tier = proj_hit[1]

        # Decision tree
        routing = evaluate_routing(IncidentEvaluationInput(
            severity=sev_norm,
            lucia_enabled=lucia_enabled,
            project_tier=project_tier,
        ))

        incident_id = uuid.uuid4()
        await self.db.execute(
            sa_text(
                "INSERT INTO incidents "
                "(id, project_id, fecha, severidad, descripcion, "
                "workflow_state, notificado_lucia, "
                "ccn_cert_routing_decision, created_at) "
                "VALUES (:id, :pid, :fecha, :sev, :desc, 'created', false, "
                "CAST(:routing AS jsonb), now())"
            ),
            {
                "id": str(incident_id),
                "pid": str(project_id),
                "fecha": fecha or datetime.now(UTC),
                "sev": sev_norm,
                "desc": descripcion,
                "routing": _jsonify(routing.to_dict()),
            },
        )
        await self.db.flush()

        # #32 · Notificación automática a INCIBE-CERT vía LUCIA (art. 33 RD
        # 311/2022) cuando el decision tree marca auto_submit_lucia (severidad
        # critical/high + lucia_enabled). Antes dead-code: submit_incident existía
        # pero nadie lo invocaba · create_incident dejaba notificado_lucia=false.
        if routing.action_required == "auto_submit_lucia":
            await self._auto_submit_lucia(
                incident_id=incident_id,
                project_id=project_id,
                severidad=sev_norm,
                descripcion=descripcion,
                fecha=fecha or datetime.now(UTC),
            )

        result = await self.db.get(Incident, incident_id)
        assert result is not None
        return result

    # ----------------------------------------------------------------
    # #32 · LUCIA auto-notificación (obligación legal art. 33 RD 311/2022)
    # ----------------------------------------------------------------

    async def _auto_submit_lucia(
        self,
        *,
        incident_id: uuid.UUID,
        project_id: uuid.UUID,
        severidad: str,
        descripcion: str,
        fecha: datetime,
    ) -> None:
        """Auto-notifica el incidente a LUCIA (INCIBE-CERT) y enlaza la submission
        al incidente. Resiliente: un fallo de LUCIA NO rompe el alta del incidente,
        pero SIEMPRE deja rastro en audit_log (R6 · art. 33 obliga trazabilidad ·
        no silent-fail). Sin credenciales del cliente → submit_incident persiste
        'pending_credentials' (fallback honesto: el cliente sube el JSON al portal)."""
        from backend.app.motors.m27_conformity.lucia_federation import (
            LuciaIncidentPayload,
            submit_incident,
        )

        # CCN-STIC 845 usa severidad en MAYÚSCULA ES; el incidente la guarda en minúscula.
        sev_map = {
            "critical": "CRITICA", "high": "ALTA",
            "medium": "MEDIA", "low": "BAJA",
        }
        master_key = os.environ.get("FULKRO_FERNET_KEY", "")
        status = "error"
        submission_id: uuid.UUID | None = None
        remote_id: str | None = None
        error_detail: str | None = None
        try:
            payload = LuciaIncidentPayload(
                incident_id=incident_id,
                severity=sev_map.get(severidad, severidad.upper()),
                title=descripcion[:120],
                description=descripcion,
                detected_at=fecha,
                affected_systems=[],
                timeline=[],
                classification="ccn-cert-taxonomy-pending",
                impact_assessment=(
                    "Evaluación detallada pendiente (notificación inicial automática)."
                ),
                contention_actions=[],
            )
            res = await submit_incident(
                self.db, project_id, payload, master_key,
                db_incident_id=incident_id,
            )
            status = res.status
            submission_id = res.submission_id_local
            remote_id = res.submission_id_remote
            error_detail = res.error_detail
            await self.db.execute(
                sa_text(
                    "UPDATE incidents SET lucia_submission_id = :sid, "
                    "notificado_lucia = :notif WHERE id = :iid"
                ),
                {
                    "sid": str(submission_id),
                    "notif": status == "sent",
                    "iid": str(incident_id),
                },
            )
        except Exception as exc:  # pragma: no cover · resiliencia
            logger.exception("#32 auto-submit LUCIA falló · incident={}", incident_id)
            error_detail = str(exc)[:300]

        await self._emit_lucia_audit(
            incident_id=incident_id,
            project_id=project_id,
            status=status,
            submission_id=submission_id,
            remote_id=remote_id,
            error_detail=error_detail,
        )

    async def _emit_lucia_audit(
        self,
        *,
        incident_id: uuid.UUID,
        project_id: uuid.UUID,
        status: str,
        submission_id: uuid.UUID | None,
        remote_id: str | None,
        error_detail: str | None,
    ) -> None:
        """R6 · audit_log inmutable de la notificación LUCIA (art. 33)."""
        try:
            await self.db.execute(
                sa_text(
                    "INSERT INTO audit_log "
                    "(id, tabla, registro_id, accion, usuario, project_id, "
                    " payload_new, timestamp) "
                    "VALUES (gen_random_uuid(), 'incidents', :rid, "
                    "'submit_lucia', 'system', :pid, CAST(:payload AS jsonb), now())"
                ),
                {
                    "rid": str(incident_id),
                    "pid": str(project_id),
                    "payload": json.dumps({
                        "submission_id": (
                            str(submission_id) if submission_id else None
                        ),
                        "status": status,
                        "remote_id": remote_id,
                        "error": error_detail,
                    }),
                },
            )
            await self.db.flush()
        except Exception:  # pragma: no cover · best-effort (no rompe el alta)
            logger.exception(
                "#32 audit_log submit_lucia emit failed · incident={}", incident_id,
            )

    # ----------------------------------------------------------------
    # Workflow state transitions (admin-only)
    # ----------------------------------------------------------------

    async def transition_workflow_state(
        self,
        incident_id: uuid.UUID,
        new_state: str,
        *,
        resolucion: str | None = None,
    ) -> Incident:
        """Marcos admin transition · enforce state machine CCN-STIC 817."""
        incident = await self.db.get(Incident, incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {incident_id} no existe")

        current = incident.workflow_state or "created"
        if current == "closed":
            raise IncidentAlreadyClosedError(
                f"Incident {incident_id} ya cerrado · no se permite transition"
            )

        valid_next = _VALID_TRANSITIONS.get(current, frozenset())
        if new_state not in valid_next:
            raise InvalidWorkflowTransitionError(
                f"Transition {current} → {new_state} no permitida · "
                f"válidas {sorted(valid_next)}"
            )

        incident.workflow_state = new_state
        if resolucion is not None:
            incident.resolucion = resolucion
        await self.db.flush()
        return incident

    # ----------------------------------------------------------------
    # Cliente review (MixinA pattern · 7ª aplicación)
    # ----------------------------------------------------------------

    async def mark_client_review(
        self,
        incident_id: uuid.UUID,
        action: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> Incident:
        """Cliente review action · revisada_ok / con_pregunta / suggest_change."""
        if action not in CLIENT_FACING_REVIEW_STATUS:
            raise InvalidReviewActionError(
                f"action '{action}' inválido · esperado "
                f"{sorted(CLIENT_FACING_REVIEW_STATUS)}"
            )
        if action in {"con_pregunta", "suggest_change"} and not (note or "").strip():
            raise InvalidReviewActionError(
                f"action '{action}' requiere note no vacía"
            )

        incident = await self.db.get(Incident, incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {incident_id} no existe")
        if incident.workflow_state not in CLIENT_VISIBLE_STATES:
            raise IncidentWorkflowError(
                f"Incident en estado '{incident.workflow_state}' · cliente NO "
                f"puede revisar hasta resolved"
            )

        incident.client_review_status = action
        incident.client_review_note = (note or "").strip() or None
        incident.client_reviewed_at = datetime.now(UTC)
        incident.client_reviewed_by_user_id = user_id
        await self.db.flush()
        return incident

    # ----------------------------------------------------------------
    # Bulk listing · cliente facing
    # ----------------------------------------------------------------

    async def get_client_visible_incidents(
        self, project_id: uuid.UUID,
    ) -> list[IncidentClientView]:
        """Lista incidents cliente-visible · filter workflow_state IN (resolved, closed)."""
        stmt = (
            select(Incident)
            .where(
                and_(
                    Incident.project_id == project_id,
                    Incident.workflow_state.in_(list(CLIENT_VISIBLE_STATES)),
                    Incident.deleted_at.is_(None),
                )
            )
            .order_by(Incident.fecha.desc().nulls_last())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [_to_client_view(r) for r in rows]

    async def get_client_visible_incident(
        self, incident_id: uuid.UUID,
    ) -> IncidentClientView:
        """Detail single · enforce cliente-visible state."""
        incident = await self.db.get(Incident, incident_id)
        if incident is None or incident.deleted_at is not None:
            raise IncidentNotFoundError(f"Incident {incident_id} no existe")
        if incident.workflow_state not in CLIENT_VISIBLE_STATES:
            raise IncidentNotFoundError(
                f"Incident {incident_id} no visible para cliente"
            )
        return _to_client_view(incident)

    # ----------------------------------------------------------------
    # Document hash + signoff
    # ----------------------------------------------------------------

    async def compute_incident_close_hash(
        self, incident_id: uuid.UUID,
    ) -> tuple[str, int]:
        """SHA256 canonical incident_close state · input firma M05."""
        incident = await self.db.get(Incident, incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {incident_id} no existe")
        if incident.workflow_state != "resolved":
            raise IncidentWorkflowError(
                f"Incident workflow_state='{incident.workflow_state}' · "
                f"esperado 'resolved' antes de cerrar"
            )

        canonical_parts: list[str] = [
            f"incident_id:{incident.id}",
            f"project_id:{incident.project_id}",
            f"severidad:{incident.severidad or ''}",
            f"descripcion_hash:{hashlib.sha256((incident.descripcion or '').encode()).hexdigest()[:16]}",
            f"resolucion_hash:{hashlib.sha256((incident.resolucion or '').encode()).hexdigest()[:16]}",
            f"client_review_status:{incident.client_review_status or 'pending'}",
            f"client_reviewed_at:{incident.client_reviewed_at.isoformat() if incident.client_reviewed_at else ''}",
        ]
        canonical = "\n".join(canonical_parts)
        document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return document_hash, len(canonical)

    async def process_incident_close_signoff(
        self,
        incident_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
    ) -> Incident:
        """Post-firma incident_close · workflow resolved → closed + link intent."""
        incident = await self.db.get(Incident, incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {incident_id} no existe")
        if incident.workflow_state != "resolved":
            raise IncidentWorkflowError(
                f"Incident workflow_state='{incident.workflow_state}' · "
                f"esperado 'resolved' para cierre"
            )

        incident.workflow_state = "closed"
        incident.client_signing_intent_id = signing_intent_id
        await self.db.flush()

        # MB-6 atom 8 · post-signoff hook cross-motor
        try:
            from backend.app.notifications.post_signoff_hooks import (
                post_signoff_incident,
            )
            await post_signoff_incident(self.db, incident=incident)
        except Exception:
            pass  # silent fail

        return incident


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _to_client_view(incident: Incident) -> IncidentClientView:
    return IncidentClientView(
        id=incident.id,
        project_id=incident.project_id,
        fecha=incident.fecha,
        severidad=incident.severidad,
        descripcion=incident.descripcion,
        resolucion=incident.resolucion,
        workflow_state=incident.workflow_state,
        client_review_status=incident.client_review_status,
        client_review_note=incident.client_review_note,
        client_reviewed_at=incident.client_reviewed_at,
        client_signing_intent_id=incident.client_signing_intent_id,
        ccn_cert_routing=incident.ccn_cert_routing_decision,
        reported_to_ccn_cert_at=incident.reported_to_ccn_cert_at,
        manual_notification_doc_id=incident.manual_notification_doc_id,
        lucia_submission_id=incident.lucia_submission_id,
        notificado_lucia=incident.notificado_lucia,
        created_at=incident.created_at,
    )


def _jsonify(d: dict) -> str:
    import json
    return json.dumps(d, default=str)
