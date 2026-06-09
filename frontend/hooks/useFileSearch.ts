"use client";

/**
 * useFileSearch · SAN-E v3.MB-6 atom 7.
 *
 * Debounced search + tab state + filter chips para /client-portal/files.
 * Q1 B · evidence + documents tabs (Q7 B separated).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  type ClientDocumentExtended,
  type ClientEvidence,
  type FileSort,
  listDocumentsExtended,
  listEvidenceExtended,
} from "@/lib/api/files-extended";
import { ClientApiError } from "@/lib/client-portal-api";

const SEARCH_DEBOUNCE_MS = 300;

export type FilesTab = "documents" | "evidence";

interface UseFileSearchResult {
  tab: FilesTab;
  setTab: (tab: FilesTab) => void;
  // Search/filter state
  search: string;
  setSearch: (s: string) => void;
  clasificacion: string | null;
  setClasificacion: (c: string | null) => void;
  scanCleanOnly: boolean;
  setScanCleanOnly: (b: boolean) => void;
  sort: FileSort;
  setSort: (s: FileSort) => void;
  // 1.C.G.B v3.10 · folder filter para arborescencia cliente
  folderId: string | null;
  setFolderId: (id: string | null) => void;
  // Data
  documents: ClientDocumentExtended[];
  evidence: ClientEvidence[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useFileSearch(initialTab: FilesTab = "documents"): UseFileSearchResult {
  const [tab, setTab] = useState<FilesTab>(initialTab);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [clasificacion, setClasificacion] = useState<string | null>(null);
  const [scanCleanOnly, setScanCleanOnly] = useState(false);
  const [sort, setSort] = useState<FileSort>("recent");
  const [folderId, setFolderId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<ClientDocumentExtended[]>([]);
  const [evidence, setEvidence] = useState<ClientEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search input → debouncedSearch
  useEffect(() => {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current !== null) clearTimeout(debounceRef.current);
    };
  }, [search]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (tab === "documents") {
        const list = await listDocumentsExtended({
          q: debouncedSearch || undefined,
          clasificacion: clasificacion ?? undefined,
          folderId: folderId ?? undefined,
          sort,
          limit: 50,
        });
        setDocuments(list);
      } else {
        const list = await listEvidenceExtended({
          q: debouncedSearch || undefined,
          scanCleanOnly: scanCleanOnly || undefined,
          sort,
          limit: 50,
        });
        setEvidence(list);
      }
    } catch (err) {
      if (err instanceof ClientApiError) setError(err.message);
      else setError("Error cargando archivos");
    } finally {
      setLoading(false);
    }
  }, [tab, debouncedSearch, clasificacion, scanCleanOnly, folderId, sort]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const refetch = useCallback(async () => {
    await fetchAll();
  }, [fetchAll]);

  return {
    tab,
    setTab,
    search,
    setSearch,
    clasificacion,
    setClasificacion,
    scanCleanOnly,
    setScanCleanOnly,
    sort,
    setSort,
    folderId,
    setFolderId,
    documents,
    evidence,
    loading,
    error,
    refetch,
  };
}
