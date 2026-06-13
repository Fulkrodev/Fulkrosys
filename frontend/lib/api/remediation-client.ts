// API cliente · motor de remediación (ADR-055). Vista R29 friendly.
// Mirror de client-cloud-remediations: usa `api` con path completo /api/v1/client-portal.
import { api } from "@/lib/api";

export interface RemediationClienteJob {
  id: string;
  title: string;
  explicacion: string | null;
  tier: string;
  necesita_autorizacion: boolean;
  estado: string;
  fecha: string | null;
}

const BASE = "/api/v1/client-portal/remediation";

export const remediationClientApi = {
  list: () => api<{ jobs: RemediationClienteJob[] }>(`${BASE}/jobs`),
  authorize: (jobId: string) =>
    api<RemediationClienteJob>(`${BASE}/jobs/${jobId}/authorize`, {
      method: "POST",
      json: {},
    }),
};
