"use client";

/**
 * CopilotGuidedFlow · structured guidance wrapper per ENS phase.
 *
 * Sub-atom Sesión 3A Phase B.2 · per-page guided sidebar that complements
 * the floating CopilotoDock (existing 1.D.B production-grade Sonnet 4.6).
 *
 * Difference vs CopilotoDock:
 * - CopilotoDock = floating chat dock (always available · ask anything LLM)
 * - CopilotGuidedFlow = persistent sidebar/banner (structured intro · steps ·
 *   next_action CTA · help_topics per current phase · R30 admin tutor)
 *
 * Wraps any admin page · provides phase context aware guidance. Skip-able
 * per user preference (localStorage flag per phase_id).
 *
 * R30 admin tutor primer principios sostener · assumes cero ENS knowledge ·
 * "hasta un mono" UX bar.
 */
import { ChevronDown, ChevronRight, Lightbulb, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface CopilotGuidedStep {
  /** Short label visible bullet (e.g. "Cliente rellena dimensiones") */
  label: string;
  /** Optional inline detail (e.g. "5 dimensiones · 19 preguntas plain") */
  detail?: string;
}

export interface CopilotGuidedHelp {
  /** Display label (e.g. "Tooltip ENS · jerga") */
  label: string;
  /** Where to go (URL OR anchor) */
  href: string;
  /** Optional · external link target. */
  external?: boolean;
}

export interface CopilotGuidedFlowProps {
  /** Stable phase identifier · used for localStorage dismiss flag */
  phaseId: string;
  /** Phase short title (e.g. "Categorización del sistema ENS") */
  title: string;
  /** ¿Qué hacemos? · 2-4 líneas plain Spanish R30 admin tutor */
  intro: string;
  /** ¿Por qué importa? · 2-3 líneas concreto */
  whyImportant: string;
  /** ¿Cómo lo haremos? · 3-6 pasos numerados */
  steps: CopilotGuidedStep[];
  /** Errores comunes a evitar · 2-4 puntos */
  commonMistakes?: string[];
  /** Tiempo estimado realista */
  estimatedTime?: string;
  /** Recursos de ayuda contextuales */
  helpTopics?: CopilotGuidedHelp[];
  /** Próxima acción CTA */
  nextAction?: {
    label: string;
    targetUrl: string;
  };
  /** Default open · usually true for first visit. */
  defaultOpen?: boolean;
  /** Container className. */
  className?: string;
}

const STORAGE_KEY_PREFIX = "fulkro_copilot_guided_dismissed_";

function getDismissKey(phaseId: string): string {
  return `${STORAGE_KEY_PREFIX}${phaseId}`;
}

function readDismissed(phaseId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(getDismissKey(phaseId)) === "1";
  } catch {
    return false;
  }
}

function writeDismissed(phaseId: string, dismissed: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (dismissed) {
      window.localStorage.setItem(getDismissKey(phaseId), "1");
    } else {
      window.localStorage.removeItem(getDismissKey(phaseId));
    }
  } catch {
    // localStorage unavailable · silently skip
  }
}

export function CopilotGuidedFlow({
  phaseId,
  title,
  intro,
  whyImportant,
  steps,
  commonMistakes,
  estimatedTime,
  helpTopics,
  nextAction,
  defaultOpen = true,
  className,
}: CopilotGuidedFlowProps) {
  const [dismissed, setDismissed] = useState(false);
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    setDismissed(readDismissed(phaseId));
  }, [phaseId]);

  const handleDismiss = useCallback(() => {
    writeDismissed(phaseId, true);
    setDismissed(true);
  }, [phaseId]);

  const handleReopen = useCallback(() => {
    writeDismissed(phaseId, false);
    setDismissed(false);
    setOpen(true);
  }, [phaseId]);

  if (dismissed) {
    return (
      <button
        type="button"
        onClick={handleReopen}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-fulkro-info/40 bg-fulkro-info/5 px-3 py-1.5 text-xs font-medium text-fulkro-info hover:bg-fulkro-info/10",
          className,
        )}
        data-testid={`copilot-guided-reopen-${phaseId}`}
      >
        <Lightbulb className="h-3.5 w-3.5" />
        Mostrar guía de esta fase
      </button>
    );
  }

  return (
    <aside
      role="complementary"
      aria-label={`Guía: ${title}`}
      className={cn(
        "rounded-xl border border-fulkro-info/30 bg-fulkro-info/5 p-4 shadow-sm",
        className,
      )}
      data-testid={`copilot-guided-${phaseId}`}
    >
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <Lightbulb
            className="mt-0.5 h-4 w-4 shrink-0 text-fulkro-info"
            aria-hidden
          />
          <div>
            <h3 className="text-sm font-bold text-fulkro-primary-700">
              {title}
            </h3>
            <p className="mt-0.5 text-xs text-fulkro-ink-500">
              Guía contextual · Marcos te explica primer principios
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Colapsar guía" : "Expandir guía"}
            className="grid h-7 w-7 place-items-center rounded-md text-fulkro-ink-500 hover:bg-fulkro-info/10"
            data-testid={`copilot-guided-toggle-${phaseId}`}
          >
            {open ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="Ocultar guía de esta fase"
            className="grid h-7 w-7 place-items-center rounded-md text-fulkro-ink-500 hover:bg-fulkro-info/10"
            data-testid={`copilot-guided-dismiss-${phaseId}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </header>

      {open && (
        <div className="space-y-3 text-sm text-fulkro-ink-700">
          {/* Intro · ¿Qué hacemos? */}
          <section>
            <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-fulkro-ink-500">
              ¿Qué hacemos?
            </h4>
            <p className="leading-relaxed">{intro}</p>
          </section>

          {/* Why important */}
          <section>
            <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-fulkro-ink-500">
              ¿Por qué importa?
            </h4>
            <p className="leading-relaxed">{whyImportant}</p>
          </section>

          {/* Steps */}
          {steps.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-fulkro-ink-500">
                ¿Cómo lo haremos?
              </h4>
              <ol className="ml-4 list-decimal space-y-1">
                {steps.map((step, i) => (
                  <li key={i} className="leading-relaxed">
                    <span className="font-medium">{step.label}</span>
                    {step.detail ? (
                      <span className="text-fulkro-ink-500">
                        {" "}
                        · {step.detail}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ol>
            </section>
          )}

          {/* Common mistakes */}
          {commonMistakes && commonMistakes.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-fulkro-ink-500">
                Errores comunes a evitar
              </h4>
              <ul className="ml-4 list-disc space-y-1">
                {commonMistakes.map((m, i) => (
                  <li key={i} className="leading-relaxed">
                    {m}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Estimated time + Help topics + Next action footer */}
          <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-fulkro-info/20 pt-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {estimatedTime ? (
                <Badge variant="secondary" className="text-[10px]">
                  ⏱ {estimatedTime}
                </Badge>
              ) : null}
              {helpTopics?.map((topic, i) =>
                topic.external ? (
                  <a
                    key={i}
                    href={topic.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline text-fulkro-info hover:text-fulkro-info/80"
                  >
                    {topic.label}
                  </a>
                ) : (
                  <Link
                    key={i}
                    href={topic.href}
                    className="underline text-fulkro-info hover:text-fulkro-info/80"
                  >
                    {topic.label}
                  </Link>
                ),
              )}
            </div>
            {nextAction ? (
              <Link
                href={nextAction.targetUrl}
                className={cn(buttonVariants({ variant: "primary", size: "sm" }))}
                data-testid={`copilot-guided-next-${phaseId}`}
              >
                {nextAction.label}
                <ChevronRight className="ml-1 h-3 w-3" />
              </Link>
            ) : null}
          </footer>
        </div>
      )}
    </aside>
  );
}
