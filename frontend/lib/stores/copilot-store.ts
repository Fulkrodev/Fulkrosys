"use client";

import { create } from "zustand";

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ text: string; ref: string }>;
  createdAt: string;
}

export interface CopilotPanelContext {
  url?: string;
  projectId?: string;
  clientId?: string;
  activeMotor?: string;
  projectPhase?: string;
  /**
   * feat/fulkro-100 Ola C · "Guíame precargado": cuando se abre el panel desde
   * el banner de siguiente-paso, este mensaje se PRE-CARGA en el composer (sin
   * auto-enviar · el admin lo revisa/edita/envía). El panel lo limpia tras
   * precargarlo (lo pone a "") para no re-precargar en aperturas siguientes.
   */
  initialMessage?: string;
}

interface CopilotState {
  open: boolean;
  panelContext: CopilotPanelContext;
  messages: CopilotMessage[];
  setOpen: (open: boolean) => void;
  toggle: () => void;
  openPanel: (context?: Partial<CopilotPanelContext>) => void;
  closePanel: () => void;
  /**
   * Merge-update panelContext · accepts partial · undefined values are
   * filtered out so consumers can pass derived fields without wiping
   * unrelated keys set por otros consumers (ActiveProjectSync vs
   * useCopilotPageContext race · Sesión 3B-2B.4 Phase 1.4 fix).
   */
  setPanelContext: (context: Partial<CopilotPanelContext>) => void;
  /** Full-replace · used by `clear` flows o cliente portal reset. */
  resetPanelContext: () => void;
  appendMessage: (message: CopilotMessage) => void;
  clear: () => void;
}

function mergePanelContext(
  prev: CopilotPanelContext,
  next: Partial<CopilotPanelContext>,
): CopilotPanelContext {
  const merged: CopilotPanelContext = { ...prev };
  for (const [key, value] of Object.entries(next)) {
    if (value !== undefined) {
      (merged as Record<string, unknown>)[key] = value;
    }
  }
  return merged;
}

export const useCopilotStore = create<CopilotState>((set) => ({
  open: false,
  panelContext: {},
  messages: [],
  setOpen: (open) => set({ open }),
  toggle: () => set((s) => ({ open: !s.open })),
  openPanel: (context) =>
    set((s) => ({
      open: true,
      panelContext: context
        ? mergePanelContext(s.panelContext, context)
        : s.panelContext,
    })),
  closePanel: () => set({ open: false }),
  setPanelContext: (context) =>
    set((s) => ({ panelContext: mergePanelContext(s.panelContext, context) })),
  resetPanelContext: () => set({ panelContext: {} }),
  appendMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),
  clear: () => set({ messages: [] }),
}));
