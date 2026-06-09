/**
 * Fixtures compartidos · fase_37 FASE C Path Hybrid v3.12 · Contracts
 * sub-contracts SubcontractsPanel + adendas audit trail.
 *
 * Cubre:
 *  - SubcontractsPanel render con 3 adendas distinct triggers
 *  - Audit trail expandable con triggers_history visible
 *  - Re-evaluar adendas mutation success
 *
 * Pattern reuse · OPS-045 audit-first sostained: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 */
import type { Page } from "@playwright/test";

import { mockProjectShell } from "../_helpers/project-shell";

export const PROJECT_FC_ID = "fc1f2c3a-bbbb-cccc-dddd-eeff00112233";

// ============================================================
// SubcontractsPanel mocks
// ============================================================

export const MOCK_ADENDAS_EMPTY = {
  project_id: PROJECT_FC_ID,
  count: 0,
  adendas: [],
};

export const MOCK_ADENDAS_WITH_HISTORY = {
  project_id: PROJECT_FC_ID,
  count: 3,
  adendas: [
    {
      addendum_id: "ad000001-aaaa-bbbb-cccc-000000000001",
      addendum_code: "ADENDA-ENS-2026-0001",
      provider_id: "pr000001-aaaa-bbbb-cccc-000000000001",
      contract_ref: "CONTRATO-CLOUDHOST-2026-001",
      normativas_cubiertas: ["ENS", "RGPD", "NIS2"],
      template_code: "E-604",
      firmado_cliente: true,
      firmado_proveedor: false,
      fecha_firma: "2026-05-15",
      fecha_vigor: "2026-05-15",
      vencimiento: "2027-05-15",
      created_at: "2026-05-23T15:00:00Z",
      audit_trail: {
        last_trigger: "materiality_material_cascade",
        last_auto_generated_at: "2026-05-24T10:00:00Z",
        triggers_history: [
          {
            trigger: "workflow_step_completed",
            completed_template_id: "ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL",
            auto_generated_at: "2026-05-23T15:00:00Z",
          },
          {
            trigger: "materiality_material_cascade",
            materiality_change_id: "ch000001-aaaa-bbbb-cccc-000000000001",
            materiality_level: "MATERIAL",
            materiality_flags_triggered: ["overlay", "renewal"],
            auto_generated_at: "2026-05-24T10:00:00Z",
          },
        ],
      },
    },
    {
      addendum_id: "ad000002-aaaa-bbbb-cccc-000000000002",
      addendum_code: "ADENDA-ENS-2026-0002",
      provider_id: "pr000002-aaaa-bbbb-cccc-000000000002",
      contract_ref: null,
      normativas_cubiertas: ["ENS", "RGPD"],
      template_code: "E-604",
      firmado_cliente: false,
      firmado_proveedor: false,
      fecha_firma: null,
      fecha_vigor: null,
      vencimiento: null,
      created_at: "2026-05-24T11:30:00Z",
      audit_trail: {
        last_trigger: "admin_manual",
        last_auto_generated_at: "2026-05-24T11:30:00Z",
        triggers_history: [
          {
            trigger: "admin_manual",
            admin_user_id: "marcos-user-id",
            auto_generated_at: "2026-05-24T11:30:00Z",
          },
        ],
      },
    },
    {
      addendum_id: "ad000003-aaaa-bbbb-cccc-000000000003",
      addendum_code: "ADENDA-ENS-2026-0003",
      provider_id: "pr000003-aaaa-bbbb-cccc-000000000003",
      contract_ref: null,
      normativas_cubiertas: ["ENS"],
      template_code: "E-604",
      firmado_cliente: false,
      firmado_proveedor: false,
      fecha_firma: null,
      fecha_vigor: null,
      vencimiento: null,
      created_at: "2026-04-30T08:00:00Z",
      audit_trail: {
        last_trigger: "manual",
        last_auto_generated_at: null,
        triggers_history: [],
      },
    },
  ],
};

export const MOCK_ADENDA_CHECK_RESPONSE = {
  project_id: PROJECT_FC_ID,
  trigger_template_id: "ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER",
  adendas_processed: 1,
  details: [
    {
      provider_id: "pr000002-aaaa-bbbb-cccc-000000000002",
      addendum_code: "ADENDA-ENS-2026-0002",
      addendum_id: "ad000002-aaaa-bbbb-cccc-000000000002",
      trigger: "admin_manual",
      completed_template_id: "ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER",
    },
  ],
};

// Empty contracts list to avoid noise in SubcontractsPanel-focused specs.
export const MOCK_CONTRACTS_EMPTY = { contracts: [] };
export const MOCK_CONTRACT_TEMPLATES = {
  templates: [
    {
      plantilla_id: "C-001",
      nombre: "Contrato de servicios de consultoría ENS",
      tipo: "servicio",
    },
  ],
};

// ============================================================
// Mock helpers
// ============================================================

export async function mockSubcontractsEmpty(page: Page) {
  // Layout shell (header + feature-flags) · evita el redirect de
  // ActiveProjectSync al selector cuando el projectId es sintético (el
  // /admin/projects/[id]/layout.tsx ahora resuelve el header y redirige si 404).
  await mockProjectShell(page, { projectId: PROJECT_FC_ID });
  await page.route(
    `**/api/v1/projects/${PROJECT_FC_ID}/providers/adendas`,
    async (route) => route.fulfill({ json: MOCK_ADENDAS_EMPTY }),
  );
  await page.route(
    `**/api/v1/contracts/projects/${PROJECT_FC_ID}/contracts`,
    async (route) => route.fulfill({ json: MOCK_CONTRACTS_EMPTY }),
  );
  await page.route(`**/api/v1/contracts/templates`, async (route) =>
    route.fulfill({ json: MOCK_CONTRACT_TEMPLATES }),
  );
}

export async function mockSubcontractsWithHistory(page: Page) {
  // Layout shell (header + feature-flags) · evita el redirect de
  // ActiveProjectSync al selector cuando el projectId es sintético.
  await mockProjectShell(page, { projectId: PROJECT_FC_ID });
  await page.route(
    `**/api/v1/projects/${PROJECT_FC_ID}/providers/adendas`,
    async (route) => route.fulfill({ json: MOCK_ADENDAS_WITH_HISTORY }),
  );
  await page.route(
    `**/api/v1/contracts/projects/${PROJECT_FC_ID}/contracts`,
    async (route) => route.fulfill({ json: MOCK_CONTRACTS_EMPTY }),
  );
  await page.route(`**/api/v1/contracts/templates`, async (route) =>
    route.fulfill({ json: MOCK_CONTRACT_TEMPLATES }),
  );
}

export async function mockAdendaCheckSuccess(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_FC_ID}/providers/adenda/check`,
    async (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({ json: MOCK_ADENDA_CHECK_RESPONSE });
      }
      return route.fallback();
    },
  );
}
