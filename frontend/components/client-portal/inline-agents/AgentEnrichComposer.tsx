"use client";

/**
 * AgentEnrichComposer · MB-7 atom 7.4-bis.
 *
 * Inline composer to enrich a free-text field with IA. Used in /dda
 * justificaciones (A31). Renders a button next to the textarea · on click
 * invokes the agent · result replaces the textarea content (with confirm).
 */
import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";

import { useInlineAgent } from "@/lib/client-portal/inline-agents/useInlineAgent";
import type { InlineAgentSlug } from "@/lib/client-portal/inline-agents/api";


interface Props {
  slug: InlineAgentSlug;
  /** Current field value (passed as extra_context). */
  currentValue: string;
  /** User-visible prompt; if empty uses currentValue as message. */
  prompt: string;
  /** Called with the enriched text on user confirm. */
  onApply: (enriched: string) => void;
  /** Optional label for the button. */
  label?: string;
}


export function AgentEnrichComposer({
  slug,
  currentValue,
  prompt,
  onApply,
  label = "Enriquecer con IA",
}: Props) {
  const { loading, error, result, invoke } = useInlineAgent(slug);
  const [showPreview, setShowPreview] = useState(false);

  const onClick = async () => {
    setShowPreview(false);
    await invoke(prompt || "Reescribe y enriquece este texto.", currentValue);
    setShowPreview(true);
  };

  const onApplyClick = () => {
    if (result?.response) {
      onApply(result.response.trim());
      setShowPreview(false);
    }
  };

  return (
    <div className="space-y-2" data-testid="agent-enrich-composer">
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-md bg-[color:var(--fulkro-accent)] px-3 py-1.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Sparkles className="h-4 w-4" />
        )}
        {label}
      </button>

      {error && (
        <p className="text-sm font-semibold text-rose-700">{error}</p>
      )}

      {showPreview && result && (
        <div className="rounded-lg border border-fulkro-surface-glass-border bg-fulkro-surface-glass-strong px-3 py-3">
          <p className="mb-1 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            Propuesta IA
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--fulkro-body)]">
            {result.response}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={onApplyClick}
              className="rounded-md bg-emerald-500 px-3 py-1.5 text-sm font-bold text-white hover:opacity-90"
            >
              Aplicar
            </button>
            <button
              type="button"
              onClick={() => setShowPreview(false)}
              className="rounded-md border border-fulkro-surface-glass-border bg-white px-3 py-1.5 text-sm font-bold text-[color:var(--fulkro-body)]"
            >
              Descartar
            </button>
            {result.citations.length > 0 && (
              <span className="text-xs font-medium text-[color:var(--fulkro-muted)]">
                {result.citations.length} cita{result.citations.length === 1 ? "" : "s"}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
