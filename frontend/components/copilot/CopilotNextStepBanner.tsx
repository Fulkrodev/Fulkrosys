"use client";

/**
 * CopilotNextStepBanner · banda proactiva "próximo paso" del copiloto admin.
 * feat/fulkro-100 · Ola 2 (copiloto proactivo).
 *
 * Visible en TODA pantalla admin de un proyecto (R23 project-scoped): el copiloto
 * te suelta el siguiente paso real (motor determinista compute_workflow_state) +
 * los bloqueos, y te lleva a hacerlo ("Ir") o abre el diálogo ("Guíame").
 *
 * Tiempo real SIN plumbing nuevo (OPS-045): se refresca con los eventos SSE que
 * YA emite el sistema (phase_changed / signing.signed / readiness_changed /
 * document.uploaded) vía useProjectEvents. R30 tutor (lenguaje admin · códigos ENS
 * permitidos · NUNCA se importa en el portal cliente).
 */
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, MessageCircle, Sparkles } from "lucide-react";

import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";
import { fetchCopilotHintAdmin } from "@/lib/api/copiloto";
import { useCopilotStore } from "@/lib/stores/copilot-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PROJECT_RE = /\/admin\/projects\/([0-9a-fA-F-]{36})/;

const PRIORITY_STYLES: Record<string, string> = {
  urgent: "border-amber-300 bg-amber-50 text-amber-900",
  normal: "border-blue-200 bg-blue-50 text-blue-900",
  low: "border-border bg-muted text-foreground",
};

export function CopilotNextStepBanner() {
  const pathname = usePathname();
  const router = useRouter();
  const projectId = pathname?.match(PROJECT_RE)?.[1] ?? null;
  const openPanel = useCopilotStore((s) => s.openPanel);

  const { data: hint, refetch } = useQuery({
    queryKey: ["copilot-hint", projectId],
    queryFn: () => fetchCopilotHintAdmin(projectId as string),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // Tiempo real: refresca el próximo paso cuando el estado del proyecto cambia.
  useProjectEvents({
    projectId: projectId ?? "",
    enabled: !!projectId,
    onPhaseChanged: () => void refetch(),
    onReadinessChanged: () => void refetch(),
    onSigningSigned: () => void refetch(),
    onDocumentUploaded: () => void refetch(),
  });

  if (!projectId || !hint?.has_action) return null;

  const tone = PRIORITY_STYLES[hint.priority] ?? PRIORITY_STYLES.normal;
  const blockerCount = hint.blockers?.length ?? 0;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-2 text-sm md:px-6",
        tone,
      )}
      role="status"
      aria-live="polite"
      data-testid="copilot-next-step-banner"
    >
      <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
      <span className="font-medium">Siguiente paso:</span>
      <span className="min-w-0 flex-1">{hint.message}</span>

      {blockerCount > 0 && (
        <span
          className="rounded-full border border-current/30 px-2 py-0.5 text-xs font-medium"
          data-testid="copilot-banner-blockers"
        >
          {blockerCount} {blockerCount === 1 ? "bloqueo" : "bloqueos"}
        </span>
      )}

      <div className="flex shrink-0 items-center gap-2">
        {hint.target_url && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 bg-white"
            onClick={() => router.push(hint.target_url as string)}
            data-testid="copilot-banner-go"
          >
            Ir <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="h-7"
          onClick={() =>
            openPanel({
              projectId,
              projectPhase: hint.current_phase,
              // Ola C · precarga la pregunta del siguiente paso en el composer.
              initialMessage: `Guíame paso a paso para completar: ${hint.message}`,
            })
          }
          data-testid="copilot-banner-guide"
        >
          <MessageCircle className="mr-1 h-3.5 w-3.5" /> Guíame
        </Button>
      </div>
    </div>
  );
}
