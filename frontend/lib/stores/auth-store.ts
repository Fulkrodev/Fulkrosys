"use client";

import { create } from "zustand";

import type { MeResponse } from "../types";

import { useActiveProjectStore } from "./active-project-store";

interface AuthState {
  user: MeResponse | null;
  csrfToken: string | null;
  ready: boolean;
  setUser: (user: MeResponse | null) => void;
  setCsrf: (csrf: string | null) => void;
  setReady: (ready: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  csrfToken: null,
  ready: false,
  setUser: (user) => set({ user }),
  setCsrf: (csrfToken) => set({ csrfToken }),
  setReady: (ready) => set({ ready }),
  logout: () => {
    // Sub-atom 1.E.2 · ADR-054 · logout limpia activeProject pero preserva
    // lastUsedProjectId persistido (L3 hybrid sostained next login mismo
    // device). Si Marcos quiere full reset cross-device · clear localStorage
    // manual o usar reset() de active-project-store.
    useActiveProjectStore.getState().clearActiveProject();
    set({ user: null, csrfToken: null });
  },
}));
