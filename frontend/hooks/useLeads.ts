"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { MOCK_LEADS } from "@/lib/mock";
import type { Lead, LeadStage } from "@/lib/types";

/**
 * SAN-D MB-19.5 (ADR-041): backend endpoints reales conectados:
 *   GET   /api/v1/commercial/leads
 *   PATCH /api/v1/commercial/leads/{id}/stage
 *
 * Strategy mock-fallback: si backend devuelve items > 0, usamos esos datos
 * reales. Si la BD está vacía o el endpoint falla (test environment sin
 * seed · cookies session ausentes en SSR), fallback transparente a
 * MOCK_LEADS — preserva Playwright pipeline.spec.ts existing sin requerir
 * fixtures de BD.
 *
 * Conexión real activa cuando admin tiene leads en BD (creación manual
 * via /admin/pipeline/new form · MB-19.C).
 *
 * Future PATCH endpoint /leads/{id} (assignment · notes) · diferido
 * MB-19.C.
 */

type LeadsState = {
  items: Lead[];
};

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchLeadsFromBackend(): Promise<Lead[] | null> {
  try {
    const res = await fetch("/api/v1/commercial/leads", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data?.items || !Array.isArray(data.items)) return null;
    return data.items as Lead[];
  } catch {
    return null;
  }
}

export function useLeads() {
  return useQuery({
    queryKey: ["leads"],
    queryFn: async (): Promise<LeadsState> => {
      // Try backend first (real data post-MB-19.5)
      const backendLeads = await fetchLeadsFromBackend();
      if (backendLeads !== null) {
        return { items: backendLeads };
      }
      // Fallback mock SOLO fuera de producción (R24 · 0 mocks en prod): un admin
      // real con 0 leads ve el estado vacío real, NUNCA leads ficticios. El mock
      // se preserva en dev/test para Playwright pipeline.spec.ts sin fixtures BD.
      if (process.env.NODE_ENV !== "production") {
        await sleep(120);
        return { items: MOCK_LEADS.map((l) => ({ ...l })) };
      }
      return { items: [] };
    },
    staleTime: 0,
  });
}

export function useUpdateLeadStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      leadId,
      stage,
      notes,
    }: {
      leadId: string;
      stage: LeadStage;
      notes?: string;
    }) => {
      // PATCH real vía wrapper `api` (añade x-csrf-token en mutaciones · antes
      // un fetch crudo SIN CSRF → 403 → el cambio NO persistía, sólo la UI
      // optimista). `notes` persiste razon_perdida+fecha_perdida cuando stage=lost.
      try {
        await api(
          `/api/v1/commercial/leads/${encodeURIComponent(leadId)}/stage`,
          { method: "PATCH", json: { stage, ...(notes ? { notes } : {}) } },
        );
        return { leadId, stage };
      } catch (err) {
        // 404 = lead inexistente en BD (datos mock demo dev/test) → fallback
        // silente optimista. Errores reales (400/403/500) se propagan → onError
        // revierte y la UI los muestra (no se tragan en silencio).
        if (err instanceof ApiError && err.status === 404) {
          await sleep(80);
          return { leadId, stage };
        }
        throw err;
      }
    },
    onMutate: async ({ leadId, stage }) => {
      await qc.cancelQueries({ queryKey: ["leads"] });
      const previous = qc.getQueryData<LeadsState>(["leads"]);
      qc.setQueryData<LeadsState>(["leads"], (old) =>
        old
          ? {
              items: old.items.map((l) =>
                l.id === leadId
                  ? {
                      ...l,
                      stage,
                      last_touched_at: new Date().toISOString(),
                    }
                  : l,
              ),
            }
          : old,
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(["leads"], ctx.previous);
      }
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });
}

// NOTA(#9): el antiguo `useUpdateLead` (mock sleep(80) que NO persistía) se
// eliminó. La única acción que lo usaba (LeadDrawer "Cerrar como perdido") ahora
// llama a `useUpdateLeadStage` con stage='lost' + notes → persistencia real
// (razon_perdida + fecha_perdida) vía PATCH /commercial/leads/{id}/stage.

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      draft: Omit<Lead, "id" | "last_touched_at" | "rag" | "score" | "stage">,
    ) => {
      await sleep(120);
      const id = `lead-${Math.random().toString(36).slice(2, 9)}`;
      const created: Lead = {
        ...draft,
        id,
        score: 50,
        rag: "amber",
        stage: "new",
        last_touched_at: new Date().toISOString(),
      };
      return created;
    },
    onSuccess: (created) => {
      qc.setQueryData<LeadsState>(["leads"], (old) =>
        old ? { items: [created, ...old.items] } : { items: [created] },
      );
    },
  });
}
