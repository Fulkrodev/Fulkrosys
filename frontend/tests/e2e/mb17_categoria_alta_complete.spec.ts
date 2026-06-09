/**
 * MB-17.8 · Suite E2E completa Categoría ALTA Proveedor Financiero.
 *
 * Cliente ALTA + archetype proveedor_financiero · verifica que UI
 * muestra TODAS las features Alta + DORA dual compliance.
 * WorkflowBlockingAlert lista 4 bloqueantes (auditor + pentest +
 * productos + criptografía).
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "cccccccc-1111-2222-3333-444444444444";

const FF_ALTA_FINANCIERO = {
  categoria: "ALTA",
  archetype: "proveedor_financiero",
  employee_count: 250,
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

const HEADER_STUB = {
  project: {
    id: PROJECT_ID,
    nombre: "Test ALTA Banco",
    fase: "verificacion",
    categoria_objetivo: "ALTA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "ca",
    nombre: "Banco Test",
    cif: "B33333333",
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

test.describe("MB-17.8 · ALTA proveedor_financiero · flujo completo", () => {
  test.beforeEach(async ({ page, context }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_ALTA_FINANCIERO }),
    );
    await page.route("**/api/v1/projects/*/header", (route) =>
      route.fulfill({ status: 200, json: HEADER_STUB }),
    );
    await page.route(
      "**/api/v1/projects/*/workflow/can-transition/*",
      (route) =>
        route.fulfill({
          status: 200,
          json: {
            can_transition: false,
            target_phase: 9,
            target_phase_label: "conformidad",
            blocking_issues: [
              {
                feature_key: "media_auditor_enac",
                description: "Asignar auditor externo ENAC obligatorio",
                target_phase: 9,
                fix_url: `/admin/projects/${PROJECT_ID}/roles?role=auditor_externo`,
              },
              {
                feature_key: "alta_pentest_cpstic",
                description: "Pentest CPSTIC obligatorio (Alta) sin completar",
                target_phase: 9,
                fix_url: `/admin/projects/${PROJECT_ID}/verification?focus=pentest_cpstic`,
              },
            ],
          },
        }),
    );
  });

  test("Sidebar admin · muestra Pentest + Red Team + Productos CPSTIC + DORA", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    await expect(page.getByText(/ENS Categoría ALTA/i)).toBeVisible();
    await expect(
      page.getByText(/Pentest CPSTIC · productos certificados/i),
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: /Verificación/i }),
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

  test("ConformityWizard · 10 steps Alta visible", async ({ page }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/conformity`);

    await expect(page.getByText(/Pentest CPSTIC ejecutado/i)).toBeVisible();
    await expect(
      page.getByText(/Productos certificados CPSTIC inventariados/i),
    ).toBeVisible();
    await expect(page.getByText(/Criptografía CCN-STIC 807/i)).toBeVisible();
    await expect(page.getByText(/Red Team E-704/i)).toBeVisible();
    await expect(
      page.getByText(/Auditor externo ENAC asignado/i),
    ).toBeVisible();
  });

  test("WorkflowBlockingAlert · 2+ bloqueantes listed con fix_url", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    await expect(page.getByText(/Transición bloqueada/i)).toBeVisible();
    await expect(
      page.getByText(/auditor externo ENAC obligatorio/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Pentest CPSTIC obligatorio/i),
    ).toBeVisible();
    const resolverButtons = page.getByRole("link", { name: /Resolver/i });
    expect(await resolverButtons.count()).toBeGreaterThanOrEqual(2);
  });
});
