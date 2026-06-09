/**
 * CopilotoAdminSidebar · sidebar dedicada NUEVA · sub-atom 1.C.D.B.3 v3.8.
 *
 * Sticky derecha (3-col layout · 24% pantalla desktop) · NO panel global.
 * UI dedicated · CopilotPanel global existing INTOCABLE (1.D.B.0 refactor).
 *
 * Estructura:
 *   Header: 🤖 Asistente ENS · Modo tutor cronológico
 *   Briefing matutino (auto-derived multi-cliente)
 *   Project guidance (cuando Marcos viendo cliente · context-aware)
 *   QuickActions (4 botones · responses context-aware)
 *   Chat input bottom (stub LLM swap-in 1.D.B.2)
 */
"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Bot, RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  fetchCopilotHintAdmin,
  type CopilotBlocker,
} from "@/lib/api/copiloto";
import { useCurrentStep } from "@/hooks/useWorkflowCommandCenter";

import { CopilotoBriefingMatutino } from "./CopilotoBriefingMatutino";
import {
  CopilotoChatInput,
  CopilotoQuickActions,
} from "./CopilotoQuickActions";

interface CopilotoAdminSidebarProps {
  projectId?: string;
  projectNombre?: string;
  faseActual?: string;
  activeStepId?: string;
  activeStepTitle?: string;
}

interface ChatHistoryEntry {
  action_id: string;
  response_text: string;
  timestamp: number;
  is_stub?: boolean;
  is_error?: boolean;
}

export function CopilotoAdminSidebar({
  projectId,
  projectNombre,
  faseActual,
  activeStepId,
  activeStepTitle,
}: CopilotoAdminSidebarProps) {
  const [history, setHistory] = React.useState<ChatHistoryEntry[]>([]);
  const { data: currentStep } = useCurrentStep(projectId);

  // FASE 2 gobierno · hint admin workflow-aware (next_step + blockers cross-actor).
  // _detect_blockers ya los calcula backend · aquí solo se exponen agrupados.
  const { data: hint } = useQuery({
    queryKey: ["copilot-hint-admin", projectId],
    queryFn: () => fetchCopilotHintAdmin(projectId as string),
    enabled: !!projectId,
  });
  const blockersByActor = groupBlockersByActor(hint?.blockers ?? []);

  const handleResponseAppend = (
    action_id: string,
    response_text: string,
    options: { is_stub?: boolean; is_error?: boolean } = {},
  ) => {
    setHistory((prev) =>
      [
        {
          action_id,
          response_text,
          timestamp: Date.now(),
          is_stub: options.is_stub,
          is_error: options.is_error,
        },
        ...prev,
      ].slice(0, 10),
    );
  };

  // Mode detection · cualquier entry NO-stub indica LLM real activo
  const hasLLMReal = history.some((h) => h.is_stub === false);
  const modeBadge = hasLLMReal
    ? { label: "LLM", variant: "success" as const }
    : { label: "Tutor", variant: "outline" as const };

  // Active step desde props (vista cronológica AHORA) prevalece sobre useCurrentStep
  // legacy · 1.D.F.0.C integration ready 1.D.F.0.D context-aware
  const resolvedStepId = activeStepId ?? currentStep?.template_id;
  const resolvedStepTitle = activeStepTitle ?? currentStep?.title;

  // 1.D.F.0.D · current_screen propagado al copilot context · permite admin
  // tutor referenciar botones específicos UI según pantalla activa.
  // usePathname is null durante SSR · safe (backend handles None)
  const pathname = usePathname();
  const currentScreen = pathname ?? undefined;

  const context = {
    project_id: projectId,
    project_nombre: projectNombre,
    step_template_id: resolvedStepId,
    step_title: resolvedStepTitle,
    fase_actual: faseActual,
    current_screen: currentScreen,
  };

  return (
    <aside
      className="flex flex-col gap-4 rounded-lg border bg-card p-4 sticky top-4"
      data-testid="copiloto-admin-sidebar"
    >
      {/* Header */}
      <header className="space-y-1 border-b pb-3">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-primary" />
          <h3 className="font-semibold text-sm">Asistente ENS</h3>
          <Badge
            variant={modeBadge.variant}
            className="text-[9px] uppercase"
            data-testid="copiloto-admin-mode-badge"
          >
            {modeBadge.label}
          </Badge>
        </div>
        <p className="text-[10px] text-foreground/70">
          Modo tutor cronológico · asume cero ENS · explica primer principios
        </p>
      </header>

      {/* Briefing matutino · multi-cliente */}
      <section>
        <CopilotoBriefingMatutino />
      </section>

      {/* Project guidance · current cliente focus */}
      {projectNombre && (
        <section className="rounded-md border bg-muted/30 p-3 text-xs space-y-1">
          <p className="font-medium text-foreground/80">
            🎯 Estás en: <span className="text-primary">{projectNombre}</span>
          </p>
          {currentStep ? (
            <p className="text-foreground/70">
              Próximo step: <span className="font-medium">{currentStep.title}</span>
              {currentStep.urgency_score >= 75 && (
                <span className="ml-1 text-red-600">(urgente)</span>
              )}
            </p>
          ) : (
            <p className="text-foreground/70 italic">
              Sin sub-pasos pendientes ahora
            </p>
          )}
        </section>
      )}

      {/* FASE 2 · Próximo paso de gobierno (next_step del scanner · antes invisible) */}
      {projectId && hint?.has_action && (
        <section
          className="rounded-md border border-primary/30 bg-primary/5 p-3 text-xs space-y-2"
          data-testid="copiloto-admin-next-step"
        >
          <p className="text-[10px] uppercase font-semibold text-primary tracking-wider">
            Próximo paso
          </p>
          <p className="text-foreground/80">{hint.message}</p>
          {hint.target_url && (
            <Link
              href={hint.target_url}
              className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
            >
              Ir <ArrowRight className="size-3" />
            </Link>
          )}
        </section>
      )}

      {/* FASE 2 · Bloqueos del workflow agrupados por quién debe actuar */}
      {projectId && (hint?.blockers?.length ?? 0) > 0 && (
        <section
          className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs space-y-2.5"
          data-testid="copiloto-admin-blockers"
        >
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="size-3.5 text-amber-600" />
            <p className="text-[10px] uppercase font-semibold text-amber-800 tracking-wider">
              Bloqueos ({hint?.blockers.length})
            </p>
            <TooltipENS
              icon="info"
              text="Un bloqueo es un requisito de gobierno ENS aún no cumplido que impide avanzar hacia la auditoría: separación de roles RSeg≠RSis (CCN-STIC-801), cadencia del comité de seguridad, firmas o pentest pendientes. Cada bloqueo indica quién debe actuar."
            />
          </div>
          {ACTOR_GROUPS.map(({ key, label }) => {
            const items = blockersByActor[key];
            if (!items || items.length === 0) return null;
            return (
              <div key={key} className="space-y-1">
                <p className="font-medium text-amber-900/90">{label}</p>
                <ul className="space-y-1">
                  {items.map((b, idx) => (
                    <li
                      key={`${b.motor}-${idx}`}
                      className="flex gap-1.5 text-amber-900/80"
                      data-testid={`copiloto-admin-blocker-${b.waiting_on}`}
                    >
                      <span className="text-amber-500">•</span>
                      <span>
                        {b.description}
                        <span className="ml-1 text-[9px] uppercase text-amber-700/70">
                          ({b.motor})
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </section>
      )}

      {/* #22 · Medidas con evidencia pendiente (cruce del semáforo por medida) */}
      {projectId && (hint?.evidence_gaps?.length ?? 0) > 0 && (
        <section
          className="rounded-md border border-sky-200 bg-sky-50 p-3 text-xs space-y-2"
          data-testid="copiloto-admin-evidence-gaps"
        >
          <div className="flex items-center gap-1.5">
            <p className="text-[10px] uppercase font-semibold text-sky-800 tracking-wider">
              Evidencias pendientes
            </p>
            <TooltipENS
              icon="info"
              text="Medidas del ENS que aplican a este proyecto pero todavía no tienen una evidencia validada que las respalde (semáforo por medida). Sube o valida la prueba en Evidencias para ponerlas en verde."
            />
          </div>
          <div className="flex flex-wrap gap-1">
            {hint?.evidence_gaps?.map((code) => (
              <span
                key={code}
                className="rounded bg-sky-100 px-1.5 py-0.5 font-mono text-[10px] text-sky-900"
              >
                {code}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* QuickActions */}
      <section>
        <CopilotoQuickActions
          context={context}
          onResponseAppend={handleResponseAppend}
        />
      </section>

      {/* Chat history · stub responses */}
      {history.length > 0 && (
        <section className="space-y-1.5 border-t pt-3">
          <div className="flex items-center justify-between">
            <p className="text-[10px] uppercase font-semibold text-foreground/70 tracking-wider">
              Respuestas recientes
            </p>
            <button
              type="button"
              onClick={() => setHistory([])}
              className="text-[10px] text-foreground/70 hover:text-foreground"
              aria-label="Limpiar"
            >
              <RefreshCcw className="size-2.5" />
            </button>
          </div>
          <div
            className="space-y-2 max-h-64 overflow-y-auto"
            data-testid="copiloto-admin-history"
          >
            {history.map((h, idx) => (
              <div
                key={h.timestamp + idx}
                className={`rounded-md border px-2.5 py-2 text-xs space-y-1 ${
                  h.is_error
                    ? "border-amber-200 bg-amber-50"
                    : "border-input bg-background"
                }`}
                data-testid={`copiloto-admin-entry-${
                  h.is_error ? "error" : h.is_stub ? "stub" : "llm"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                    {labelForAction(h.action_id)}
                  </Badge>
                  {h.is_stub && !h.is_error && (
                    <span className="text-[9px] uppercase tracking-wider text-foreground/50">
                      stub fallback
                    </span>
                  )}
                </div>
                <p
                  className={`whitespace-pre-wrap ${
                    h.is_error ? "text-amber-900" : "text-foreground/80"
                  }`}
                >
                  {h.response_text}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Chat input · bottom */}
      <section className="border-t pt-3 mt-auto">
        <CopilotoChatInput
          context={context}
          onResponseAppend={handleResponseAppend}
        />
      </section>
    </aside>
  );
}

// Orden de presentación + etiquetas friendly por actor (R30 admin tutor).
const ACTOR_GROUPS: { key: CopilotBlocker["waiting_on"]; label: string }[] = [
  { key: "admin", label: "Te toca a ti (Fulkro)" },
  { key: "cliente", label: "Esperando al cliente" },
  { key: "external_auditor", label: "Esperando a la entidad certificadora (ENAC)" },
  { key: "system", label: "Automático / sistema" },
];

function groupBlockersByActor(
  blockers: CopilotBlocker[],
): Record<string, CopilotBlocker[]> {
  const grouped: Record<string, CopilotBlocker[]> = {};
  for (const b of blockers) {
    (grouped[b.waiting_on] ??= []).push(b);
  }
  return grouped;
}

function labelForAction(actionId: string): string {
  switch (actionId) {
    case "que_hago":
      return "¿Qué hago?";
    case "explica_paso":
      return "Explica paso";
    case "draft_email":
      return "Draft email";
    case "briefing_reunion":
      return "Briefing reunión";
    case "chat_send":
      return "Chat";
    default:
      return actionId;
  }
}
