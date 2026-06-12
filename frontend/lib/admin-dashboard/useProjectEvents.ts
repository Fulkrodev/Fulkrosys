"use client";

/**
 * useProjectEvents · hook SSE → TanStack Query invalidation (MB-13.3 · ADR-035).
 *
 * Conecta a ``GET /api/v1/projects/{id}/events`` vía EventSource browser API
 * y dispara invalidate queries (admin-dashboard / readiness / alerts) cuando
 * el backend dispatcha eventos:
 *   - readiness_changed → invalida ["admin-dashboard", projectId]
 *   - phase_changed     → invalida ["admin-dashboard"], ["workflow"], etc
 *   - alert_new         → invalida ["alerts", "active"], ["alerts", projectId]
 *
 * Browser auto-reconnect en EventSource on error · sin retry custom.
 * Si el backend reinicia, EventSource intentará reconnectar 3-5s después.
 */
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

/** Ola 3 #12 · payload enriquecido de los eventos de firma (cliente → admin). */
export interface SigningEventData {
  intent_id?: string;
  signable_type?: string;
  signable_label?: string;
  signable_ref_id?: string | null;
  signable_ref_type?: string | null;
  contract_id?: string;
  plantilla_id?: string | null;
  signer_name?: string;
  primary_actor?: string;
  project_id?: string;
  signed_at?: string;
  event_hash_sha256?: string;
  reason?: string;
}

interface UseProjectEventsOptions {
  projectId: string;
  enabled?: boolean;
  onPhaseChanged?: (newPhase: string) => void;
  onReadinessChanged?: () => void;
  onAlertNew?: () => void;
  // Ola 3 #12 · el admin ve la firma del cliente en realtime
  onSigningSigned?: (data: SigningEventData) => void;
  onSigningDeclined?: (data: SigningEventData) => void;
  // FIX P2-3 · el admin ve en realtime el documento que el cliente comparte
  onDocumentUploaded?: () => void;
  // feat/fulkro-100 Ola A · el admin ve en realtime cuando el cliente rellena el
  // cuestionario de continuidad o aprueba/comenta un borrador BIA/DRP.
  onContinuidadChanged?: () => void;
}

export function useProjectEvents({
  projectId,
  enabled = true,
  onPhaseChanged,
  onReadinessChanged,
  onAlertNew,
  onSigningSigned,
  onSigningDeclined,
  onDocumentUploaded,
  onContinuidadChanged,
}: UseProjectEventsOptions): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || !projectId || typeof window === "undefined") {
      return;
    }

    const url = `/api/v1/projects/${projectId}/events`;
    const eventSource = new EventSource(url, { withCredentials: true });

    const handleReadinessChanged = () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-dashboard", projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["readiness", projectId],
      });
      onReadinessChanged?.();
    };

    const handlePhaseChanged = (e: MessageEvent) => {
      let newPhase = "";
      try {
        const parsed = JSON.parse(e.data);
        newPhase = parsed.new_phase ?? "";
      } catch {
        // ignore malformed
      }
      queryClient.invalidateQueries({
        queryKey: ["admin-dashboard", projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workflow", projectId],
      });
      onPhaseChanged?.(newPhase);
    };

    const handleAlertNew = () => {
      queryClient.invalidateQueries({ queryKey: ["alerts", "active"] });
      queryClient.invalidateQueries({
        queryKey: ["alerts", projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin-dashboard", projectId],
      });
      onAlertNew?.();
    };

    const handleHeartbeat = () => {
      // connection alive · no-op
    };

    // Ola 3 #12 · el admin VE la firma del cliente en realtime (la firma es el
    // motor de avance). Toast legible "{firmante} firmó {documento}" + refresh.
    const parseSigning = (e: MessageEvent): SigningEventData => {
      try {
        return JSON.parse(e.data) as SigningEventData;
      } catch {
        return {};
      }
    };

    const refreshOnSigning = () => {
      queryClient.invalidateQueries({
        queryKey: ["admin-dashboard", projectId],
      });
      queryClient.invalidateQueries({ queryKey: ["workflow", projectId] });
    };

    const handleSigningSigned = (e: MessageEvent) => {
      const data = parseSigning(e);
      const who = data.signer_name ?? "El cliente";
      const what = data.signable_label ?? "un documento";
      const ref = data.plantilla_id ? ` ${data.plantilla_id}` : "";
      toast.success(`${who} firmó ${what}${ref}`);
      refreshOnSigning();
      onSigningSigned?.(data);
    };

    const handleSigningDeclined = (e: MessageEvent) => {
      const data = parseSigning(e);
      const who = data.signer_name ?? "El cliente";
      const what = data.signable_label ?? "un documento";
      toast.warning(`${who} rechazó ${what}`);
      refreshOnSigning();
      onSigningDeclined?.(data);
    };

    // FIX P2-3 · gestor documental compartido · refresca cuando el cliente sube
    const handleDocumentUploaded = () => {
      onDocumentUploaded?.();
    };

    // Ola A · buzón de continuidad · refresca cuando el cliente actúa
    const handleContinuidadChanged = () => {
      onContinuidadChanged?.();
    };

    eventSource.addEventListener("readiness_changed", handleReadinessChanged);
    eventSource.addEventListener("phase_changed", handlePhaseChanged);
    eventSource.addEventListener("alert_new", handleAlertNew);
    eventSource.addEventListener("heartbeat", handleHeartbeat);
    eventSource.addEventListener("signing.signed", handleSigningSigned);
    eventSource.addEventListener("signing.declined", handleSigningDeclined);
    eventSource.addEventListener("document.uploaded", handleDocumentUploaded);
    eventSource.addEventListener(
      "continuidad.questionnaire.submitted",
      handleContinuidadChanged,
    );
    eventSource.addEventListener(
      "continuidad.draft.approved",
      handleContinuidadChanged,
    );
    eventSource.addEventListener(
      "continuidad.draft.comment",
      handleContinuidadChanged,
    );

    eventSource.onerror = () => {
      // Browser auto-reconnects · just log
      // eslint-disable-next-line no-console
      console.debug(
        "SSE connection error · browser auto-reconnects",
        projectId,
      );
    };

    return () => {
      eventSource.removeEventListener(
        "readiness_changed",
        handleReadinessChanged,
      );
      eventSource.removeEventListener("phase_changed", handlePhaseChanged);
      eventSource.removeEventListener("alert_new", handleAlertNew);
      eventSource.removeEventListener("heartbeat", handleHeartbeat);
      eventSource.removeEventListener("signing.signed", handleSigningSigned);
      eventSource.removeEventListener(
        "signing.declined",
        handleSigningDeclined,
      );
      eventSource.removeEventListener(
        "document.uploaded",
        handleDocumentUploaded,
      );
      eventSource.removeEventListener(
        "continuidad.questionnaire.submitted",
        handleContinuidadChanged,
      );
      eventSource.removeEventListener(
        "continuidad.draft.approved",
        handleContinuidadChanged,
      );
      eventSource.removeEventListener(
        "continuidad.draft.comment",
        handleContinuidadChanged,
      );
      eventSource.close();
    };
  }, [
    projectId,
    enabled,
    queryClient,
    onPhaseChanged,
    onReadinessChanged,
    onAlertNew,
    onSigningSigned,
    onSigningDeclined,
    onDocumentUploaded,
    onContinuidadChanged,
  ]);
}
