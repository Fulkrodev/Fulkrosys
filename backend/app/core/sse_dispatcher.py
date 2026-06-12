"""SSE dispatcher · pub-sub in-memory para event-driven UI (MB-13.3 · ADR-035).

Singleton ``sse_dispatcher`` permite a SQLAlchemy event listeners y demás
servicios backend dispatcher eventos a subscribers SSE conectados via
``GET /api/v1/projects/{id}/events``.

Backend escala a multi-instance via Redis pubsub futuro (no MB-13);
aquí basta in-memory porque el deploy actual es single-instance dev.

Eventos canónicos emitidos en MB-13.3:
- ``readiness_changed``    cuando cambia algún Asset/MageritThreat/
                            DdaEntry/Evidence asociado a project_id
- ``phase_changed``         cuando ``projects.fase`` cambia
- ``alert_new``             cuando AlertService.trigger_alert (MB-13.4)

Sesión 3B-2B.11 Ejecutable 6 Phase 11.1 (2026-05-27):
- Per-event ``event_id`` UUID generation (uniquely identify each dispatched event)
- Ring-buffer per channel (deque maxlen=100 · replay buffer for reconnect resume)
- ``subscribe(channel, last_event_id=None)`` con replay logic post Last-Event-ID
- Forward-compat con browser EventSource native ``Last-Event-ID`` header
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


@dataclass
class SseEvent:
    """Event entregado a subscribers. timestamp en ISO UTC.

    Sesión 3B-2B.11 Phase 11.1: ``event_id`` UUID added · unique per dispatched
    event. Used for Last-Event-ID resume replay buffer match.
    """

    type: str
    data: dict
    timestamp: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class SseDispatcher:
    """In-memory pub-sub de SSE events.

    Cada subscriber espera un canal (ej. ``project:{uuid}``) y recibe
    eventos via ``asyncio.Queue``. Si el queue se llena (cliente lento),
    el dispatch dropea el evento con warning · reintento es responsabilidad
    del cliente vía polling baseline.

    Sesión 3B-2B.11 Phase 11.1: replay buffer per channel · ``deque(maxlen=100)``
    retiene últimos 100 events por channel para replay-on-resume via
    Last-Event-ID. Browser EventSource native sets header al reconectar.
    """

    QUEUE_MAXSIZE = 100
    REPLAY_BUFFER_MAXLEN = 100

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[SseEvent]]] = (
            defaultdict(list)
        )
        self._replay_buffers: dict[str, deque[SseEvent]] = defaultdict(
            lambda: deque(maxlen=self.REPLAY_BUFFER_MAXLEN),
        )

    async def subscribe(
        self,
        channel: str,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[SseEvent, None]:
        """Subscribe a channel · yields events hasta cancelación.

        Si ``last_event_id`` provisto y existe en replay buffer · primero yields
        los events posteriores a ese ID (backfill). Luego stream realtime.
        Si ``last_event_id`` NO en buffer (gap too large > 100 events) · skip
        replay (cliente UI debe refetch full state via tanstack invalidate).
        """
        queue: asyncio.Queue[SseEvent] = asyncio.Queue(
            maxsize=self.QUEUE_MAXSIZE,
        )
        self._subscribers[channel].append(queue)

        try:
            if last_event_id:
                replay_events = self._compute_replay(channel, last_event_id)
                for replay_event in replay_events:
                    yield replay_event

            while True:
                event = await queue.get()
                yield event
        except asyncio.CancelledError:
            logger.debug("SSE subscriber cancelled: %s", channel)
            raise
        finally:
            try:
                self._subscribers[channel].remove(queue)
            except ValueError:
                pass
            if channel in self._subscribers and not self._subscribers[channel]:
                del self._subscribers[channel]

    def _compute_replay(
        self, channel: str, last_event_id: str,
    ) -> list[SseEvent]:
        """Return events posteriores a last_event_id desde replay buffer.

        Empty list si last_event_id NO en buffer (gap demasiado grande).
        """
        buffer = self._replay_buffers.get(channel)
        if not buffer:
            return []
        items = list(buffer)
        for idx, ev in enumerate(items):
            if ev.event_id == last_event_id:
                return items[idx + 1:]
        return []

    async def dispatch(
        self, channel: str, event_type: str, data: dict,
    ) -> None:
        """Dispatch event · entrega best-effort a todos subscribers + append replay buffer."""
        event = SseEvent(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._replay_buffers[channel].append(event)

        subscribers = list(self._subscribers.get(channel, []))
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full · dropping event channel=%s type=%s",
                    channel, event_type,
                )

    def subscriber_count(self, channel: str) -> int:
        return len(self._subscribers.get(channel, []))

    def replay_buffer_size(self, channel: str) -> int:
        """Current replay buffer size for channel (testing visibility)."""
        return len(self._replay_buffers.get(channel, ()))


# Sub-atom 1.D.G v3.11 · event types per audience
ADMIN_EVENT_TYPES: frozenset[str] = frozenset({
    "readiness_changed",
    "phase_changed",
    "alert_new",
    "step_completed",
    "step_unblocked",
    "step_blocked",
    # Sesión 3B-2B.8 CLUSTER 5 Phase 5C · chat realtime admin recv
    # cliente messages. Audience filter (sender_type=client) applied in
    # event_matches_audience cross-actor section.
    "chat_message_new",
    # Ola 3 #12 (2026-06-04) · el admin VE la firma del cliente en realtime
    # (la firma es el motor de avance · antes solo lo veía al refrescar). Son
    # SIEMPRE acciones del cliente → sin filtro cross-actor (membresía basta).
    # signing.requested NO se incluye: lo origina el propio admin (eco inútil).
    "signing.signed",
    "signing.declined",
    # M8 Autopilot v2.0 · progreso live del pentesting automático (admin-only)
    "m08_autopilot_started",
    "m08_phase_change",
    "m08_run_completed",
    # Gestor documental compartido (FIX P2-3 · 2026-06-09): el admin ve en
    # realtime cuando el cliente sube un documento (y viceversa · cross-actor
    # natural en un espacio documental por-proyecto compartido).
    "document.uploaded",
    # Continuidad BIA/DRP (feat/fulkro-100 · 2026-06-12): el admin VE en
    # realtime cuando el cliente rellena el cuestionario, aprueba o comenta un
    # borrador BIA/DRP. Son SIEMPRE acciones del cliente → admin-facing
    # (membresía basta · mismo patrón cross-actor que signing.signed).
    "continuidad.questionnaire.submitted",
    "continuidad.draft.approved",
    "continuidad.draft.comment",
})

CLIENTE_EVENT_TYPES: frozenset[str] = frozenset({
    # Workflow steps (1.D.G v3.11)
    "step_completed",
    "step_unblocked",
    "step_blocked",
    # Sesión 3B-2B.8 Phase 1A + 1B · cliente portal admin↔cliente sync events
    "m01.categorizacion.completed",
    "m02.magerit.updated",
    # Sesión 3B-2B.8 CLUSTER 2 Phase 2A · SSE wire-completeness fix
    # (CRITICAL bug pre-existing · 12 events bloqueados pre-fix · cliente
    # UIs Phase 1C+1E+Bloque 3+5+M21+M08 NUNCA recibían realtime updates)
    "m17.plan.updated",  # Phase 1E
    "cloud.connector.disconnect_requested",  # Phase 1C
    "chat_message_new",  # M21 chat cliente↔admin
    "pentest_check_required",  # M08 pentest auto-trigger ALTA
    # Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central SSE wire
    # (M21 inbox auto-refetch realtime · DRY centralized dispatch from
    # emit_client_notification fn · forward-compat ALL VALID_TYPES incl
    # report_available · acta_review · evidence_request · etc).
    # Filosofía cliente-mínimo: cliente RECIBE notif appearance realtime ·
    # NO opera admin internals · ownership audience-filtered.
    "client_notification.created",
    # Bloque 3+5 cloud remediation lifecycle (9 events)
    "cloud_remediation_proposed",
    "cloud_remediation_approved",
    "cloud_remediation_rejected",
    "cloud_remediation_executing",
    "cloud_remediation_executed",
    "cloud_remediation_failed",
    "cloud_remediation_verification_pending",
    "cloud_remediation_verified",
    "cloud_remediation_rollback_requested",
    # Ejecutable 8 Pasada 16 (F-08-02 / F-13 / F-15-01): firma in-portal (m05_signing) +
    # acompañamiento auditoría (m_audit_accompaniment). El cliente debe recibirlos en realtime
    # (antes degradaban a polling 30s en /firmas-pendientes y /certificacion).
    "signing.requested",
    "signing.signed",
    "signing.declined",
    "accompaniment.state.advanced",
    # Gestor documental compartido (FIX P2-3 · 2026-06-09): el cliente ve en
    # realtime cuando el admin comparte un documento nuevo en su proyecto (y el
    # eco de su propia subida). Filtro de audiencia salta los documentos
    # marcados ``interno`` (NO visibles para el cliente · ver event_matches_audience).
    "document.uploaded",
    # Ola 3 #14 (2026-06-04) · POLÍTICA NUEVA: el cliente ve su progreso de fase
    # en realtime (transparencia outcome-as-a-service · "ve su proyecto
    # avanzar"). Revierte el bloqueo anterior. readiness_changed/alert_new
    # SIGUEN admin-internos (NO cliente-facing). Payload limpio: solo
    # {project_id, old_phase, new_phase} · sin metadata interna del consultor.
    "phase_changed",
    # Continuidad BIA/DRP (feat/fulkro-100 · 2026-06-12): el cliente recibe en
    # realtime cuando Marcos prepara un borrador BIA/DRP listo para aprobar
    # (admin-origin · cliente-facing).
    "continuidad.draft_ready",
})

# DISEÑO DE AUDIENCIAS (resuelto · Marcos 2026-05-31): admin y cliente son conjuntos
# DISTINTOS que SE SOLAPAN, NO una relación de subconjunto. Comparten solo los eventos
# cross-actor (workflow steps + chat, y desde Ola 3 #14 phase_changed por transparencia);
# el resto de eventos cliente-facing (client_notification, m01/m02 sync, cloud_remediation,
# signing, plan, accompaniment, pentest) son EXCLUSIVOS de cliente y NO se eco-difunden a
# admin (filosofía cliente-mínimo). Se descartó el invariante `CLIENTE ⊆ ADMIN` (rompía los
# tests que asertan que el admin NO recibe el eco de eventos puramente de cliente).
# ADMIN_EVENT_TYPES es el set admin canónico. Invariante blindado en
# test_cross_actor_blocking_semantics.test_cliente_admin_event_audiences_are_distinct_by_design.


def event_matches_audience(
    event_type: str,
    audience: str,
    data: dict,
) -> bool:
    """Filtra events per audience cliente vs admin (1.D.G v3.11 + CLUSTER 2 Phase 2A).

    Cliente recibe events workflow + sync motors + cloud remediation lifecycle +
    chat + pentest check + plan updated. Filosofía cliente-mínimo sostained:
    cliente VE/RECIBE updates de admin operations · NO emite operations admin.

    Admin recibe TODOS los eventos ADMIN_EVENT_TYPES.
    """
    if audience == "admin":
        if event_type not in ADMIN_EVENT_TYPES:
            return False
        # CLUSTER 5 Phase 5C · admin recv chat_message_new ONLY when sender
        # is cliente (admin NO own echo). Mirror of cliente cross-actor
        # filter at line 196-198.
        if event_type == "chat_message_new":
            sender_type = data.get("sender_type", "client")
            return sender_type == "client"
        return True

    if audience != "cliente":
        return False

    if event_type not in CLIENTE_EVENT_TYPES:
        return False

    # Cross-actor filter per event semantics
    primary_actor = data.get("primary_actor", "admin")

    # ─── Workflow step events (cross-actor filter) ───
    if event_type == "step_completed":
        # Cliente quiere saber cuando admin terminó algo · NO cuando cliente termina
        return primary_actor == "admin"
    if event_type in ("step_unblocked", "step_blocked"):
        # cliente solo si steps que LE TOCA
        return primary_actor == "cliente"

    # ─── Phase 1A + 1B sync events (admin actor only) ───
    if event_type == "m01.categorizacion.completed":
        return primary_actor == "admin"
    if event_type == "m02.magerit.updated":
        return primary_actor == "admin"

    # ─── Ola 3 #14 · phase_changed cliente-facing (política transparencia) ───
    # El cliente VE su progreso de fase. Payload ya limpio en el emit
    # (dashboard_events._on_project_update · solo old/new phase · sin internals).
    if event_type == "phase_changed":
        return True

    # ─── CLUSTER 2 Phase 2A · cliente-relevant lifecycle events ───

    # Phase 1E · admin PATCH task → cliente sees plan update READ-ONLY
    if event_type == "m17.plan.updated":
        return True

    # Phase 1C · cliente own request echo (always own action)
    if event_type == "cloud.connector.disconnect_requested":
        return True

    # M21 chat · cliente recibe cuando ADMIN responde (NO own echo)
    if event_type == "chat_message_new":
        sender_type = data.get("sender_type", "admin")
        return sender_type == "admin"

    # M08 pentest auto-trigger · cliente ALTA category authorization needed
    if event_type == "pentest_check_required":
        return True

    # Gestor documental compartido (FIX P2-3) · el cliente recibe el evento de
    # documento nuevo SALVO que esté marcado ``interno`` (espejo del filtro
    # ``d.interno = false`` de la lista de documentos del portal cliente).
    if event_type == "document.uploaded":
        return not bool(data.get("interno", False))

    # Phase 2D · ClientNotification SSE wire · cliente recibe realtime
    # appearance of in-app notification (inbox auto-refetch trigger).
    # Audience-level ownership ya filtered en channel (project:{id} +
    # _verify_client_owns_project) · semantic-level filter aquí trivially
    # permit dado client_user_id propagated en data para frontend
    # invalidate query target.
    if event_type == "client_notification.created":
        return True

    # Bloque 3+5 cloud remediation lifecycle · cliente sees full lifecycle
    # Cuando orchestrator emit con audience field present, respect filter;
    # else default visible (cliente UI usa /remediaciones page subscribe pattern)
    if event_type.startswith("cloud_remediation_"):
        audience_data = data.get("audience")
        if audience_data is not None:
            return audience_data in ("cliente", "both")
        return True

    # Fallback · whitelisted pero sin semantic logic explicit → permit
    return True


sse_dispatcher = SseDispatcher()
