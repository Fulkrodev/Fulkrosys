"use client";

/**
 * WorkflowStepDeliverables · sub-atom 1.C.D.D.2 v3.8.
 *
 * Componente reusable admin + cliente · render deliverables per step con
 * status badges + download per code + bulk ZIP.
 *
 * Adapta tono según `tone` prop:
 *   - "admin" · técnico · explícito (admin opera profesional)
 *   - "client" · friendly · sin jerga (R29 sostener)
 *
 * Status visualization:
 *   ✅ available · button "Descargar" enabled
 *   🔄 needs_regen · button disabled + label "Actualizar plantilla"
 *   ⏳ missing · button disabled + label tono según mode
 *
 * Bulk ZIP:
 *   - Botón "Descargar TODOS (ZIP)" enabled si counts.available > 0
 *   - Trigger window.location · backend StreamingResponse attachment
 */
import * as React from "react";
import {
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  Package,
  RefreshCw,
} from "lucide-react";

import {
  downloadBulkZipUrl,
  downloadDeliverableUrl,
  type ApiMode,
  type DeliverableState,
} from "@/lib/api/workflow-deliverables";
import { useStepDeliverables } from "@/hooks/useStepDeliverables";
import { cn } from "@/lib/utils";

interface WorkflowStepDeliverablesProps {
  projectId: string;
  templateId: string;
  mode?: ApiMode;
  tone?: "admin" | "client";
}

function StatusIcon({ status }: { status: DeliverableState["status"] }) {
  if (status === "available") {
    return (
      <CheckCircle2
        className="size-4 text-emerald-600"
        strokeWidth={2.3}
        aria-hidden
      />
    );
  }
  if (status === "needs_regen") {
    return (
      <RefreshCw
        className="size-4 text-amber-600"
        strokeWidth={2.3}
        aria-hidden
      />
    );
  }
  return (
    <FileText
      className="size-4 text-foreground/40"
      strokeWidth={2.3}
      aria-hidden
    />
  );
}

function statusLabel(
  status: DeliverableState["status"],
  tone: "admin" | "client",
): string {
  if (status === "available") return tone === "client" ? "Disponible" : "Listo";
  if (status === "needs_regen") {
    return tone === "client" ? "Pendiente actualizar" : "Necesita regenerar";
  }
  return tone === "client" ? "Aún no preparado" : "Pendiente generar";
}

function emptyStateMessage(tone: "admin" | "client"): string {
  return tone === "client"
    ? "Este paso no requiere entregables específicos."
    : "Sin entregables declarados para este sub-paso.";
}

export function WorkflowStepDeliverables({
  projectId,
  templateId,
  mode = "admin",
  tone = "admin",
}: WorkflowStepDeliverablesProps) {
  const query = useStepDeliverables(projectId, templateId, mode);

  if (query.isLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-foreground/60">
        <Loader2 className="size-4 animate-spin" />
        Cargando entregables…
      </div>
    );
  }

  if (query.isError) {
    return (
      <p className="text-sm text-foreground/60">
        {tone === "client"
          ? "Estamos teniendo problemas al cargar los documentos · prueba en un momento."
          : "Error cargando deliverables · revisa permisos o intenta refrescar."}
      </p>
    );
  }

  const data = query.data;
  if (!data || data.deliverable_codes.length === 0) {
    return (
      <p className="text-sm italic text-foreground/55">
        {emptyStateMessage(tone)}
      </p>
    );
  }

  const hasAvailable = data.counts.available > 0;
  const bulkUrl = downloadBulkZipUrl(projectId, templateId);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-foreground/60">
          {tone === "client"
            ? `${data.counts.available} de ${data.deliverable_codes.length} preparados`
            : `${data.counts.available}/${data.deliverable_codes.length} listos · ${data.counts.missing} pendientes generar`}
        </p>

        {hasAvailable && (
          <a
            href={bulkUrl}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium",
              "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100",
            )}
            data-testid="deliverables-bulk-zip"
          >
            <Package className="size-3.5" strokeWidth={2.3} aria-hidden />
            {tone === "client"
              ? "Descargar todos (ZIP)"
              : "Descargar todos (ZIP)"}
          </a>
        )}
      </div>

      <ul className="space-y-2">
        {data.deliverables.map((d) => {
          const downloadable = d.status === "available" && d.evidence_id;
          const fileLabel =
            d.fichero_nombre_original || `${d.code}.pdf`;
          return (
            <li
              key={d.code}
              className="flex items-center justify-between gap-2 rounded-md border bg-card px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                <StatusIcon status={d.status} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{d.code}</p>
                  <p className="truncate text-xs text-foreground/55">
                    {downloadable ? fileLabel : statusLabel(d.status, tone)}
                  </p>
                </div>
              </div>

              {downloadable && d.evidence_id ? (
                <a
                  href={downloadDeliverableUrl(projectId, d.evidence_id)}
                  className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                  data-testid={`deliverable-download-${d.code}`}
                >
                  <Download className="size-3" strokeWidth={2.3} aria-hidden />
                  Descargar
                </a>
              ) : (
                <span
                  className="text-xs italic text-foreground/45"
                  aria-label={statusLabel(d.status, tone)}
                >
                  {statusLabel(d.status, tone)}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
