"use client";

/**
 * Hook AI Act art.50 transparency log cliente · sub-atom 1.E.1.B.2.
 *
 * Fetch wrapper sobre /client-portal/transparency/log endpoint.
 * R29 firmísimo · NO presión · empty state friendly · error message
 * suave (NO destructive · NO red por defecto).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type ClientTransparencyEvent,
  type ClientTransparencyLogResponse,
  getClientTransparencyLog,
} from "@/lib/api/transparency-client";
import { ClientApiError } from "@/lib/client-portal-api";

interface UseClientTransparencyLogResult {
  loading: boolean;
  error: string | null;
  clientId: string | null;
  items: ClientTransparencyEvent[];
  total: number;
  days: number;
  refetch: () => Promise<void>;
}

export function useClientTransparencyLog(
  days: number = 180,
): UseClientTransparencyLogResult {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ClientTransparencyLogResponse | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getClientTransparencyLog(days);
      setData(response);
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("No pudimos cargar el registro de transparencia.");
      }
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return {
    loading,
    error,
    clientId: data?.client_id ?? null,
    items: data?.items ?? [],
    total: data?.total ?? 0,
    days: data?.days ?? days,
    refetch,
  };
}
