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
import json
import logging
import os
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
        """Despacha un evento: a este proceso y, si hay Redis, a los demas.

        D4 (2026-09-10). Antes solo entregaba en ESTE proceso. Medido con dos
        replicas detras de nginx y dos conexiones SSE abiertas, una en cada
        replica: el evento llegaba a UNA de las dos. Ver
        `docs/adr/ADR-003-escalabilidad-horizontal.md` y el arnes que lo mide,
        `scripts/probar_dos_replicas.sh`.

        Sin Redis se comporta exactamente igual que antes: el modo de una sola
        replica no depende de nada nuevo.
        """
        event = SseEvent(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.entregar_local(channel, event)
        await publicar_en_bus(channel, event)

    def entregar_local(self, channel: str, event: SseEvent) -> None:
        """Entrega a los suscriptores DE ESTE proceso y anota en el replay buffer.

        Lo llaman `dispatch` (evento nacido aqui) y el puente de Redis (evento
        nacido en otra replica). Separarlo es lo que evita el bucle: el puente
        NO vuelve a publicar lo que acaba de recibir.
        """
        self._replay_buffers[channel].append(event)

        subscribers = list(self._subscribers.get(channel, []))
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full · dropping event channel=%s type=%s",
                    channel, event.type,
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
    # Retainer check-in trimestral (feat/fulkro-100 Ola B · 2026-06-13): el
    # cliente ve aparecer su informe trimestral al instante cuando Marcos lo
    # envía (admin-origin · cliente-facing).
    "retainer.checkin.sent",
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


# ════════════════════════════════════════════════════════════════════════════
# D4 · puente entre replicas por Redis
#
# El despachador de arriba es de PROCESO: sus diccionarios viven en memoria. Con
# una sola replica eso basta y es lo mas rapido que hay. Con dos, un evento
# nacido en la replica A no llega jamas a los suscriptores de la B.
#
# Medido antes de escribir esto (scripts/probar_dos_replicas.sh, apartado 5):
# dos conexiones SSE abiertas por nginx, una en cada replica, y un PATCH que
# despacha `m17.plan.updated` -> "solo a 1 de 2".
#
# El puente es deliberadamente lo minimo: publicar en Redis lo que se despacha y
# entregar en local lo que llegue de otras replicas. Contrapartidas escritas en
# docs/adr/ADR-003-escalabilidad-horizontal.md; en resumen:
#
#   · Entrega "como mucho una vez". Si Redis se cae o la replica esta arrancando,
#     el evento se pierde y NADIE lo reintenta. Es aceptable porque el SSE de
#     esta aplicacion es una senal para refrescar, no un canal de datos: la
#     interfaz vuelve a pedir el estado por HTTP. Un evento perdido cuesta que
#     una pantalla tarde en actualizarse, no que se pierda un dato.
#   · El replay buffer (deque de 100 por canal, para Last-Event-ID) sigue siendo
#     de proceso. Si el navegador reconecta y cae en OTRA replica, el hueco no se
#     puede rellenar. Ver el ADR.
#   · Sin Redis, todo esto no existe y el comportamiento es el de siempre.
# ════════════════════════════════════════════════════════════════════════════

#: Prefijo de los canales de Redis. Va con prefijo propio para no chocar con
#: Celery, que usa las bases 1 y 2 del mismo servidor.
_PREFIJO_BUS = "fulkro:sse:"

#: Identificador de ESTE proceso. Viaja en cada mensaje para descartar el eco:
#: quien publica ya ha entregado en local, y volver a entregarlo duplicaria.
_ID_PROCESO = str(uuid.uuid4())

_cliente_bus = None          # redis.asyncio.Redis | None
_bus_desactivado = False     # True cuando no hay Redis: no se reintenta por evento
_tarea_puente = None         # asyncio.Task | None


def _url_redis() -> str:
    return os.environ.get("REDIS_URL", "").strip()


async def _obtener_cliente():
    """Cliente de Redis perezoso. Devuelve None si no hay Redis utilizable."""
    global _cliente_bus, _bus_desactivado
    if _bus_desactivado:
        return None
    if _cliente_bus is not None:
        return _cliente_bus
    url = _url_redis()
    if not url:
        _bus_desactivado = True
        logger.info("SSE: sin REDIS_URL · entrega solo dentro de este proceso")
        return None
    try:
        import redis.asyncio as redis_asyncio
        _cliente_bus = redis_asyncio.from_url(url, decode_responses=True)
        await _cliente_bus.ping()
        return _cliente_bus
    except Exception as exc:  # noqa: BLE001 — degradar, nunca tumbar el despacho
        _bus_desactivado = True
        _cliente_bus = None
        logger.warning(
            "SSE: Redis no utilizable (%s: %s) · entrega solo dentro de este "
            "proceso. Con mas de una replica, los eventos NO cruzan.",
            type(exc).__name__, exc,
        )
        return None


async def publicar_en_bus(channel: str, event: SseEvent) -> None:
    """Publica el evento para las demas replicas. Best-effort y silencioso."""
    cliente = await _obtener_cliente()
    if cliente is None:
        return
    try:
        await cliente.publish(_PREFIJO_BUS + channel, json.dumps({
            "origen": _ID_PROCESO,
            "type": event.type,
            "data": event.data,
            "timestamp": event.timestamp,
            "event_id": event.event_id,
        }))
    except Exception as exc:  # noqa: BLE001
        logger.warning("SSE: no se pudo publicar en Redis (%s)", exc)


async def _bucle_puente() -> None:
    """Escucha lo que publican las demas replicas y lo entrega aqui."""
    cliente = await _obtener_cliente()
    if cliente is None:
        return
    pubsub = cliente.pubsub(ignore_subscribe_messages=True)
    await pubsub.psubscribe(_PREFIJO_BUS + "*")
    logger.info("SSE: puente entre replicas escuchando en %s*", _PREFIJO_BUS)
    try:
        async for mensaje in pubsub.listen():
            if not mensaje or mensaje.get("type") not in ("message", "pmessage"):
                continue
            try:
                cuerpo = json.loads(mensaje["data"])
            except (TypeError, ValueError):
                continue
            if cuerpo.get("origen") == _ID_PROCESO:
                continue  # eco de lo nuestro: ya se entrego en local
            canal = str(mensaje["channel"])[len(_PREFIJO_BUS):]
            sse_dispatcher.entregar_local(canal, SseEvent(
                type=cuerpo.get("type", ""),
                data=cuerpo.get("data") or {},
                timestamp=cuerpo.get("timestamp", ""),
                event_id=cuerpo.get("event_id") or str(uuid.uuid4()),
            ))
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("SSE: el puente entre replicas se ha caido (%s)", exc)
    finally:
        try:
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass


async def arrancar_puente_sse() -> None:
    """Lo llama el `lifespan` de la aplicacion. Sin Redis no hace nada."""
    global _tarea_puente
    if _tarea_puente is not None and not _tarea_puente.done():
        return
    if not _url_redis():
        logger.info("SSE: sin REDIS_URL · no se arranca el puente entre replicas")
        return
    _tarea_puente = asyncio.create_task(_bucle_puente(), name="sse-puente-replicas")


async def parar_puente_sse() -> None:
    """Cierre ordenado desde el `lifespan`."""
    global _tarea_puente, _cliente_bus
    if _tarea_puente is not None:
        _tarea_puente.cancel()
        try:
            await _tarea_puente
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _tarea_puente = None
    if _cliente_bus is not None:
        try:
            await _cliente_bus.aclose()
        except Exception:  # noqa: BLE001
            pass
        _cliente_bus = None
