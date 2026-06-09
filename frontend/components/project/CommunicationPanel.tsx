/**
 * CommunicationPanel · K.X Comunicaciones al cliente (Motor 18).
 *
 * Vista de plan de comunicación + reportes generados + escalations
 * activas. Reemplaza stub EmptyStateUpcoming consumiendo M18 backend
 * extensivo existing.
 *
 * Backend: m18_communication prefix `/api/v1/communication`.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertOctagon,
  CalendarClock,
  CheckCircle2,
  FileText,
  Loader2,
  MessageSquare,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  communicationApi,
  type CommunicationEscalation,
  type CommunicationPlan,
  type CommunicationReport,
} from "@/lib/api/communication";

export function CommunicationPanel({ projectId }: { projectId: string }) {
  const plan = useQuery<CommunicationPlan>({
    queryKey: ["m18", "plan", projectId],
    queryFn: () => communicationApi.getPlan(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
    retry: false,
  });

  const reports = useQuery({
    queryKey: ["m18", "reports", projectId],
    queryFn: () => communicationApi.listReports(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const escalations = useQuery({
    queryKey: ["m18", "escalations", projectId],
    queryFn: () => communicationApi.listEscalations(projectId, { resuelto: false }),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquare size={16} /> Comunicaciones al cliente (M18)
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Plan de cadencia · reportes generados · escalations activas
          </p>
        </CardHeader>
      </Card>

      <PlanCard query={plan} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileText size={14} /> Reportes
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reports.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : reports.isError ? (
            <Alert variant="danger">
              <AlertTitle>No se pudieron cargar los reportes</AlertTitle>
              <AlertDescription>
                {reports.error instanceof Error
                  ? reports.error.message
                  : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !reports.data || reports.data.reports.length === 0 ? (
            <EmptyState
              title="Sin reportes generados"
              description="Cuando se genere el primer reporte aparecerá aquí."
            />
          ) : (
            <ul className="space-y-1.5">
              {reports.data.reports.slice(0, 20).map((r) => (
                <ReportRow key={r.id} report={r} />
              ))}
              {reports.data.reports.length > 20 ? (
                <li className="pt-1 text-[11px] text-fulkro-ink-500">
                  …y {reports.data.reports.length - 20} más
                </li>
              ) : null}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <AlertOctagon size={14} className="text-amber-600" />
            Escalations activas
          </CardTitle>
        </CardHeader>
        <CardContent>
          {escalations.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
            </div>
          ) : escalations.isError ? (
            <Alert variant="danger">
              <AlertTitle>No se pudieron cargar las escalations</AlertTitle>
              <AlertDescription>
                {escalations.error instanceof Error
                  ? escalations.error.message
                  : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : !escalations.data ||
            escalations.data.escalations.length === 0 ? (
            <div className="flex items-center gap-2 text-xs text-fulkro-ink-700">
              <CheckCircle2 size={12} className="text-fulkro-success" /> Sin
              escalations activas
            </div>
          ) : (
            <ul className="space-y-1.5">
              {escalations.data.escalations.map((e) => (
                <EscalationRow key={e.id} item={e} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function PlanCard({
  query,
}: {
  query: ReturnType<typeof useQuery<CommunicationPlan>>;
}) {
  if (query.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-4 text-xs text-fulkro-ink-500">
          <Loader2 size={12} className="animate-spin" /> cargando plan…
        </CardContent>
      </Card>
    );
  }
  // 404 o error → mostrar EmptyState (plan aún no creado)
  if (query.isError || !query.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <CalendarClock size={14} /> Plan de comunicación
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-fulkro-ink-500">
            Plan de cadencia aún no configurado para este proyecto.
          </p>
        </CardContent>
      </Card>
    );
  }
  const plan = query.data;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2 text-sm">
          <span className="flex items-center gap-2">
            <CalendarClock size={14} /> Plan de comunicación
          </span>
          {plan.estado ? (
            <Badge variant="secondary">{plan.estado}</Badge>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-y-1 text-xs">
        <span className="text-fulkro-ink-500">Cadencia</span>
        <span className="font-mono text-fulkro-ink-700">
          {plan.cadencia ?? "—"}
        </span>
        <span className="text-fulkro-ink-500">Destinatarios</span>
        <span className="text-fulkro-ink-700">
          {plan.destinatarios && plan.destinatarios.length
            ? plan.destinatarios.join(", ")
            : "—"}
        </span>
        {plan.activated_at ? (
          <>
            <span className="text-fulkro-ink-500">Activado</span>
            <span className="text-fulkro-ink-700">
              {new Date(plan.activated_at).toLocaleDateString()}
            </span>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ReportRow({ report }: { report: CommunicationReport }) {
  return (
    <li className="flex items-start justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {report.titulo ?? `Reporte ${report.id.slice(0, 8)}`}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[10px] text-fulkro-ink-500">
          {report.tipo ? <span>{report.tipo}</span> : null}
          {report.fecha_periodo ? <span>· {report.fecha_periodo}</span> : null}
          {report.sent_at ? (
            <span>· enviado {new Date(report.sent_at).toLocaleDateString()}</span>
          ) : null}
        </p>
      </div>
      {report.estado ? (
        <Badge variant="outline" className="shrink-0">
          {report.estado}
        </Badge>
      ) : null}
    </li>
  );
}

function EscalationRow({ item }: { item: CommunicationEscalation }) {
  const sevTone =
    item.severidad === "critica" || item.severidad === "alta"
      ? "warning"
      : "secondary";
  return (
    <li className="flex items-start justify-between gap-3 rounded-md border border-amber-200 bg-amber-50/40 px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {item.evento_tipo ?? "Escalation"}
        </p>
        {item.detalle ? (
          <p className="mt-0.5 truncate text-[11px] text-fulkro-ink-500">
            {item.detalle}
          </p>
        ) : null}
        {item.detected_at ? (
          <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
            {new Date(item.detected_at).toLocaleString()}
          </p>
        ) : null}
      </div>
      {item.severidad ? (
        <Badge variant={sevTone} className="shrink-0">
          {item.severidad}
        </Badge>
      ) : null}
    </li>
  );
}
