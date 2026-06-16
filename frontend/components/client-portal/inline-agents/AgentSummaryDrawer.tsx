"use client";

/**
 * AgentSummaryDrawer · MB-7 atom 7.4-bis.
 *
 * Side drawer with an IA-generated summary of a document/acta/DdA section.
 * Used in /policies (A04) /actas (A18) /dda (A04). On mount invokes the
 * agent · displays markdown response + citations.
 */
import { useEffect } from "react";
import { Bot, Loader2, X } from "lucide-react";

import { useEscapeKey } from "@/hooks/useEscapeKey";
import { useInlineAgent } from "@/lib/client-portal/inline-agents/useInlineAgent";
import type { InlineAgentSlug } from "@/lib/client-portal/inline-agents/api";


interface Props {
  open: boolean;
  onClose: () => void;
  slug: InlineAgentSlug;
  title: string;
  prompt: string;
  extraContext?: string;
}


export function AgentSummaryDrawer({
  open,
  onClose,
  slug,
  title,
  prompt,
  extraContext,
}: Props) {
  const { loading, error, result, invoke, reset } = useInlineAgent(slug);
  useEscapeKey(onClose, open);

  useEffect(() => {
    if (open && !result && !loading) {
      void invoke(prompt, extraContext);
    }
    if (!open) {
      // Reset state when closed so next open re-fetches fresh summary
      reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-label={title}
      data-testid="agent-summary-drawer"
    >
      <button
        type="button"
        onClick={onClose}
        aria-label="Cerrar"
        className="absolute inset-0 bg-black/40"
      />
      <div className="relative flex h-full w-full max-w-md flex-col bg-white shadow-2xl md:max-w-lg">
        <header className="flex items-center justify-between border-b border-fulkro-surface-glass-border px-5 py-4">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-[color:var(--fulkro-accent)]" />
            <h2 className="text-base font-bold text-[color:var(--fulkro-title)]">
              {title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar drawer"
            className="grid h-8 w-8 place-items-center rounded-lg text-[color:var(--fulkro-muted)] hover:bg-fulkro-surface-glass-strong"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="grid place-items-center py-12 text-[color:var(--fulkro-muted)]">
              <Loader2 className="h-6 w-6 animate-spin" />
              <p className="mt-3 text-sm font-medium">Analizando…</p>
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-rose-300/40 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-700">
              {error}
            </div>
          )}
          {result && (
            <div className="space-y-4">
              <article className="prose prose-sm max-w-none whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--fulkro-body)]">
                {result.response}
              </article>
              {result.citations.length > 0 && (
                <section>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                    Referencias
                  </h3>
                  <ul className="space-y-1 text-xs text-[color:var(--fulkro-body)]">
                    {result.citations.map((cit, i) => (
                      <li key={i} className="rounded bg-fulkro-surface-glass-strong px-2 py-1">
                        [{cit}]
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}
        </div>

        {result && (
          <footer className="border-t border-fulkro-surface-glass-border px-5 py-3 text-xs text-[color:var(--fulkro-muted)]">
            {result.tokens_input + result.tokens_output} tokens · {result.latency_ms} ms
          </footer>
        )}
      </div>
    </div>
  );
}
