"use client";

/**
 * RecentActivityCard · admin home proyecto activity feed
 * (SAN-D MB-19.16 cosecha · DEC-MB13-RECENT-ACTIVITY-CARD).
 *
 * Agrega últimas N actividades del proyecto desde:
 * - ClientUserAudit hash chain rows (login · evidence_uploaded · etc)
 * - ClientTask transitions (lifecycle pending → done)
 *
 * Cache TanStack `recent-activity` · refetch interval 60s · stale 30s
 * (mismo pattern ActiveAlertsCard MB-14).
 *
 * Foundation MB-14.1 hash chain queryable + MB-14.3 ClientTaskService
 * lifecycle existing.
 *
 * Refs: ADR-035 · DEC-MB13-RECENT-ACTIVITY-CARD asignado MB-19.
 */

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  Clock,
  FileUp,
  LogIn,
  ShieldCheck,
  UserPlus,
  XCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

interface ActivityItem {
  id: string;
  type: "audit" | "task";
  action: string;
  label: string;
  actor_email: string | null;
  metadata: Record<string, unknown>;
  occurred_at: string | null;
}

interface RecentActivityResponse {
  items: ActivityItem[];
  total: number;
}

async function fetchRecentActivity(
  projectId: string,
): Promise<RecentActivityResponse> {
  return api<RecentActivityResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/recent-activity?limit=20`,
  );
}

/**
 * Icon resolver per action type · semantic visual coherence.
 */
function ActivityIcon({ action }: { action: string }) {
  const className = "h-4 w-4";
  if (action.startsWith("login_success") || action === "LOGIN") {
    return <LogIn className={className} aria-hidden="true" />;
  }
  if (action === "login_failure" || action === "account_locked") {
    return <XCircle className={className} aria-hidden="true" />;
  }
  if (action === "evidence_uploaded") {
    return <FileUp className={className} aria-hidden="true" />;
  }
  if (action === "task_completed") {
    return <CheckCircle2 className={className} aria-hidden="true" />;
  }
  if (action === "task_started") {
    return <Clock className={className} aria-hidden="true" />;
  }
  if (action === "user_created" || action === "first_access_completed") {
    return <UserPlus className={className} aria-hidden="true" />;
  }
  if (action === "totp_enabled" || action === "password_change") {
    return <ShieldCheck className={className} aria-hidden="true" />;
  }
  return <Activity className={className} aria-hidden="true" />;
}

/**
 * Formato relativo · "hace X días/horas/min" para occurred_at.
 * Evita Intl.RelativeTimeFormat para soportar SSR sin locale config.
 */
function formatRelative(iso: string | null): string {
  if (!iso) return "";
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const diffMs = now - then;
    const diffMin = Math.floor(diffMs / 60_000);
    if (diffMin < 1) return "ahora";
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `hace ${diffHr} h`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `hace ${diffDay} d`;
    return new Date(iso).toLocaleDateString("es-ES");
  } catch {
    return "";
  }
}

interface RecentActivityCardProps {
  projectId: string;
}

export function RecentActivityCard({ projectId }: RecentActivityCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["recent-activity", projectId],
    queryFn: () => fetchRecentActivity(projectId),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <Card data-testid="recent-activity-card-skeleton">
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return null;
  }

  const items = data.items;

  return (
    <Card data-testid="recent-activity-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5" aria-hidden="true" />
          Actividad reciente
          {items.length > 0 && ` (${items.length})`}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Sin actividad registrada para este proyecto
          </p>
        ) : (
          <ul className="space-y-2" role="list">
            {items.slice(0, 8).map((item) => (
              <li
                key={item.id}
                className="flex items-start gap-3 rounded-md border-l-2 border-l-fulkro-info/40 bg-fulkro-info/5 p-2"
              >
                <span className="mt-0.5 text-fulkro-info">
                  <ActivityIcon action={item.action} />
                </span>
                <div className="flex-1 text-sm">
                  <p className="font-medium">{item.label}</p>
                  {item.actor_email ? (
                    <p className="text-xs text-muted-foreground">
                      {item.actor_email}
                    </p>
                  ) : null}
                  {item.metadata && "title" in item.metadata ? (
                    <p className="text-xs text-muted-foreground">
                      {String(item.metadata.title)}
                    </p>
                  ) : null}
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatRelative(item.occurred_at)}
                </span>
              </li>
            ))}
            {items.length > 8 && (
              <li className="text-xs text-muted-foreground">
                + {items.length - 8} más actividades recientes
              </li>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
