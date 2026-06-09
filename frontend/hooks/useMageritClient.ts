"use client";

/**
 * Hook MAGERIT cliente in-portal · SAN-E v3.MB-5.4.
 *
 * Carga summary + list assets para el project del cliente · expose review
 * action persistente. Pattern alineado useDdaClient · useState+useEffect
 * (NO TanStack Query · client-portal style).
 */
import { useCallback, useEffect, useState } from "react";

import {
  type AssetReviewAction,
  type AssetReviewStatus,
  type MageritAssetClientView,
  type MageritClientSummary,
  type MageritRiskClientView,
  type MageritSeverity,
  getMageritClientSummary,
  listMageritClientAssets,
  listMageritClientRisks,
  reviewMageritClientAsset,
  reviewMageritClientRisk,
} from "@/lib/api/magerit";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";


interface ProjectInfo {
  id: string;
  nombre?: string;
  categoria_objetivo?: string | null;
}


interface UseMageritClientResult {
  loading: boolean;
  error: string | null;
  projectId: string | null;
  summary: MageritClientSummary | null;
  assets: MageritAssetClientView[];
  risks: MageritRiskClientView[];
  reviewFilter: AssetReviewStatus | "all";
  setReviewFilter: (s: AssetReviewStatus | "all") => void;
  typeFilter: string | "all";
  setTypeFilter: (t: string | "all") => void;
  severityFilter: MageritSeverity | "all";
  setSeverityFilter: (s: MageritSeverity | "all") => void;
  refetch: () => Promise<void>;
  reviewAsset: (
    assetId: string,
    action: AssetReviewAction,
    note?: string,
  ) => Promise<void>;
  reviewRisk: (
    riskId: string,
    action: AssetReviewAction,
    note?: string,
  ) => Promise<void>;
}


export function useMageritClient(): UseMageritClientResult {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [summary, setSummary] = useState<MageritClientSummary | null>(null);
  const [assets, setAssets] = useState<MageritAssetClientView[]>([]);
  const [risks, setRisks] = useState<MageritRiskClientView[]>([]);
  const [reviewFilter, setReviewFilter] = useState<
    AssetReviewStatus | "all"
  >("all");
  const [typeFilter, setTypeFilter] = useState<string | "all">("all");
  const [severityFilter, setSeverityFilter] = useState<
    MageritSeverity | "all"
  >("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(
    async (
      pid: string,
      review: AssetReviewStatus | "all",
      type: string | "all",
      severity: MageritSeverity | "all",
    ) => {
      try {
        const assetFilters: {
          asset_type?: string;
          review_status?: AssetReviewStatus;
        } = {};
        if (type !== "all") assetFilters.asset_type = type;
        if (review !== "all") assetFilters.review_status = review;

        const riskFilters: {
          severity?: MageritSeverity;
          review_status?: AssetReviewStatus;
        } = {};
        if (severity !== "all") riskFilters.severity = severity;
        if (review !== "all") riskFilters.review_status = review;

        const [s, a, r] = await Promise.all([
          getMageritClientSummary(pid),
          listMageritClientAssets(pid, assetFilters),
          listMageritClientRisks(pid, riskFilters),
        ]);
        setSummary(s);
        setAssets(a);
        setRisks(r);
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error cargando MAGERIT");
      }
    },
    [],
  );

  // Initial load · resolve project_id
  useEffect(() => {
    let cancelled = false;
    async function init() {
      setLoading(true);
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        setProjectId(proj.id);
        await fetchAll(proj.id, reviewFilter, typeFilter, severityFilter);
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

  // Refetch on filter change
  useEffect(() => {
    if (!projectId) return;
    void fetchAll(projectId, reviewFilter, typeFilter, severityFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewFilter, typeFilter, severityFilter, projectId]);

  const refetch = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    await fetchAll(projectId, reviewFilter, typeFilter, severityFilter);
  }, [projectId, reviewFilter, typeFilter, severityFilter, fetchAll]);

  const reviewAsset = useCallback(
    async (
      assetId: string,
      action: AssetReviewAction,
      note?: string,
    ) => {
      try {
        await reviewMageritClientAsset(assetId, action, note);
        await refetch();
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error guardando review");
      }
    },
    [refetch],
  );

  const reviewRisk = useCallback(
    async (riskId: string, action: AssetReviewAction, note?: string) => {
      try {
        await reviewMageritClientRisk(riskId, action, note);
        await refetch();
      } catch (err) {
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error guardando review riesgo");
      }
    },
    [refetch],
  );

  return {
    loading,
    error,
    projectId,
    summary,
    assets,
    risks,
    reviewFilter,
    setReviewFilter,
    typeFilter,
    setTypeFilter,
    severityFilter,
    setSeverityFilter,
    refetch,
    reviewAsset,
    reviewRisk,
  };
}
