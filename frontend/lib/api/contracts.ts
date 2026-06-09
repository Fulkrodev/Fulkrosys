/**
 * API client · Motor 14 Contracts.
 *
 * Endpoints servidos desde m14 con prefix `/api/v1/contracts`:
 *   GET  /api/v1/contracts/templates
 *   GET  /api/v1/contracts/projects/{id}/contracts
 *   GET  /api/v1/contracts/projects/{id}/contracts/{cid}
 *   POST /api/v1/contracts/projects/{id}/contracts/generate
 *   POST /api/v1/contracts/projects/{id}/contracts/generate-llm
 *   POST /api/v1/contracts/projects/{id}/contracts/{cid}/sign-marcos
 *   POST /api/v1/contracts/projects/{id}/contracts/{cid}/send-client
 *   GET  /api/v1/contracts/projects/{id}/contracts/{cid}/commitments
 *   GET  /api/v1/contracts/projects/{id}/contracts/{cid}/docx
 *
 * Proposals (M13) usado por wizard Step 2 para seleccionar propuesta won:
 *   GET  /api/v1/commercial/projects/{id}/proposals
 */
import { api } from "@/lib/api";
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE = "/api/v1/contracts";
const BASE_COMMERCIAL = "/api/v1/commercial";

export type ContractEstado =
  | "draft"
  | "firmado_marcos"
  | "sent"
  | "firmado_cliente"
  | "vigente"
  | "vencido"
  | "rescindido";

export interface ContractTemplate {
  plantilla_id: string;
  nombre: string;
  tipo: string;
}

export interface Contract {
  id: string;
  lead_id: string | null;
  proposal_id: string | null;
  project_id: string | null;
  tipo: string;
  plantilla_id: string;
  cliente_firmante_nombre: string;
  cliente_firmante_cargo: string;
  clausula_recursos: Record<string, unknown> | null;
  parametros_xyzpr: Record<string, unknown> | null;
  hash_sha256: string | null;
  firmado_marcos_at: string | null;
  firmado_cliente_at: string | null;
  firmado_cliente_link_id: string | null;
  vigente_desde: string | null;
  vigente_hasta: string | null;
  estado: ContractEstado;
  adendas: unknown[] | null;
  scan_window: Record<string, unknown> | null;
  created_at: string | null;
}

export interface ContractsListResponse {
  contracts: Contract[];
}

export interface ContractGenerateBody {
  proposal_id: string;
  plantilla_id: string;
  cliente_firmante_nombre: string;
  cliente_firmante_cargo: string;
  vigencia_meses?: number;
  parametros_xyzpr?: Record<string, unknown>;
  clausula_recursos?: Record<string, unknown>;
}

export interface ContractCommitment {
  id: string;
  contract_id: string;
  project_id: string | null;
  tipo: string;
  descripcion: string | null;
  parametro: string | null;
  valor_esperado: string | null;
  valor_actual: string | null;
  cumplido: boolean | null;
  ultima_verificacion_at: string | null;
}

export interface ProposalSummary {
  id: string;
  project_id: string;
  lead_id: string | null;
  numero: string | null;
  estado: string;
  total_eur: number | null;
  created_at: string | null;
}

// #9 · datos del cliente para pre-rellenar el wizard de contrato.
export interface ContractClientPrefill {
  razon_social: string | null;
  cif: string | null;
  domicilio_fiscal: string | null;
  persona_contacto: string | null;
}

export const contractsApi = {
  listTemplates: () =>
    api<{ templates: ContractTemplate[] }>(`${BASE}/templates`),

  list: (projectId: string) =>
    api<ContractsListResponse>(
      `${BASE}/projects/${projectId}/contracts`,
    ),

  get: (projectId: string, contractId: string) =>
    api<Contract>(`${BASE}/projects/${projectId}/contracts/${contractId}`),

  generate: (projectId: string, body: ContractGenerateBody) =>
    api<Contract>(`${BASE}/projects/${projectId}/contracts/generate`, {
      json: body,
    }),

  signMarcos: (projectId: string, contractId: string) =>
    api<Contract>(
      `${BASE}/projects/${projectId}/contracts/${contractId}/sign-marcos`,
      { json: {} },
    ),

  sendClient: (
    projectId: string,
    contractId: string,
    body: { recipient_email: string; base_url?: string },
  ) =>
    api<{ contract: Contract; magic_link: unknown }>(
      `${BASE}/projects/${projectId}/contracts/${contractId}/send-client`,
      { json: body },
    ),

  listCommitments: (projectId: string, contractId: string) =>
    api<{ commitments: ContractCommitment[] }>(
      `${BASE}/projects/${projectId}/contracts/${contractId}/commitments`,
    ),

  listProposals: (projectId: string) =>
    api<{ proposals: ProposalSummary[] } | ProposalSummary[]>(
      `${BASE_COMMERCIAL}/projects/${projectId}/proposals`,
    ),

  // #9 · prefill del cliente para el wizard de contrato.
  clientPrefill: (projectId: string) =>
    api<ContractClientPrefill>(
      `${BASE}/projects/${projectId}/contracts/client-prefill`,
    ),

  /**
   * Descarga DOCX como Blob — no usa el wrapper `api` porque devuelve binario.
   */
  async downloadDocx(projectId: string, contractId: string): Promise<Blob> {
    const headers = new Headers();
    const csrf = getCsrfToken();
    if (csrf) headers.set(CSRF_HEADER, csrf);

    const response = await fetch(
      `${BASE}/projects/${projectId}/contracts/${contractId}/docx`,
      {
        method: "GET",
        headers,
        credentials: "include",
      },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const payload = await response.json();
        if (payload && typeof payload === "object" && "detail" in payload) {
          detail = String((payload as { detail: unknown }).detail);
        }
      } catch {
        // not JSON
      }
      throw new Error(detail);
    }
    return response.blob();
  },
};

export const CONTRACT_ESTADO_LABELS: Record<ContractEstado, string> = {
  draft: "Borrador",
  firmado_marcos: "Firmado por Marcos",
  sent: "Enviado al cliente",
  firmado_cliente: "Firmado por cliente",
  vigente: "Vigente",
  vencido: "Vencido",
  rescindido: "Rescindido",
};

export const CONTRACT_ESTADO_VARIANTS: Record<
  ContractEstado,
  "secondary" | "warning" | "success" | "danger"
> = {
  draft: "secondary",
  firmado_marcos: "warning",
  sent: "warning",
  firmado_cliente: "warning",
  vigente: "success",
  vencido: "secondary",
  rescindido: "danger",
};
