/**
 * Fixtures compartidos · fase_24 sub-atom 1.D.D v3.11 · M14 Contracts +
 * M28 Change Governance wizard.
 *
 * Cubre:
 *  - M14 Contracts list + wizard 3 steps generate C-001 (con mock proposals
 *    won + mock generated contract)
 *  - M28 Change Governance wizard 5 steps · materiality determinista
 *    (intake + assess endpoints mocked)
 *
 * Pattern reuse · OPS-045 18ª aplicación consecutiva: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 */
import type { Page } from "@playwright/test";

// FIX specs UI evolucionada: el UUID hardcodeado viejo nunca se siembra. El
// proyecto fijo E2E sembrado por globalSetup (seed-rich-demo-project) usa el
// UUID determinista 00000000-…-001 (ALTA). Apuntamos ahí para que el layout
// project-scoped resuelva el proyecto real · los endpoints de contratos/cambios
// siguen mockeados. Mismo patrón que san_e_v3.
export const PROJECT_DD_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

// ============================================================
// M14 Contracts mocks
// ============================================================

export const MOCK_CONTRACT_TEMPLATES = {
  templates: [
    {
      plantilla_id: "C-001",
      nombre: "Contrato de servicios de consultoría ENS",
      tipo: "servicio",
    },
    {
      plantilla_id: "C-002",
      nombre: "Adenda contractual proveedores (ENS/RGPD Art.28)",
      tipo: "adenda",
    },
    {
      plantilla_id: "C-003",
      nombre: "Contrato de retainer post-certificación",
      tipo: "retainer",
    },
    {
      plantilla_id: "C-004",
      nombre: "NDA mutuo",
      tipo: "nda",
    },
    {
      plantilla_id: "C-005",
      nombre: "Acuerdo de nivel de servicio (SLA)",
      tipo: "sla",
    },
  ],
};

export const MOCK_CONTRACTS_LIST = {
  contracts: [
    {
      id: "c0000001-aaaa-bbbb-cccc-000000000001",
      lead_id: null,
      proposal_id: "p0000001-aaaa-bbbb-cccc-000000000001",
      project_id: PROJECT_DD_ID,
      tipo: "servicio",
      plantilla_id: "C-001",
      cliente_firmante_nombre: "Ana García López",
      cliente_firmante_cargo: "CEO",
      clausula_recursos: {},
      parametros_xyzpr: {},
      hash_sha256: "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
      firmado_marcos_at: "2026-05-10T10:00:00Z",
      firmado_cliente_at: "2026-05-12T15:30:00Z",
      firmado_cliente_link_id: null,
      vigente_desde: "2026-05-12",
      vigente_hasta: "2027-05-12",
      estado: "vigente",
      adendas: [],
      scan_window: null,
      created_at: "2026-05-08T09:00:00Z",
    },
    {
      id: "c0000002-aaaa-bbbb-cccc-000000000002",
      lead_id: null,
      proposal_id: "p0000002-aaaa-bbbb-cccc-000000000002",
      project_id: PROJECT_DD_ID,
      tipo: "servicio",
      plantilla_id: "C-001",
      cliente_firmante_nombre: "Pedro Ruiz",
      cliente_firmante_cargo: "Director TI",
      clausula_recursos: {},
      parametros_xyzpr: {},
      hash_sha256: null,
      firmado_marcos_at: null,
      firmado_cliente_at: null,
      firmado_cliente_link_id: null,
      vigente_desde: "2026-05-15",
      vigente_hasta: "2027-05-15",
      estado: "draft",
      adendas: [],
      scan_window: null,
      created_at: "2026-05-15T11:00:00Z",
    },
  ],
};

export const MOCK_PROPOSALS_WON = {
  proposals: [
    {
      id: "p0000003-aaaa-bbbb-cccc-000000000003",
      project_id: PROJECT_DD_ID,
      lead_id: null,
      numero: "P-2026-014",
      estado: "won",
      total_eur: 9500,
      created_at: "2026-04-30T10:00:00Z",
    },
  ],
};

export const MOCK_CONTRACT_GENERATED = {
  id: "c0000099-aaaa-bbbb-cccc-000000000099",
  lead_id: null,
  proposal_id: "p0000003-aaaa-bbbb-cccc-000000000003",
  project_id: PROJECT_DD_ID,
  tipo: "servicio",
  plantilla_id: "C-001",
  cliente_firmante_nombre: "Test Firmante",
  cliente_firmante_cargo: "CEO",
  clausula_recursos: {},
  parametros_xyzpr: {},
  hash_sha256: null,
  firmado_marcos_at: null,
  firmado_cliente_at: null,
  firmado_cliente_link_id: null,
  vigente_desde: "2026-05-20",
  vigente_hasta: "2027-05-20",
  estado: "draft",
  adendas: [],
  scan_window: null,
  created_at: "2026-05-20T12:00:00Z",
};

export async function mockContractsBase(page: Page) {
  await page.route(
    `**/api/v1/contracts/templates`,
    async (route) =>
      void (await route.fulfill({ status: 200, json: MOCK_CONTRACT_TEMPLATES })),
  );
  await page.route(
    `**/api/v1/contracts/projects/${PROJECT_DD_ID}/contracts`,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, json: MOCK_CONTRACTS_LIST });
      } else {
        await route.continue();
      }
    },
  );
  await page.route(
    `**/api/v1/commercial/projects/${PROJECT_DD_ID}/proposals`,
    async (route) =>
      void (await route.fulfill({ status: 200, json: MOCK_PROPOSALS_WON })),
  );
}

export async function mockContractGenerate(page: Page) {
  await page.route(
    `**/api/v1/contracts/projects/${PROJECT_DD_ID}/contracts/generate`,
    async (route) =>
      void (await route.fulfill({
        status: 201,
        json: MOCK_CONTRACT_GENERATED,
      })),
  );
}

// ============================================================
// M28 Change Governance mocks
// ============================================================

export const CHANGE_ID = "ch000001-aaaa-bbbb-cccc-000000000001";

export const MOCK_CHANGES_OPEN_LIST = [
  {
    change_id: CHANGE_ID,
    state: "assessed",
    description: "Migración base de datos PostgreSQL 14 → 16",
  },
  {
    change_id: "ch000002-aaaa-bbbb-cccc-000000000002",
    state: "intake",
    description: "Nuevo proveedor cloud secundario",
  },
];

export const MOCK_CHANGE_INTAKE_RESPONSE = {
  change_id: CHANGE_ID,
  state: "intake",
};

export const MOCK_ASSESSMENT_MATERIAL = {
  change_id: CHANGE_ID,
  project_id: PROJECT_DD_ID,
  description: "Migración base de datos PostgreSQL 14 → 16",
  materiality_level: "MATERIAL",
  materiality_score: 85,
  impact_vector: {
    evidence: true,
    document: true,
    control: true,
    overlay: false,
    roles: false,
    risk_analysis: true,
    dda: true,
    category: false,
    renewal: false,
    extraordinary: true,
  },
  required_documents: ["E-046", "E-615"],
  required_workflows: [
    "ar_rebaseline",
    "dda_update",
    "extraordinary_audit",
  ],
  required_signoffs: ["comite", "rseg", "sponsor"],
  customer_actions: ["Convocar comite extraordinario en 24h"],
  deadline_policy: "1d",
  assessed_at: "2026-05-20T13:00:00Z",
};

export const MOCK_IMPACT_MATERIAL = {
  change_id: CHANGE_ID,
  impact_vector: MOCK_ASSESSMENT_MATERIAL.impact_vector,
  materiality_level: MOCK_ASSESSMENT_MATERIAL.materiality_level,
  materiality_score: MOCK_ASSESSMENT_MATERIAL.materiality_score,
};

export async function mockChangesListBase(page: Page) {
  await page.route(
    `**/api/v1/changes/projects/${PROJECT_DD_ID}/changes/open`,
    async (route) =>
      void (await route.fulfill({
        status: 200,
        json: MOCK_CHANGES_OPEN_LIST,
      })),
  );
}

export async function mockChangesIntakeAndAssess(page: Page) {
  await page.route(
    `**/api/v1/changes/projects/${PROJECT_DD_ID}/changes`,
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          json: MOCK_CHANGE_INTAKE_RESPONSE,
        });
      } else {
        await route.continue();
      }
    },
  );
  await page.route(
    `**/api/v1/changes/projects/${PROJECT_DD_ID}/changes/${CHANGE_ID}/assess`,
    async (route) =>
      void (await route.fulfill({
        status: 200,
        json: MOCK_ASSESSMENT_MATERIAL,
      })),
  );
}

export async function mockChangeImpact(page: Page) {
  await page.route(
    `**/api/v1/changes/projects/${PROJECT_DD_ID}/changes/${CHANGE_ID}/impact`,
    async (route) =>
      void (await route.fulfill({
        status: 200,
        json: MOCK_IMPACT_MATERIAL,
      })),
  );
}
