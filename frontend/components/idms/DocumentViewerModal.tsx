/**
 * DocumentViewerModal · 1.C.G.A v3.10 · admin preview + metadata.
 *
 * Reuse endpoint existing GET /api/v1/idms/projects/{id}/idms/documents/{id}
 * (returns document + tags + versions + folder en single response).
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2 } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { idmsApi } from "@/lib/api/idms";

interface DocumentViewerModalProps {
  projectId: string;
  documentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentViewerModal({
  projectId,
  documentId,
  open,
  onOpenChange,
}: DocumentViewerModalProps) {
  const detail = useQuery({
    queryKey: ["idms", "document-detail", projectId, documentId],
    queryFn: () => idmsApi.getDocument(projectId, documentId as string),
    enabled: open && Boolean(documentId),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText size={16} />
            {detail.data?.nombre ?? "Documento"}
          </DialogTitle>
          <DialogDescription>
            Vista detallada · metadatos · etiquetas ENS · historial versiones
          </DialogDescription>
        </DialogHeader>

        {detail.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : detail.isError ? (
          <p className="text-sm text-fulkro-danger">
            Error al cargar documento.
          </p>
        ) : detail.data ? (
          <div className="space-y-4 text-sm">
            <Section title="Metadatos">
              <Field label="Tipo" value={detail.data.tipo} />
              <Field label="Estado" value={detail.data.estado} />
              <Field label="Clasificación" value={detail.data.clasificacion} />
              <Field
                label="Tamaño"
                value={
                  detail.data.file_size_bytes
                    ? `${(detail.data.file_size_bytes / 1024).toFixed(1)} KB`
                    : "—"
                }
              />
              <Field
                label="Hash SHA-256"
                value={detail.data.content_hash}
                mono
              />
              <Field
                label="Carpeta"
                value={detail.data.folder?.name ?? "(raíz)"}
              />
              <Field
                label="Creado"
                value={fmtDate(detail.data.created_at ?? null)}
              />
              <Field
                label="Caduca"
                value={fmtDate(detail.data.expires_at ?? null)}
              />
            </Section>

            {detail.data.tags && detail.data.tags.length > 0 ? (
              <Section title={`Etiquetas (${detail.data.tags.length})`}>
                <div className="flex flex-wrap gap-1.5">
                  {detail.data.tags.map((t) => (
                    <Badge key={t.id} variant="secondary">
                      {t.tag_type}: {t.tag_value}
                    </Badge>
                  ))}
                </div>
              </Section>
            ) : null}

            {detail.data.versions && detail.data.versions.length > 0 ? (
              <Section title={`Versiones (${detail.data.versions.length})`}>
                <ul className="space-y-1">
                  {detail.data.versions.slice(0, 6).map((v) => (
                    <li
                      key={v.id}
                      className="flex items-center justify-between rounded border border-fulkro-ink-300 px-2 py-1.5 text-xs"
                    >
                      <span className="font-mono">v{v.version}</span>
                      <span className="text-fulkro-ink-500">
                        {fmtDate(v.generado_at)} · {v.generado_por ?? "—"}
                      </span>
                    </li>
                  ))}
                  {detail.data.versions.length > 6 ? (
                    <li className="text-[11px] text-fulkro-ink-500">
                      …y {detail.data.versions.length - 6} versiones más
                    </li>
                  ) : null}
                </ul>
              </Section>
            ) : null}

            {detail.data.storage_path ? (
              <p className="text-xs text-fulkro-ink-500">
                <Loader2 size={10} className="mr-1 inline" />
                Preview inline diferido a polish T1 · descarga desde versions modal.
              </p>
            ) : null}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
        {title}
      </h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-2 text-xs">
      <span className="w-28 shrink-0 text-fulkro-ink-500">{label}</span>
      <span
        className={`flex-1 break-all ${mono ? "font-mono text-[10px]" : ""}`}
      >
        {value || "—"}
      </span>
    </div>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}
