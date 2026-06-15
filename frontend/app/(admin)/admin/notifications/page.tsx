"use client";

/**
 * /admin/notifications · centro de eventos NotificationOrchestrator
 * (MB-16.5 ADR-039).
 *
 * Diagnostic: listado eventos últimos N · filtro status + event_type ·
 * acción redispatch para events failed.
 */
import { Bell, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { EventsTable } from "@/components/notifications/EventsTable";
import {
  listNotificationEventsAdmin,
  redispatchNotificationEventAdmin,
} from "@/lib/notifications/api";
import type {
  NotificationEvent,
  NotificationStatus,
} from "@/lib/notifications/schemas";
import { NOTIFICATION_STATUSES } from "@/lib/notifications/schemas";

type StatusFilter = NotificationStatus | "all";

export default function AdminNotificationsPage() {
  const [events, setEvents] = useState<NotificationEvent[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listNotificationEventsAdmin({
      status: statusFilter === "all" ? undefined : statusFilter,
      event_type: eventTypeFilter.trim() || undefined,
      limit: 100,
    })
      .then((res) => {
        if (cancelled) return;
        setEvents(res.items);
        setTotal(res.total);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "No se pudieron cargar los eventos",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [statusFilter, eventTypeFilter, refreshKey]);

  const summary = useMemo(() => {
    const counts: Record<NotificationStatus, number> = {
      queued: 0,
      dispatching: 0,
      delivered: 0,
      failed: 0,
      suppressed_dnd: 0,
    };
    for (const e of events) counts[e.status] = (counts[e.status] ?? 0) + 1;
    return counts;
  }, [events]);

  return (
    <div className="mx-auto max-w-6xl py-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Bell className="h-6 w-6 text-fulkro-primary-500" />
          <div>
            <h1 className="text-2xl font-semibold text-fulkro-ink-900">
              Notificaciones
            </h1>
            <p className="text-sm text-fulkro-ink-500">
              Diagnóstico y reintento manual del orquestador.
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setRefreshKey((k) => k + 1)}
          data-testid="btn-refresh-events"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Recargar
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {NOTIFICATION_STATUSES.map((s) => (
          <Card key={s} data-testid={`stat-card-${s}`}>
            <CardContent className="py-3">
              <p className="text-xs text-fulkro-ink-500 uppercase">{s}</p>
              <p className="text-xl font-semibold">{summary[s]}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Eventos recientes</CardTitle>
          <CardDescription>
            Total: {total} · mostrando hasta 100 por página.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1">
              <Label htmlFor="status-filter">Estado</Label>
              <Select
                value={statusFilter}
                onValueChange={(v) => setStatusFilter(v as StatusFilter)}
              >
                <SelectTrigger
                  id="status-filter"
                  data-testid="select-status-filter"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {NOTIFICATION_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="event-type-filter">Tipo de evento</Label>
              <Input
                id="event-type-filter"
                placeholder="ej. task_assigned"
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                data-testid="input-event-type-filter"
              />
            </div>
          </div>

          {error ? (
            <div
              role="alert"
              className="rounded-md bg-fulkro-danger-50 px-3 py-2 text-sm text-fulkro-danger-700"
              data-testid="events-load-error"
            >
              {error}
            </div>
          ) : null}

          <EventsTable
            events={events}
            loading={loading}
            onRedispatch={async (eventId) => {
              const result = await redispatchNotificationEventAdmin(eventId);
              setRefreshKey((k) => k + 1);
              return result;
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
