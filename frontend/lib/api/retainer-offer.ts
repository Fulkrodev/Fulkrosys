/**
 * Oferta de retainer post-certificación (in-portal · cookie).
 *
 * Defecto P0 resuelto: el backend (offer_retainer) emitía notificación a
 * `/client-portal/retainer` pero ni la ruta frontend ni los endpoints existían.
 *
 *  - GET  /api/v1/client-portal/retainer-offer                  · oferta (proyecto único R27)
 *  - POST /api/v1/client-portal/retainer-offer/{projectId}/decision · accept|decline|thinking
 */
import { clientApi } from "@/lib/client-portal-api";

export interface RetainerOfferTier {
  tier_code: string;
  label: string;
  precio_mensual: number;
  sla: string;
  recommended: boolean;
}

export interface RetainerOffer {
  project_id: string;
  project_name: string;
  categoria: string | null;
  certified_at: string | null;
  lifecycle_state: string | null;
  recommended_tiers: string[];
  tiers: RetainerOfferTier[];
}

export type RetainerDecision = "accept" | "decline" | "thinking";

export function getRetainerOffer(): Promise<RetainerOffer> {
  return clientApi<RetainerOffer>("/client-portal/retainer-offer");
}

export function submitRetainerDecision(
  projectId: string,
  body: { decision: RetainerDecision; tier?: string },
): Promise<Record<string, unknown>> {
  return clientApi<Record<string, unknown>>(
    `/client-portal/retainer-offer/${projectId}/decision`,
    { json: body },
  );
}
