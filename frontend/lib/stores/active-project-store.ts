"use client";

/**
 * Active Project Store · Zustand + persist middleware.
 *
 * Sub-atom 1.E.2 Phase C · ADR-054 Project-Scoped Admin UX.
 *
 * Source of truth: URL param `params.id` en /admin/projects/[id]/*.
 * Cache cross-navigation: `activeProject` (full project metadata para
 * sidebar banner + breadcrumb sin re-fetch).
 * L3 hybrid post-login: `lastUsedProjectId` persistido localStorage.
 *
 * Sólo admin · cliente portal NO usa este store (R29 client-scoped
 * natively · cliente ve sólo SU proyecto · 1 proyecto/user).
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type EnsCategory = "BASICA" | "MEDIA" | "ALTA";

export interface ActiveProject {
  id: string;
  name: string;
  clientId: string;
  clientName: string;
  ensCategory: EnsCategory | null;
  status: string;
  lastAccessedAt: number;
}

interface ActiveProjectStore {
  /** Current active project · sincronizado con URL param vía routing guard. */
  activeProject: ActiveProject | null;
  /** L3 hybrid · last-used project ID persistido cross-session. */
  lastUsedProjectId: string | null;
  /** Set active project + update lastUsed timestamp. */
  setActiveProject: (p: ActiveProject | null) => void;
  /** Clear active project (logout / explicit deselect). NO clear lastUsedProjectId. */
  clearActiveProject: () => void;
  /** Full reset · logout flow clear todo. */
  reset: () => void;
}

export const STORAGE_KEY = "fulkro-active-project";

export const useActiveProjectStore = create<ActiveProjectStore>()(
  persist(
    (set) => ({
      activeProject: null,
      lastUsedProjectId: null,
      setActiveProject: (p) =>
        set({
          activeProject: p,
          // Solo actualizar lastUsedProjectId si project provided
          // (NULL setActiveProject NO debe perder memoria L3).
          ...(p ? { lastUsedProjectId: p.id } : {}),
        }),
      clearActiveProject: () => set({ activeProject: null }),
      reset: () => set({ activeProject: null, lastUsedProjectId: null }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // Solo persistir lastUsedProjectId · activeProject se hidrata desde
      // URL param routing guard onMount (URL es source of truth canonical).
      partialize: (state) => ({ lastUsedProjectId: state.lastUsedProjectId }),
    },
  ),
);

/**
 * SSR-safe helper para leer lastUsedProjectId desde localStorage.
 * Usado por redirect.ts L3 hybrid · NO usar Zustand directamente porque
 * `redirect.ts` no es React component (no puede llamar hooks).
 */
export function readLastUsedProjectIdFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: { lastUsedProjectId?: string } };
    return parsed.state?.lastUsedProjectId ?? null;
  } catch {
    return null;
  }
}
