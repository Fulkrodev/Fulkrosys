"use client";

/**
 * CopilotoDock · floating global dock · MB-7 atom 7.2 plan v6.
 *
 * Reuses agent_14_copiloto pipeline (no new RAG). Streaming via
 * /api/v1/client-portal/copiloto/chat/stream (SSE). Quick actions
 * catalog contextual per current page.
 *
 * Q1.D · global dock + deep-link to /client-portal/copiloto/[thread_id]
 *   (deep-link kept simple · single ephemeral conversation stored
 *    in localStorage for now · full thread persistence diferida).
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Bot, Loader2, Send, Sparkles, X } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

import {
  type CopilotHint,
  type CopilotMessage,
  type QuickAction,
  fetchCopilotHintCliente,
  fetchQuickActions,
  streamCopilotAnswer,
} from "@/lib/api/copiloto";


interface Props {
  hideOnPaths?: string[];
}


function inferContext(pathname: string | null): string {
  if (!pathname) return "default";
  if (pathname.includes("magerit")) return "magerit";
  if (pathname.includes("dda")) return "dda";
  if (pathname.includes("conformidad")) return "conformidad";
  if (pathname.includes("evidencias")) return "evidencias";
  if (pathname.includes("incidents")) return "incidents";
  return "default";
}


export function CopilotoDock({ hideOnPaths = [] }: Props) {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
  const [quickLoading, setQuickLoading] = useState(false);
  // Sesión 3B-2B.8 Phase 1D · workflow-aware proactive hint cliente.
  const [hint, setHint] = useState<CopilotHint | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const ctx = inferContext(pathname);
  const shouldHide = hideOnPaths.some((p) => pathname.startsWith(p));

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setQuickLoading(true);
    fetchQuickActions(ctx)
      .then((actions) => {
        if (!cancelled) setQuickActions(actions);
      })
      .catch(() => {
        if (!cancelled) setQuickActions([]);
      })
      .finally(() => {
        if (!cancelled) setQuickLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, ctx]);

  // Sesión 3B-2B.8 Phase 1D · fetch proactive hint cliente al abrir dock.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setHintLoading(true);
    fetchCopilotHintCliente()
      .then((h) => {
        if (!cancelled) setHint(h);
      })
      .catch(() => {
        if (!cancelled) setHint(null);
      })
      .finally(() => {
        if (!cancelled) setHintLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // feat/fulkro-100 · copiloto cliente ÚNICO: cualquier CTA del portal
  // (p.ej. WorkflowFAQContextual) abre ESTE dock global vía evento, en vez de
  // montar un segundo copiloto. Consolidación (Marcos: "el cliente solo uno").
  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener("fulkro:open-cliente-copiloto", handler);
    return () =>
      window.removeEventListener("fulkro:open-cliente-copiloto", handler);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming]);

  const submit = useCallback(
    async (question: string) => {
      if (!question.trim() || streaming) return;
      const userMsg: CopilotMessage = { role: "user", content: question };
      setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
      setInput("");
      setStreaming(true);
      try {
        await streamCopilotAnswer(
          { question, page_context: { url: pathname } },
          (delta) => {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === "assistant") {
                next[next.length - 1] = {
                  role: "assistant",
                  content: (last.content ?? "") + delta,
                };
              }
              return next;
            });
          },
        );
      } catch (err) {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.role === "assistant" && !last.content) {
            next[next.length - 1] = {
              role: "assistant",
              content: "Lo siento, no he podido responder. Intenta de nuevo en unos segundos.",
            };
          }
          return next;
        });
      } finally {
        setStreaming(false);
      }
    },
    [pathname, streaming],
  );

  if (shouldHide) return null;

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Abrir copiloto FULKRO"
          className="fixed bottom-6 right-6 z-50 grid h-14 w-14 place-items-center rounded-full bg-[color:var(--fulkro-accent)] text-white shadow-lg ring-2 ring-white/20 transition hover:scale-105 hover:opacity-90 md:bottom-8 md:right-8"
          data-testid="copiloto-dock-toggle"
        >
          <Bot className="h-6 w-6" />
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-end p-0 md:bottom-8 md:right-8 md:inset-auto md:p-0"
          data-testid="copiloto-dock-open"
        >
          <div
            className="flex h-dvh w-full flex-col rounded-none border-l border-fulkro-surface-glass-border bg-white shadow-2xl md:h-[600px] md:w-[400px] md:rounded-2xl md:border"
          >
            <header className="flex items-center justify-between border-b border-fulkro-surface-glass-border px-4 py-3">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-[color:var(--fulkro-accent)]" />
                <h2 className="text-base font-bold text-[color:var(--fulkro-title)]">
                  Copiloto FULKRO
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Cerrar copiloto"
                className="grid h-8 w-8 place-items-center rounded-lg text-[color:var(--fulkro-muted)] hover:bg-fulkro-surface-glass-strong"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto px-4 py-3"
              data-testid="copiloto-messages"
            >
              {messages.length === 0 ? (
                <div className="space-y-3">
                  {/* Sesión 3B-2B.8 Phase 1D · proactive hint banner */}
                  {hintLoading ? (
                    <Skeleton
                      className="h-16 w-full rounded-lg"
                      data-testid="copiloto-hint-skeleton"
                    />
                  ) : hint?.has_action ? (
                    <div
                      className={`rounded-lg border p-3 text-sm ${
                        hint.priority === "urgent"
                          ? "border-amber-300 bg-amber-50/60 text-amber-900"
                          : hint.priority === "normal"
                            ? "border-fulkro-primary-200 bg-fulkro-primary-50/40 text-fulkro-primary-800"
                            : "border-fulkro-ink-200 bg-fulkro-ink-50 text-fulkro-ink-700"
                      }`}
                      data-testid="copiloto-hint-banner"
                      data-priority={hint.priority}
                    >
                      <p className="mb-2 leading-relaxed">{hint.message}</p>
                      {hint.target_url && (
                        <Link
                          href={hint.target_url}
                          className="inline-flex items-center gap-1 text-xs font-semibold underline-offset-2 hover:underline"
                          data-testid="copiloto-hint-cta"
                        >
                          Ir a la acción
                          <ArrowRight className="size-3" />
                        </Link>
                      )}
                    </div>
                  ) : null}

                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    Pregúntame lo que necesites sobre tu proyecto ENS.
                  </p>
                  {quickLoading ? (
                    <div className="space-y-2">
                      <Skeleton className="h-9 w-full rounded-lg" />
                      <Skeleton className="h-9 w-full rounded-lg" />
                      <Skeleton className="h-9 w-full rounded-lg" />
                    </div>
                  ) : quickActions.length > 0 ? (
                    <div className="space-y-2">
                      {quickActions.map((qa) => (
                        <button
                          key={qa.id}
                          type="button"
                          onClick={() => void submit(qa.prefill_query)}
                          className="flex w-full items-center gap-2 rounded-lg border border-fulkro-surface-glass-border bg-fulkro-surface-glass-strong px-3 py-2 text-left text-sm font-medium text-[color:var(--fulkro-body)] hover:bg-fulkro-surface-glass"
                        >
                          <Sparkles className="h-4 w-4 shrink-0 text-[color:var(--fulkro-accent)]" />
                          <span>{qa.label}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : (
                <ul className="space-y-3">
                  {messages.map((msg, i) => (
                    <li
                      key={i}
                      className={`flex ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                          msg.role === "user"
                            ? "bg-[color:var(--fulkro-accent)] text-white"
                            : "bg-fulkro-surface-glass-strong text-[color:var(--fulkro-body)]"
                        }`}
                      >
                        {msg.content || (
                          <span className="inline-flex items-center gap-1 text-[color:var(--fulkro-muted)]">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            pensando…
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void submit(input);
              }}
              className="border-t border-fulkro-surface-glass-border px-3 py-3"
            >
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Escribe tu pregunta…"
                  disabled={streaming}
                  className="flex-1 rounded-lg border border-fulkro-surface-glass-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[color:var(--fulkro-accent)]/40"
                  data-testid="copiloto-input"
                />
                <button
                  type="submit"
                  disabled={streaming || !input.trim()}
                  className="grid h-9 w-9 place-items-center rounded-lg bg-[color:var(--fulkro-accent)] text-white disabled:opacity-50"
                  aria-label="Enviar pregunta"
                  data-testid="copiloto-send"
                >
                  {streaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
