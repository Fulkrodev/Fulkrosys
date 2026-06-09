/**
 * Fixtures compartidos · fase_25 sub-atom 1.D.E v3.11 · MCPs project-scoped
 * operativos.
 *
 * Cubre:
 *  - GET /api/v1/mcps/tools → catalog 13 tools 4 familias
 *  - POST /api/v1/projects/{id}/mcps/{mcp}/tools/{tool}/execute → 201
 *  - GET /api/v1/projects/{id}/mcps/executions/{exec_id} → status
 *  - GET /api/v1/projects/{id}/mcps/executions → history
 *
 * Pattern reuse · OPS-045 19ª aplicación consecutiva: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 *
 * R23 sostener firmísimo · TODO project-scoped (directiva Marcos 20 May).
 */
import type { Page } from "@playwright/test";

// FIX specs UI evolucionada: el UUID hardcodeado viejo nunca se siembra. El
// proyecto fijo E2E sembrado por globalSetup (seed-rich-demo-project) usa el
// UUID determinista 00000000-…-001 (ALTA). Apuntamos ahí para que el layout
// project-scoped resuelva el proyecto real · los endpoints MCP siguen
// mockeados. Mismo patrón que san_e_v3.
export const PROJECT_EE_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

// ============================================================
// Mock catalog 13 tools 4 familias
// ============================================================

export const MOCK_MCP_CATALOG = {
  total: 13,
  families: {
    vulnscan: [
      {
        mcp_name: "vulnscan",
        tool_name: "nuclei_scan",
        label: "Nuclei",
        description:
          "Template-driven vulnerability scanner con 8000+ CVE/misconfig.",
        risk_level: "medium",
        estimated_duration_s: 1800,
        params: [
          {
            name: "target",
            type: "string",
            description: "URL o IP objetivo",
            required: true,
            default: null,
            enum: null,
            placeholder: "https://example.com",
          },
          {
            name: "severity",
            type: "string",
            description: "Severidades (csv)",
            required: false,
            default: "critical,high,medium",
            enum: null,
            placeholder: null,
          },
          {
            name: "rate_limit",
            type: "integer",
            description: "Requests/segundo",
            required: false,
            default: 150,
            enum: null,
            placeholder: null,
          },
        ],
      },
      {
        mcp_name: "vulnscan",
        tool_name: "openvas_scan",
        label: "OpenVAS",
        description: "Scanner red Greenbone.",
        risk_level: "medium",
        estimated_duration_s: 3600,
        params: [
          {
            name: "target_ip",
            type: "string",
            description: "IP/CIDR",
            required: true,
            default: null,
            enum: null,
            placeholder: "10.0.0.0/24",
          },
        ],
      },
      {
        mcp_name: "vulnscan",
        tool_name: "trivy_scan",
        label: "Trivy",
        description: "Vuln scan en imágenes Docker.",
        risk_level: "low",
        estimated_duration_s: 600,
        params: [
          {
            name: "target_image",
            type: "string",
            description: "Imagen Docker",
            required: true,
            default: null,
            enum: null,
            placeholder: "alpine:3.18",
          },
        ],
      },
      {
        mcp_name: "vulnscan",
        tool_name: "grype_sbom_scan",
        label: "Grype",
        description: "Escaneo SBOM.",
        risk_level: "low",
        estimated_duration_s: 300,
        params: [],
      },
    ],
    cloud: [
      {
        mcp_name: "cloud",
        tool_name: "prowler_scan",
        label: "Prowler",
        description: "Auditoría AWS · CIS · NIST.",
        risk_level: "low",
        estimated_duration_s: 1800,
        params: [
          {
            name: "aws_account",
            type: "string",
            description: "ID cuenta AWS",
            required: true,
            default: null,
            enum: null,
            placeholder: "123456789012",
          },
          {
            name: "compliance_check",
            type: "enum",
            description: "Marco",
            required: false,
            default: "cis_2.0",
            enum: ["cis_2.0", "nist_800_53", "iso_27001", "ens_311"],
            placeholder: null,
          },
        ],
      },
      {
        mcp_name: "cloud",
        tool_name: "scoutsuite_scan",
        label: "ScoutSuite",
        description: "Multi-cloud AWS/Azure/GCP.",
        risk_level: "low",
        estimated_duration_s: 1200,
        params: [],
      },
      {
        mcp_name: "cloud",
        tool_name: "pacu_audit",
        label: "Pacu",
        description: "Exploitation AWS.",
        risk_level: "high",
        estimated_duration_s: 1800,
        params: [],
      },
      {
        mcp_name: "cloud",
        tool_name: "kube_security_scan",
        label: "Kubernetes Security",
        description: "Auditoría K8s.",
        risk_level: "medium",
        estimated_duration_s: 900,
        params: [],
      },
    ],
    config: [
      {
        mcp_name: "config",
        tool_name: "clara_scan",
        label: "CLARA",
        description: "CCN-CERT auditor.",
        risk_level: "low",
        estimated_duration_s: 600,
        params: [],
      },
      {
        mcp_name: "config",
        tool_name: "cis_cat_scan",
        label: "CIS-CAT",
        description: "CIS Benchmarks.",
        risk_level: "low",
        estimated_duration_s: 600,
        params: [],
      },
      {
        mcp_name: "config",
        tool_name: "lynis_audit",
        label: "Lynis",
        description: "Hardening Linux.",
        risk_level: "low",
        estimated_duration_s: 300,
        params: [],
      },
      {
        mcp_name: "config",
        tool_name: "openscap_scan",
        label: "OpenSCAP",
        description: "Compliance SCAP.",
        risk_level: "low",
        estimated_duration_s: 900,
        params: [],
      },
    ],
    phishing: [
      {
        mcp_name: "phishing",
        tool_name: "gophish_campaign",
        label: "GoPhish",
        description: "Simulacro phishing controlado.",
        risk_level: "high",
        estimated_duration_s: 86400,
        params: [
          {
            name: "campaign_name",
            type: "string",
            description: "Nombre campaña",
            required: true,
            default: null,
            enum: null,
            placeholder: "Q2 2026 awareness",
          },
          {
            name: "target_users",
            type: "string",
            description: "Emails (csv)",
            required: true,
            default: null,
            enum: null,
            placeholder: "u1@empresa.es,u2@empresa.es",
          },
        ],
      },
    ],
  },
};

// ============================================================
// Mock execution responses
// ============================================================

export const EXECUTION_ID = "ee777777-aaaa-bbbb-cccc-dddddddd0001";
export const EVIDENCE_DOC_ID = "ed999999-aaaa-bbbb-cccc-dddddddd0001";

export const MOCK_EXECUTION_PENDING = {
  execution_id: EXECUTION_ID,
  project_id: PROJECT_EE_ID,
  mcp_name: "vulnscan",
  tool_name: "nuclei_scan",
  params: { target: "https://example.com" },
  triggered_by: "marcos",
  status: "pending",
  progress: 0,
  started_at: null,
  completed_at: null,
  result: null,
  error: null,
  evidence_document_id: null,
};

export const MOCK_EXECUTION_COMPLETED = {
  ...MOCK_EXECUTION_PENDING,
  status: "completed",
  progress: 100,
  started_at: "2026-05-20T13:00:00Z",
  completed_at: "2026-05-20T13:30:00Z",
  result: {
    _simulated: true,
    findings: [],
    summary: { total: 0, risk_level: "medium" },
  },
  evidence_document_id: EVIDENCE_DOC_ID,
};

export const MOCK_EXECUTIONS_HISTORY = {
  project_id: PROJECT_EE_ID,
  total: 1,
  executions: [MOCK_EXECUTION_COMPLETED],
};

// ============================================================
// Mock route helpers
// ============================================================

export async function mockMcpCatalog(page: Page) {
  await page.route(`**/api/v1/mcps/tools`, async (route) => {
    await route.fulfill({ status: 200, json: MOCK_MCP_CATALOG });
  });
}

export async function mockMcpExecutionsHistoryEmpty(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/executions`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: { project_id: PROJECT_EE_ID, total: 0, executions: [] },
      });
    },
  );
}

export async function mockMcpExecutionsHistoryWithItem(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/executions`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_EXECUTIONS_HISTORY,
      });
    },
  );
}

export async function mockMcpExecuteAndGet(
  page: Page,
  mcp = "vulnscan",
  tool = "nuclei_scan",
) {
  // POST execute → pending
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/${mcp}/tools/${tool}/execute`,
    async (route) => {
      await route.fulfill({
        status: 201,
        json: {
          ...MOCK_EXECUTION_PENDING,
          mcp_name: mcp,
          tool_name: tool,
        },
      });
    },
  );
  // GET execution → completed (polling backup vía useMCPExecution)
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/executions/${EXECUTION_ID}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          ...MOCK_EXECUTION_COMPLETED,
          mcp_name: mcp,
          tool_name: tool,
        },
      });
    },
  );
  // GET report download
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/executions/${EXECUTION_ID}/report`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          execution_id: EXECUTION_ID,
          status: "completed",
        }),
      });
    },
  );
  // SSE stream · respond with simple 200 (browser EventSource intentará
  // reconnect · suficiente para test render)
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/mcps/executions/${EXECUTION_ID}/stream`,
    async (route) => {
      // UI drift: McpExecutionProgress es SSE-driven · al recibir el evento
      // "completed" invalida la query y refetcha el GET /executions/{id} (que
      // ya mockeamos como completed) · sin ese evento la ejecución se queda en
      // "pending" y el result panel nunca aparece. Emitimos un stream SSE con
      // el evento completed para disparar la transición.
      const completedEvent =
        `event: completed\n` +
        `data: ${JSON.stringify({
          execution_id: EXECUTION_ID,
          status: "completed",
          progress: 100,
        })}\n\n`;
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: completedEvent,
      });
    },
  );
}
