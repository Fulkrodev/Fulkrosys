"use client";

import * as React from "react";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ExternalLink,
  FileText,
  GraduationCap,
  Inbox as InboxIcon,
  Loader2,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useDismiss,
  useInbox,
  useMarkActioned,
  useMarkRead,
} from "@/hooks/useClientNotifications";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { useClientProjectId } from "@/hooks/useClientProjectId";
import type { ClientNotification } from "@/lib/client-notifications/api";

type FilterMode = "unread" | "all";

const TYPE_META: Record<string, { label: string; icon: typeof Bell }> = {
  evidence_request: { label: "Aportar evidencia", icon: FileText },
  acta_review: { label: "Firmar acta", icon: FileText },
  retainer_offer: { label: "Oferta retainer", icon: Sparkles },
  retainer_reconsideration: { label: "Reconsidera retainer", icon: Sparkles },
  onboarding_ready: { label: "Onboarding listo", icon: Sparkles },
  invoice_review: { label: "Revisar factura", icon: FileText },
  risk_validation: { label: "Validar riesgo", icon: ShieldAlert },
  compliance_confirmation: { label: "Confirmar conformidad", icon: CheckCircle2 },
  meeting_invite: { label: "Reunión", icon: Bell },
  scope_change_validation: { label: "Validar cambio scope", icon: AlertTriangle },
  incident_report: { label: "Incidente", icon: ShieldAlert },
  nps_survey: { label: "Encuesta NPS", icon: Sparkles },
  vote_request: { label: "Voto comité", icon: Sparkles },
  report_available: { label: "Reporte disponible", icon: FileText },
  renewal_campaign: { label: "Renovación", icon: Sparkles },
  info_request: { label: "Información", icon: FileText },
  generic_alert: { label: "Alerta", icon: AlertTriangle },
};

const PRIORITY_VARIANT: Record<string, "secondary" | "info" | "warning" | "danger"> = {
  low: "secondary",
  normal: "info",
  high: "warning",
  urgent: "danger",
};

const PRIORITY_LABEL: Record<string, string> = {
  low: "baja",
  normal: "normal",
  high: "alta",
  urgent: "urgente",
};

function formatRelative(iso: string): string {
  const dt = new Date(iso);
  const diffMs = Date.now() - dt.getTime();
  const min = Math.floor(diffMs / 60_000);
  if (min < 1) return "ahora";
  if (min < 60) return `${min} min`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

export function NotificationsInboxPanel() {
  const [filter, setFilter] = React.useState<FilterMode>("unread");
  const { data, isLoading } = useInbox({
    include_read: filter === "all",
  });
  const markReadMutation = useMarkRead();
  const dismissMutation = useDismiss();
  const markActionedMutation = useMarkActioned();

  // Sesión 3B-2B.8 CLUSTER 2 Phase 2D · SSE auto-refetch on
  // `client_notification.created` (DRY centralizado · emit_client_notification
  // dispatches SSE post-persist · NotificationsInboxPanel invalidates inbox
  // queries realtime · polling 30s fallback preserved si EventSource fails).
  const { projectId } = useClientProjectId();
  useClientProjectEvents(projectId, {
    enabled: Boolean(projectId),
    invalidateQueries: [["client-inbox"]],
  });

  const items = data?.notifications ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Bell size={18} className="text-fulkro-primary-700" />
            <CardTitle className="text-base">
              Notificaciones
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({items.length})
              </span>
            </CardTitle>
            <TooltipENS term="inbox_cliente" />
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Button
              type="button"
              size="sm"
              variant={filter === "unread" ? "primary" : "outline"}
              onClick={() => setFilter("unread")}
            >
              No leídas
            </Button>
            <Button
              type="button"
              size="sm"
              variant={filter === "all" ? "primary" : "outline"}
              onClick={() => setFilter("all")}
            >
              Todas
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-fulkro-ink-500">
            <Loader2 className="size-4 animate-spin" />
            Cargando notificaciones…
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <InboxIcon className="size-8" />
            <p className="text-sm">
              {filter === "unread"
                ? "Todo al día · sin notificaciones nuevas"
                : "Sin notificaciones"}
            </p>
          </div>
        ) : (
          items.map((n) => (
            <NotificationCard
              key={n.id}
              notification={n}
              onMarkRead={() => markReadMutation.mutate(n.id)}
              onDismiss={() => dismissMutation.mutate(n.id)}
              onActioned={() => markActionedMutation.mutate(n.id)}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function NotificationCard({
  notification,
  onMarkRead,
  onDismiss,
  onActioned,
}: {
  notification: ClientNotification;
  onMarkRead: () => void;
  onDismiss: () => void;
  onActioned: () => void;
}) {
  const meta = TYPE_META[notification.type] ?? TYPE_META.generic_alert;
  const Icon = meta.icon;
  const isRead = notification.read_at !== null;
  const priorityVariant = PRIORITY_VARIANT[notification.priority] ?? "info";

  return (
    <div
      className={cn(
        "rounded-lg border p-3 transition-colors",
        isRead
          ? "border-fulkro-ink-100 bg-fulkro-canvas"
          : "border-fulkro-primary-700 bg-white",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <Icon className="mt-0.5 size-4 text-fulkro-ink-500" />
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">{notification.title}</span>
              <Badge variant={priorityVariant}>
                {PRIORITY_LABEL[notification.priority] ?? notification.priority}
              </Badge>
              {!isRead ? <Badge variant="warning">nuevo</Badge> : null}
            </div>
            {notification.body ? (
              <p className="line-clamp-2 text-xs text-fulkro-ink-500">
                {notification.body}
              </p>
            ) : null}
            <div className="flex items-center gap-2 text-xs text-fulkro-ink-500">
              <span>{meta.label}</span>
              <span>·</span>
              <span>{formatRelative(notification.created_at)}</span>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        {!isRead ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={onMarkRead}
            disabled={isRead}
          >
            Marcar leída
          </Button>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onDismiss}
        >
          <X className="mr-1 size-3" />
          Descartar
        </Button>
        <Link
          href={notification.target_url}
          onClick={onActioned}
          className="inline-flex items-center rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-fulkro-primary-700/90"
        >
          <ExternalLink className="mr-1 size-3" />
          Ir
        </Link>
      </div>
    </div>
  );
}
