"use client";

/**
 * McpExecutionsHistory · Sub-atom 1.D.E.B v3.11.
 *
 * Historial de ejecuciones MCP per project · timestamps · tool · status ·
 * link descarga reporte. Refresh 30s para ver running → completed.
 *
 * Project-scoped (R23 sostener firmísimo) · consume
 * GET /api/v1/projects/{id}/mcps/executions.
 */
import { useState } from "react";
import { History } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  MCP_STATUS_LABELS,
  MCP_STATUS_VARIANTS,
  type MCPExecution,
} from "@/lib/api/mcps";

import { useMCPsExecutions } from "@/hooks/useMCPs";

interface McpExecutionsHistoryProps {
  projectId: string;
  onSelectExecution?: (execution: MCPExecution) => void;
}

export function McpExecutionsHistory({
  projectId,
  onSelectExecution,
}: McpExecutionsHistoryProps) {
  const historyQuery = useMCPsExecutions(projectId);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const items = historyQuery.data?.executions ?? [];
  const filtered =
    statusFilter === "all"
      ? items
      : items.filter((e) => e.status === statusFilter);

  return (
    <Card data-testid="mcp-executions-history">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <History size={16} /> Historial ejecuciones
        </CardTitle>
        <div className="flex flex-wrap gap-1">
          {(
            ["all", "running", "completed", "failed"] as const
          ).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={statusFilter === s ? "primary" : "outline"}
              onClick={() => setStatusFilter(s)}
              data-testid={`mcp-history-filter-${s}`}
            >
              {s === "all" ? "Todos" : MCP_STATUS_LABELS[s]}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 p-4 pt-0">
        {historyQuery.isLoading ? (
          <>
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </>
        ) : historyQuery.isError ? (
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar el historial</AlertTitle>
            <AlertDescription>
              {historyQuery.error instanceof Error
                ? historyQuery.error.message
                : "Error desconocido"}
            </AlertDescription>
          </Alert>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="Sin ejecuciones"
            description={
              statusFilter === "all"
                ? "Ejecuta un MCP para empezar."
                : "Ningún MCP en ese estado."
            }
          />
        ) : (
          filtered.map((e) => (
            <button
              key={e.execution_id}
              type="button"
              onClick={() => onSelectExecution?.(e)}
              className="flex w-full items-start justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-2 text-left transition-colors hover:bg-fulkro-surface-glass-strong/50"
              data-testid={`mcp-history-row-${e.execution_id}`}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fulkro-ink-700">
                  {e.mcp_name}/{e.tool_name}
                </p>
                <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
                  #{e.execution_id.slice(0, 8)} ·{" "}
                  {e.started_at
                    ? new Date(e.started_at).toLocaleString("es-ES", {
                        hour12: false,
                      })
                    : "no iniciado"}
                </p>
              </div>
              <Badge
                variant={MCP_STATUS_VARIANTS[e.status]}
                className="shrink-0"
              >
                {MCP_STATUS_LABELS[e.status]}
              </Badge>
            </button>
          ))
        )}
      </CardContent>
    </Card>
  );
}
