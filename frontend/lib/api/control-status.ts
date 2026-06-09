/**
 * lib/api/control-status · Ola 4 cierre · las lentes "semáforo" (#20) y
 * "madurez CMM" (#21) de una medida ENS.
 *
 * Dos wrappers (OPS-044): api() admin (BASE /api/v1) · clientApi() cliente
 * (proyecto resuelto de sesión). Fetch-on-expand desde la fila SoA (no N+1).
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

const BASE = "/api/v1";

export type Semaforo = "verde" | "amarillo" | "rojo" | "no_aplica";

/** #20 · semáforo de evidencia por medida (anti-falso-verde · Evidence-based). */
export interface ControlStatusResult {
  control_id: string | null;
  measure_code: string | null;
  semaforo: Semaforo;
  documents_count: number;
  documents_approved_count: number;
  documents_signed_count: number;
  cliente_reviewed_count: number;
  expired_count: number;
  missing_reasons: string[];
  requirements_met: Record<string, boolean>;
}

/** #21 · lente madurez CMM por medida (derivada de la SoA). */
export interface MeasureCmm {
  measure_code: string;
  estado_implementacion: string | null;
  cmm_level: string | null;
  cmm_label: string | null;
  target_level: string | null;
}

const q = (measureCode: string) =>
  `measure_code=${encodeURIComponent(measureCode)}`;

// ── Admin (require_owner · projectId explícito) ──
export function getAdminMeasureStatus(
  projectId: string,
  measureCode: string,
): Promise<ControlStatusResult> {
  return api<ControlStatusResult>(
    `${BASE}/admin/projects/${projectId}/controls/status?${q(measureCode)}`,
  );
}

export function getAdminMeasureCmm(
  projectId: string,
  measureCode: string,
): Promise<MeasureCmm> {
  return api<MeasureCmm>(
    `${BASE}/admin/projects/${projectId}/controls/cmm?${q(measureCode)}`,
  );
}

// ── Cliente (doble pool · proyecto resuelto de sesión) ──
export function getClienteMeasureStatus(
  measureCode: string,
): Promise<ControlStatusResult> {
  return clientApi<ControlStatusResult>(
    `/client-portal/controls/status?${q(measureCode)}`,
  );
}

export function getClienteMeasureCmm(
  measureCode: string,
): Promise<MeasureCmm> {
  return clientApi<MeasureCmm>(
    `/client-portal/controls/cmm?${q(measureCode)}`,
  );
}
