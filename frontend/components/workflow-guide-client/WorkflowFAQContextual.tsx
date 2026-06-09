"use client";

/**
 * WorkflowFAQContextual · sub-atom 1.C.D.C.2 v3.8.
 *
 * FAQ contextual primer principios · cliente puede no saber NADA de ENS.
 * Sostener R30 inverso aplicado cliente (asume cero conocimiento · explica desde 0).
 *
 * R29 sostener:
 *   ✅ Tono amable · sin jerga
 *   ✅ Tutor paciente disponible
 *   ✅ Una pregunta "Necesito ayuda" point of entry copiloto cliente (commit 3)
 *   ❌ NO presión · NO "deberías saber esto"
 */
import * as React from "react";
import { ChevronDown, HelpCircle, MessageCircle } from "lucide-react";

import { cn } from "@/lib/utils";

interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

const FAQ_CONTEXTUAL: FAQItem[] = [
  {
    id: "que-es-ens",
    question: "¿Qué es ENS · sin tecnicismos?",
    answer:
      "ENS (Esquema Nacional de Seguridad) son las reglas oficiales que España exige a empresas que trabajan con Administración Pública. Te certificas una vez · puedes presentarte a contratos públicos. Sin ENS · estás fuera.",
  },
  {
    id: "por-que-tantos-pasos",
    question: "¿Por qué tiene tantos pasos?",
    answer:
      "Porque ENS cubre todo: cómo proteges datos · cómo formas a tu equipo · cómo respondes ante problemas. Cada paso es una pieza del puzle. Los hacemos uno a uno · no necesitas hacerlos todos a la vez.",
  },
  {
    id: "cuanto-tiempo",
    question: "¿Cuánto tiempo me va a llevar?",
    answer:
      "Depende del tamaño de tu empresa y del nivel ENS objetivo. Lo importante: NO hay prisa coercitiva · avanzas a tu ritmo. Si tienes 1h a la semana · perfecto. Si tienes más · vamos más rápido.",
  },
  {
    id: "no-entiendo-algo",
    question: "Si no entiendo algo · ¿qué hago?",
    answer:
      "Preguntas. Sin miedo. Hay términos técnicos extraños (DORA · NIS2 · MAGERIT...) que muy poca gente conoce. Marcos te los explica con palabras normales · no con jerga consultora.",
  },
  {
    id: "documentos-complicados",
    question: "Los documentos parecen complicados · ¿los hago yo?",
    answer:
      "No los haces tú desde cero. Marcos te da plantillas · tú rellenas SOLO lo que conoces de tu empresa (cuántos empleados · qué sistemas usas · etc). El resto lo prepara Marcos contigo.",
  },
];

interface WorkflowFAQContextualProps {
  onOpenCopiloto?: () => void;
  className?: string;
}

export function WorkflowFAQContextual({
  onOpenCopiloto,
  className,
}: WorkflowFAQContextualProps) {
  const [openId, setOpenId] = React.useState<string | null>(null);

  return (
    <section
      className={cn(
        "rounded-2xl border border-blue-50 bg-white p-5",
        className,
      )}
      aria-labelledby="faq-heading"
    >
      <div className="mb-3 flex items-center gap-2">
        <HelpCircle
          className="size-5 text-blue-600"
          strokeWidth={2.3}
          aria-hidden
        />
        <h2
          id="faq-heading"
          className="text-base font-bold text-[color:var(--fulkro-title)]"
        >
          Preguntas frecuentes
        </h2>
      </div>

      <ul className="space-y-1.5">
        {FAQ_CONTEXTUAL.map((item) => {
          const isOpen = openId === item.id;
          return (
            <li
              key={item.id}
              className="rounded-lg border border-blue-50 bg-blue-50/30"
            >
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : item.id)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              >
                <span className="text-sm font-medium text-[color:var(--fulkro-body)]">
                  {item.question}
                </span>
                <ChevronDown
                  className={cn(
                    "size-4 shrink-0 text-blue-500 transition-transform",
                    isOpen && "rotate-180",
                  )}
                  strokeWidth={2.3}
                  aria-hidden
                />
              </button>
              {isOpen && (
                <div className="px-4 pb-3">
                  <p className="text-sm text-[color:var(--fulkro-body)]">
                    {item.answer}
                  </p>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {onOpenCopiloto && (
        <button
          type="button"
          onClick={onOpenCopiloto}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-white px-4 py-2.5 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50"
        >
          <MessageCircle className="size-4" strokeWidth={2.3} aria-hidden />
          ¿Tienes otra pregunta? Pídeme ayuda
        </button>
      )}
    </section>
  );
}
