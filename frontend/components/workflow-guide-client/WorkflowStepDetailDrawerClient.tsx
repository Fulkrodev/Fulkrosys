"use client";

/**
 * WorkflowStepDetailDrawerClient · sub-atom 1.C.D.C.2 v3.8.
 *
 * Sheet drawer 3 tabs (vs 5 admin) · adapted tono cliente friendly.
 *
 * Tabs cliente:
 *   📋 Detalle · description_detailed + completion_criteria simplified
 *   ❓ ¿Por qué importa? · rationale + business impact primer principios
 *   📂 ¿Qué necesito? · deliverable_codes friendly + tooltips ENS contextuales
 *
 * Tabs admin NO incluidas (R29 + R30 inverso · cliente NO técnico):
 *   ❌ Actores (CISO+DPO+Comité jerga)
 *   ❌ Adaptación (19 dims técnicas ruido cliente)
 *   ❌ ENS refs separado (tooltips_ens distribuidos inline NEED tab)
 */
import * as React from "react";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  HelpCircle,
  Lightbulb,
} from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { WorkflowStepDeliverables } from "@/components/workflow-deliverables/WorkflowStepDeliverables";
import type { EnrichedStepState } from "@/lib/api/client-workflow-guide";

interface WorkflowStepDetailDrawerClientProps {
  step: EnrichedStepState | null;
  projectId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WorkflowStepDetailDrawerClient({
  step,
  projectId,
  open,
  onOpenChange,
}: WorkflowStepDetailDrawerClientProps) {
  if (!step) return null;

  const tooltipEntries = Object.entries(step.tooltips_ens ?? {});

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto sm:max-w-lg"
      >
        <SheetHeader className="space-y-2">
          <SheetTitle className="text-lg">{step.title}</SheetTitle>
          <SheetDescription>Fase {step.phase}</SheetDescription>
        </SheetHeader>

        <Tabs defaultValue="detalle" className="mt-6">
          <TabsList className="grid w-full grid-cols-3 text-xs">
            <TabsTrigger value="detalle">
              <FileText className="mr-1 size-3" strokeWidth={2.3} aria-hidden />
              Detalle
            </TabsTrigger>
            <TabsTrigger value="porque">
              <HelpCircle
                className="mr-1 size-3"
                strokeWidth={2.3}
                aria-hidden
              />
              ¿Por qué?
            </TabsTrigger>
            <TabsTrigger value="necesito">
              <Lightbulb
                className="mr-1 size-3"
                strokeWidth={2.3}
                aria-hidden
              />
              ¿Qué necesito?
            </TabsTrigger>
          </TabsList>

          {/* ─── Tab 1 · Detalle ─── */}
          <TabsContent value="detalle" className="space-y-4 pt-4">
            {step.description_detailed_es ? (
              <div>
                <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  ¿Qué tienes que hacer?
                </p>
                <p className="whitespace-pre-line text-sm text-[color:var(--fulkro-body)]">
                  {step.description_detailed_es}
                </p>
              </div>
            ) : (
              <p className="text-sm text-[color:var(--fulkro-muted)]">
                Tu consultor te explicará los detalles cuando lleguemos a este paso.
              </p>
            )}

            {step.completion_criteria_detailed.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  ¿Cómo sabrás que está hecho?
                </p>
                <ul className="space-y-1.5">
                  {step.completion_criteria_detailed.map((criterion, idx) => (
                    <li
                      key={idx}
                      className="flex gap-2 text-sm text-[color:var(--fulkro-body)]"
                    >
                      <CheckCircle2
                        className="mt-0.5 size-3.5 shrink-0 text-emerald-500"
                        strokeWidth={2.3}
                        aria-hidden
                      />
                      <span>{criterion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </TabsContent>

          {/* ─── Tab 2 · ¿Por qué importa? ─── */}
          <TabsContent value="porque" className="space-y-4 pt-4">
            {step.rationale_es ? (
              <div className="rounded-lg bg-blue-50/60 p-4">
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-700">
                  ¿Por qué es importante?
                </p>
                <p className="whitespace-pre-line text-sm text-[color:var(--fulkro-body)]">
                  {step.rationale_es}
                </p>
              </div>
            ) : (
              <p className="text-sm text-[color:var(--fulkro-muted)]">
                Cada paso del ENS tiene un propósito · te lo explicaremos sin
                jerga técnica cuando lo abordemos juntos.
              </p>
            )}

            {step.adaptation_notes_es && (
              <div>
                <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Adaptado a tu proyecto
                </p>
                <p className="whitespace-pre-line text-sm text-[color:var(--fulkro-body)]">
                  {step.adaptation_notes_es}
                </p>
              </div>
            )}

            {step.variant_extra_focus && (
              <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-3">
                <p className="mb-1 text-xs font-bold uppercase tracking-wider text-amber-700">
                  Especial para tu sector
                </p>
                <p className="text-sm text-[color:var(--fulkro-body)]">
                  {step.variant_extra_focus}
                </p>
              </div>
            )}
          </TabsContent>

          {/* ─── Tab 3 · ¿Qué necesito? · 1.C.D.D.2 wired backend ─── */}
          <TabsContent value="necesito" className="space-y-4 pt-4">
            {projectId && step.deliverable_codes.length > 0 ? (
              <>
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Documentos que prepararás
                </p>
                <WorkflowStepDeliverables
                  projectId={projectId}
                  templateId={step.template_id}
                  mode="client"
                  tone="client"
                />
                <p className="mt-3 text-xs text-[color:var(--fulkro-muted)]">
                  Marcos te dará las plantillas cuando llegues a este paso · solo
                  rellenas lo que conoces de tu empresa.
                </p>
              </>
            ) : step.deliverable_codes.length > 0 ? (
              <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Documentos que prepararás
                </p>
                <ul className="space-y-1.5">
                  {step.deliverable_codes.map((code) => (
                    <li
                      key={code}
                      className="flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50/40 px-3 py-2"
                    >
                      <FileText
                        className="size-3.5 shrink-0 text-blue-600"
                        strokeWidth={2.3}
                        aria-hidden
                      />
                      <span className="text-sm font-medium text-[color:var(--fulkro-body)]">
                        {code}
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-[color:var(--fulkro-muted)]">
                  Marcos te dará las plantillas cuando llegues a este paso · solo
                  rellenas lo que conoces de tu empresa.
                </p>
              </div>
            ) : (
              <p className="text-sm text-[color:var(--fulkro-muted)]">
                Este paso no requiere documentos específicos · es una acción que
                completas marcando &laquo;Hecho&raquo; cuando termines.
              </p>
            )}

            {tooltipEntries.length > 0 && (
              <div>
                <p className="mb-2 flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  <BookOpen className="size-3" strokeWidth={2.3} />
                  Términos que aparecerán
                </p>
                <dl className="space-y-2">
                  {tooltipEntries.map(([term, definition]) => (
                    <div
                      key={term}
                      className="rounded-md border border-blue-50 bg-white px-3 py-2"
                    >
                      <dt className="text-xs font-semibold text-blue-700">
                        {term}
                      </dt>
                      <dd className="text-sm text-[color:var(--fulkro-body)]">
                        {definition}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
