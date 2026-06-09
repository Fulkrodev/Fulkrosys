/**
 * DocumentVersionHistoryModal · 1.C.G.A v3.10 · history versiones per documento.
 *
 * Reuse endpoint existing GET /api/v1/idms/projects/{id}/idms/documents/{id}/versions.
 * Lista cronológica versiones · hash SHA-256 · autor · timestamp.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { idmsApi } from "@/lib/api/idms";

interface DocumentVersionHistoryModalProps {
  projectId: string;
  documentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentVersionHistoryModal({
  projectId,
  documentId,
  open,
  onOpenChange,
}: DocumentVersionHistoryModalProps) {
  const versions = useQuery({
    queryKey: ["idms", "document-versions", projectId, documentId],
    queryFn: () => idmsApi.listVersions(projectId, documentId as string),
    enabled: open && Boolean(documentId),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History size={16} />
            Historial de versiones
          </DialogTitle>
          <DialogDescription>
            Listado cronológico de versiones del documento · hash SHA-256 verificable.
          </DialogDescription>
        </DialogHeader>

        {versions.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : versions.isError ? (
          <p className="text-sm text-fulkro-danger">
            Error al cargar versiones.
          </p>
        ) : !versions.data?.versions || versions.data.versions.length === 0 ? (
          <EmptyState
            title="Sin versiones"
            description="Este documento todavía no tiene versiones registradas."
          />
        ) : (
          <ul className="space-y-2">
            {versions.data.versions.map((v) => (
              <li
                key={v.id}
                className="rounded-md border border-fulkro-ink-300 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold">
                    v{v.version}
                  </span>
                  <span className="text-xs text-fulkro-ink-500">
                    {fmtDateTime(v.generado_at)} · {v.generado_por ?? "—"}
                  </span>
                </div>
                {v.hash_sha256 ? (
                  <p className="mt-1 break-all font-mono text-[10px] text-fulkro-ink-500">
                    SHA-256: {v.hash_sha256}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
