"use client";

import * as React from "react";

import {
  cancelMeeting as apiCancelMeeting,
  completeMeeting as apiCompleteMeeting,
  getMeeting,
  postMeetingAction as apiPostAction,
  updateMeeting as apiUpdateMeeting,
} from "@/lib/admin-meetings/api";
import type {
  MeetingCancel,
  MeetingComplete,
  MeetingDetail,
  MeetingPostActionRequest,
  MeetingPostActionResponse,
  MeetingUpdate,
} from "@/lib/admin-meetings/schemas";

/**
 * useMeeting — hook real backend para detalle meeting (FASE 7.B.2 + B10).
 *
 * Sustituyó `useMeetingSession` legacy mock-driven (sprint4-mock) en
 * sub-bloque 7.B.10 cleanup. Componentes meeting refactor completos
 * en components/admin-meetings/* — legacy components/meeting/* eliminado.
 *
 * sprint4-mock.ts / sprint4-types.ts SE MANTIENEN (consumers fuera scope
 * FASE 7: copilot, public portals, audit, magic-links). Los tipos
 * `MeetingSession`/`MeetingLiveOutput`/funciones `mockMeeting` quedan
 * como dead code en esos archivos pero no rompen runtime — limpieza
 * opcional S13.
 *
 * Estados gestionados:
 *   - meeting (MeetingDetail | null) — fetched on mount
 *   - loading / error
 *   - savingNotes (boolean autosave indicator)
 *   - savedAt (timestamp last successful save)
 *
 * Métodos:
 *   - reload() — re-fetch detail (post-action / status transition)
 *   - patchMeeting(payload) — PATCH partial pre-completion
 *   - complete(payload) — workflow transition + auto-log M30 backend
 *   - cancel(payload) — idempotente
 *   - postAction(payload) — 4 cross-motor handlers
 */
export interface UseMeetingResult {
  meeting: MeetingDetail | null;
  loading: boolean;
  error: string | null;
  savingNotes: boolean;
  savedAt: Date | null;
  reload: () => Promise<void>;
  patchMeeting: (payload: MeetingUpdate) => Promise<void>;
  complete: (payload: MeetingComplete) => Promise<void>;
  cancel: (payload?: MeetingCancel) => Promise<void>;
  postAction: (
    payload: MeetingPostActionRequest,
  ) => Promise<MeetingPostActionResponse>;
}

export function useMeeting(meetingId: string): UseMeetingResult {
  const [meeting, setMeeting] = React.useState<MeetingDetail | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [savingNotes] = React.useState(false);
  const [savedAt, setSavedAt] = React.useState<Date | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMeeting(meetingId);
      setMeeting(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando reunión");
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  const patchMeeting = React.useCallback(
    async (payload: MeetingUpdate) => {
      try {
        const updated = await apiUpdateMeeting(meetingId, payload);
        setMeeting(updated);
        setSavedAt(new Date());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error guardando cambios");
        throw e;
      }
    },
    [meetingId],
  );

  const complete = React.useCallback(
    async (payload: MeetingComplete) => {
      try {
        const updated = await apiCompleteMeeting(meetingId, payload);
        setMeeting(updated);
        setSavedAt(new Date());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error completando reunión");
        throw e;
      }
    },
    [meetingId],
  );

  const cancel = React.useCallback(
    async (payload: MeetingCancel = {}) => {
      try {
        const updated = await apiCancelMeeting(meetingId, payload);
        setMeeting(updated);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error cancelando reunión");
        throw e;
      }
    },
    [meetingId],
  );

  const postAction = React.useCallback(
    async (payload: MeetingPostActionRequest) => {
      const response = await apiPostAction(meetingId, payload);
      await reload();
      return response;
    },
    [meetingId, reload],
  );

  return {
    meeting,
    loading,
    error,
    savingNotes,
    savedAt,
    reload,
    patchMeeting,
    complete,
    cancel,
    postAction,
  };
}
