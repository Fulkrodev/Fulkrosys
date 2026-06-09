/**
 * MCPs API client — Sub-bloque 9.B (status registry) + sub-atom 1.D.E v3.11
 * (executions project-scoped).
 *
 * Endpoints servidos:
 *   GET /api/v1/mcps/status → registry estatico 14 MCPs
 *   GET /api/v1/mcps/tools → catalog 13 tools 4 familias (1.D.E.A)
 *   POST /api/v1/projects/{id}/mcps/{mcp}/tools/{tool}/execute (1.D.E.A)
 *   GET /api/v1/projects/{id}/mcps/executions/{exec_id}
 *   GET /api/v1/projects/{id}/mcps/executions/{exec_id}/stream → SSE
 *   GET /api/v1/projects/{id}/mcps/executions/{exec_id}/report → JSON DL
 *   GET /api/v1/projects/{id}/mcps/executions → history per project
 *
 * R23 sostener firmísimo · TODO project-scoped (directiva Marcos).
 */
import { api } from "@/lib/api";

export type MCPState = "real" | "available" | "coming_soon" | "blocked";

export type MCPCategory =
  | "scope"
  | "recon"
  | "vulnscan"
  | "webpentest"
  | "infra"
  | "redteam"
  | "cloud"
  | "config"
  | "phishing"
  | "apisec"
  | "mobile"
  | "wireless"
  | "cracking"
  | "sast";

export interface MCPStatus {
  name: string;
  label: string;
  description: string;
  category: MCPCategory;
  state: MCPState;
  version: string | null;
  docker_image: string | null;
  tools_count: number;
  last_health_check: string | null;
}

export interface MCPsStatusResponse {
  total: number;
  real_count: number;
  available_count: number;
  coming_soon_count: number;
  blocked_count: number;
  items: MCPStatus[];
}

export const getMCPsStatus = (): Promise<MCPsStatusResponse> =>
  api<MCPsStatusResponse>("/api/v1/mcps/status");

// ════════════════════════════════════════════════════════════════════
// Sub-atom 1.D.E.A v3.11 · catalog + executions project-scoped
// ════════════════════════════════════════════════════════════════════

export type MCPFamily = "vulnscan" | "cloud" | "config" | "phishing";
export type MCPExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed";
export type MCPRiskLevel = "low" | "medium" | "high";

export interface MCPToolParam {
  name: string;
  type: string; // string · integer · enum
  description: string;
  required: boolean;
  default: unknown | null;
  enum: string[] | null;
  placeholder: string | null;
}

export interface MCPToolSchema {
  mcp_name: MCPFamily;
  tool_name: string;
  label: string;
  description: string;
  risk_level: MCPRiskLevel;
  estimated_duration_s: number;
  params: MCPToolParam[];
}

export interface MCPCatalog {
  families: Record<MCPFamily, MCPToolSchema[]>;
  total: number;
}

export interface MCPExecution {
  execution_id: string;
  project_id: string;
  mcp_name: MCPFamily;
  tool_name: string;
  params: Record<string, unknown>;
  triggered_by: string;
  status: MCPExecutionStatus;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  evidence_document_id: string | null;
}

export interface MCPExecutionsHistory {
  project_id: string;
  total: number;
  executions: MCPExecution[];
}

export const MCP_FAMILY_LABELS: Record<MCPFamily, string> = {
  vulnscan: "Vulnerability Scan",
  cloud: "Cloud Security",
  config: "Configuration Audit",
  phishing: "Phishing Simulation",
};

export const MCP_RISK_LABELS: Record<MCPRiskLevel, string> = {
  low: "Bajo",
  medium: "Medio",
  high: "Alto",
};

export const MCP_RISK_VARIANTS: Record<
  MCPRiskLevel,
  "success" | "warning" | "danger"
> = {
  low: "success",
  medium: "warning",
  high: "danger",
};

export const MCP_STATUS_LABELS: Record<MCPExecutionStatus, string> = {
  pending: "Pendiente",
  running: "Ejecutando",
  completed: "Completado",
  failed: "Fallido",
};

export const MCP_STATUS_VARIANTS: Record<
  MCPExecutionStatus,
  "secondary" | "info" | "success" | "danger"
> = {
  pending: "secondary",
  running: "info",
  completed: "success",
  failed: "danger",
};

export const mcpsApi = {
  getCatalog: () => api<MCPCatalog>("/api/v1/mcps/tools"),

  execute: (
    projectId: string,
    mcpName: MCPFamily,
    toolName: string,
    params: Record<string, unknown>,
  ) =>
    api<MCPExecution>(
      `/api/v1/projects/${projectId}/mcps/${mcpName}/tools/${toolName}/execute`,
      { json: { params } },
    ),

  getExecution: (projectId: string, executionId: string) =>
    api<MCPExecution>(
      `/api/v1/projects/${projectId}/mcps/executions/${executionId}`,
    ),

  listExecutions: (projectId: string) =>
    api<MCPExecutionsHistory>(
      `/api/v1/projects/${projectId}/mcps/executions`,
    ),

  /**
   * SSE stream URL builder. Consume via `new EventSource(url, { withCredentials: true })`.
   */
  streamUrl: (projectId: string, executionId: string): string =>
    `/api/v1/projects/${projectId}/mcps/executions/${executionId}/stream`,

  /**
   * Descarga reporte JSON · usa fetch directo (Blob).
   */
  async downloadReport(
    projectId: string,
    executionId: string,
  ): Promise<Blob> {
    const response = await fetch(
      `/api/v1/projects/${projectId}/mcps/executions/${executionId}/report`,
      { credentials: "include" },
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
