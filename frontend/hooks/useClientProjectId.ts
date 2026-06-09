"use client";

/**
 * Resolve current cliente project_id once · sub-atom 1.C.B fase 4b helper.
 *
 * Patron presente en useIncidentsClient · useConformidadClient · usePoliciesClient
 * extraido como hook reusable. Backend endpoint ``/api/v1/client-portal/project``
 * devuelve el project_id asociado al ClientUser autenticado (via cookie sesion).
 */
import { useEffect, useState } from "react";

import { ClientApiError, clientApi } from "@/lib/client-portal-api";


interface ProjectInfo {
  id: string;
}


export interface UseClientProjectIdResult {
  projectId: string | null;
  loading: boolean;
  error: string | null;
}


export function useClientProjectId(): UseClientProjectIdResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (!cancelled) setProjectId(proj.id);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ClientApiError) setError(err.message);
        else setError("No se pudo resolver el proyecto del cliente");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { projectId, loading, error };
}
