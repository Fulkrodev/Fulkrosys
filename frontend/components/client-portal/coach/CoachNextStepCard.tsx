"use client";

/**
 * CoachNextStepCard · el copiloto guía al cliente con su siguiente paso.
 * feat/fulkro-100 · Ola 2 (copiloto proactivo · cara cliente).
 *
 * Mismo motor determinista que el admin (compute_workflow_state, rol cliente)
 * pero R29 firmísimo: lenguaje llano, sin códigos ENS, ámbar (NUNCA rojo), tono
 * "sin prisa por tu parte" y estado vacío en clave de enhorabuena. Tiempo real
 * via useClientProjectEvents (refresca cuando el admin avanza el proyecto).
 */
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Sparkles, ArrowRight } from "lucide-react";

import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { fetchCopilotHintCliente } from "@/lib/api/copiloto";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  projectId?: string | null;
}

const HINT_KEY = ["copilot-hint-cliente"];

export function CoachNextStepCard({ projectId }: Props) {
  const router = useRouter();

  const { data: hint, isLoading } = useQuery({
    queryKey: HINT_KEY,
    queryFn: () => fetchCopilotHintCliente(),
    staleTime: 30_000,
  });

  // Tiempo real: cuando el admin avanza el proyecto, el siguiente paso se refresca.
  useClientProjectEvents(projectId ?? null, {
    invalidateQueries: [HINT_KEY],
  });

  if (isLoading) return null;

  // Estado "al día" · enhorabuena, sin presión (R29).
  if (!hint?.has_action) {
    return (
      <Card className="border-emerald-200 bg-emerald-50/60">
        <CardContent className="flex items-center gap-3 py-4">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" aria-hidden />
          <p className="text-sm text-emerald-900" data-testid="coach-card-done">
            {hint?.message ??
              "Todo al día por tu parte. Sin prisa: te avisaremos aquí cuando haya algo nuevo."}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className="border-amber-200 bg-amber-50"
      role="status"
      aria-live="polite"
      data-testid="coach-card-action"
    >
      <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
        <Sparkles className="h-5 w-5 shrink-0 text-amber-600" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Tu siguiente paso
          </p>
          <p className="text-sm text-amber-950">{hint.message}</p>
        </div>
        {hint.target_url && (
          <Button
            size="sm"
            className="shrink-0 bg-amber-600 hover:bg-amber-700"
            onClick={() => router.push(hint.target_url as string)}
            data-testid="coach-card-go"
          >
            Hacerlo <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
