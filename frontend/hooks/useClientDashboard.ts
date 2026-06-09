"use client";

/**
 * useClientDashboard · MB-7 atom 7.1 plan v6.
 *
 * Polls GET /api/v1/client-portal/dashboard/adaptive every 30s.
 * Mirrors useState pattern of other client portal hooks (no SWR/react-query
 * dependency to stay consistent with siblings: useActasClient,
 * useDdaClient, etc.).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  type AdaptiveDashboardResponse,
  fetchAdaptiveDashboard,
} from "@/lib/api/dashboard";
import { ClientApiError } from "@/lib/client-portal-api";

interface UseClientDashboardResult {
  loading: boolean;
  error: string | null;
  data: AdaptiveDashboardResponse | null;
  refetch: () => Promise<void>;
}

const POLL_INTERVAL_MS = 30_000;

export function useClientDashboard(): UseClientDashboardResult {
  const [data, setData] = useState<AdaptiveDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const resp = await fetchAdaptiveDashboard();
      if (!cancelledRef.current) {
        setData(resp);
        setError(null);
      }
    } catch (err) {
      if (cancelledRef.current) return;
      if (err instanceof ClientApiError) setError(err.message);
      else setError("Error cargando dashboard");
    } finally {
      if (!cancelledRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    void load();
    const id = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    const onFocus = () => void load();
    window.addEventListener("focus", onFocus);
    return () => {
      cancelledRef.current = true;
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [load]);

  const refetch = useCallback(async () => {
    setError(null);
    await load();
  }, [load]);

  return { loading, error, data, refetch };
}
