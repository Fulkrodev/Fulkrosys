// API cliente · motor de remediación (ADR-055). Vista R29 friendly.
// OPS-044: clientApi wrapper prepends /api/v1 (BASE sin prefijo).
import { clientApi } from "@/lib/client-portal-api";

export interface RemediationClienteJob {
  id: string;
  title: string;
  explicacion: string | null;
  tier: string;
  necesita_autorizacion: boolean;
  estado: string;
  fecha: string | null;
}

const BASE = "/client-portal/remediation";

export const remediationClientApi = {
  list: () => clientApi<{ jobs: RemediationClienteJob[] }>(`${BASE}/jobs`),
  authorize: (jobId: string) =>
    clientApi<RemediationClienteJob>(`${BASE}/jobs/${jobId}/authorize`, {
      method: "POST",
      json: {},
    }),
};
