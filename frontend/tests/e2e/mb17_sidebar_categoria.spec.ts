/**
 * MB-17.3 · ProjectTabs condicional per categoría B/M/A + arquetipo PYME.
 *
 * Verifica que tabs no aplicables ocultas según project feature flags:
 *   - BASICA: oculta /verification + /audit + Pentest CPSTIC + Red Team
 *   - ALTA: muestra Pentest CPSTIC + Red Team + Productos CPSTIC
 *   - SECTOR_SALUD: muestra "Art.9 RGPD" tab + banner Stethoscope
 *   - PROVEEDOR_FINANCIERO MEDIA: muestra "DORA" tab
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_BASICA_ID = "11111111-1111-1111-1111-111111111111";
const PROJECT_MEDIA_ID = "22222222-2222-2222-2222-222222222222";
const PROJECT_ALTA_ID = "33333333-3333-3333-3333-333333333333";
const PROJECT_SALUD_ID = "44444444-4444-4444-4444-444444444444";

const FF_BASICA_SAAS = {
  categoria: "BASICA",
  archetype: "saas_only",
  employee_count: null,
  features: {
    basica_autoevaluacion: true,
    media_auditor_enac: false,
    media_auditoria_externa: false,
    refuerzos_r1: false,
    alta_pentest_cpstic: false,
    alta_productos_cpstic: false,
    alta_criptografia_807: false,
    alta_red_team: false,
    alta_co_consultoria: false,
    refuerzos_r2_r3_r4: false,
    art9_rgpd_data: false,
    pre_categorizacion_alta_salud: false,
    pce_universidades: false,
    cra_sdlc_seguro: false,
    dora_dual_compliance: false,
    skip_mp_if_instalaciones: true,
    ztna_mfa_obligatorio: false,
    pce_nis2: false,
  },
};

const FF_ALTA_FINANCIERO = {
  categoria: "ALTA",
  archetype: "proveedor_financiero",
  employee_count: 200,
  features: {
    basica_autoevaluacion: false,
    media_auditor_enac: true,
    media_auditoria_externa: true,
    refuerzos_r1: true,
    alta_pentest_cpstic: true,
    alta_productos_cpstic: true,
    alta_criptografia_807: true,
    alta_red_team: true,
    alta_co_consultoria: true,
    refuerzos_r2_r3_r4: true,
    art9_rgpd_data: false,
    pre_categorizacion_alta_salud: false,
    pce_universidades: false,
    cra_sdlc_seguro: false,
    dora_dual_compliance: true,
    skip_mp_if_instalaciones: false,
    ztna_mfa_obligatorio: false,
    pce_nis2: true,
  },
};

const FF_MEDIA_SALUD = {
  categoria: "MEDIA",
  archetype: "sector_salud",
  employee_count: 80,
  features: {
    basica_autoevaluacion: false,
    media_auditor_enac: true,
    media_auditoria_externa: true,
    refuerzos_r1: true,
    alta_pentest_cpstic: false,
    alta_productos_cpstic: false,
    alta_criptografia_807: false,
    alta_red_team: false,
    alta_co_consultoria: false,
    refuerzos_r2_r3_r4: false,
    art9_rgpd_data: true,
    pre_categorizacion_alta_salud: true,
    pce_universidades: false,
    cra_sdlc_seguro: false,
    dora_dual_compliance: false,
    skip_mp_if_instalaciones: false,
    ztna_mfa_obligatorio: false,
    pce_nis2: true,
  },
};

const PROJECT_HEADER_STUB = {
  project: {
    id: "stub",
    nombre: "Test Project",
    fase: "diagnostico",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "client-stub",
    nombre: "Test Client",
    cif: "B12345678",
    sector: null,
    provincia: null,
  },
  rseg_contact: null,
  ciso_contact: null,
  conformity: {
    route_status: null,
    route_type: null,
    expiration_date: null,
    submissions_count: 0,
    renewals_count: 0,
    material_changes_count: 0,
  },
};

test.describe("MB-17.3 · ProjectTabs condicional per categoría", () => {
  test.beforeEach(async ({ page, context }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_BASICA_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_BASICA_SAAS }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_ALTA_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_ALTA_FINANCIERO }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_SALUD_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_MEDIA_SALUD }),
    );
    await page.route(`**/api/v1/projects/*/header`, (route) =>
      route.fulfill({ status: 200, json: PROJECT_HEADER_STUB }),
    );
  });

  test("BASICA SaaS · oculta Verificación + Auditoría + Pentest CPSTIC", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_BASICA_ID}/summary`);

    // Always-visible tabs presentes
    await expect(page.getByRole("link", { name: /Resumen/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Roadmap/i })).toBeVisible();

    // Tabs MEDIA+ ocultas. Nota: el tab condicional es exactamente "Auditoría"
    // (ProjectTabs.tsx /audit · categories MEDIA/ALTA). Existe además un tab
    // incondicional "Auditoría seca" (/audit-dry-run) que SÍ se muestra en
    // BÁSICA, por lo que el matcher debe ser exacto para no contarlo.
    await expect(
      page.getByRole("link", { name: /Verificación/i }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("link", { name: "Auditoría", exact: true }),
    ).toHaveCount(0);

    // Tabs ALTA ocultas
    await expect(
      page.getByRole("link", { name: /Pentest CPSTIC/i }),
    ).toHaveCount(0);
    await expect(page.getByRole("link", { name: /Red Team/i })).toHaveCount(0);
    await expect(
      page.getByRole("link", { name: /Productos CPSTIC/i }),
    ).toHaveCount(0);
  });

  test("ALTA proveedor_financiero · muestra todos tabs Alta + DORA", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ALTA_ID}/summary`);

    await expect(
      page.getByRole("link", { name: /Verificación/i }),
    ).toBeVisible();
    // Exact match: en ALTA conviven el tab "Auditoría" (/audit) y
    // "Auditoría seca" (/audit-dry-run) → /Auditoría/i dispararía strict-mode.
    await expect(
      page.getByRole("link", { name: "Auditoría", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Pentest CPSTIC/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /Red Team/i })).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Productos CPSTIC/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /^DORA$/i })).toBeVisible();
  });

  test("MEDIA sector_salud · muestra Art.9 RGPD tab + banner Stethoscope", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_SALUD_ID}/summary`);

    // Tab Art.9 RGPD visible
    await expect(
      page.getByRole("link", { name: /Art\.9 RGPD/i }),
    ).toBeVisible();

    // Banner mensaje sector salud
    await expect(page.getByText(/Sector salud · Art\.9 RGPD/i)).toBeVisible();
    await expect(page.getByText(/datos especiales/i)).toBeVisible();

    // Tabs ALTA ocultas (es MEDIA)
    await expect(
      page.getByRole("link", { name: /Pentest CPSTIC/i }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("link", { name: /^DORA$/i }),
    ).toHaveCount(0);
  });

  test("Banner contextual ENS Categoría visible per proyecto", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ALTA_ID}/summary`);

    await expect(page.getByText(/ENS Categoría ALTA/i)).toBeVisible();
    await expect(
      page.getByText(/Pentest CPSTIC · productos certificados/i),
    ).toBeVisible();
  });
});
