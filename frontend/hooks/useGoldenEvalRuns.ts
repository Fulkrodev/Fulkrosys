"use client";

/**
 * Hook golden eval runs admin · sub-atom 1.E.1.B.3.E.
 *
 * useState pattern · auto-refresh para datasets list + runs history.
 * Reuse pattern useTransparencyLog · admin observability convention.
 */
import { useCallback, useEffect, useState } from "react";

import {
  type AvailableDataset,
  type GoldenEvalRunDetail,
  type GoldenEvalRunsListResponse,
  type TriggerEvalRunPayload,
  listAvailableDatasets,
  listEvalRuns,
  triggerEvalRun,
} from "@/lib/api/golden-eval-admin";
import { ApiError } from "@/lib/api";

interface UseGoldenEvalRunsResult {
  loading: boolean;
  error: string | null;
  datasets: AvailableDataset[];
  runs: GoldenEvalRunDetail[];
  totalRuns: number;
  daysWindow: number;
  selectedAgent: string | null;
  setSelectedAgent: (agent: string | null) => void;
  setDaysWindow: (days: number) => void;
  triggering: boolean;
  triggerError: string | null;
  trigger: (payload: TriggerEvalRunPayload) => Promise<GoldenEvalRunDetail | null>;
  refetch: () => Promise<void>;
}

export function useGoldenEvalRuns(
  initialDays: number = 30,
): UseGoldenEvalRunsResult {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<AvailableDataset[]>([]);
  const [runsResp, setRunsResp] = useState<GoldenEvalRunsListResponse | null>(
    null,
  );
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [daysWindow, setDaysWindow] = useState<number>(initialDays);
  const [triggering, setTriggering] = useState<boolean>(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ds, runs] = await Promise.all([
        listAvailableDatasets(),
        listEvalRuns(selectedAgent, daysWindow),
      ]);
      setDatasets(ds);
      setRunsResp(runs);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No pudimos cargar los datasets golden eval.");
      }
    } finally {
      setLoading(false);
    }
  }, [selectedAgent, daysWindow]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const trigger = useCallback(
    async (
      payload: TriggerEvalRunPayload,
    ): Promise<GoldenEvalRunDetail | null> => {
      setTriggering(true);
      setTriggerError(null);
      try {
        const detail = await triggerEvalRun(payload);
        await refetch();
        return detail;
      } catch (err) {
        if (err instanceof ApiError) {
          setTriggerError(err.message);
        } else {
          setTriggerError("Error disparando la evaluación.");
        }
        return null;
      } finally {
        setTriggering(false);
      }
    },
    [refetch],
  );

  return {
    loading,
    error,
    datasets,
    runs: runsResp?.items ?? [],
    totalRuns: runsResp?.total ?? 0,
    daysWindow,
    selectedAgent,
    setSelectedAgent,
    setDaysWindow,
    triggering,
    triggerError,
    trigger,
    refetch,
  };
}
