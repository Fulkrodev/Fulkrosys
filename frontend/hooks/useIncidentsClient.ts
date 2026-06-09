"use client";

/**
 * Hook incidents cliente · SAN-E v3.MB-6 atom 3.
 *
 * Carga lista incidents visible (resolved + closed) + review action + close signoff.
 * Pattern useState alineado cliente-portal.
 */
import { useCallback, useEffect, useState } from "react";

import {
  type IncidentClient,
  type IncidentReviewAction,
  listClientIncidents,
  reviewIncident,
} from "@/lib/api/incidents";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseIncidentsClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  incidents: IncidentClient[];
  reviewIncidentAction: (
    incidentId: string,
    action: IncidentReviewAction,
    note?: string,
  ) => Promise<void>;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
}

export function useIncidentsClient(): UseIncidentsClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<IncidentClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (pid: string) => {
    try {
      const list = await listClientIncidents(pid);
      setIncidents(list);
    } catch (err) {
      if (err instanceof ClientApiError) setError(err.message);
      else setError("Error cargando incidents");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      setLoading(true);
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        setProjectId(proj.id);
        await fetchAll(proj.id);
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ClientApiError) setError(err.message);
          else setError("No se pudo resolver el proyecto del cliente");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reviewIncidentAction = useCallback(
    async (
      incidentId: string,
      action: IncidentReviewAction,
      note?: string,
    ) => {
      if (!projectId) return;
      try {
        await reviewIncident(incidentId, action, note);
        await fetchAll(projectId);
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error guardando review");
        throw err;
      }
    },
    [projectId, fetchAll],
  );

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchAll(projectId);
  }, [projectId, fetchAll]);

  return {
    loading,
    error,
    projectId,
    incidents,
    reviewIncidentAction,
    refetch,
  };
}
