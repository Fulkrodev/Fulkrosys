"use client";

/**
 * CoachNextStepStrip · banda fina "tu siguiente paso" PERSISTENTE en TODAS las
 * páginas del portal cliente. feat/fulkro-100 Ola C (copiloto siempre presente).
 *
 * Espejo fino del CopilotNextStepBanner admin, pero R29 firmísimo: ámbar (NUNCA
 * rojo), lenguaje llano, sin códigos ENS, tono "sin prisa". A diferencia del
 * CoachNextStepCard (rico, en el dashboard), este strip:
 *   - devuelve null cuando NO hay acción (no satura cada página con "al día")
 *   - es compacto (una línea) para vivir en el layout global
 *   - "Hacerlo" lleva al sitio · "Pregúntame" abre el copiloto del cliente
 *
 * Tiempo real: se refresca cuando el admin avanza el proyecto (SSE).
 */
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, MessageCircle, Sparkles } from "lucide-react";

import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { fetchCopilotHintCliente } from "@/lib/api/copiloto";
import { Button } from "@/components/ui/button";

interface Props {
  projectId?: string | null;
}

const HINT_KEY = ["copilot-hint-cliente"];

export function CoachNextStepStrip({ projectId }: Props) {
  const router = useRouter();

  const { data: hint } = useQuery({
    queryKey: HINT_KEY,
    queryFn: () => fetchCopilotHintCliente(),
    staleTime: 30_000,
  });

  useClientProjectEvents(projectId ?? null, {
    invalidateQueries: [HINT_KEY],
  });

  if (!hint?.has_action) return null;

  const openCopiloto = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("fulkro:open-cliente-copiloto"));
    }
  };

  return (
    <div
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-950 md:px-6"
      role="status"
      aria-live="polite"
      data-testid="coach-next-step-strip"
    >
      <Sparkles className="h-4 w-4 shrink-0 text-amber-600" aria-hidden />
      <span className="font-medium">Tu siguiente paso:</span>
      <span className="min-w-0 flex-1">{hint.message}</span>
      <div className="flex shrink-0 items-center gap-2">
        {hint.target_url && (
          <Button
            size="sm"
            className="h-7 bg-amber-600 hover:bg-amber-700"
            onClick={() => router.push(hint.target_url as string)}
            data-testid="coach-strip-go"
          >
            Hacerlo <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-amber-800 hover:bg-amber-100"
          onClick={openCopiloto}
          data-testid="coach-strip-ask"
        >
          <MessageCircle className="mr-1 h-3.5 w-3.5" /> Pregúntame
        </Button>
      </div>
    </div>
  );
}
