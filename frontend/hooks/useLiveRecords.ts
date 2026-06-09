"use client";

/**
 * Hooks live_records portal cliente · sub-atom 1.C.B fase 4a.
 *
 * Pattern useState/useEffect/useCallback (coherente con useIncidentsClient,
 * useDdaClient, etc. · NO react-query/swr · pattern plataforma sostenido).
 *
 * 3 hooks publicos:
 *   - useLiveRecordsDashboard(projectId) → 26 blocks + total_active
 *   - useLiveRecords(projectId, registerType, params) → paginated list
 *   - useLiveRecord(projectId, registerType, recordId) → single entry
 */
import { useCallback, useEffect, useState } from "react";

import { ClientApiError } from "@/lib/client-portal-api";
import {
  archiveLiveRecord,
  createLiveRecord,
  exportLiveRecordsCsv,
  exportLiveRecordsXlsx,
  getLiveRecord,
  getLiveRecordsDashboard,
  listLiveRecords,
  triggerBlobDownload,
  updateLiveRecord,
  type ListLiveRecordsParams,
} from "@/lib/api/live-records";
import type {
  LiveRecord,
  LiveRecordListResponse,
  LiveRecordUpdatePayload,
  LiveRecordsDashboardResponse,
  RegisterType,
} from "@/lib/types/live-records";


function resolveErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ClientApiError) return err.message || fallback;
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}


// ─── Dashboard ────────────────────────────────────────────────────────────


export interface UseLiveRecordsDashboardResult {
  dashboard: LiveRecordsDashboardResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}


export function useLiveRecordsDashboard(
  projectId: string | null,
): UseLiveRecordsDashboardResult {
  const [dashboard, setDashboard] = useState<LiveRecordsDashboardResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async (pid: string) => {
    setError(null);
    try {
      const data = await getLiveRecordsDashboard(pid);
      setDashboard(data);
    } catch (err) {
      setError(resolveErrorMessage(err, "Error cargando dashboard de registros"));
    }
  }, []);

  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      await fetchDashboard(projectId);
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, fetchDashboard]);

  const refetch = useCallback(async () => {
    if (!projectId) return;
    await fetchDashboard(projectId);
  }, [projectId, fetchDashboard]);

  return { dashboard, loading, error, refetch };
}


// ─── Paginated list per register_type ────────────────────────────────────


export interface UseLiveRecordsResult {
  records: LiveRecord[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  create: (entryData: Record<string, unknown>) => Promise<LiveRecord>;
  update: (
    recordId: string,
    payload: LiveRecordUpdatePayload,
  ) => Promise<LiveRecord>;
  archive: (recordId: string) => Promise<void>;
  exportCsv: () => Promise<void>;
  exportXlsx: () => Promise<void>;
}


export function useLiveRecords(
  projectId: string | null,
  registerType: RegisterType | null,
  params: ListLiveRecordsParams = {},
): UseLiveRecordsResult {
  const [records, setRecords] = useState<LiveRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { status, limit = 50, offset = 0 } = params;

  const fetchList = useCallback(async (pid: string, rt: RegisterType) => {
    setError(null);
    try {
      const data: LiveRecordListResponse = await listLiveRecords(pid, rt, {
        status,
        limit,
        offset,
      });
      setRecords(data.records);
      setTotal(data.total);
    } catch (err) {
      setError(resolveErrorMessage(err, "Error cargando registros"));
    }
  }, [status, limit, offset]);

  useEffect(() => {
    if (!projectId || !registerType) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      await fetchList(projectId, registerType);
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, registerType, fetchList]);

  const refetch = useCallback(async () => {
    if (!projectId || !registerType) return;
    await fetchList(projectId, registerType);
  }, [projectId, registerType, fetchList]);

  const create = useCallback(
    async (entryData: Record<string, unknown>) => {
      if (!projectId || !registerType) {
        throw new Error("projectId / registerType requeridos para crear");
      }
      const record = await createLiveRecord(projectId, registerType, entryData);
      await fetchList(projectId, registerType);
      return record;
    },
    [projectId, registerType, fetchList],
  );

  const update = useCallback(
    async (recordId: string, payload: LiveRecordUpdatePayload) => {
      if (!projectId || !registerType) {
        throw new Error("projectId / registerType requeridos para editar");
      }
      const record = await updateLiveRecord(
        projectId,
        registerType,
        recordId,
        payload,
      );
      await fetchList(projectId, registerType);
      return record;
    },
    [projectId, registerType, fetchList],
  );

  const archive = useCallback(
    async (recordId: string) => {
      if (!projectId || !registerType) {
        throw new Error("projectId / registerType requeridos para archivar");
      }
      await archiveLiveRecord(projectId, registerType, recordId);
      await fetchList(projectId, registerType);
    },
    [projectId, registerType, fetchList],
  );

  const exportCsv = useCallback(async () => {
    if (!projectId || !registerType) return;
    const blob = await exportLiveRecordsCsv(projectId, registerType);
    triggerBlobDownload(blob, `${registerType}_${projectId}.csv`);
  }, [projectId, registerType]);

  const exportXlsx = useCallback(async () => {
    if (!projectId || !registerType) return;
    const blob = await exportLiveRecordsXlsx(projectId, registerType);
    triggerBlobDownload(blob, `${registerType}_${projectId}.xlsx`);
  }, [projectId, registerType]);

  return {
    records,
    total,
    limit,
    offset,
    loading,
    error,
    refetch,
    create,
    update,
    archive,
    exportCsv,
    exportXlsx,
  };
}


// ─── Single record ────────────────────────────────────────────────────────


export interface UseLiveRecordResult {
  record: LiveRecord | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}


export function useLiveRecord(
  projectId: string | null,
  registerType: RegisterType | null,
  recordId: string | null,
): UseLiveRecordResult {
  const [record, setRecord] = useState<LiveRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOne = useCallback(
    async (pid: string, rt: RegisterType, rid: string) => {
      setError(null);
      try {
        const data = await getLiveRecord(pid, rt, rid);
        setRecord(data);
      } catch (err) {
        setError(resolveErrorMessage(err, "Error cargando registro"));
      }
    },
    [],
  );

  useEffect(() => {
    if (!projectId || !registerType || !recordId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      await fetchOne(projectId, registerType, recordId);
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, registerType, recordId, fetchOne]);

  const refetch = useCallback(async () => {
    if (!projectId || !registerType || !recordId) return;
    await fetchOne(projectId, registerType, recordId);
  }, [projectId, registerType, recordId, fetchOne]);

  return { record, loading, error, refetch };
}
