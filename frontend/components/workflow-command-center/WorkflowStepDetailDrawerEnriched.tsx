/**
 * WorkflowStepDetailDrawerEnriched · Sheet drawer 5 tabs · sub-atom 1.C.D.B.2 v3.8.
 *
 * UX FULKRO premium · 5 tabs:
 *   📋 Detalle · description_detailed + rationale + completion_criteria
 *   👥 Actores · lista actors + roles
 *   📂 Deliverables · codes con preview · download stub (1.C.D.D ready)
 *   🎯 Adaptación · AdaptationBadge expanded + applicable_* + variants
 *   📖 ENS refs · tooltips_ens expanded + cross-references Anexo II
 */
"use client";

import {
  BookOpen,
  CheckCircle2,
  Compass,
  FileText,
  FolderOpen,
  Users2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WorkflowStepDeliverables } from "@/components/workflow-deliverables/WorkflowStepDeliverables";

import type {
  EnrichedStepState,
  ProjectDimsLike,
} from "@/lib/api/workflow-command-center";

interface WorkflowStepDetailDrawerEnrichedProps {
  step: EnrichedStepState | null;
  dims: ProjectDimsLike | null;
  projectId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WorkflowStepDetailDrawerEnriched({
  step,
  dims,
  projectId,
  open,
  onOpenChange,
}: WorkflowStepDetailDrawerEnrichedProps) {
  if (!step) return null;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl overflow-y-auto"
      >
        <SheetHeader className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <SheetTitle className="text-lg">{step.title}</SheetTitle>
            {step.is_enriched && (
              <Badge variant="outline" className="text-[10px]">
                enriched
              </Badge>
            )}
          </div>
          <SheetDescription>
            Fase {step.phase}
            {step.order_within_phase !== null &&
              ` · paso ${step.order_within_phase}`}
            {step.estimated_days !== null &&
              ` · estimado ${step.estimated_days} días`}
          </SheetDescription>
        </SheetHeader>

        <Tabs defaultValue="detalle" className="mt-6">
          <TabsList className="grid w-full grid-cols-5 text-xs">
            <TabsTrigger value="detalle">
              <FileText className="size-3 mr-1" />
              Detalle
            </TabsTrigger>
            <TabsTrigger value="actores">
              <Users2 className="size-3 mr-1" />
              Actores
            </TabsTrigger>
            <TabsTrigger value="deliverables">
              <FolderOpen className="size-3 mr-1" />
              Entregas
            </TabsTrigger>
            <TabsTrigger value="adaptacion">
              <Compass className="size-3 mr-1" />
              Adaptación
            </TabsTrigger>
            <TabsTrigger value="ens">
              <BookOpen className="size-3 mr-1" />
              ENS
            </TabsTrigger>
          </TabsList>

          {/* Tab 1 · Detalle */}
          <TabsContent value="detalle" className="space-y-4 pt-4">
            {step.description_detailed_es && (
              <section>
                <h4 className="text-sm font-semibold mb-1">Descripción</h4>
                <p className="text-sm text-foreground/80 whitespace-pre-line">
                  {step.description_detailed_es}
                </p>
              </section>
            )}
            {step.rationale_es && (
              <section>
                <h4 className="text-sm font-semibold mb-1">Por qué ahora</h4>
                <p className="text-sm text-foreground/80 whitespace-pre-line">
                  {step.rationale_es}
                </p>
              </section>
            )}
            {step.completion_criteria_detailed.length > 0 && (
              <section>
                <h4 className="text-sm font-semibold mb-1">
                  Criterios de finalización
                </h4>
                <ul className="space-y-1.5">
                  {step.completion_criteria_detailed.map((c, idx) => (
                    <li key={idx} className="flex gap-2 text-sm text-foreground/80">
                      <CheckCircle2 className="size-3.5 mt-0.5 text-emerald-600 shrink-0" />
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {step.adaptation_notes_es && (
              <section className="rounded-md border bg-muted/40 p-3">
                <h4 className="text-xs font-semibold mb-1 uppercase text-foreground/60">
                  Notas adaptación
                </h4>
                <p className="text-xs text-foreground/80">
                  {step.adaptation_notes_es}
                </p>
              </section>
            )}
          </TabsContent>

          {/* Tab 2 · Actores */}
          <TabsContent value="actores" className="space-y-3 pt-4">
            {step.actors.length === 0 ? (
              <p className="text-sm italic text-foreground/55">
                Sin actores declarados en el sub-paso
              </p>
            ) : (
              <ul className="space-y-2">
                {step.actors.map((actor, idx) => (
                  <li
                    key={idx}
                    className="flex items-center gap-2 rounded-md border bg-card px-3 py-2"
                  >
                    <Users2 className="size-3.5 text-foreground/60" />
                    <span className="text-sm">{actor}</span>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          {/* Tab 3 · Deliverables · 1.C.D.D.2 v3.8 wired backend */}
          <TabsContent value="deliverables" className="space-y-3 pt-4">
            {projectId ? (
              <WorkflowStepDeliverables
                projectId={projectId}
                templateId={step.template_id}
                mode="admin"
                tone="admin"
              />
            ) : step.deliverable_codes.length === 0 ? (
              <p className="text-sm italic text-foreground/55">
                Sin entregables declarados
              </p>
            ) : (
              <>
                <p className="text-xs text-foreground/60">
                  Plantillas que produce este sub-paso.
                </p>
                <ul className="space-y-2">
                  {step.deliverable_codes.map((code) => (
                    <li
                      key={code}
                      className="flex items-center justify-between rounded-md border bg-card px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <FolderOpen className="size-3.5 text-foreground/60" />
                        <span className="text-sm font-medium">{code}</span>
                      </div>
                      <span className="text-xs italic text-foreground/40">
                        projectId requerido
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {step.prerequisite_template_ids.length > 0 && (
              <section className="border-t pt-3">
                <h4 className="text-xs font-semibold uppercase text-foreground/60 mb-2">
                  Pre-requisitos
                </h4>
                <ul className="space-y-1">
                  {step.prerequisite_template_ids.map((id) => (
                    <li
                      key={id}
                      className="text-xs text-foreground/70 font-mono"
                    >
                      → {id}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </TabsContent>

          {/* Tab 4 · Adaptación */}
          <TabsContent value="adaptacion" className="space-y-4 pt-4">
            {dims && (
              <section>
                <h4 className="text-sm font-semibold mb-2">
                  19 dimensiones del proyecto que aplican
                </h4>
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  <DimsRow label="Categoría" value={dims.categoria_objetivo} />
                  <DimsRow label="Arquetipo" value={dims.archetype} />
                  <DimsRow label="Tamaño" value={dims.tamano_empleados} />
                  <DimsRow label="Madurez ENS" value={dims.madurez_ens_actual} />
                  <DimsRow label="DPO" value={dims.dpo_designado} />
                  <DimsRow label="DORA" value={dims.aplica_dora} />
                  <DimsRow label="NIS2" value={dims.aplica_nis2} />
                  <DimsRow label="AI Act" value={dims.aplica_ai_act} />
                </dl>
              </section>
            )}
            {step.variant_extra_focus && (
              <section className="rounded-md border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-3">
                <h4 className="text-xs font-semibold uppercase text-blue-700 dark:text-blue-300 mb-1">
                  Variante arquetipo aplicada
                </h4>
                <p className="text-sm">{step.variant_extra_focus}</p>
                {step.variant_reference_norms.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {step.variant_reference_norms.map((n) => (
                      <Badge key={n} variant="outline" className="text-[10px]">
                        {n}
                      </Badge>
                    ))}
                  </div>
                )}
              </section>
            )}
          </TabsContent>

          {/* Tab 5 · ENS refs */}
          <TabsContent value="ens" className="space-y-3 pt-4">
            {Object.keys(step.tooltips_ens).length === 0 ? (
              <p className="text-sm italic text-foreground/55">
                Sin referencias ENS específicas declaradas
              </p>
            ) : (
              <ul className="space-y-2">
                {Object.entries(step.tooltips_ens).map(([code, tooltip]) => (
                  <li
                    key={code}
                    className="rounded-md border bg-card p-3"
                  >
                    <Badge variant="outline" className="text-xs mb-1">
                      {code}
                    </Badge>
                    <p className="text-sm text-foreground/80">{tooltip}</p>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-foreground/55 italic pt-2 border-t">
              Refs ENS Anexo II RD 311/2022. Tooltips expanded contextualmente al
              sub-paso · cross-references disponibles vía corpus search.
            </p>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

function DimsRow({
  label,
  value,
}: {
  label: string;
  value: string | null | boolean | undefined;
}) {
  const display =
    value === null || value === undefined || value === ""
      ? "—"
      : typeof value === "boolean"
        ? value
          ? "sí"
          : "no"
        : value;
  return (
    <>
      <dt className="text-foreground/60">{label}</dt>
      <dd className="font-medium truncate">{display}</dd>
    </>
  );
}
