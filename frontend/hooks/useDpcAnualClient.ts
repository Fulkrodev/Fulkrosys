"use client";

/**
 * Hook DPC anual cliente · SAN-E v3.MB-6 atom 2.
 *
 * Carga lista declarations (current + history) + detail expand 4 secciones contexto.
 * Pattern useState + useEffect alineado cliente-portal (no TanStack).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type DpcContextDetail,
  type DpcDeclaration,
  type DpcReviewAction,
  getDpcDeclarationDetail,
  listDpcDeclarations,
  reviewDpcDeclaration,
} from "@/lib/api/dpc-anual";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface UseDpcAnualClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  declarations: DpcDeclaration[];
  currentDeclaration: DpcDeclaration | null;  // first unsigned
  currentDetail: DpcContextDetail | null;
  reviewDeclaration: (
    declarationId: string,
    action: DpcReviewAction,
    note?: string,
  ) => Promise<void>;
  refetch: () => Promise<void>;
}

interface ProjectInfo {
  id: string;
}

export function useDpcAnualClient(): UseDpcAnualClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [declarations, setDeclarations] = useState<DpcDeclaration[]>([]);
  const [currentDeclaration, setCurrentDeclaration] =
    useState<DpcDeclaration | null>(null);
  const [currentDetail, setCurrentDetail] = useState<DpcContextDetail | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (pid: string) => {
    try {
      const list = await listDpcDeclarations(pid);
      setDeclarations(list);
      // current = primera sin firmar (status='draft') · ordered DESC year en backend
      const current = list.find((d) => d.status !== "signed") ?? null;
      setCurrentDeclaration(current);
      if (current) {
        const detail = await getDpcDeclarationDetail(current.id);
        setCurrentDetail(detail);
      } else {
        setCurrentDetail(null);
      }
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Error cargando DPC anual");
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

  const reviewDeclaration = useCallback(
    async (declarationId: string, action: DpcReviewAction, note?: string) => {
      if (!projectId) return;
      try {
        await reviewDpcDeclaration(declarationId, action, note);
        await fetchAll(projectId);
      } catch (err) {
        if (err instanceof ClientApiError) {
          setError(err.message);
        } else {
          setError("Error guardando review DPC");
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
    declarations,
    currentDeclaration,
    currentDetail,
    reviewDeclaration,
    refetch,
  };
}
