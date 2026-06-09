"use client";

/**
 * useClientProjectEvents · SSE listener cliente filtered per audience (1.D.G.E v3.11).
 *
 * Subscribes a /api/v1/client-portal/projects/{id}/events · auto-reconnect via
 * browser EventSource API. Backend ya filtra eventos audience cliente
 * (event_matches_audience cliente filter).
 *
 * Patrón mirror useProjectEvents admin (existing en lib/admin-dashboard).
 *
 * Eventos recibidos (post backend filtering):
 *  - step_completed (cuando admin terminó · primary_actor=admin)
 *  - step_unblocked (cuando cliente debe actuar · primary_actor=cliente)
 *  - step_blocked (cuando cliente bloqueado · primary_actor=cliente)
 */
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

export type CloudRemediationEventType =
  | "cloud_remediation_proposed"
  | "cloud_remediation_approved"
  | "cloud_remediation_rejected"
  | "cloud_remediation_executing"
  | "cloud_remediation_executed"
  | "cloud_remediation_failed";

/** Sesión 3B-2B.8 Phase 1A + 1B + 1E · cliente portal sync events admin → cliente. */
export type ClientSyncEventType =
  | "m01.categorizacion.completed"
  | "m02.magerit.updated"
  | "m17.plan.updated";

/**
 * Sesión 3B-2B.8 Phase 1C · cloud connector lifecycle events cliente subscribe.
 *
 * - disconnect_requested: emitted by cliente request-disconnect endpoint
 * - connected/disconnected/sync_completed/error: forward-compat (emitted by
 *   M16 OAuth callback / admin revoke / sync orchestrator · future wire-in).
 */
export type CloudConnectorEventType =
  | "cloud.connector.disconnect_requested"
  | "cloud.connector.connected"
  | "cloud.connector.disconnected"
  | "cloud.connector.sync_completed"
  | "cloud.connector.error";

/**
 * Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central SSE wire.
 *
 * Triggers cliente inbox auto-refetch realtime cuando emit_client_notification
 * fires desde cualquier motor backend (DRY centralizado). Forward-compat ALL
 * VALID_TYPES (report_available · acta_review · evidence_request · etc).
 *
 * Filosofía cliente-mínimo: cliente RECIBE notif appearance realtime · NO
 * opera admin internals · ownership audience-filtered backend-side.
 */
export type ClientNotificationEventType =
  | "client_notification.created";

/**
 * Sesión 3B-2B.8 CLUSTER 5 Phase 5C delta · chat realtime cliente↔admin
 * (ADR-038 SAN-D MB-14.5/6 + Phase 2A SSE whitelist).
 *
 * Backend audience filter (event_matches_audience cliente):
 * - sender_type === "admin" → cliente recv (NO own echo)
 * - sender_type === "cliente" → admin recv only (NOT this hook)
 *
 * Filosofía cliente-mínimo: cliente RECIBE realtime admin replies <2s
 * empirical · NO polling fallback (graceful EventSource auto-reconnect).
 */
export type ChatEventType = "chat_message_new";

/**
 * Ejecutable 7.7 · TIER 1 canvas signing events admin → cliente realtime.
 *
 * Backend emit en SigningService.sign_canvas + admin_request_signature +
 * reject_intent endpoints (channel project:{id}).
 *
 * - signing.requested · admin trigger intent · cliente recv → refresh pending list
 * - signing.signed · cliente firmó · refresh history + pending
 * - signing.declined · cliente rechazó · refresh history + pending
 */
export type SignatureEventType =
  | "signing.requested"
  | "signing.signed"
  | "signing.declined";

export type ChatSenderTypeData = "client" | "admin" | "system";

/**
 * Ola 3 #14 (2026-06-04) · phase_changed cliente-facing.
 *
 * POLÍTICA NUEVA: el cliente ve su progreso de fase en realtime
 * (transparencia outcome-as-a-service · "ve su proyecto avanzar"). Backend
 * emite payload LIMPIO (solo old_phase/new_phase · sin metadata interna del
 * consultor) desde dashboard_events._on_project_update.
 */
export type PhaseChangedEventType = "phase_changed";

/**
 * Ejecutable 7.5 · acompañamiento auditoría/certificación → cliente realtime.
 * Backend emite en m_audit_accompaniment/service.py (channel project:{id}) al
 * avanzar el estado de la máquina. Antes el frontend NO lo escuchaba → la
 * timeline de /client-portal/certificacion no refrescaba (auditoría 2026-06-07).
 */
export type AccompanimentEventType = "accompaniment.state.advanced";

/**
 * FIX P2-3 (2026-06-09) · gestor documental compartido cliente↔admin.
 * El backend emite ``document.uploaded`` en el canal del proyecto cuando el admin
 * comparte un documento (o como eco de la propia subida del cliente). El filtro de
 * audiencia salta los documentos ``interno``. El cliente refresca su lista.
 */
export type DocumentEventType = "document.uploaded";

export type ClientSseEventType =
  | "step_completed"
  | "step_unblocked"
  | "step_blocked"
  | CloudRemediationEventType
  | ClientSyncEventType
  | CloudConnectorEventType
  | ClientNotificationEventType
  | ChatEventType
  | SignatureEventType
  | PhaseChangedEventType
  | AccompanimentEventType
  | DocumentEventType
  | "heartbeat";

export interface ClientSseEvent {
  type: ClientSseEventType;
  data: {
    // Workflow events (existing)
    template_id?: string;
    primary_actor?: "admin" | "cliente" | "system";
    step_title?: string;
    unblocked_by_template_id?: string;
    estimated_days_to_complete?: number | null;
    blocker_reason?: string;
    // Cloud remediation events (Bloque 3+5)
    gap_id?: string;
    approval_status?: string;
    ens_measure_code?: string;
    severity?: string;
    title?: string;
    audience?: string;
    // Sesión 3B-2B.8 Phase 1A · M01 categorización sync
    system_id?: string;
    system_nombre?: string;
    categoria_resultante?: string;
    determining_dimension?: string;
    aprobado_por?: string;
    fecha_acta?: string | null;
    // Sesión 3B-2B.8 Phase 1B · M02 MAGERIT sync
    analysis_id?: string;
    analysis_name?: string;
    assets_count?: number;
    threats_count?: number;
    safeguards_count?: number;
    frozen_at?: string | null;
    // Sesión 3B-2B.8 Phase 1C · cloud connector lifecycle
    connector_id?: string;
    provider?: string;
    thread_id?: string;
    // Sesión 3B-2B.8 CLUSTER 5 Phase 5C · chat realtime cliente↔admin
    message_id?: string;
    sender_type?: ChatSenderTypeData;
    content_preview?: string;
    created_at?: string;
    // Sesión 3B-2B.8 Phase 1E · M17 plan updated
    task_id?: string;
    task_code?: string;
    task_name?: string;
    status?: string;
    progress_pct?: number;
    // Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central SSE wire
    notification_id?: string;
    client_user_id?: string;
    emitted_by_motor?: string;
    // Ola 3 #14 · phase_changed (payload limpio · sin internals del consultor)
    old_phase?: string | null;
    new_phase?: string | null;
    // FIX P2-3 · gestor documental compartido (document.uploaded)
    document_id?: string;
    nombre?: string;
    source?: "admin" | "cliente";
    interno?: boolean;
    // Common
    _timestamp?: string;
  };
}

interface UseClientProjectEventsOptions {
  enabled?: boolean;
  onStepUnblocked?: (event: ClientSseEvent) => void;
  onStepCompleted?: (event: ClientSseEvent) => void;
  onStepBlocked?: (event: ClientSseEvent) => void;
  // Cloud remediation handlers (Bloque 3+5)
  onCloudRemediationProposed?: (event: ClientSseEvent) => void;
  onCloudRemediationExecuting?: (event: ClientSseEvent) => void;
  onCloudRemediationExecuted?: (event: ClientSseEvent) => void;
  onCloudRemediationFailed?: (event: ClientSseEvent) => void;
  // Sesión 3B-2B.8 Phase 1A + 1B + 1E · cliente sync events admin → cliente
  onM01CategorizacionCompleted?: (event: ClientSseEvent) => void;
  onM02MageritUpdated?: (event: ClientSseEvent) => void;
  onM17PlanUpdated?: (event: ClientSseEvent) => void;
  // Sesión 3B-2B.8 Phase 1C · cloud connector lifecycle
  onCloudConnectorDisconnectRequested?: (event: ClientSseEvent) => void;
  onCloudConnectorConnected?: (event: ClientSseEvent) => void;
  onCloudConnectorDisconnected?: (event: ClientSseEvent) => void;
  onCloudConnectorSyncCompleted?: (event: ClientSseEvent) => void;
  onCloudConnectorError?: (event: ClientSseEvent) => void;
  // Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central wire
  onClientNotificationCreated?: (event: ClientSseEvent) => void;
  // Sesión 3B-2B.8 CLUSTER 5 Phase 5C · chat realtime
  onChatMessageNew?: (event: ClientSseEvent) => void;
  // Ejecutable 7.7 · TIER 1 canvas signing realtime
  onSigningRequested?: (event: ClientSseEvent) => void;
  onSigningSigned?: (event: ClientSseEvent) => void;
  onSigningDeclined?: (event: ClientSseEvent) => void;
  // Ola 3 #14 · phase_changed cliente-facing (transparencia de progreso)
  onPhaseChanged?: (event: ClientSseEvent) => void;
  // FIX P2-3 · gestor documental compartido (documento nuevo en el proyecto)
  onDocumentUploaded?: (event: ClientSseEvent) => void;
  invalidateQueries?: string[][];
}

export function useClientProjectEvents(
  projectId: string | null,
  options: UseClientProjectEventsOptions = {},
) {
  const {
    enabled = true,
    onStepUnblocked,
    onStepCompleted,
    onStepBlocked,
    onCloudRemediationProposed,
    onCloudRemediationExecuting,
    onCloudRemediationExecuted,
    onCloudRemediationFailed,
    onM01CategorizacionCompleted,
    onM02MageritUpdated,
    onM17PlanUpdated,
    onCloudConnectorDisconnectRequested,
    onCloudConnectorConnected,
    onCloudConnectorDisconnected,
    onCloudConnectorSyncCompleted,
    onCloudConnectorError,
    onClientNotificationCreated,
    onChatMessageNew,
    onSigningRequested,
    onSigningSigned,
    onSigningDeclined,
    onPhaseChanged,
    onDocumentUploaded,
    invalidateQueries = [],
  } = options;
  const queryClient = useQueryClient();
  const [lastEvent, setLastEvent] = useState<ClientSseEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !projectId || typeof window === "undefined") return;

    const url = `/api/v1/client-portal/projects/${projectId}/events`;
    const source = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = source;

    const handleEvent = (type: ClientSseEvent["type"]) =>
      (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data) as ClientSseEvent["data"];
          const evt: ClientSseEvent = { type, data };
          setLastEvent(evt);

          if (type === "step_unblocked" && onStepUnblocked) {
            onStepUnblocked(evt);
          } else if (type === "step_completed" && onStepCompleted) {
            onStepCompleted(evt);
          } else if (type === "step_blocked" && onStepBlocked) {
            onStepBlocked(evt);
          } else if (
            type === "cloud_remediation_proposed" &&
            onCloudRemediationProposed
          ) {
            onCloudRemediationProposed(evt);
          } else if (
            type === "cloud_remediation_executing" &&
            onCloudRemediationExecuting
          ) {
            onCloudRemediationExecuting(evt);
          } else if (
            type === "cloud_remediation_executed" &&
            onCloudRemediationExecuted
          ) {
            onCloudRemediationExecuted(evt);
          } else if (
            type === "cloud_remediation_failed" &&
            onCloudRemediationFailed
          ) {
            onCloudRemediationFailed(evt);
          } else if (
            type === "m01.categorizacion.completed" &&
            onM01CategorizacionCompleted
          ) {
            onM01CategorizacionCompleted(evt);
          } else if (
            type === "m02.magerit.updated" &&
            onM02MageritUpdated
          ) {
            onM02MageritUpdated(evt);
          } else if (
            type === "m17.plan.updated" &&
            onM17PlanUpdated
          ) {
            onM17PlanUpdated(evt);
          } else if (
            type === "cloud.connector.disconnect_requested" &&
            onCloudConnectorDisconnectRequested
          ) {
            onCloudConnectorDisconnectRequested(evt);
          } else if (
            type === "cloud.connector.connected" &&
            onCloudConnectorConnected
          ) {
            onCloudConnectorConnected(evt);
          } else if (
            type === "cloud.connector.disconnected" &&
            onCloudConnectorDisconnected
          ) {
            onCloudConnectorDisconnected(evt);
          } else if (
            type === "cloud.connector.sync_completed" &&
            onCloudConnectorSyncCompleted
          ) {
            onCloudConnectorSyncCompleted(evt);
          } else if (
            type === "cloud.connector.error" &&
            onCloudConnectorError
          ) {
            onCloudConnectorError(evt);
          } else if (
            type === "client_notification.created" &&
            onClientNotificationCreated
          ) {
            onClientNotificationCreated(evt);
          } else if (type === "chat_message_new" && onChatMessageNew) {
            onChatMessageNew(evt);
          } else if (type === "signing.requested" && onSigningRequested) {
            onSigningRequested(evt);
          } else if (type === "signing.signed" && onSigningSigned) {
            onSigningSigned(evt);
          } else if (type === "signing.declined" && onSigningDeclined) {
            onSigningDeclined(evt);
          } else if (type === "phase_changed" && onPhaseChanged) {
            onPhaseChanged(evt);
          } else if (type === "document.uploaded" && onDocumentUploaded) {
            onDocumentUploaded(evt);
          }

          // Ejecutable 7.7 · auto-invalidate signing queries (DRY)
          if (
            type === "signing.requested"
            || type === "signing.signed"
            || type === "signing.declined"
          ) {
            queryClient.invalidateQueries({ queryKey: ["pending-signatures"] });
            queryClient.invalidateQueries({ queryKey: ["signing-history"] });
          }

          // Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central
          // SSE wire · auto-invalidate inbox queries (DRY centralizado ·
          // forward-compat ALL VALID_TYPES emitted via emit_client_notification)
          if (type === "client_notification.created") {
            queryClient.invalidateQueries({ queryKey: ["client-inbox"] });
          }

          // Sesión 3B-2B.8 CLUSTER 5 Phase 5C · chat realtime
          // auto-invalidate chat threads + messages queries DRY centralized.
          if (type === "chat_message_new") {
            queryClient.invalidateQueries({ queryKey: ["client-chat"] });
          }

          // Ola 3 #14 · phase_changed · refresca la vista de progreso/fase del
          // cliente (transparencia outcome-as-a-service · "ve su proyecto avanzar").
          if (type === "phase_changed") {
            queryClient.invalidateQueries({ queryKey: ["portal-workflow"] });
            queryClient.invalidateQueries({
              queryKey: ["client-workflow-guide", projectId],
            });
          }

          // Invalidate queries para refresh data
          for (const key of invalidateQueries) {
            queryClient.invalidateQueries({ queryKey: key });
          }
        } catch {
          /* Parse error · best-effort */
        }
      };

    source.addEventListener("step_completed", handleEvent("step_completed"));
    source.addEventListener("step_unblocked", handleEvent("step_unblocked"));
    source.addEventListener("step_blocked", handleEvent("step_blocked"));
    // Ejecutable 7.5 · acompañamiento auditoría/certificación realtime (fix 2026-06-07)
    source.addEventListener(
      "accompaniment.state.advanced",
      handleEvent("accompaniment.state.advanced"),
    );
    source.addEventListener(
      "cloud_remediation_proposed",
      handleEvent("cloud_remediation_proposed"),
    );
    source.addEventListener(
      "cloud_remediation_executing",
      handleEvent("cloud_remediation_executing"),
    );
    source.addEventListener(
      "cloud_remediation_executed",
      handleEvent("cloud_remediation_executed"),
    );
    source.addEventListener(
      "cloud_remediation_failed",
      handleEvent("cloud_remediation_failed"),
    );
    // Sesión 3B-2B.8 Phase 1A · cliente sync admin → cliente
    source.addEventListener(
      "m01.categorizacion.completed",
      handleEvent("m01.categorizacion.completed"),
    );
    // Sesión 3B-2B.8 Phase 1B · M02 MAGERIT sync admin → cliente
    source.addEventListener(
      "m02.magerit.updated",
      handleEvent("m02.magerit.updated"),
    );
    // Sesión 3B-2B.8 Phase 1E · M17 plan task updated admin → cliente
    source.addEventListener(
      "m17.plan.updated",
      handleEvent("m17.plan.updated"),
    );
    // Sesión 3B-2B.8 Phase 1C · cloud connector lifecycle
    source.addEventListener(
      "cloud.connector.disconnect_requested",
      handleEvent("cloud.connector.disconnect_requested"),
    );
    source.addEventListener(
      "cloud.connector.connected",
      handleEvent("cloud.connector.connected"),
    );
    source.addEventListener(
      "cloud.connector.disconnected",
      handleEvent("cloud.connector.disconnected"),
    );
    source.addEventListener(
      "cloud.connector.sync_completed",
      handleEvent("cloud.connector.sync_completed"),
    );
    source.addEventListener(
      "cloud.connector.error",
      handleEvent("cloud.connector.error"),
    );
    // Sesión 3B-2B.8 CLUSTER 2 Phase 2D · ClientNotification central SSE wire
    source.addEventListener(
      "client_notification.created",
      handleEvent("client_notification.created"),
    );
    // Sesión 3B-2B.8 CLUSTER 5 Phase 5C · chat realtime cliente↔admin
    source.addEventListener(
      "chat_message_new",
      handleEvent("chat_message_new"),
    );
    // Ejecutable 7.7 · TIER 1 canvas signing events realtime
    source.addEventListener(
      "signing.requested",
      handleEvent("signing.requested"),
    );
    source.addEventListener(
      "signing.signed",
      handleEvent("signing.signed"),
    );
    source.addEventListener(
      "signing.declined",
      handleEvent("signing.declined"),
    );
    // Ola 3 #14 · phase_changed cliente-facing (transparencia de progreso)
    source.addEventListener(
      "phase_changed",
      handleEvent("phase_changed"),
    );
    // FIX P2-3 · gestor documental compartido (documento nuevo en el proyecto)
    source.addEventListener(
      "document.uploaded",
      handleEvent("document.uploaded"),
    );

    source.onerror = () => {
      // EventSource auto-reconnects · solo log si necesario debugging
    };

    return () => {
      source.close();
      eventSourceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, enabled]);

  return { lastEvent };
}
