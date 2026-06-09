"use client";

/**
 * McpExecutionResult · Sub-atom 1.D.E.B v3.11.
 *
 * Vista del resultado de una ejecución MCP completada · summary +
 * findings count + botón "Descargar reporte JSON" + link evidencia
 * adjuntada en IDMS (folder 13_Informes_Tecnicos).
 *
 * Project-scoped · auth require_owner backend (R23 sostener).
 */
import { useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { mcpsApi, type MCPExecution } from "@/lib/api/mcps";

interface McpExecutionResultProps {
  projectId: string;
  execution: MCPExecution;
}

export function McpExecutionResult({
  projectId,
  execution,
}: McpExecutionResultProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await mcpsApi.downloadReport(
        projectId,
        execution.execution_id,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mcp_${execution.mcp_name}_${execution.tool_name}_${execution.execution_id.slice(
        0,
        8,
      )}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Reporte descargado");
    } catch (err) {
      toast.error("Error descargando reporte", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setDownloading(false);
    }
  };

  const summary = (execution.result as
    | { summary?: Record<string, unknown>; _simulated?: boolean }
    | null) ?? null;
  const findingsCount = ((execution.result as
    | { findings?: unknown[] }
    | null)?.findings ?? []).length;

  return (
    <Card data-testid={`mcp-execution-result-${execution.execution_id}`}>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-sm font-semibold text-fulkro-title">
            Resultado · {execution.mcp_name}/{execution.tool_name}
          </h4>
          {summary?._simulated && (
            <Badge variant="warning">Simulado · USE_MCP_REAL=false</Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <ResultRow label="Hallazgos" value={String(findingsCount)} />
          <ResultRow
            label="Risk"
            value={String(summary?.summary?.["risk_level"] ?? "—")}
          />
        </div>

        {execution.evidence_document_id ? (
          <Alert variant="success" data-testid="mcp-execution-evidence">
            <AlertTitle>Evidencia adjuntada al IDMS</AlertTitle>
            <AlertDescription>
              Reporte guardado en folder{" "}
              <code>13_Informes_Tecnicos</code> · documento{" "}
              <code>{execution.evidence_document_id.slice(0, 12)}…</code>
            </AlertDescription>
          </Alert>
        ) : (
          <Alert variant="warning">
            <AlertTitle>Evidence NO adjuntada</AlertTitle>
            <AlertDescription>
              No se pudo adjuntar el reporte al IDMS automáticamente · revisa
              logs servidor.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={downloading}
            data-testid="mcp-execution-download"
          >
            {downloading ? (
              <Loader2 size={14} className="mr-1 animate-spin" />
            ) : (
              <Download size={14} className="mr-1" />
            )}
            Descargar reporte (JSON)
          </Button>
          {execution.evidence_document_id && (
            <a
              href={`/admin/projects/${projectId}/documents`}
              className="inline-flex h-8 items-center gap-1 rounded-md px-3 text-sm font-semibold text-fulkro-body hover:bg-fulkro-surface-glass-strong hover:text-fulkro-title"
              data-testid="mcp-execution-evidence-link"
            >
              <FileText size={14} className="mr-1" />
              Ver en IDMS
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ResultRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-semibold uppercase text-muted-foreground">
        {label}
      </span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
