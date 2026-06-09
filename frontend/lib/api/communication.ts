/**
 * API client · Motor 18 Communication.
 *
 * Endpoints servidos desde m18 con prefix `/api/v1/communication`.
 * Las rutas project-scoped repiten `/communication/`.
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/communication";

export interface CommunicationPlan {
  id?: string;
  project_id?: string;
  cadencia?: string;
  estado?: string;
  destinatarios?: string[];
  scope?: Record<string, unknown>;
  activated_at?: string | null;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface CommunicationReport {
  id: string;
  project_id?: string;
  tipo?: string;
  estado?: string;
  titulo?: string;
  resumen?: string;
  fecha_periodo?: string;
  generated_at?: string | null;
  sent_at?: string | null;
  [key: string]: unknown;
}

export interface CommunicationEscalation {
  id: string;
  project_id?: string;
  evento_tipo?: string;
  severidad?: string;
  resuelto?: boolean;
  detected_at?: string;
  resolved_at?: string | null;
  detalle?: string;
  [key: string]: unknown;
}

export const communicationApi = {
  getPlan: (projectId: string) =>
    api<CommunicationPlan>(
      `${BASE}/projects/${projectId}/communication/plan`,
    ),

  listReports: (
    projectId: string,
    opts: { tipo?: string; estado?: string } = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.tipo) sp.set("tipo", opts.tipo);
    if (opts.estado) sp.set("estado", opts.estado);
    const qs = sp.toString();
    return api<{ reports: CommunicationReport[] }>(
      `${BASE}/projects/${projectId}/communication/reports${qs ? `?${qs}` : ""}`,
    );
  },

  listEscalations: (
    projectId: string,
    opts: { resuelto?: boolean } = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.resuelto !== undefined) {
      sp.set("resuelto", String(opts.resuelto));
    }
    const qs = sp.toString();
    return api<{ escalations: CommunicationEscalation[] }>(
      `${BASE}/projects/${projectId}/communication/escalations${qs ? `?${qs}` : ""}`,
    );
  },

  activeEscalationsCount: (projectId: string) =>
    api<{ active_count: number }>(
      `${BASE}/projects/${projectId}/communication/escalations/active-count`,
    ),
};
