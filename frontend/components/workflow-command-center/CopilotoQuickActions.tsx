/**
 * CopilotoQuickActions · 4 buttons stub · sub-atom 1.C.D.B.3 v3.8.
 *
 * Click QuickAction dispatch CopilotoAdmin chat con action_id contextualizado.
 * Stub responses CALIDAD coherentes con context current (project + step).
 */
"use client";

import * as React from "react";
import {
  Compass,
  Calendar,
  HelpCircle,
  Loader2,
  Mail,
  Send,
} from "lucide-react";

import { Button } from "@/components/ui/button";

import { useCopilotoChat } from "@/hooks/useCopilotoAdmin";
import type { CopilotActionId } from "@/lib/api/copiloto-admin";

interface ProjectContext {
  project_id?: string;
  project_nombre?: string;
  step_template_id?: string;
  step_title?: string;
  fase_actual?: string;
  // 1.D.F.0.D · screen-aware admin tutor button-level guidance
  current_screen?: string;
  active_motor?: string;
}

interface CopilotoQuickActionsProps {
  context: ProjectContext;
  onResponseAppend: (
    action_id: string,
    response_text: string,
    options?: { is_stub?: boolean; is_error?: boolean },
  ) => void;
}

interface QuickActionDef {
  id: CopilotActionId;
  label: string;
  icon: React.ReactNode;
}

const QUICK_ACTIONS: QuickActionDef[] = [
  { id: "que_hago", label: "¿Qué hago ahora?", icon: <HelpCircle className="size-3" /> },
  { id: "explica_paso", label: "Explícame este paso", icon: <Compass className="size-3" /> },
  { id: "draft_email", label: "Draft email", icon: <Mail className="size-3" /> },
  { id: "briefing_reunion", label: "Briefing reunión", icon: <Calendar className="size-3" /> },
];

export function CopilotoQuickActions({
  context,
  onResponseAppend,
}: CopilotoQuickActionsProps) {
  const mutation = useCopilotoChat();
  const [activeAction, setActiveAction] = React.useState<string | null>(null);

  const handleClick = (actionId: CopilotActionId) => {
    setActiveAction(actionId);
    mutation.mutate(
      {
        action_id: actionId,
        ...context,
      },
      {
        onSuccess: (data) => {
          onResponseAppend(actionId, data.response_text, {
            is_stub: data.is_stub,
          });
          setActiveAction(null);
        },
        onError: () => {
          onResponseAppend(
            actionId,
            "Hubo un problema técnico con el copiloto. " +
              "Intenta de nuevo en un momento · si persiste · revisa la " +
              "configuración LLM o el log de m_observability.",
            { is_error: true },
          );
          setActiveAction(null);
        },
      },
    );
  };

  return (
    <div className="space-y-1.5" data-testid="copiloto-admin-quick-actions">
      <p className="text-[10px] uppercase font-semibold text-foreground/70 tracking-wider">
        Acciones rápidas
      </p>
      <div className="grid grid-cols-1 gap-1.5">
        {QUICK_ACTIONS.map((qa) => {
          const isPending =
            activeAction === qa.id && mutation.isPending;
          return (
            <Button
              key={qa.id}
              variant="outline"
              size="sm"
              className="justify-start text-xs h-8"
              onClick={() => handleClick(qa.id)}
              disabled={isPending}
            >
              {isPending ? (
                <Loader2 className="mr-2 size-3 animate-spin" />
              ) : (
                <span className="mr-2">{qa.icon}</span>
              )}
              {qa.label}
            </Button>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================
// Chat input · stub LLM swap-in 1.D.B.2
// ============================================================

interface CopilotoChatInputProps {
  context: ProjectContext;
  onResponseAppend: (
    action_id: string,
    response_text: string,
    options?: { is_stub?: boolean; is_error?: boolean },
  ) => void;
}

export function CopilotoChatInput({
  context,
  onResponseAppend,
}: CopilotoChatInputProps) {
  const [value, setValue] = React.useState("");
  const mutation = useCopilotoChat();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    mutation.mutate(
      {
        action_id: "chat_send",
        question: value,
        ...context,
      },
      {
        onSuccess: (data) => {
          onResponseAppend("chat_send", data.response_text, {
            is_stub: data.is_stub,
          });
          setValue("");
        },
        onError: () => {
          onResponseAppend(
            "chat_send",
            "Hubo un problema técnico con el copiloto. Intenta de nuevo en " +
              "un momento.",
            { is_error: true },
          );
        },
      },
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-1.5"
      data-testid="copiloto-admin-chat-form"
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Pregúntame algo…"
        className="flex-1 rounded-md border border-input bg-background px-2 py-1.5 text-xs"
        disabled={mutation.isPending}
        data-testid="copiloto-admin-chat-input"
      />
      <Button
        type="submit"
        size="sm"
        variant="primary"
        className="h-8 w-8 p-0"
        disabled={mutation.isPending || !value.trim()}
        aria-label="Enviar"
        data-testid="copiloto-admin-chat-send"
      >
        {mutation.isPending ? (
          <Loader2 className="size-3 animate-spin" />
        ) : (
          <Send className="size-3" />
        )}
      </Button>
    </form>
  );
}
