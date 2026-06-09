"use client";

/**
 * useInlineAgent + useInlineAgentSuggestion hooks.
 *
 * MB-7 atom 7.4-bis · invoke + quick-suggestion patterns.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  type InlineAgentResponse,
  type InlineAgentSlug,
  type QuickSuggestion,
  fetchQuickSuggestion,
  invokeInlineAgent,
} from "@/lib/client-portal/inline-agents/api";
import { ClientApiError } from "@/lib/client-portal-api";


interface UseInlineAgentResult {
  loading: boolean;
  error: string | null;
  result: InlineAgentResponse | null;
  invoke: (userMessage: string, extraContext?: string) => Promise<void>;
  reset: () => void;
}


export function useInlineAgent(
  slug: InlineAgentSlug,
  pageUrl?: string,
): UseInlineAgentResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InlineAgentResponse | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  const invoke = useCallback(
    async (userMessage: string, extraContext?: string) => {
      setLoading(true);
      setError(null);
      try {
        const resp = await invokeInlineAgent(slug, {
          user_message: userMessage,
          extra_context: extraContext,
          page_url: pageUrl,
        });
        if (!cancelledRef.current) setResult(resp);
      } catch (err) {
        if (cancelledRef.current) return;
        if (err instanceof ClientApiError) {
          setError(err.message);
        } else {
          setError("Error invocando agente");
        }
      } finally {
        if (!cancelledRef.current) setLoading(false);
      }
    },
    [slug, pageUrl],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { loading, error, result, invoke, reset };
}


interface UseSuggestionResult {
  loading: boolean;
  available: boolean;
  suggestion: QuickSuggestion | null;
}


export function useInlineAgentSuggestion(
  slug: InlineAgentSlug,
  pageUrl?: string,
): UseSuggestionResult {
  const [suggestion, setSuggestion] = useState<QuickSuggestion | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchQuickSuggestion(slug, pageUrl)
      .then((data) => {
        if (!cancelled) setSuggestion(data);
      })
      .catch(() => {
        if (!cancelled) setSuggestion({ available: false });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, pageUrl]);

  return {
    loading,
    available: Boolean(suggestion?.available),
    suggestion,
  };
}
