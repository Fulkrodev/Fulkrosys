"use client";

/**
 * Hook policies cliente · SAN-E v3.MB-6 atom 1.
 *
 * Carga summary tier + 25 policies + acción review individual + bulk-hash
 * pre-firma. Pattern useState + useEffect alineado cliente-portal (no TanStack).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type PolicyClientView,
  type PolicyReviewAction,
  type PolicySummary,
  getPoliciesSummary,
  listClientPolicies,
  reviewClientPolicy,
} from "@/lib/api/policies";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UsePoliciesClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  summary: PolicySummary | null;
  policies: PolicyClientView[];
  reviewPolicy: (
    documentId: string,
    action: PolicyReviewAction,
    note?: string,
  ) => Promise<void>;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
  nombre?: string;
}

export function usePoliciesClient(): UsePoliciesClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [summary, setSummary] = useState<PolicySummary | null>(null);
  const [policies, setPolicies] = useState<PolicyClientView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (pid: string) => {
    try {
      const [s, p] = await Promise.all([
        getPoliciesSummary(pid),
        listClientPolicies(pid),
      ]);
      setSummary(s);
      setPolicies(p);
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Error cargando políticas");
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
        await fetchAll(proj.id);
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

  const reviewPolicy = useCallback(
    async (documentId: string, action: PolicyReviewAction, note?: string) => {
      if (!projectId) return;
      try {
        await reviewClientPolicy(documentId, action, note);
        await fetchAll(projectId);
      } catch (err) {
        if (err instanceof ClientApiError) {
          setError(err.message);
        } else {
          setError("Error guardando review");
        }
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
    summary,
    policies,
    reviewPolicy,
    refetch,
  };
}
