"use client";

/**
 * Hook firmas hub cliente · SAN-E v3.MB-6 atom 0.2.
 *
 * Carga history project (4 cards per signable_type operativo) + chain integrity
 * status + readiness_snapshot post-conformidad. Pattern useState + useEffect
 * alineado con resto cliente-portal hooks (no TanStack Query).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type SigningHistoryClientResponse,
  getClientSigningHistory,
} from "@/lib/api/signing-history";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseSigningHistoryClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  history: SigningHistoryClientResponse | null;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
  nombre?: string;
}

export function useSigningHistoryClient(): UseSigningHistoryClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [history, setHistory] = useState<SigningHistoryClientResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async (pid: string) => {
    try {
      const h = await getClientSigningHistory(pid);
      setHistory(h);
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Error cargando historial de firmas");
      }
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
        await fetchHistory(proj.id);
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ClientApiError) {
            setError(err.message);
          } else {
            setError("No se pudo resolver el proyecto del cliente");
          }
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

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchHistory(projectId);
  }, [projectId, fetchHistory]);

  return {
    loading,
    error,
    projectId,
    history,
    refetch,
  };
}
