"use client";

/**
 * AutopilotPanel · M8 Autopilot (doc §13).
 *
 * Botón "Continuar Autopilot" (Gate 1 ya superado en el portal cliente:
 * autorización + scope) con selector de categoría BASICA/MEDIA/ALTA. Tras
 * lanzar, muestra progreso live por FASE (recon→detection→normalization→
 * verification→triage→reporting), coverage% live, contadores de severidad,
 * badge run_manifest_hash (determinismo), aviso honesto de run parcial y la
 * lista de herramientas intentadas/fallidas.
 *
 * SSE admin (canal project:{id}) vía GET /api/v1/projects/{id}/events +
 * polling 2s fallback (patrón espejo McpExecutionProgress + useMCPExecution).
 *
 * R23 project-scoped · "Perfecto" = cobertura demostrable + evidencia, NO
 * cero vulnerabilidades (doc §0 honest boundaries).
 */
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Fingerprint,
  Loader2,
  PlayCircle,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  AUTOPILOT_PHASE_LABELS,
  AUTOPILOT_PHASES,
  AUTOPILOT_STATUS_LABELS,
  AUTOPILOT_STATUS_VARIANTS,
  autopilotApi,
  type AutopilotCategory,
  type AutopilotPhase,
  type AutopilotStatus,
} from "@/lib/api/autopilot";
import { autopilotKeys, useAutopilotStatus, useStartAutopilot } from "@/hooks/useAutopilot";
import { cn } from "@/lib/utils";

const CATEGORY_LIST: Array<{
  value: AutopilotCategory;
  title: string;
  description: string;
}> = [
  {
    value: "BASICA",
    title: "Básica",
    description:
      "Pipeline ligero automatizado · cobertura demostrable de lo automatizable. Sin atestación externa.",
  },
  {
    value: "MEDIA",
    title: "Media",
    description:
      "Pipeline ampliado con análisis web y hardening. Cierre automatizado con evidencia ENAC.",
  },
  {
    value: "ALTA",
    title: "Alta (interna)",
    description:
      "Pipeline completo · al finalizar pausa en Gate 2 para validación y atestación de un pentester acreditado (CPSTIC/OSCP).",
  },
];

interface AutopilotPanelProps {
  projectId: string;
  /** Notifica al padre el run activo (para wiring de Gate 2 / Evidence Pack). */
  onRunChange?: (runId: string | null, status: AutopilotStatus | null) => void;
}

function phaseIndex(phase: AutopilotPhase | null): number {
  if (!phase) return -1;
  return AUTOPILOT_PHASES.indexOf(phase);
}

export function AutopilotPanel({ projectId, onRunChange }: AutopilotPanelProps) {
  const qc = useQueryClient();
  const [category, setCategory] = React.useState<AutopilotCategory>("BASICA");
  const [activeRunId, setActiveRunId] = React.useState<string | null>(null);

  const startMutation = useStartAutopilot(projectId);
  // Si no hay run lanzado en esta sesión, consulta el último del proyecto.
  const statusQuery = useAutopilotStatus(projectId, activeRunId);

  const status = statusQuery.data;
  const autopilotStatus: AutopilotStatus | null =
    status?.autopilot_status ?? null;
  const currentRunId = status?.run_id ?? activeRunId;

  // Propaga cambios de run al padre (Gate 2 + Evidence Pack).
  React.useEffect(() => {
    onRunChange?.(currentRunId ?? null, autopilotStatus);
  }, [currentRunId, autopilotStatus, onRunChange]);

  // ── SSE admin (canal project:{id}) · invalida queries en cada evento ──
  React.useEffect(() => {
    if (!projectId || typeof window === "undefined") return;
    const url = autopilotApi.streamUrl(projectId);
    const es = new EventSource(url, { withCredentials: true });

    const invalidate = () => {
      qc.invalidateQueries({ queryKey: autopilotKeys.all(projectId) });
    };
    const onCompleted = (e: MessageEvent) => {
      invalidate();
      try {
        const data = JSON.parse(e.data) as { status?: string };
        if (data.status === "failed") {
          toast.error("Autopilot finalizó con error");
        }
      } catch {
        /* noop */
      }
    };

    es.addEventListener("m08_autopilot_started", invalidate);
    es.addEventListener("m08_phase_change", invalidate);
    es.addEventListener("m08_run_completed", onCompleted);
    es.onerror = () => {
      // Browser auto-reconnect · polling cubre la consistencia.
      // eslint-disable-next-line no-console
      console.debug("Autopilot SSE reconnecting", projectId);
    };

    return () => {
      es.close();
    };
  }, [projectId, qc]);

  async function handleLaunch() {
    try {
      const res = await startMutation.mutateAsync({ category });
      setActiveRunId(res.run_id);
      toast.success(`Autopilot ${res.category} lanzado`, {
        description: `Run ${res.run_id.slice(0, 8)}… · progreso en vivo abajo.`,
      });
    } catch (err) {
      toast.error("No se pudo lanzar el autopilot", {
        description: (err as Error).message,
      });
    }
  }

  const isActive =
    autopilotStatus === "authorized" || autopilotStatus === "running";
  const isLaunching = startMutation.isPending;
  const currentPhaseIdx = phaseIndex(status?.autopilot_phase ?? null);
  const completedPhases = isActive
    ? currentPhaseIdx
    : autopilotStatus === "completed" || autopilotStatus === "partial"
      ? AUTOPILOT_PHASES.length
      : currentPhaseIdx;
  const coveragePct = status?.coverage_pct ?? 0;

  return (
    <Card data-testid="autopilot-panel">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert size={20} className="text-fulkro-primary-700" />
            Autopilot de verificación
          </CardTitle>
          <CardDescription>
            Gate 1 ya autorizado por el cliente (alcance + autorización).{" "}
            <span className="font-semibold">Continúa</span> para ejecutar el
            pipeline automatizado.{" "}
            <TooltipENS
              text="Perfecto = cobertura máxima demostrable de lo automatizable + evidencia reproducible y trazable. NO garantiza ausencia de vulnerabilidades; reporta la cobertura real (doc §0)."
              icon="info"
              iconSize={13}
            />
          </CardDescription>
        </div>
        {autopilotStatus && (
          <Badge variant={AUTOPILOT_STATUS_VARIANTS[autopilotStatus]}>
            {AUTOPILOT_STATUS_LABELS[autopilotStatus]}
          </Badge>
        )}
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {/* Selector de categoría + lanzamiento */}
        <div className="flex flex-col gap-3">
          <div
            className="grid gap-2 md:grid-cols-3"
            role="radiogroup"
            aria-label="Categoría ENS del autopilot"
          >
            {CATEGORY_LIST.map((c) => (
              <button
                key={c.value}
                type="button"
                role="radio"
                aria-checked={category === c.value}
                disabled={isActive || isLaunching}
                onClick={() => setCategory(c.value)}
                className={cn(
                  "rounded-md border p-3 text-left transition-colors disabled:opacity-60",
                  category === c.value
                    ? "border-fulkro-primary-700 bg-fulkro-primary-700/5"
                    : "border-[color:var(--fulkro-surface-glass-border)] hover:bg-fulkro-ink-100",
                )}
              >
                <span className="font-semibold text-fulkro-primary-700">
                  {c.title}
                </span>
                <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                  {c.description}
                </p>
              </button>
            ))}
          </div>
          <div>
            <Button
              onClick={handleLaunch}
              disabled={isActive || isLaunching}
              className="gap-2"
              data-testid="autopilot-continue-btn"
              aria-label={`Continuar autopilot categoría ${category}`}
            >
              {isLaunching ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <PlayCircle size={16} />
              )}
              {isActive ? "Autopilot en curso…" : "Continuar Autopilot"}
            </Button>
          </div>
        </div>

        {/* Progreso por fase */}
        {(isActive || autopilotStatus) && (
          <div
            className="flex flex-col gap-3"
            data-testid="autopilot-phase-progress"
          >
            <div className="flex items-center justify-between">
              <h4 className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                Fases del pipeline
              </h4>
              {currentRunId && (
                <span className="font-mono text-[11px] text-muted-foreground">
                  run #{currentRunId.slice(0, 8)}
                </span>
              )}
            </div>
            <ol className="flex flex-wrap gap-2">
              {AUTOPILOT_PHASES.map((p, i) => {
                const done = i < completedPhases;
                const current = i === currentPhaseIdx && isActive;
                return (
                  <li
                    key={p}
                    aria-label={`Fase ${AUTOPILOT_PHASE_LABELS[p]}: ${
                      done ? "completada" : current ? "en curso" : "pendiente"
                    }`}
                    className={cn(
                      "flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium",
                      done &&
                        "border-fulkro-success/40 bg-fulkro-success/10 text-fulkro-success-700",
                      current &&
                        "border-fulkro-info/40 bg-fulkro-info/10 text-fulkro-info-700",
                      !done &&
                        !current &&
                        "border-[color:var(--fulkro-surface-glass-border)] text-[color:var(--fulkro-muted)]",
                    )}
                  >
                    {done ? (
                      <CheckCircle2 size={13} />
                    ) : current ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <span className="inline-block h-[13px] w-[13px] rounded-full border border-current opacity-50" />
                    )}
                    {AUTOPILOT_PHASE_LABELS[p]}
                  </li>
                );
              })}
            </ol>
          </div>
        )}

        {/* Cobertura live */}
        {(isActive || status) && (
          <div className="flex flex-col gap-1.5" data-testid="autopilot-coverage">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
                Cobertura{" "}
                <TooltipENS
                  text="Porcentaje de activos en alcance efectivamente escaneados. Es la métrica de honestidad: ¿lo probasteis todo?"
                  icon="info"
                  iconSize={12}
                />
              </span>
              <span className="font-semibold text-fulkro-primary-700">
                {coveragePct.toFixed(1)}%
                {status?.assets_in_scope != null && (
                  <span className="ml-1 font-normal text-muted-foreground">
                    ({status.assets_scanned ?? 0}/{status.assets_in_scope} activos)
                  </span>
                )}
              </span>
            </div>
            <Progress
              value={coveragePct}
              color={coveragePct >= 95 ? "success" : "primary"}
              className="h-2"
            />
          </div>
        )}

        {/* Contadores de severidad */}
        {status && (
          <div
            className="flex flex-wrap items-center gap-2"
            data-testid="autopilot-severity-counts"
          >
            <span className="text-sm font-semibold text-[color:var(--fulkro-subtitle)]">
              Hallazgos ({status.total_findings}):
            </span>
            <SeverityChip label="crítico" count={status.critical_count} className="bg-fulkro-danger text-white" />
            <SeverityChip label="alto" count={status.high_count} className="bg-fulkro-danger/70 text-white" />
            <SeverityChip label="medio" count={status.medium_count} className="bg-fulkro-warning text-white" />
            <SeverityChip label="bajo" count={status.low_count} className="bg-fulkro-info text-white" />
            <SeverityChip label="info" count={status.info_count} className="bg-fulkro-ink-300 text-fulkro-ink-700" />
          </div>
        )}

        {/* Determinismo · run_manifest_hash */}
        {status?.run_manifest_hash && (
          <div className="flex items-center gap-2 text-xs" data-testid="autopilot-manifest-hash">
            <Fingerprint size={14} className="text-fulkro-primary-700" />
            <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
              Determinismo{" "}
              <TooltipENS
                text="Hash del manifiesto del run. Dos runs idénticos producen el mismo hash: prueba de reproducibilidad para la auditoría ENAC."
                icon="info"
                iconSize={12}
              />
            </span>
            <code
              className="rounded bg-fulkro-ink-50 px-1.5 py-0.5 font-mono text-[11px] text-fulkro-ink-700"
              title={status.run_manifest_hash}
            >
              {status.run_manifest_hash.slice(0, 16)}…
            </code>
          </div>
        )}

        {/* Aviso honesto de run parcial */}
        {status?.partial_run && (
          <Alert variant="warning" data-testid="autopilot-partial-notice">
            <AlertTriangle size={16} />
            <AlertTitle>Cobertura parcial</AlertTitle>
            <AlertDescription>
              No se pudieron escanear todos los activos en alcance
              ({status.assets_scanned ?? 0}/{status.assets_in_scope ?? 0}). La
              cobertura reportada es honesta: el pack de evidencia refleja
              exactamente lo que se probó.
            </AlertDescription>
          </Alert>
        )}

        {/* Herramientas intentadas / fallidas */}
        {status &&
          (status.tools_attempted.length > 0 ||
            status.tools_failed.length > 0) && (
            <div className="flex flex-col gap-1.5 text-xs" data-testid="autopilot-tools">
              {status.tools_attempted.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
                    Herramientas:
                  </span>
                  {status.tools_attempted.map((t) => (
                    <Badge
                      key={t}
                      variant={
                        status.tools_failed.includes(t) ? "danger" : "success"
                      }
                    >
                      {status.tools_failed.includes(t) ? (
                        <XCircle size={11} className="mr-1" />
                      ) : (
                        <CheckCircle2 size={11} className="mr-1" />
                      )}
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
              {status.tools_failed.length > 0 && (
                <p className="text-fulkro-danger">
                  {status.tools_failed.length} herramienta(s) fallaron · contribuye
                  a la cobertura parcial.
                </p>
              )}
            </div>
          )}

        {/* Errores de carga del estado (404 = aún no hay runs · silenciado) */}
        {statusQuery.isError && (
          <p className="text-xs text-muted-foreground">
            Aún no se ha ejecutado ningún autopilot en este proyecto.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function SeverityChip({
  label,
  count,
  className,
}: {
  label: string;
  count: number;
  className: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
        className,
      )}
      aria-label={`${count} hallazgos de severidad ${label}`}
    >
      <span>{count}</span>
      <span className="opacity-80">{label}</span>
    </span>
  );
}
