"use client";

/**
 * Hook actas cliente · SAN-E v3.MB-6 atom 5.
 *
 * useState pattern (consistent atoms 0.2/1/2/3/4 cliente portal).
 * Soporta filter chip subtype (sub-Q3 cement).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type ActaClientView,
  type ActaReviewAction,
  type ActaSubtype,
  listClientActas,
  reviewActa,
} from "@/lib/api/actas";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseActasClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  actas: ActaClientView[];
  subtypeFilter: ActaSubtype | null;
  setSubtypeFilter: (subtype: ActaSubtype | null) => void;
  reviewActaAction: (
    meetingId: string,
    action: ActaReviewAction,
    note?: string,
  ) => Promise<void>;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
}

export function useActasClient(): UseActasClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [actas, setActas] = useState<ActaClientView[]>([]);
  const [subtypeFilter, setSubtypeFilterState] = useState<ActaSubtype | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(
    async (pid: string, subtype: ActaSubtype | null) => {
      try {
        const list = await listClientActas(pid, subtype ?? undefined);
        setActas(list);
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error cargando actas");
      }
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    async function init() {
      setLoading(true);
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        setProjectId(proj.id);
        await fetchAll(proj.id, null);
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

  const setSubtypeFilter = useCallback(
    (subtype: ActaSubtype | null) => {
      setSubtypeFilterState(subtype);
      if (projectId) void fetchAll(projectId, subtype);
    },
    [projectId, fetchAll],
  );

  const reviewActaAction = useCallback(
    async (
      meetingId: string,
      action: ActaReviewAction,
      note?: string,
    ) => {
      if (!projectId) return;
      try {
        await reviewActa(meetingId, action, note);
        await fetchAll(projectId, subtypeFilter);
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error guardando review");
        throw err;
      }
    },
    [projectId, subtypeFilter, fetchAll],
  );

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchAll(projectId, subtypeFilter);
  }, [projectId, subtypeFilter, fetchAll]);

  return {
    loading,
    error,
    projectId,
    actas,
    subtypeFilter,
    setSubtypeFilter,
    reviewActaAction,
    refetch,
  };
}
