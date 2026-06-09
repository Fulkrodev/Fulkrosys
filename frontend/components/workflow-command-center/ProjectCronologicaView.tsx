/**
 * ProjectCronologicaView · vista maestra per-cliente · refactor 1.D.F.0.C v3.11.
 *
 * Cambios 1.D.F.0.C:
 *   - Toggle "Vista AHORA" vs "Vista Completa" top-bar
 *   - Estado persisted en localStorage per project (clave wcc-view-mode:{projectId})
 *   - AHORA sticky pin-to-top delegated WorkflowTimelineAdmin
 *   - CopilotoAdminSidebar recibe activeStep para context-aware guidance 1.D.F.0.D
 */
"use client";

import * as React from "react";
import { ListTree, LayoutList, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useProjectCronologica } from "@/hooks/useWorkflowCommandCenter";
import type { EnrichedStepState } from "@/lib/api/workflow-command-center";

import { CopilotoAdminSidebar } from "./CopilotoAdminSidebar";
import { ProjectContextHeader } from "./ProjectContextHeader";
import { WorkflowBlockersPanel } from "./WorkflowBlockersPanel";
import { WorkflowStepDetailDrawerEnriched } from "./WorkflowStepDetailDrawerEnriched";
import {
  WorkflowTimelineAdmin,
  type WorkflowTimelineViewMode,
} from "./WorkflowTimelineAdmin";

interface ProjectCronologicaViewProps {
  projectId: string;
  initialStepId?: string;
}

const VIEW_MODE_STORAGE_KEY_PREFIX = "wcc-view-mode:";

// 1.D.G.D · viewMode extended con "blockers" (Próximos pasos cross-actor agrupado)
type ExtendedViewMode = WorkflowTimelineViewMode | "blockers";

function getStoredViewMode(projectId: string): ExtendedViewMode {
  if (typeof window === "undefined") return "complete";
  try {
    const raw = window.localStorage.getItem(
      `${VIEW_MODE_STORAGE_KEY_PREFIX}${projectId}`,
    );
    if (raw === "ahora-only" || raw === "complete" || raw === "blockers") {
      return raw;
    }
  } catch {
    /* localStorage unavailable · fallback */
  }
  return "complete";
}

function storeViewMode(projectId: string, mode: ExtendedViewMode): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      `${VIEW_MODE_STORAGE_KEY_PREFIX}${projectId}`,
      mode,
    );
  } catch {
    /* localStorage unavailable · best-effort */
  }
}

export function ProjectCronologicaView({
  projectId,
  initialStepId,
}: ProjectCronologicaViewProps) {
  const { data, isLoading, isError, error } = useProjectCronologica(projectId);
  const [drawerStep, setDrawerStep] = React.useState<EnrichedStepState | null>(
    null,
  );
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [viewMode, setViewMode] = React.useState<ExtendedViewMode>("complete");

  // Hydrate viewMode from localStorage post-mount (SSR safe)
  React.useEffect(() => {
    setViewMode(getStoredViewMode(projectId));
  }, [projectId]);

  const handleViewModeChange = (mode: ExtendedViewMode) => {
    setViewMode(mode);
    storeViewMode(projectId, mode);
  };

  // Deep-link · open drawer when ?step=... matches on data load
  React.useEffect(() => {
    if (!data || !initialStepId) return;
    const all = [
      ...data.completed,
      ...(data.ahora ? [data.ahora] : []),
      ...data.proximos_7d,
      ...data.proximos_30d,
    ];
    const match = all.find((s) => s.template_id === initialStepId);
    if (match) {
      setDrawerStep(match);
      setDrawerOpen(true);
    }
  }, [data, initialStepId]);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Cargando vista del proyecto…
      </div>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-6 space-y-2">
          <p className="font-medium">No se pudo cargar la vista del proyecto</p>
          <p className="text-sm text-foreground/70">
            {error instanceof Error ? error.message : String(error)}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  // Compute Kpi3MicroRow inputs
  const dimsCaptured = computeDimsCaptured(data.dims);
  const proximoHitoDays =
    data.ahora?.estimated_days ?? data.proximos_7d[0]?.estimated_days ?? null;

  const handleOpenDetail = (step: EnrichedStepState) => {
    setDrawerStep(step);
    setDrawerOpen(true);
  };

  return (
    <div className="space-y-6">
      <ProjectContextHeader
        projectId={projectId}
        projectNombre={data.project_nombre}
        categoria={data.dims.categoria_objetivo ?? null}
        archetype={data.dims.archetype ?? null}
        currentPhase={data.current_phase}
        progressPct={data.progress.global_pct}
        progressCompleted={data.progress.global_completed}
        progressTotal={data.progress.global_total}
        dimsCaptured={dimsCaptured}
        dimsTotal={19}
        proximoHitoDays={proximoHitoDays}
      />

      {/* Toggle vista top-bar */}
      <div
        className="flex items-center gap-2 rounded-md border bg-card p-2"
        data-testid="view-mode-toggle"
        role="group"
        aria-label="Modo de vista del workflow"
      >
        <Button
          type="button"
          size="sm"
          variant={viewMode === "ahora-only" ? "primary" : "outline"}
          onClick={() => handleViewModeChange("ahora-only")}
          data-testid="view-mode-ahora-only"
          aria-pressed={viewMode === "ahora-only"}
        >
          <Sparkles className="mr-1 size-3.5" />
          Vista AHORA
        </Button>
        <Button
          type="button"
          size="sm"
          variant={viewMode === "complete" ? "primary" : "outline"}
          onClick={() => handleViewModeChange("complete")}
          data-testid="view-mode-complete"
          aria-pressed={viewMode === "complete"}
        >
          <LayoutList className="mr-1 size-3.5" />
          Vista Completa
        </Button>
        <Button
          type="button"
          size="sm"
          variant={viewMode === "blockers" ? "primary" : "outline"}
          onClick={() => handleViewModeChange("blockers")}
          data-testid="view-mode-blockers"
          aria-pressed={viewMode === "blockers"}
        >
          <ListTree className="mr-1 size-3.5" />
          Próximos pasos
        </Button>
        <span className="ml-auto text-[10px] text-foreground/55 italic">
          AHORA siempre fijo arriba
        </span>
      </div>

      {/* 2-col grid (workflow + copiloto sidebar) · responsive */}
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          {viewMode === "blockers" ? (
            <WorkflowBlockersPanel
              projectId={projectId}
              steps={[
                ...(data.ahora ? [data.ahora] : []),
                ...data.proximos_7d,
                ...data.proximos_30d,
                ...data.completed,
              ]}
              onOpenDetail={handleOpenDetail}
            />
          ) : (
            <WorkflowTimelineAdmin
              projectId={projectId}
              dims={data.dims}
              completed={data.completed}
              ahora={data.ahora}
              proximos7d={data.proximos_7d}
              proximos30d={data.proximos_30d}
              onOpenDetail={handleOpenDetail}
              viewMode={viewMode as WorkflowTimelineViewMode}
            />
          )}
        </div>
        {/* Copiloto admin sidebar sticky right · 320px desktop · stack mobile */}
        <div className="lg:block">
          <CopilotoAdminSidebar
            projectId={projectId}
            projectNombre={data.project_nombre}
            faseActual={data.current_phase}
            activeStepId={data.ahora?.template_id}
            activeStepTitle={data.ahora?.title}
          />
        </div>
      </div>

      <WorkflowStepDetailDrawerEnriched
        step={drawerStep}
        dims={data.dims}
        projectId={projectId}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}

function computeDimsCaptured(dims: Record<string, unknown>): number {
  // Lightweight client-side count · mirrors backend compute_dims_captured (1.C.D.A.0)
  let count = 1; // fase always counts
  if (dims.categoria_objetivo) count++;
  if (dims.archetype) count++;
  if (dims.tamano_empleados && dims.tamano_empleados !== "pequeno") count++;
  if (dims.madurez_ens_actual && dims.madurez_ens_actual !== "L0") count++;
  if (dims.geografia_operacion && dims.geografia_operacion !== "spain") count++;
  if (dims.procesa_datos_sensibles_rgpd9) count++;
  if (dims.aplica_nis2 && dims.aplica_nis2 !== "no") count++;
  if (dims.aplica_dora && dims.aplica_dora !== "no") count++;
  if (dims.aplica_ai_act && dims.aplica_ai_act !== "no") count++;
  if (dims.dpo_designado && dims.dpo_designado !== "no_designado") count++;
  if (
    dims.arquitectura_sistemas &&
    dims.arquitectura_sistemas !== "cloud_native"
  )
    count++;
  if (dims.multi_tenancy && dims.multi_tenancy !== "single") count++;
  if (dims.equipo_ti_tamano && dims.equipo_ti_tamano !== "1_3") count++;
  if (
    Array.isArray(dims.certificaciones_previas) &&
    dims.certificaciones_previas.length > 0
  )
    count++;
  if (dims.urgencia_certificacion && dims.urgencia_certificacion !== "6m") count++;
  if (dims.presupuesto_disponible && dims.presupuesto_disponible !== "estandar")
    count++;
  if (dims.compromiso_interno && dims.compromiso_interno !== "reactivo") count++;
  if (dims.horas_cliente_semana && dims.horas_cliente_semana !== "5_15h") count++;
  return count;
}
