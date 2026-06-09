"use client";

/**
 * DocumentsView · Phase 5.9 auditor portal · 10 docs canonical + signed ZIP.
 *
 * Display:
 * - audit_preparation_runs list (last 5 ordered DESC)
 * - Per run: estado + categoria + timestamps lifecycle
 * - Signed ZIP download CTA si dossier_generated_at present
 * - Descarga el dossier ZIP firmado por el endpoint token-gated del auditor
 *   (GET /public/auditor-portal/{token}/dossier.zip) · #1 Ejecutable 8
 *   (NO duplica binary streaming · metadata + redirect link only)
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, Download, Layers, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getAuditorPortalDocuments,
  type AuditorPortalDocumentRun,
  type AuditorPortalDocuments,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
}

const ESTADO_VARIANT: Record<string, "success" | "warning" | "info" | "outline"> = {
  dossier_generated: "success",
  in_progress: "warning",
  completed: "success",
  pending: "outline",
  draft: "outline",
};

function RunRow({
  run,
  onDownload,
  downloading,
}: {
  run: AuditorPortalDocumentRun;
  onDownload: (runId: string) => void;
  downloading: boolean;
}) {
  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-documents-run-${run.id}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-fulkro-ink-900">
            Categoría {run.categoria}{" "}
            <Badge
              variant={ESTADO_VARIANT[run.estado] ?? "outline"}
              className="ml-2"
            >
              {run.estado}
            </Badge>
          </p>
          <p className="text-[11px] text-fulkro-ink-500">
            Creado:{" "}
            {run.created_at
              ? new Date(run.created_at).toLocaleString()
              : "—"}
          </p>
        </div>
        {run.signed_zip_available ? (
          <Button
            size="sm"
            onClick={() => onDownload(run.id)}
            disabled={downloading}
            data-testid={`auditor-documents-download-${run.id}`}
            aria-label={`Descargar ZIP firmado para la preparación ${run.id}`}
          >
            <Download size={14} className="mr-1" aria-hidden="true" />
            {downloading ? "Generando…" : "ZIP firmado (ENAC)"}
          </Button>
        ) : (
          <Badge variant="outline">Dossier no generado</Badge>
        )}
      </div>
      <div className="mt-1 grid grid-cols-2 gap-1 text-[12px] text-fulkro-ink-500 sm:grid-cols-3">
        <span>
          Inicio:{" "}
          {run.started_at
            ? new Date(run.started_at).toLocaleString()
            : "—"}
        </span>
        <span>
          Fin:{" "}
          {run.completed_at
            ? new Date(run.completed_at).toLocaleString()
            : "—"}
        </span>
        <span>
          Dossier:{" "}
          {run.dossier_generated_at
            ? new Date(run.dossier_generated_at).toLocaleString()
            : "—"}
        </span>
      </div>
    </div>
  );
}

export function DocumentsView({ token: _token }: Props) {
  // _token unused para query (uses positional param) · prefixed underscore
  const token = _token;
  const data = useQuery<AuditorPortalDocuments>({
    queryKey: ["auditor-portal", "documents", token],
    queryFn: () => getAuditorPortalDocuments(token),
    enabled: Boolean(token),
    staleTime: 30_000,
    retry: false,
  });

  const downloadMut = useMutation({
    mutationFn: async (_runId: string) => {
      // Ejecutable 8 OLA 0 (#1): el auditor descarga el dossier por el endpoint
      // TOKEN-GATED (GET · el magic-link en la URL autoriza · sin cookie). Antes
      // el FE POSTeaba a `signed_zip_endpoint`, que es el endpoint ADMIN
      // (require_owner) → 401/403 para el auditor ENAC. El endpoint correcto
      // `GET /public/auditor-portal/{token}/dossier.zip` ya existía sin usarse.
      const response = await fetch(
        `/api/v1/public/auditor-portal/${token}/dossier.zip`,
        { method: "GET" },
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dossier_signed_${_runId}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-documents-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando documentos…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-documents-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudieron cargar los documentos</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-documents-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Layers
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Documentos canónicos ENAC
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <strong>{data.data.total_runs}</strong> preparaciones registradas.
            Descarga el ZIP firmado (Ed25519) para verificación de integridad.
          </p>
          <Alert>
            <AlertTitle>Verificación independiente</AlertTitle>
            <AlertDescription>
              El manifiesto del ZIP incluye un bloque <code className="font-mono">_signature</code>{" "}
              Ed25519. La firma puede verificarse offline con la clave pública
              del consultor responsable.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {data.data.runs.length === 0 ? (
          <Alert>
            <AlertTitle>Sin preparaciones</AlertTitle>
            <AlertDescription>
              No hay preparaciones de auditoría registradas para este proyecto.
            </AlertDescription>
          </Alert>
        ) : (
          data.data.runs.map((r) => (
            <RunRow
              key={r.id}
              run={r}
              onDownload={(id) => downloadMut.mutate(id)}
              downloading={downloadMut.isPending}
            />
          ))
        )}
        {downloadMut.isError ? (
          <Alert variant="danger" data-testid="auditor-documents-download-error">
            <AlertTitle>No se pudo descargar el ZIP</AlertTitle>
            <AlertDescription>
              Reintenta más tarde o contacta con el consultor responsable.
            </AlertDescription>
          </Alert>
        ) : null}
      </div>
    </div>
  );
}
