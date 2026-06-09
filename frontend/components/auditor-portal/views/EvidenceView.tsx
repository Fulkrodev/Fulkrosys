"use client";

/**
 * EvidenceView · Phase 5.5 auditor portal · evidence vault read-only.
 *
 * Display:
 * - Grouped counts per measure_code (table summary)
 * - Filter measure_code (server-side query)
 * - Items list · nombre archivo + mime + tamaño + hash SHA256 + scan status
 *   + caducidad alert si vigente flag false o fecha_caducidad past
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Download, FolderArchive, Loader2 } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  getAuditorPortalEvidence,
  type AuditorPortalEvidence,
  type AuditorPortalEvidenceItem,
} from "@/lib/api/auditor-portal";
import { AnnotationPanel } from "@/components/auditor-portal/annotations/AnnotationPanel";

interface Props {
  token: string;
}

function fmtSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

const SCAN_VARIANT: Record<string, "success" | "warning" | "danger"> = {
  clean: "success",
  scanning: "warning",
  infected: "danger",
  error: "warning",
  quarantined: "danger",
};

function EvidenceRow({
  item,
  token,
}: {
  item: AuditorPortalEvidenceItem;
  token: string;
}) {
  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-evidence-item-${item.id}`}
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-fulkro-ink-900">
            {item.fichero_nombre_original ?? item.nombre_tipo ?? "Archivo"}
          </p>
          {item.measure_code ? (
            <p className="text-[11px] text-fulkro-ink-500">
              Medida: <span className="font-mono">{item.measure_code}</span>
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-1">
          {item.scan_status ? (
            <Badge
              variant={SCAN_VARIANT[item.scan_status] ?? "secondary"}
              data-testid="auditor-evidence-scan-badge"
            >
              {item.scan_status}
            </Badge>
          ) : null}
          {!item.vigente ? (
            <Badge variant="warning">No vigente</Badge>
          ) : null}
          {/* #6 · descarga token-gated del fichero de evidencia (FileResponse).
              Oculta para ficheros en cuarentena/infectados (el endpoint también
              lo bloquea). El token de la URL autoriza · sin cookie. */}
          {item.scan_status !== "quarantined" &&
          item.scan_status !== "infected" ? (
            <a
              href={`/api/v1/public/auditor-portal/${token}/evidence/${item.id}/download`}
              download
              className="inline-flex items-center gap-1 rounded-md border border-fulkro-ink-300 bg-white px-2 py-1 text-[11px] font-medium text-fulkro-ink-700 hover:bg-fulkro-ink-50"
              data-testid={`auditor-evidence-download-${item.id}`}
              aria-label={`Descargar evidencia ${
                item.fichero_nombre_original ?? "archivo"
              }`}
            >
              <Download size={12} aria-hidden="true" />
              Descargar
            </a>
          ) : null}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1 text-[12px] text-fulkro-ink-500 sm:grid-cols-4">
        <span>Tipo: {item.nombre_tipo ?? "—"}</span>
        <span>Mime: {item.fichero_mime_type ?? "—"}</span>
        <span>Tamaño: {fmtSize(item.fichero_tamano_bytes)}</span>
        <span>
          Fecha:{" "}
          {item.fecha_evidencia
            ? new Date(item.fecha_evidencia).toLocaleDateString()
            : "—"}
        </span>
      </div>
      {item.hash_sha256 ? (
        <p className="mt-1 font-mono text-[10px] text-fulkro-ink-500">
          sha256: {item.hash_sha256.slice(0, 16)}…
        </p>
      ) : null}
      <div className="mt-2">
        <AnnotationPanel
          token={token}
          targetType="evidence"
          targetId={item.id}
          targetLabel={item.fichero_nombre_original ?? "Evidencia"}
          compact
        />
      </div>
    </div>
  );
}

export function EvidenceView({ token }: Props) {
  const [filter, setFilter] = React.useState<string>("");
  const data = useQuery<AuditorPortalEvidence>({
    queryKey: ["auditor-portal", "evidence", token, filter],
    queryFn: () =>
      getAuditorPortalEvidence(token, filter ? { measure_code: filter } : undefined),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-evidence-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando evidencias…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-evidence-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudieron cargar las evidencias</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  const { items, grouped_by_measure } = data.data;

  return (
    <div className="space-y-4" data-testid="auditor-evidence-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FolderArchive
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Evidencias del proyecto
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p data-testid="auditor-evidence-total">
            <strong>{data.data.total_items}</strong> evidencias registradas
            {filter ? ` para la medida ${filter}` : ""}
          </p>
          <div>
            <label
              htmlFor="auditor-evidence-filter"
              className="text-[11px] uppercase tracking-wider text-fulkro-ink-500"
            >
              Filtrar por medida (código exacto)
            </label>
            <Input
              id="auditor-evidence-filter"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="ej.: org.1 · op.acc.1 · mp.s.2"
              aria-label="Filtrar evidencias por código de medida"
              data-testid="auditor-evidence-filter"
              className="h-9"
            />
          </div>
        </CardContent>
      </Card>

      {grouped_by_measure.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resumen por medida</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-1 text-[12px] sm:grid-cols-4">
              {grouped_by_measure.map((g) => (
                <button
                  key={g.measure_code}
                  type="button"
                  onClick={() => setFilter(g.measure_code)}
                  className="rounded-md border border-fulkro-ink-300/60 bg-white p-2 text-left hover:bg-fulkro-ink-50"
                  data-testid={`auditor-evidence-group-${g.measure_code}`}
                >
                  <p className="font-mono text-[11px] font-semibold text-fulkro-ink-900">
                    {g.measure_code}
                  </p>
                  <p className="text-fulkro-ink-500">{g.total} archivos</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="space-y-2">
        {items.length === 0 ? (
          <Alert>
            <AlertTitle>Sin evidencias</AlertTitle>
            <AlertDescription>
              No hay evidencias registradas con los filtros aplicados.
            </AlertDescription>
          </Alert>
        ) : (
          items.map((item) => (
            <EvidenceRow key={item.id} item={item} token={token} />
          ))
        )}
      </div>
    </div>
  );
}
