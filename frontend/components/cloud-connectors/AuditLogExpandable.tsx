"use client";

/**
 * AuditLogExpandable · admin polish Bloque 3+5 v3.12.
 *
 * Audit log expandable per CloudGap · ENAC trazabilidad transparente para
 * Marcos. Muestra cronológicamente todas las state transitions del workflow
 * approval.
 *
 * Per entry: action badge + actor_type + timestamp + notes + metadata JSONB.
 */
import { useState } from "react";
import { ChevronDown, ChevronRight, History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminAuditLog } from "@/hooks/useAdminCloudRemediations";
import {
  ADMIN_LOG_ACTION_LABELS,
  ADMIN_LOG_ACTION_VARIANTS,
  type AdminRemediationLog,
  type AdminRemediationLogAction,
} from "@/lib/api/cloud-remediations-admin";

interface AuditLogExpandableProps {
  projectId: string;
  gapId: string;
  /** Si false · component oculto (e.g. para gaps en estado 'detected' sin history). */
  visible?: boolean;
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-ES", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function LogEntry({ log }: { log: AdminRemediationLog }) {
  const action = log.action as AdminRemediationLogAction;
  const label = ADMIN_LOG_ACTION_LABELS[action] ?? log.action;
  const variant = ADMIN_LOG_ACTION_VARIANTS[action] ?? "outline";
  return (
    <li
      className="flex items-start gap-3 py-2 border-b border-border last:border-0"
      data-testid="audit-log-entry"
    >
      <Badge variant={variant} className="text-[10px] shrink-0 mt-0.5">
        {label}
      </Badge>
      <div className="flex-1 min-w-0 text-xs">
        <div className="text-muted-foreground">
          <span className="font-medium">{log.actor_type}</span>
          {log.actor_user_id && (
            <>
              {" · "}
              <code className="text-[10px]">
                {log.actor_user_id.slice(0, 8)}
              </code>
            </>
          )}
          {" · "}
          {formatTimestamp(log.created_at)}
        </div>
        {log.notes && (
          <p className="text-foreground/80 mt-1 whitespace-pre-line">
            {log.notes}
          </p>
        )}
        {log.metadata && Object.keys(log.metadata).length > 0 && (
          <details className="text-muted-foreground mt-1">
            <summary className="cursor-pointer text-[10px]">
              Metadata
            </summary>
            <pre className="text-[10px] mt-1 bg-muted/40 p-2 rounded overflow-x-auto">
              {JSON.stringify(log.metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </li>
  );
}

export function AuditLogExpandable({
  projectId,
  gapId,
  visible = true,
}: AuditLogExpandableProps) {
  const [expanded, setExpanded] = useState(false);
  const query = useAdminAuditLog(projectId, gapId, expanded && visible);

  if (!visible) return null;

  const logs = query.data?.logs ?? [];

  return (
    <div className="border-t border-border pt-2" data-testid="audit-log-expandable">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setExpanded((v) => !v)}
        className="h-7 px-2 text-xs"
        data-testid="audit-log-toggle"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 mr-1" />
        ) : (
          <ChevronRight className="h-3 w-3 mr-1" />
        )}
        <History className="h-3 w-3 mr-1" />
        Trazabilidad ENAC
      </Button>

      {expanded && (
        <div
          className="mt-2 ml-4 pl-2 border-l border-border"
          data-testid="audit-log-content"
        >
          {query.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : query.isError ? (
            <p className="text-xs text-destructive">
              No se pudo cargar el audit log.
            </p>
          ) : logs.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-2">
              Sin transiciones registradas todavía.
            </p>
          ) : (
            <ul className="space-y-0" data-testid="audit-log-list">
              {logs.map((l) => (
                <LogEntry key={l.id} log={l} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
