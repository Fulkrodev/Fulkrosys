"use client";

/**
 * Hook Conformidad ENS cliente in-portal · SAN-E v3.MB-5.6.
 *
 * Carga declaration + readiness (parallel) · expose markReviewed action.
 * Pattern alineado usePentestAuthClient / useMageritClient (single-object).
 *
 * Tier-aware: declaration.tier + declaration.declaration_type controlan UX.
 */
import { useCallback, useEffect, useState } from "react";

import {
  type ConformidadDeclarationClientView,
  type ConformityReadinessView,
  getConformidadDeclaration,
  getConformidadReadiness,
  markConformidadReviewed,
} from "@/lib/api/conformidad";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";


interface ProjectInfo {
  id: string;
  nombre?: string;
}


interface UseConformidadClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  declaration: ConformidadDeclarationClientView | null;
  readiness: ConformityReadinessView | null;
  notFound: boolean;
  refetch: () => Promise<void>;
  markReviewed: (concernsNote?: string) => Promise<void>;
}


export function useConformidadClient(): UseConformidadClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [declaration, setDeclaration] =
    useState<ConformidadDeclarationClientView | null>(null);
  const [readiness, setReadiness] = useState<ConformityReadinessView | null>(
    null,
  );
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async (pid: string) => {
    try {
      // Readiness siempre disponible · declaration puede 404 si admin NO ha preparado draft
      const readinessRes = await getConformidadReadiness(pid);
      setReadiness(readinessRes);

      try {
        const decl = await getConformidadDeclaration(pid);
        setDeclaration(decl);
        setNotFound(false);
      } catch (declErr) {
        if (declErr instanceof ClientApiError && declErr.status === 404) {
          setNotFound(true);
          setDeclaration(null);
        } else {
          throw declErr;
        }
      }
    } catch (err) {
      if (err instanceof ClientApiError) setError(err.message);
      else setError("Error cargando conformidad");
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

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchAll(projectId);
  }, [projectId, fetchAll]);

  const markReviewed = useCallback(
    async (concernsNote?: string) => {
      if (!projectId) return;
      try {
        const updated = await markConformidadReviewed(projectId, concernsNote);
        setDeclaration(updated);
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error guardando revisión");
      }
    },
    [projectId],
  );

  return {
    loading,
    error,
    projectId,
    declaration,
    readiness,
    notFound,
    refetch,
    markReviewed,
  };
}
