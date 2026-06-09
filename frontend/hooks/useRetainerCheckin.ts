"use client";

/**
 * Hook retainer checkin cliente · SAN-E v3.MB-6 atom 4.
 *
 * Consideration A · separated de `useRetainer.ts` existing (admin TanStack RQ) ·
 * cliente checkin usa useState pattern coherente atoms 0.2/1/2/3.
 */
import { useCallback, useEffect, useState } from "react";

import {
  type CheckinReviewAction,
  type RetainerCheckin,
  listClientCheckins,
  reviewCheckin,
} from "@/lib/api/retainer-checkin";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseRetainerCheckinResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  checkins: RetainerCheckin[];
  reviewCheckinAction: (
    reportId: string,
    action: CheckinReviewAction,
    note?: string,
  ) => Promise<void>;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
}

export function useRetainerCheckin(): UseRetainerCheckinResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [checkins, setCheckins] = useState<RetainerCheckin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (pid: string) => {
    try {
      const list = await listClientCheckins(pid);
      setCheckins(list);
    } catch (err) {
      if (err instanceof ClientApiError) setError(err.message);
      else setError("Error cargando comités retainer");
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

  const reviewCheckinAction = useCallback(
    async (
      reportId: string,
      action: CheckinReviewAction,
      note?: string,
    ) => {
      if (!projectId) return;
      try {
        await reviewCheckin(reportId, action, note);
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
    checkins,
    reviewCheckinAction,
    refetch,
  };
}
