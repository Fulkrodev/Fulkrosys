"use client";

/**
 * McpExecutionProgress · Sub-atom 1.D.E.B v3.11.
 *
 * Stream SSE de progress events para una ejecución MCP. Reuse pattern
 * `useProjectEvents.ts` (EventSource browser API). Eventos:
 *   - started · progress · completed · failed · heartbeat
 *
 * Combinado con `useMCPExecution` polling 2s para garantizar consistencia
 * post-reload (SSE no persiste cross-navigation · polling fallback).
 *
 * R23 sostener · project-scoped URL.
 */
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  MCP_STATUS_LABELS,
  MCP_STATUS_VARIANTS,
  mcpsApi,
  type MCPExecutionStatus,
} from "@/lib/api/mcps";

import { mcpsKeys, useMCPExecution } from "@/hooks/useMCPs";

interface McpExecutionProgressProps {
  projectId: string;
  executionId: string;
  /** Disparado al recibir completed/failed (refresh parent list). */
  onFinished?: (status: MCPExecutionStatus) => void;
}

interface SSEEntry {
  type: string;
  data: Record<string, unknown>;
  ts: string;
}

export function McpExecutionProgress({
  projectId,
  executionId,
  onFinished,
}: McpExecutionProgressProps) {
  const qc = useQueryClient();
  const executionQuery = useMCPExecution(projectId, executionId);
  const [events, setEvents] = useState<SSEEntry[]>([]);

  useEffect(() => {
    if (!projectId || !executionId || typeof window === "undefined") return;

    const url = mcpsApi.streamUrl(projectId, executionId);
    const es = new EventSource(url, { withCredentials: true });

    const handle = (type: string) => (e: MessageEvent) => {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(e.data);
      } catch {
        parsed = { raw: e.data };
      }
      setEvents((prev) => [
        ...prev.slice(-49),
        {
          type,
          data: parsed,
          ts: new Date().toISOString(),
        },
      ]);
      if (type === "completed" || type === "failed") {
        qc.invalidateQueries({
          queryKey: mcpsKeys.execution(projectId, executionId),
        });
        qc.invalidateQueries({ queryKey: mcpsKeys.executions(projectId) });
        onFinished?.(type as MCPExecutionStatus);
        es.close();
      }
    };

    es.addEventListener("started", handle("started"));
    es.addEventListener("progress", handle("progress"));
    es.addEventListener("completed", handle("completed"));
    es.addEventListener("failed", handle("failed"));
    es.addEventListener("heartbeat", () => {
      // no-op
    });

    es.onerror = () => {
      // Browser auto-reconnect · log
      // eslint-disable-next-line no-console
      console.debug("MCP SSE connection error · reconnecting", executionId);
    };

    return () => {
      es.close();
    };
  }, [projectId, executionId, qc, onFinished]);

  const execution = executionQuery.data;
  const status: MCPExecutionStatus = execution?.status ?? "pending";
  const progress = execution?.progress ?? 0;

  return (
    <div
      className="space-y-3"
      data-testid={`mcp-execution-progress-${executionId}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {status === "running" ? (
            <Loader2 size={18} className="animate-spin text-fulkro-info" />
          ) : status === "completed" ? (
            <CheckCircle2 size={18} className="text-fulkro-success" />
          ) : status === "failed" ? (
            <XCircle size={18} className="text-fulkro-danger" />
          ) : null}
          <Badge variant={MCP_STATUS_VARIANTS[status]}>
            {MCP_STATUS_LABELS[status]}
          </Badge>
          <span
            className="font-mono text-[11px] text-muted-foreground"
            data-testid="mcp-execution-id"
          >
            #{executionId.slice(0, 8)}
          </span>
        </div>
        <span className="text-sm font-semibold text-fulkro-title">
          {progress}%
        </span>
      </div>

      <Progress value={progress} className="h-2" />

      {execution?.error && (
        <Alert variant="danger" data-testid="mcp-execution-error">
          <AlertTitle>Ejecución fallida</AlertTitle>
          <AlertDescription>{execution.error}</AlertDescription>
        </Alert>
      )}

      <div
        className="max-h-48 overflow-y-auto rounded-md border bg-fulkro-ink-50 p-2 text-[11px]"
        data-testid="mcp-execution-log"
      >
        {events.length === 0 ? (
          <p className="text-muted-foreground">
            Esperando eventos del MCP server…
          </p>
        ) : (
          <ul className="space-y-0.5 font-mono">
            {events.map((evt, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-fulkro-ink-500">
                  {new Date(evt.ts).toLocaleTimeString("es-ES", {
                    hour12: false,
                  })}
                </span>
                <span className="font-semibold text-fulkro-title">
                  [{evt.type}]
                </span>
                <span className="truncate">
                  {(evt.data.message as string) ??
                    (evt.data.progress !== undefined
                      ? `progress=${evt.data.progress}`
                      : JSON.stringify(evt.data).slice(0, 80))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
