/**
 * Fixtures fase_36 · Project Selector UX admin (sub-atom 1.E.2 ADR-054).
 *
 * Cubre flow project-scoped admin:
 *  - Login → /admin/projects (selector landing) cuando NO lastUsed
 *  - Login → /admin/projects/{lastUsed}/dashboard cuando localStorage existing
 *  - Sidebar ActiveProjectBanner visible + ProjectSwitcherDropdown
 *  - Breadcrumb persistent project-scoped
 *  - Cross-project data leak prevention E2E
 */
import type { Page } from "@playwright/test";

export const PROJECT_F36_A_ID = "f361a1a1-3611-4611-8611-f361a1a1a1a1";
export const PROJECT_F36_B_ID = "f362b2b2-3622-4622-8622-f362b2b2b2b2";
export const CLIENT_F36_ID = "c361c1c1-3611-4611-8611-c361c1c1c1c1";

const CLIENTS_BASE = [
  {
    id: PROJECT_F36_A_ID,
    nombre: "Cliente Piloto MEDIA SL",
    cif: "B12345678",
    sector: "tecnologia",
    rag: "green",
  },
  {
    id: PROJECT_F36_B_ID,
    nombre: "Cliente Segundo BÁSICA SA",
    cif: "B87654321",
    sector: "consultoria",
    rag: "amber",
  },
];

const PROJECT_HEADER_A = {
  project: {
    id: PROJECT_F36_A_ID,
    nombre: "ENS Media - Cliente Piloto",
    fase: "implantacion",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "active",
    fecha_kickoff: "2026-03-01",
    fecha_objetivo_certificacion: "2026-12-31",
    certified_at: null,
  },
  cliente: {
    id: CLIENT_F36_ID,
    nombre: "Cliente Piloto MEDIA SL",
    cif: "B12345678",
    sector: "tecnologia",
    provincia: "Madrid",
  },
  rseg_contact: null,
  ciso_contact: null,
  conformity: {
    route_status: "active",
    route_type: "certificacion_enac",
    expiration_date: null,
    submissions_count: 0,
    renewals_count: 0,
    material_changes_count: 0,
  },
};

const PROJECT_HEADER_B = {
  ...PROJECT_HEADER_A,
  project: {
    ...PROJECT_HEADER_A.project,
    id: PROJECT_F36_B_ID,
    nombre: "ENS Básica - Cliente Segundo",
    categoria_objetivo: "BASICA",
  },
  cliente: {
    ...PROJECT_HEADER_A.cliente,
    id: PROJECT_F36_B_ID,
    nombre: "Cliente Segundo BÁSICA SA",
    cif: "B87654321",
  },
};

export async function mockClientsAndHeaders(page: Page): Promise<void> {
  await page.route("**/api/v1/clients", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(CLIENTS_BASE),
    });
  });
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F36_A_ID}/header$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(PROJECT_HEADER_A),
      });
    },
  );
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F36_B_ID}/header$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(PROJECT_HEADER_B),
      });
    },
  );

  // Feature flags stub para layout (ProjectFeaturesProvider)
  await page.route(
    /\/api\/v1\/projects\/.+\/feature-flags/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          project_id: PROJECT_F36_A_ID,
          features: {},
        }),
      });
    },
  );

  // Permissive catch-all stub para resto endpoints proyecto (compliance,
  // dashboard KPI, etc.) · evita errores en fixtures focal.
  await page.route(/\/api\/v1\/admin\/compliance\//, async (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ overall: "green", open_alerts: 0 }),
    }),
  );
}
