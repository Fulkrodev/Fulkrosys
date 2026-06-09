"use client";

/**
 * NotificationsDlqWidget · Sesión 3B-2B.11 Phase 11.3 admin visibility
 * failed notifications (retry_count >= 3) cross-cliente.
 *
 * R23 admin top-level legitimate · operations console embed.
 * R30 admin tutor friendly · explains DLQ semántica + reprocess action UX.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { notificationsDlqApi } from "@/lib/api/notifications-dlq";

export function NotificationsDlqWidget() {
  const queryClient = useQueryClient();

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["notifications-dlq-summary"],
    queryFn: () => notificationsDlqApi.summary(),
    refetchInterval: 60_000,
  });

  const { data: entries } = useQuery({
    queryKey: ["notifications-dlq-list"],
    queryFn: () => notificationsDlqApi.list({ limit: 10 }),
    enabled: !!summary && summary.total_count > 0,
  });

  const reprocessMutation = useMutation({
    mutationFn: (event_id: string) => notificationsDlqApi.reprocess(event_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-dlq-summary"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-dlq-list"] });
    },
  });

  return (
    <Card data-testid="notifications-dlq-widget">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle
            className={
              summary && summary.total_count > 0
                ? "h-5 w-5 text-fulkro-warning"
                : "h-5 w-5 text-muted-foreground"
            }
            strokeWidth={2.3}
          />
          DLQ notificaciones ·{" "}
          <TooltipENS text="Dead Letter Queue: notificaciones email/WhatsApp que fallaron 3 veces seguidas. Permite reprocess manual desde aquí." />
        </CardTitle>
        <CardDescription>
          Notificaciones con dispatch fallido (retry exhausted · max 3 intentos).
          Reprocessing reset retry_count → 0 + re-queue Celery worker.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {summaryLoading ? (
          <p className="text-sm text-muted-foreground">Cargando...</p>
        ) : (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <Badge
              variant={summary && summary.total_count > 0 ? "warning" : "success"}
            >
              Total: {summary?.total_count ?? 0}
            </Badge>
            <Badge variant="default">
              Últimas 24h: {summary?.last_24h_count ?? 0}
            </Badge>
          </div>
        )}

        {summary && summary.total_count > 0 && summary.by_event_type && (
          <div className="rounded-md border p-3 text-xs">
            <p className="font-medium mb-1">Por tipo:</p>
            <ul className="grid gap-1 md:grid-cols-2">
              {Object.entries(summary.by_event_type)
                .slice(0, 6)
                .map(([type, count]) => (
                  <li key={type} className="flex items-center justify-between">
                    <span className="font-mono">{type}</span>
                    <Badge variant="default">{count}</Badge>
                  </li>
                ))}
            </ul>
          </div>
        )}

        {entries && entries.items.length > 0 && (
          <ul className="space-y-2" data-testid="notifications-dlq-list">
            {entries.items.slice(0, 5).map((e) => (
              <li
                key={e.event_id}
                className="flex items-center justify-between rounded border p-2 text-xs"
              >
                <div>
                  <p className="font-mono">{e.event_type}</p>
                  <p className="text-muted-foreground">{e.recipient_email}</p>
                  {e.error && (
                    <p className="text-fulkro-danger truncate max-w-xs">
                      {e.error}
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={reprocessMutation.isPending}
                  onClick={() => reprocessMutation.mutate(e.event_id)}
                  data-testid={`dlq-reprocess-${e.event_id}`}
                >
                  <RefreshCcw className="mr-1 h-3 w-3" strokeWidth={2.3} />
                  Reprocesar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
