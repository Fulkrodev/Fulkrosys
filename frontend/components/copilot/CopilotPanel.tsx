"use client";

import { MessageCircle, RefreshCcw, Sparkles } from "lucide-react";
import * as React from "react";

import {
  CopilotComposer,
  type CopilotComposerHandle,
} from "@/components/copilot/CopilotComposer";
import { CopilotMessages } from "@/components/copilot/CopilotMessages";
import { QuickActionButtons } from "@/components/copilot/QuickActionButtons";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useCopilot } from "@/hooks/useCopilot";
import { useCopilotPageContext } from "@/hooks/useCopilotPageContext";
import { useCopilotPanelShortcut } from "@/hooks/useCopilotPanelShortcut";
import { useCopilotStore } from "@/lib/stores/copilot-store";
import { cn } from "@/lib/utils";

const MOTOR_LABEL: Record<string, string> = {
  magerit: "MAGERIT · Análisis de riesgos",
  obligations: "Obligaciones ENS",
  conformity: "Conformidad ENS",
  diagnosis: "Diagnóstico inicial",
  evidence: "Evidencias",
};

export function CopilotPanel() {
  useCopilotPanelShortcut();
  useCopilotPageContext();

  const open = useCopilotStore((s) => s.open);
  const setOpen = useCopilotStore((s) => s.setOpen);
  const closePanel = useCopilotStore((s) => s.closePanel);
  const openPanel = useCopilotStore((s) => s.openPanel);
  const panelContext = useCopilotStore((s) => s.panelContext);

  const {
    messages,
    isStreaming,
    sendMessage,
    cancel,
    clear,
  } = useCopilot();
  const composerRef = React.useRef<CopilotComposerHandle>(null);

  React.useEffect(() => {
    if (open) {
      const id = window.setTimeout(() => {
        composerRef.current?.focus();
        // Ola C · "Guíame precargado": si se abrió con un mensaje inicial (desde
        // el banner de siguiente-paso), lo pre-carga en el composer y lo limpia
        // del contexto para no re-precargarlo en aperturas posteriores.
        const store = useCopilotStore.getState();
        const initial = store.panelContext.initialMessage;
        if (initial) {
          composerRef.current?.setValue(initial);
          store.setPanelContext({ initialMessage: "" });
        }
      }, 80);
      return () => window.clearTimeout(id);
    }
    return undefined;
  }, [open]);

  function handleQuickAction(query: string) {
    composerRef.current?.setValue(query);
    void sendMessage(query);
  }

  const motorLabel = panelContext.activeMotor
    ? MOTOR_LABEL[panelContext.activeMotor] ?? panelContext.activeMotor
    : null;
  const subtitle = motorLabel
    ? `Contexto activo: ${motorLabel}`
    : "Asistente ENS · ⌘J / Ctrl+J abre y cierra";

  return (
    <>
      <button
        type="button"
        onClick={() => openPanel()}
        style={{ background: "var(--fulkro-sidebar-gradient)" }}
        className={cn(
          "fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full text-white shadow-ink ring-1 ring-white/15 transition-all hover:scale-105",
          open && "pointer-events-none scale-90 opacity-0",
        )}
        aria-label="Abrir copiloto (Cmd/Ctrl+J)"
        aria-hidden={open}
        tabIndex={open ? -1 : 0}
      >
        <MessageCircle size={26} strokeWidth={2.4} />
      </button>

      <Sheet
        open={open}
        onOpenChange={(next) => (next ? setOpen(true) : closePanel())}
      >
        <SheetContent
          side="right"
          className="flex h-dvh w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-[480px]"
          style={{
            backgroundColor: "#ffffff",
            borderColor: "var(--fulkro-surface-glass-border)",
            boxShadow: "-8px 0 28px rgba(15, 12, 41, 0.18)",
          }}
        >
          <SheetHeader
            className="flex-row items-start justify-between gap-2 border-b px-4 py-3 text-left"
            style={{
              borderColor: "var(--fulkro-surface-glass-border)",
              backgroundColor: "#f4f3fd",
            }}
          >
            <div className="min-w-0">
              <SheetTitle className="flex items-center gap-2 text-base font-bold text-[color:var(--fulkro-title)]">
                <Sparkles size={18} strokeWidth={2.4} />
                Copiloto FULKRO
              </SheetTitle>
              <p className="truncate text-xs font-medium text-[color:var(--fulkro-muted)]">
                {subtitle}
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clear}
              disabled={isStreaming}
              className="text-xs font-semibold"
              aria-label="Reiniciar conversación"
            >
              <RefreshCcw className="mr-1 h-3.5 w-3.5" strokeWidth={2.3} />
              Reiniciar
            </Button>
          </SheetHeader>

          <div className="flex flex-1 flex-col gap-2 overflow-hidden px-3 py-3">
            <CopilotMessages
              messages={messages}
              emptyState="Empieza preguntando o usa una acción rápida abajo."
            />
          </div>

          <div
            className="space-y-2 border-t px-3 py-3"
            style={{
              borderColor: "var(--fulkro-surface-glass-border)",
              backgroundColor: "#f4f3fd",
            }}
          >
            <QuickActionButtons
              context={panelContext.activeMotor}
              projectId={panelContext.projectId}
              disabled={isStreaming}
              onSelect={handleQuickAction}
            />
            <CopilotComposer
              ref={composerRef}
              isStreaming={isStreaming}
              onSend={sendMessage}
              onCancel={cancel}
            />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
