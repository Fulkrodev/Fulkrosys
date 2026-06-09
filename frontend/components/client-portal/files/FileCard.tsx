"use client";

/**
 * FileCard · summary list item documents + evidence.
 * SAN-E v3.MB-6 atom 7.
 *
 * Drop-in ScanStatusBadge atom 6 (2ª aplicación · Q5 A) si evidence mode.
 */
import { ChevronRight, Download, Eye, FileText, History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScanStatusBadge } from "@/components/ui/scan-status-badge";
import type {
  ClientDocumentExtended,
  ClientEvidence,
} from "@/lib/api/files-extended";
import { cn } from "@/lib/utils";

interface DocumentProps {
  mode: "document";
  item: ClientDocumentExtended;
  onPreview: (id: string) => void;
  onVersions: (id: string) => void;
  onDownload: (id: string) => void;
}

interface EvidenceProps {
  mode: "evidence";
  item: ClientEvidence;
  onPreview: (id: string) => void;
  onDownload: (id: string) => void;
}

type Props = DocumentProps | EvidenceProps;

function fmtSize(bytes: number | null | undefined): string {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-ES");
  } catch {
    return iso;
  }
}

export function FileCard(props: Props) {
  const isDoc = props.mode === "document";
  const item = props.item;
  const title = isDoc
    ? (item as ClientDocumentExtended).nombre ?? (item as ClientDocumentExtended).codigo ?? "Documento"
    : (item as ClientEvidence).fichero_nombre_original ?? "Evidencia";
  const isPdf = isDoc
    ? !!(item as ClientDocumentExtended).pdf_path
    : ((item as ClientEvidence).fichero_mime_type ?? "").startsWith("application/pdf");
  const size = isDoc
    ? (item as ClientDocumentExtended).file_size_bytes
    : (item as ClientEvidence).fichero_tamano_bytes;
  const created = isDoc
    ? (item as ClientDocumentExtended).created_at
    : (item as ClientEvidence).created_at;

  return (
    <Card
      data-testid={`file-card-${item.id}`}
      data-mode={props.mode}
      className={cn(
        "p-4 hover:bg-fulkro-ink-50 transition-colors flex items-start gap-3",
      )}
    >
      <FileText
        className="h-5 w-5 mt-0.5 text-fulkro-primary-700 flex-shrink-0"
        aria-hidden
      />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="font-semibold text-sm text-fulkro-ink-800 truncate">
          {title}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-fulkro-ink-500">
          <span>{fmtDate(created)}</span>
          <span>·</span>
          <span className="font-mono tabular-nums">{fmtSize(size)}</span>
          {isDoc && (item as ClientDocumentExtended).clasificacion && (
            <>
              <span>·</span>
              <Badge variant="secondary">
                {(item as ClientDocumentExtended).clasificacion}
              </Badge>
            </>
          )}
          {!isDoc && (
            <>
              <span>·</span>
              <ScanStatusBadge
                status={(item as ClientEvidence).scan_status}
                size="sm"
              />
            </>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-1.5 items-end flex-shrink-0">
        {isPdf && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => props.onPreview(item.id)}
            data-testid={`file-preview-${item.id}`}
            aria-label="Previsualizar"
          >
            <Eye className="h-3 w-3" aria-hidden />
            <span className="ml-1.5">Ver</span>
          </Button>
        )}
        {isDoc && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => (props as DocumentProps).onVersions(item.id)}
            data-testid={`file-versions-${item.id}`}
            aria-label="Historial versiones"
          >
            <History className="h-3 w-3" aria-hidden />
            <span className="ml-1.5">Versiones</span>
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          onClick={() => props.onDownload(item.id)}
          data-testid={`file-download-${item.id}`}
          aria-label="Descargar"
        >
          <Download className="h-3 w-3" aria-hidden />
          <span className="ml-1.5">Descargar</span>
        </Button>
      </div>
      <ChevronRight
        className="h-4 w-4 text-fulkro-ink-400 flex-shrink-0 mt-1"
        aria-hidden
      />
    </Card>
  );
}
