"use client";

import {
  AlertCircle,
  BadgeCheck,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Download,
  ExternalLink,
  Loader2,
  Shield,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { AuditScheduleCountdown } from "@/components/conformity/AuditScheduleCountdown";
import { DistintivoDownload } from "@/components/conformity/DistintivoDownload";
import { InesAnnualReportPanel } from "@/components/conformity/InesAnnualReportPanel";
import { LuciaSubmissionsPanel } from "@/components/conformity/LuciaSubmissionsPanel";
import { RenewalClock } from "@/components/retainer/RetainerBadges";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import {
  conformityKeys,
  useConformity,
  useExternalExports,
  useRenewal,
  useRevalidateRoute,
  useRouteHistory,
  useConformitySubmissionsList,
} from "@/hooks/useConformity";
import { getConformityStatusLifecycle } from "@/lib/api/conformity";
import { cn, formatDay } from "@/lib/utils";

type UiState =
  | "DRAFT"
  | "LOCKED"
  | "PREPARING"
  | "SUBMITTED"
  | "AUDITED"
  | "CONFORMANT";

type UiSubmissionState =
  | "NOT_STARTED"
  | "PENDING"
  | "COMPLETED"
  | "REJECTED";

const STATES: UiState[] = [
  "LOCKED",
  "PREPARING",
  "SUBMITTED",
  "AUDITED",
  "CONFORMANT",
];

const STATE_LABEL: Record<UiState, string> = {
  DRAFT: "Borrador",
  LOCKED: "Cerrado",
  PREPARING: "Preparando",
  SUBMITTED: "Enviado",
  AUDITED: "Auditado",
  CONFORMANT: "Conforme",
};

const SUBMISSION_LABEL: Record<UiSubmissionState, string> = {
  NOT_STARTED: "No iniciado",
  PENDING: "Pendiente",
  COMPLETED: "Completado",
  REJECTED: "Rechazado",
};

const SUBMISSION_STYLES: Record<UiSubmissionState, string> = {
  NOT_STARTED:
    "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
  PENDING: "bg-fulkro-warning/10 text-fulkro-warning",
  COMPLETED: "bg-fulkro-success/10 text-fulkro-success",
  REJECTED: "bg-fulkro-danger/10 text-fulkro-danger",
};

interface UiSubmissionRow {
  id: string;
  system: string;
  state: UiSubmissionState;
  submitted_at: string | null;
  proof_code: string | null;
}

function backendStatusToUi(state: string | undefined): UiSubmissionState {
  switch (state) {
    case "COMPLETED":
    case "completed":
      return "COMPLETED";
    case "REJECTED":
    case "rejected":
      return "REJECTED";
    case "PENDING":
    case "pending":
    case "SUBMITTED":
    case "submitted":
      return "PENDING";
    default:
      return "NOT_STARTED";
  }
}

// FIX (bug-hunt 2026-06-14): el backend devuelve el RouteState CANÓNICO
// (route_machine.py: ROUTE_PENDING/ROUTE_LOCKED/DECLARATION_IN_PROGRESS/…),
// no las 6 etiquetas de UI. Antes cualquier valor canónico caía a "DRAFT" →
// el stepper se quedaba siempre en "Borrador". Mapeo explícito backend→UI.
const ROUTE_STATE_TO_UI: Record<string, UiState> = {
  ROUTE_PENDING: "DRAFT",
  ROUTE_LOCKED: "LOCKED",
  DECLARATION_IN_PROGRESS: "PREPARING",
  CERTIFICATION_IN_PROGRESS: "PREPARING",
  READY_FOR_DECLARATION: "PREPARING",
  READY_FOR_AUDITOR: "PREPARING",
  UNDER_REVIEW: "SUBMITTED",
  OBSERVED: "AUDITED",
  CORRECTION_REQUIRED: "AUDITED",
  CONFORMANT: "CONFORMANT",
  REGISTERED: "CONFORMANT",
  ACTIVE: "CONFORMANT",
  RENEWAL_DUE: "CONFORMANT",
  RENEWAL_PENDING: "CONFORMANT",
  EXPIRED: "CONFORMANT",
  SUSPENDED: "CONFORMANT",
};

function safeRouteState(state: string | undefined): UiState {
  if (!state) return "DRAFT";
  // valores ya en formato UI (retrocompat) o el mapeo canónico
  if (
    state === "LOCKED" || state === "PREPARING" || state === "SUBMITTED" ||
    state === "AUDITED" || state === "CONFORMANT" || state === "DRAFT"
  ) {
    return state as UiState;
  }
  return ROUTE_STATE_TO_UI[state] ?? "DRAFT";
}

function dateDiffDays(target: string | null): number {
  if (!target) return 0;
  const ms = new Date(target).getTime() - Date.now();
  return Math.max(0, Math.round(ms / (1000 * 60 * 60 * 24)));
}

export function ConformityConsole({ projectId }: { projectId: string }) {
  const { data: status, isLoading: loadingStatus } = useConformity(projectId);
  const { data: submissions } = useConformitySubmissionsList(projectId);
  const { data: exports } = useExternalExports(projectId);
  const { data: renewal } = useRenewal(projectId);
  const { data: routeHistory } = useRouteHistory(projectId);
  const revalidate = useRevalidateRoute(projectId);
  const qc = useQueryClient();

  const busy = revalidate.isPending;
  const isLoading = loadingStatus;

  if (isLoading || !status) {
    return (
      <div className="flex h-32 items-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
        <Loader2 size={14} className="animate-spin" /> cargando conformidad...
      </div>
    );
  }

  const route = status.route;
  const currentState = safeRouteState(route?.state);
  const category = (route?.category as "BASICA" | "MEDIA" | "ALTA" | undefined) ?? "BASICA";

  const expiresAt = route?.next_review_due ?? renewal?.target_renewal_date ?? null;
  const tMinusDays = renewal?.days_remaining ?? dateDiffDays(expiresAt);

  const overlayCode = route?.overlay_code ?? null;

  const uiSubmissions: UiSubmissionRow[] = (submissions?.items ?? []).map(
    (s) => ({
      id: s.id,
      system: s.external_system ?? s.submission_type,
      state: backendStatusToUi(s.status),
      submitted_at: s.submitted_at,
      proof_code: s.external_ref_id,
    }),
  );

  const externalExportsReady = (exports ?? []).filter((e) => e.proof_uploaded)
    .length;

  const timeline = buildTimelineFromHistory(routeHistory?.history ?? []);

  // S16 fix: antes era un stub (setTimeout + toast). El "asistente" re-valida
  // la ruta de conformidad contra sus invariantes (revalidate · endpoint real
  // POST /conformity/projects/{id}/route/revalidate) y devuelve al usuario las
  // incidencias detectadas, que es exactamente la consulta que aporta valor.
  async function runAssistant() {
    try {
      await revalidate.mutateAsync();
      const fresh = await qc.fetchQuery({
        queryKey: conformityKeys.status(projectId),
        queryFn: () => getConformityStatusLifecycle(projectId),
      });
      if (fresh.invariants_ok) {
        toast.success("Ruta de conformidad revalidada · sin incidencias");
      } else {
        const detail =
          fresh.invariant_violations.length > 0
            ? fresh.invariant_violations.join(" · ")
            : "incidencias detectadas en la ruta";
        toast.warning(`Revisar conformidad: ${detail}`);
      }
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "No se pudo revalidar la conformidad",
      );
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4 p-5">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Ruta de conformidad <InfoTag term="ENS" display="ENS" /> {category}
            </p>
            <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
              {STATE_LABEL[currentState]}
            </h1>
            {expiresAt && (
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Vigente hasta {formatDay(expiresAt)}
              </p>
            )}
            {!expiresAt && (
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Sin fecha de revision asignada
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {expiresAt && (
              <RenewalClock
                tMinusDays={tMinusDays}
                expiresAt={expiresAt}
              />
            )}
            <Button
              variant="primary"
              size="md"
              onClick={runAssistant}
              disabled={busy}
            >
              {busy ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : (
                <Sparkles size={14} strokeWidth={2.4} />
              )}
              Consultar Asistente
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Maquina de estados</CardTitle>
        </CardHeader>
        <CardContent>
          <StateMachineView current={currentState} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Envios</CardTitle>
          </CardHeader>
          <CardContent>
            {uiSubmissions.length === 0 ? (
              <p className="inline-flex items-center gap-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                <AlertCircle size={12} strokeWidth={2.4} /> Sin envios registrados.
              </p>
            ) : (
              <ul className="space-y-2">
                {uiSubmissions.map((sub) => (
                  <SubmissionRow key={sub.id} submission={sub} />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <aside className="flex flex-col gap-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <Shield size={22} strokeWidth={2.2} /> Capa activa
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {overlayCode ? (
                <>
                  <p className="font-bold text-[color:var(--fulkro-title)]">
                    {overlayCode}
                  </p>
                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    Overlay aplicado a la ruta de conformidad.
                  </p>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold",
                      "bg-fulkro-success/10 text-fulkro-success",
                    )}
                  >
                    <BadgeCheck size={12} strokeWidth={2.4} /> Validado
                  </span>
                </>
              ) : (
                <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  Sin capa aplicable detectada.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <Clock size={22} strokeWidth={2.2} /> Cronologia ruta
              </CardTitle>
            </CardHeader>
            <CardContent>
              {timeline.length === 0 ? (
                <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                  Sin transiciones registradas.
                </p>
              ) : (
                <ol className="relative space-y-3 pl-4">
                  <span className="absolute left-[7px] top-2 bottom-2 w-px bg-fulkro-ink-300/70" />
                  {timeline.map((m) => (
                    <li key={m.id} className="relative text-xs">
                      <span
                        className={cn(
                          "absolute -left-[13px] top-1 h-3 w-3 rounded-full border-2 border-fulkro-ink-50",
                          m.done ? "bg-fulkro-success" : "bg-fulkro-ink-300",
                        )}
                        aria-hidden
                      />
                      <p className="font-bold text-[color:var(--fulkro-title)]">
                        {m.label}
                      </p>
                      <p className="text-fulkro-ink-500">
                        {m.at_label}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <Download size={22} strokeWidth={2.2} /> Exportaciones externas
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-base font-medium text-[color:var(--fulkro-body)]">
                {externalExportsReady} exportaci
                {externalExportsReady !== 1 ? "ones" : "on"} list
                {externalExportsReady !== 1 ? "as" : "a"} para descarga (
                <InfoTag term="PILAR" display="PILAR" />/
                <InfoTag term="LUCIA" display="LUCIA" />/
                <InfoTag term="INES" display="INES" />).
              </p>
              <Button variant="outline" size="sm" className="w-full">
                <Download size={14} strokeWidth={2.4} /> Descargar ultimo envio
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
      <DistintivoDownload projectId={projectId} />
      <AuditScheduleCountdown projectId={projectId} />
      <LuciaSubmissionsPanel projectId={projectId} />
      <InesAnnualReportPanel projectId={projectId} />
    </div>
  );
}

interface TimelineMilestone {
  id: string;
  label: string;
  at_label: string;
  done: boolean;
}

function buildTimelineFromHistory(
  history: { from_state: string | null; to_state: string; at: string }[],
): TimelineMilestone[] {
  return history.map((h, idx) => ({
    id: `m-${idx}`,
    label: `${h.from_state ?? "INICIO"} -> ${h.to_state}`,
    at_label: formatDay(h.at),
    done: true,
  }));
}

function StateMachineView({ current }: { current: UiState }) {
  const icons: Record<UiState, LucideIcon> = {
    DRAFT: Circle,
    LOCKED: Circle,
    PREPARING: Circle,
    SUBMITTED: ExternalLink,
    AUDITED: Calendar,
    CONFORMANT: CheckCircle2,
  };
  const currentIdx = STATES.indexOf(current);
  return (
    <ol className="flex flex-wrap items-center gap-2">
      {STATES.map((state, idx) => {
        const Icon = icons[state];
        const done = idx < currentIdx;
        const active = idx === currentIdx;
        const last = idx === STATES.length - 1;
        return (
          <li key={state} className="flex items-center gap-2">
            <div
              className={cn(
                "flex items-center gap-2 rounded-md border px-3 py-1.5",
                done &&
                  "border-fulkro-success/40 bg-fulkro-success/10 text-fulkro-success",
                active &&
                  "border-fulkro-primary-700 bg-fulkro-primary-700 text-white",
                !done &&
                  !active &&
                  "border-[color:var(--fulkro-surface-glass-border)] text-fulkro-ink-500",
              )}
            >
              <Icon size={14} strokeWidth={2.4} />
              <span className="text-xs font-semibold uppercase tracking-wider">
                {STATE_LABEL[state]}
              </span>
            </div>
            {!last && (
              <span
                className={cn(
                  "h-0.5 w-6",
                  done ? "bg-fulkro-success" : "bg-fulkro-ink-300/70",
                )}
                aria-hidden
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function SubmissionRow({ submission }: { submission: UiSubmissionRow }) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm">
      <div className="min-w-0">
        <p className="font-bold text-[color:var(--fulkro-title)]">
          {submission.system}
        </p>
        <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
          {submission.submitted_at
            ? `Enviado ${formatDay(submission.submitted_at)}`
            : "Sin envio"}
          {submission.proof_code ? ` - ${submission.proof_code}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-bold",
            SUBMISSION_STYLES[submission.state],
          )}
        >
          {SUBMISSION_LABEL[submission.state]}
        </span>
        {submission.state === "NOT_STARTED" && (
          <Button variant="outline" size="sm">
            Iniciar
          </Button>
        )}
        {submission.state === "PENDING" && (
          <Button variant="outline" size="sm">
            Exportar
          </Button>
        )}
      </div>
    </li>
  );
}