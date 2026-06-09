"use client";

/**
 * AgentSuggestionBanner · MB-7 atom 7.4-bis.
 *
 * Inline banner with a cached IA suggestion. Used in /dda /conformidad
 * /files. Hidden when not available (tier excluded) or no response.
 */
import { Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useInlineAgentSuggestion } from "@/lib/client-portal/inline-agents/useInlineAgent";
import type { InlineAgentSlug } from "@/lib/client-portal/inline-agents/api";


interface Props {
  slug: InlineAgentSlug;
  pageUrl?: string;
  /** Localstorage key to remember dismissal. */
  dismissKey?: string;
  /** Tier note shown when agent not available. */
  tierGatedNote?: string;
}


export function AgentSuggestionBanner({
  slug,
  pageUrl,
  dismissKey,
  tierGatedNote,
}: Props) {
  const [dismissed, setDismissed] = useState(false);
  const { loading, available, suggestion } = useInlineAgentSuggestion(
    slug, pageUrl,
  );

  useEffect(() => {
    if (!dismissKey || typeof window === "undefined") return;
    try {
      if (window.localStorage.getItem(dismissKey)) setDismissed(true);
    } catch {
      // ignore
    }
  }, [dismissKey]);

  const onDismiss = () => {
    setDismissed(true);
    if (dismissKey) {
      try {
        window.localStorage.setItem(dismissKey, "1");
      } catch {
        // ignore
      }
    }
  };

  if (dismissed) return null;
  if (loading) return null;
  if (!available) {
    if (!tierGatedNote) return null;
    return (
      <div
        className="rounded-lg border border-amber-300/30 bg-amber-500/10 px-4 py-2 text-xs font-medium text-amber-800"
        data-testid="agent-suggestion-tier-gated"
      >
        {tierGatedNote}
      </div>
    );
  }
  if (!suggestion?.response) return null;

  return (
    <div
      className="flex items-start gap-3 rounded-xl border border-[color:var(--fulkro-accent)]/30 bg-[color:var(--fulkro-accent)]/5 px-4 py-3"
      data-testid="agent-suggestion-banner"
    >
      <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-[color:var(--fulkro-accent)]" />
      <div className="flex-1 text-sm leading-relaxed text-[color:var(--fulkro-body)]">
        <p className="font-bold text-[color:var(--fulkro-title)]">
          Sugerencia IA
        </p>
        <p className="mt-1 whitespace-pre-wrap">{suggestion.response}</p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Descartar sugerencia"
        className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[color:var(--fulkro-muted)] hover:bg-fulkro-surface-glass-strong"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
