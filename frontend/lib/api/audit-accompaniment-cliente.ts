/**
 * Audit Accompaniment cliente API client · Sesión 3B-4 Ejecutable 7.5 Phase 7.5.3.
 *
 * 1 endpoint backend read-only:
 *   GET /client-portal/accompaniment/timeline
 *
 * Cliente-mínimo filosofía: cliente RECIBE timeline updates · NO opera proceso.
 * R29 friendly · sin technical jargon · single-project per cliente LIMIT 1.
 */
import { clientApi } from "@/lib/client-portal-api";

import type { AccompanimentTimeline } from "@/lib/api/audit-accompaniment";

export const auditAccompanimentClienteApi = {
  getTimeline: async (): Promise<AccompanimentTimeline> => {
    return clientApi<AccompanimentTimeline>("/client-portal/accompaniment/timeline");
  },
};
