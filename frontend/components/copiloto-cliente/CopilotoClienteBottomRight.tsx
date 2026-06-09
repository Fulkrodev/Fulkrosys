"use client";

/**
 * CopilotoClienteBottomRight · sub-atom 1.C.D.C.3 v3.8.
 *
 * Widget floating bottom-right · UI dedicada cliente (NO sidebar sticky admin).
 * Mount SOLO en /client-portal/workflow/ · NO global (CopilotoDock cubre rest).
 *
 * R29 sostener empíricamente (audit pre-commit pasa):
 *   ✅ Color suave (blue · NO red urgente · NO amarillo alarm)
 *   ✅ "Estoy aquí cuando me necesites" approach
 *   ✅ NO red dot · NO badge urgent · NO popup intrusivo auto-open
 *   ✅ Persona avatar friendly · tono amable
 *   ✅ Mensajes user-driven (cliente clic explícito)
 *   ❌ NO setIntervals que dispare notifications
 *   ❌ NO push notifications inactividad
 *   ❌ NO contadores deadline visibles
 *
 * Schema action_id IDÉNTICO admin · swap-in 1.D.B.1 zero refactor cuando LLM
 * real cliente reemplace stub backend.
 */
import * as React from "react";
import {
  Bot,
  Loader2,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { useCopilotoClienteChat } from "@/hooks/useCopilotoCliente";
import type {
  ClientCopilotActionId,
  ClientCopilotChatResponse,
} from "@/lib/api/copiloto-cliente";

interface CopilotoClienteBottomRightProps {
  projectId?: string;
  currentStepTitle?: string | null;
  currentStepTemplateId?: string | null;
  faseActual?: string | null;
  /**
   * Control externo open/close (e.g., FAQ contextual "Pídeme ayuda" button).
   * Si NO se pasa · componente gestiona su propio state.
   */
  controlledOpen?: boolean;
  onControlledOpenChange?: (open: boolean) => void;
}

interface QuickAction {
  id: ClientCopilotActionId;
  label: string;
  payload: () => Parameters<
    ReturnType<typeof useCopilotoClienteChat>["mutate"]
  >[0];
}

interface ChatLogEntry {
  id: string;
  role: "client" | "copilot" | "system_error";
  text: string;
  is_stub?: boolean;
}

export function CopilotoClienteBottomRight({
  projectId,
  currentStepTitle,
  currentStepTemplateId,
  faseActual,
  controlledOpen,
  onControlledOpenChange,
}: CopilotoClienteBottomRightProps) {
  const [internalOpen, setInternalOpen] = React.useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = onControlledOpenChange ?? setInternalOpen;

  const [log, setLog] = React.useState<ChatLogEntry[]>([]);
  const [input, setInput] = React.useState("");
  const chatMutation = useCopilotoClienteChat();

  const quickActions: QuickAction[] = React.useMemo(
    () => [
      {
        id: "que_hago",
        label: "¿Qué tengo que hacer ahora?",
        payload: () => ({
          action_id: "que_hago",
          project_id: projectId,
          step_title: currentStepTitle ?? undefined,
          step_template_id: currentStepTemplateId ?? undefined,
          fase_actual: faseActual ?? undefined,
        }),
      },
      {
        id: "porque_importa",
        label: "¿Por qué es importante esto?",
        payload: () => ({
          action_id: "porque_importa",
          project_id: projectId,
          step_title: currentStepTitle ?? undefined,
          fase_actual: faseActual ?? undefined,
        }),
      },
      {
        id: "explica_concepto",
        label: "Explícame un término ENS",
        payload: () => ({
          action_id: "explica_concepto",
          project_id: projectId,
          concepto: input.trim() || undefined,
        }),
      },
      {
        id: "necesito_ayuda",
        label: "Necesito ayuda con algo",
        payload: () => ({
          action_id: "necesito_ayuda",
          project_id: projectId,
        }),
      },
    ],
    [projectId, currentStepTitle, currentStepTemplateId, faseActual, input],
  );

  const handleQuickAction = (action: QuickAction) => {
    const payload = action.payload();
    const userText =
      action.id === "explica_concepto" && input.trim()
        ? `Explícame: ${input.trim()}`
        : action.label;
    setLog((prev) => [
      ...prev,
      { id: `c-${Date.now()}`, role: "client", text: userText },
    ]);
    if (action.id === "explica_concepto") setInput("");

    chatMutation.mutate(payload, {
      onSuccess: (data: ClientCopilotChatResponse) => {
        setLog((prev) => [
          ...prev,
          {
            id: `r-${Date.now()}`,
            role: "copilot",
            text: data.response_text,
            is_stub: data.is_stub,
          },
        ]);
      },
      onError: () => {
        setLog((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: "system_error",
            text:
              "Estoy teniendo dificultades técnicas · prueba de nuevo en un " +
              "momento. Sigo aquí cuando me necesites.",
          },
        ]);
        toast.error(
          "Estamos teniendo problemas técnicos · prueba en un momento",
        );
      },
    });
  };

  const handleChatSend = () => {
    const question = input.trim();
    if (!question) return;
    setLog((prev) => [
      ...prev,
      { id: `c-${Date.now()}`, role: "client", text: question },
    ]);
    setInput("");
    chatMutation.mutate(
      {
        action_id: "chat_send",
        project_id: projectId,
        question,
      },
      {
        onSuccess: (data) => {
          setLog((prev) => [
            ...prev,
            {
              id: `r-${Date.now()}`,
              role: "copilot",
              text: data.response_text,
              is_stub: data.is_stub,
            },
          ]);
        },
        onError: () => {
          setLog((prev) => [
            ...prev,
            {
              id: `e-${Date.now()}`,
              role: "system_error",
              text:
                "Estoy teniendo dificultades técnicas · prueba de nuevo en " +
                "un momento. Sigo aquí cuando me necesites.",
            },
          ]);
          toast.error(
            "Estamos teniendo problemas técnicos · prueba en un momento",
          );
        },
      },
    );
  };

  return (
    <>
      {/* Floating button bottom-right · color suave · NO red dot */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Abrir asistente ENS"
          className="fixed bottom-6 right-6 z-40 flex h-14 items-center gap-2 rounded-full bg-blue-600 px-4 text-white shadow-lg ring-2 ring-blue-100 transition hover:bg-blue-700 md:bottom-8 md:right-8"
          data-testid="copiloto-cliente-toggle"
        >
          <Bot className="size-5" strokeWidth={2.3} aria-hidden />
          <span className="text-sm font-medium">Asistente ENS</span>
        </button>
      )}

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="flex w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-md"
        >
          <SheetHeader className="border-b border-blue-50 bg-blue-50/40 px-5 py-4">
            <div className="flex items-center gap-2">
              <Bot className="size-5 text-blue-600" strokeWidth={2.3} />
              <SheetTitle className="text-base font-semibold text-blue-900">
                🙂 Tu asistente ENS
              </SheetTitle>
            </div>
            <p className="text-xs text-blue-700">
              Estoy aquí cuando me necesites · sin prisa.
            </p>
          </SheetHeader>

          {/* Chat log + quick actions */}
          <div
            className="flex-1 overflow-y-auto px-5 py-4"
            data-testid="copiloto-cliente-chat"
          >
            {log.length === 0 ? (
              <div className="space-y-3">
                <p className="text-sm text-[color:var(--fulkro-body)]">
                  Pregúntame algo · sin prisa. Puedo ayudarte con cualquier
                  duda sobre tu workflow ENS.
                </p>
                <div className="space-y-2">
                  {quickActions.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      onClick={() => handleQuickAction(action)}
                      disabled={chatMutation.isPending}
                      className="flex w-full items-center gap-2 rounded-lg border border-blue-100 bg-white px-3 py-2.5 text-left text-sm font-medium text-[color:var(--fulkro-body)] transition-colors hover:border-blue-200 hover:bg-blue-50 disabled:opacity-50"
                    >
                      <Sparkles
                        className="size-3.5 shrink-0 text-blue-500"
                        strokeWidth={2.3}
                        aria-hidden
                      />
                      <span>{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <ul className="space-y-3" data-testid="copiloto-cliente-log">
                {log.map((entry) => (
                  <li
                    key={entry.id}
                    className={`flex ${
                      entry.role === "client" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                        entry.role === "client"
                          ? "bg-blue-600 text-white"
                          : entry.role === "system_error"
                            ? "border border-amber-200 bg-amber-50 text-amber-900"
                            : "border border-blue-100 bg-blue-50/60 text-[color:var(--fulkro-body)]"
                      }`}
                      data-testid={`copiloto-cliente-msg-${entry.role}`}
                    >
                      <span className="whitespace-pre-line">{entry.text}</span>
                      {entry.role === "copilot" && entry.is_stub && (
                        <span className="mt-1 block text-[10px] uppercase tracking-wider text-blue-500/70">
                          asistente en preparación
                        </span>
                      )}
                    </div>
                  </li>
                ))}
                {chatMutation.isPending && (
                  <li
                    className="flex justify-start"
                    data-testid="copiloto-cliente-typing"
                    aria-label="El asistente está pensando"
                  >
                    <div className="flex items-center gap-2 rounded-2xl border border-blue-100 bg-blue-50/40 px-3.5 py-2.5 text-sm text-blue-700">
                      <span className="flex items-center gap-1">
                        <span
                          className="size-1.5 animate-pulse rounded-full bg-blue-500"
                          style={{ animationDelay: "0ms" }}
                        />
                        <span
                          className="size-1.5 animate-pulse rounded-full bg-blue-500"
                          style={{ animationDelay: "150ms" }}
                        />
                        <span
                          className="size-1.5 animate-pulse rounded-full bg-blue-500"
                          style={{ animationDelay: "300ms" }}
                        />
                      </span>
                      <span className="text-xs">pensando…</span>
                    </div>
                  </li>
                )}
              </ul>
            )}
          </div>

          {/* Quick actions footer + chat input · always visible */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleChatSend();
            }}
            className="border-t border-blue-50 bg-white px-3 py-3"
          >
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Pregúntame algo · sin prisa"
                disabled={chatMutation.isPending}
                className="flex-1 rounded-lg border border-blue-100 bg-white px-3 py-2 text-sm focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
                data-testid="copiloto-cliente-input"
                aria-label="Tu pregunta"
              />
              <button
                type="submit"
                disabled={chatMutation.isPending || !input.trim()}
                className="grid size-9 place-items-center rounded-lg bg-blue-600 text-white disabled:opacity-50"
                aria-label="Enviar pregunta"
                data-testid="copiloto-cliente-send"
              >
                {chatMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Send className="size-4" />
                )}
              </button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </>
  );
}
