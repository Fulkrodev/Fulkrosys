"use client";

/**
 * Hook DdA cliente in-portal · SAN-E v3.MB-5.3.
 *
 * Carga summary + list de medidas para el project del cliente · expone
 * acciones review (revisada_ok · con_pregunta · suggest_change) que
 * persisten via POST /portal/dda/entries/{id}/review y refrescan.
 *
 * Pattern alineado con dashboard cliente: useState + useEffect ·
 * cero TanStack Query (client-portal style).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type DdaClientEntryView,
  type DdaClientReviewAction,
  type DdaClientSummary,
  type DdaFamily,
  getClientDdaSummary,
  listClientDdaMeasures,
  reviewClientDdaEntry,
} from "@/lib/api/dda";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseDdaClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  summary: DdaClientSummary | null;
  entries: DdaClientEntryView[];
  familyFilter: DdaFamily | "all";
  setFamilyFilter: (f: DdaFamily | "all") => void;
  refetch: () => Promise<void>;
  reviewEntry: (
    entryId: string,
    action: DdaClientReviewAction,
    note?: string,
  ) => Promise<void>;
}

interface ProjectInfo {
  id: string;
  nombre?: string;
  categoria_objetivo?: string | null;
}

export function useDdaClient(): UseDdaClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [summary, setSummary] = useState<DdaClientSummary | null>(null);
  const [entries, setEntries] = useState<DdaClientEntryView[]>([]);
  const [familyFilter, setFamilyFilter] = useState<DdaFamily | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(
    async (pid: string, filter: DdaFamily | "all") => {
      try {
        const [s, e] = await Promise.all([
          getClientDdaSummary(pid),
          listClientDdaMeasures(
            pid,
            filter === "all" ? undefined : { family: filter },
          ),
        ]);
        setSummary(s);
        setEntries(e);
      } catch (err) {
        if (err instanceof ClientApiError) {
          setError(err.message);
        } else {
          setError("Error cargando DdA");
        }
      }
    },
    [],
  );

  // Initial load · resolve project_id from /client-portal/project
  useEffect(() => {
    let cancelled = false;
    async function init() {
      setLoading(true);
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        setProjectId(proj.id);
        await fetchAll(proj.id, familyFilter);
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

  // Refetch on filter change
  useEffect(() => {
    if (!projectId) return;
    void fetchAll(projectId, familyFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyFilter, projectId]);

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchAll(projectId, familyFilter);
  }, [projectId, familyFilter, fetchAll]);

  const reviewEntry = useCallback(
    async (
      entryId: string,
      action: DdaClientReviewAction,
      note?: string,
    ) => {
      try {
        await reviewClientDdaEntry(entryId, action, note);
        await refetch();
      } catch (err) {
        if (err instanceof ClientApiError) {
          setError(err.message);
        } else {
          setError("Error guardando review");
        }
      }
    },
    [refetch],
  );

  return {
    loading,
    error,
    projectId,
    summary,
    entries,
    familyFilter,
    setFamilyFilter,
    refetch,
    reviewEntry,
  };
}
