"use client";

/**
 * Tabla eventos NotificationOrchestrator (admin · MB-16.5 ADR-039).
 *
 * Diagnostic listado con status badges + acción redispatch para
 * eventos failed. Filter dropdowns status + event_type.
 */
import { Inbox, RefreshCw, Send } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import type {
  NotificationEvent,
  NotificationStatus,
  RedispatchResponse,
} from "@/lib/notifications/schemas";

interface EventsTableProps {
  events: NotificationEvent[];
  onRedispatch: (eventId: string) => Promise<RedispatchResponse>;
  loading?: boolean;
}

function statusBadgeVariant(
  status: NotificationStatus,
): "success" | "warning" | "danger" | "info" | "secondary" {
  switch (status) {
    case "delivered":
      return "success";
    case "failed":
      return "danger";
    case "queued":
    case "dispatching":
      return "info";
    case "suppressed_dnd":
      return "warning";
    default:
      return "secondary";
  }
}

function statusLabel(status: NotificationStatus): string {
  switch (status) {
    case "delivered":
      return "Entregada";
    case "failed":
      return "Fallida";
    case "queued":
      return "En cola";
    case "dispatching":
      return "Enviando";
    case "suppressed_dnd":
      return "Silenciada (DND)";
    default:
      return status;
  }
}

export function EventsTable({
  events,
  onRedispatch,
  loading,
}: EventsTableProps) {
  const [redispatching, setRedispatching] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    eventId: string;
    message: string;
    error: boolean;
  } | null>(null);

  async function handleRedispatch(eventId: string) {
    setRedispatching(eventId);
    setFeedback(null);
    try {
      const result = await onRedispatch(eventId);
      setFeedback({
        eventId,
        message: `Redispatch ${result.status}`,
        error: result.status === "failed",
      });
    } catch (err) {
      setFeedback({
        eventId,
        message:
          err instanceof Error
            ? err.message
            : "Error al re-dispatchar el evento",
        error: true,
      });
    } finally {
      setRedispatching(null);
    }
  }

  if (loading) {
    return (
      <div
        className="text-sm text-fulkro-ink-500 py-8 text-center"
        data-testid="events-loading"
      >
        Cargando eventos...
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-2 py-12 text-center"
        data-testid="events-empty"
      >
        <Inbox className="h-12 w-12 text-fulkro-ink-300" />
        <p className="text-sm text-fulkro-ink-500">
          No hay eventos en el rango seleccionado.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto" data-testid="events-table">
      <table aria-label="Eventos de notificación" className="w-full text-sm">
        <thead className="bg-fulkro-ink-50 text-fulkro-ink-700">
          <tr>
            <th className="px-3 py-2 text-left">Evento</th>
            <th className="px-3 py-2 text-left">Destinatario</th>
            <th className="px-3 py-2 text-left">Estado</th>
            <th className="px-3 py-2 text-left">Canales</th>
            <th className="px-3 py-2 text-left">Creado</th>
            <th className="px-3 py-2 text-left">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-fulkro-ink-100">
          {events.map((event) => (
            <tr key={event.id} data-testid={`event-row-${event.id}`}>
              <td className="px-3 py-2">
                <div className="flex flex-col">
                  <span className="font-medium text-fulkro-ink-900">
                    {event.event_type}
                  </span>
                  {event.template_used ? (
                    <span className="text-xs text-fulkro-ink-500">
                      template: {event.template_used}
                    </span>
                  ) : null}
                </div>
              </td>
              <td className="px-3 py-2 text-fulkro-ink-700">
                {event.recipient_email}
              </td>
              <td className="px-3 py-2">
                <Badge
                  variant={statusBadgeVariant(event.status)}
                  data-testid={`event-status-${event.id}`}
                >
                  {statusLabel(event.status)}
                </Badge>
                {event.error ? (
                  <p className="mt-1 text-xs text-fulkro-danger-700 max-w-xs truncate">
                    {event.error}
                  </p>
                ) : null}
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  {(event.channels_succeeded ?? []).map((c) => (
                    <Badge
                      key={`ok-${c}`}
                      variant="success"
                      className="text-[11px]"
                    >
                      ✓ {c}
                    </Badge>
                  ))}
                  {(event.channels_failed ?? []).map((c) => (
                    <Badge
                      key={`fail-${c}`}
                      variant="danger"
                      className="text-[11px]"
                    >
                      ✗ {c}
                    </Badge>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 text-fulkro-ink-500 text-xs">
                {new Date(event.created_at).toLocaleString("es-ES")}
              </td>
              <td className="px-3 py-2">
                {event.status === "failed" ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={redispatching === event.id}
                    onClick={() => handleRedispatch(event.id)}
                    data-testid={`btn-redispatch-${event.id}`}
                  >
                    {redispatching === event.id ? (
                      <>
                        <RefreshCw className="mr-1 h-3 w-3 animate-spin" />
                        Reintentando...
                      </>
                    ) : (
                      <>
                        <Send className="mr-1 h-3 w-3" />
                        Reintentar
                      </>
                    )}
                  </Button>
                ) : (
                  <span className="text-xs text-fulkro-ink-600">—</span>
                )}
                {feedback && feedback.eventId === event.id ? (
                  <p
                    className={`mt-1 text-xs ${feedback.error ? "text-fulkro-danger-700" : "text-fulkro-success-700"}`}
                    data-testid={`feedback-${event.id}`}
                  >
                    {feedback.message}
                  </p>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
