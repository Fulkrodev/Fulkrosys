/**
 * MB-17.7 · ConformityWizard adaptado per categoría B/M/A.
 *
 * Verifica:
 *   - BASICA: muestra autoevaluación CCN-STIC 809 + Declaración Conformidad
 *     Básica · oculta Pentest CPSTIC + Red Team + Auditor ENAC
 *   - MEDIA: muestra Auditor ENAC + Auditoría externa · oculta Pentest
 *   - ALTA: muestra Pentest CPSTIC + Productos CPSTIC + Red Team +
 *     Criptografía 807
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_BASICA_ID = "55555555-5555-5555-5555-555555555555";
const PROJECT_MEDIA_ID = "66666666-6666-6666-6666-666666666666";
const PROJECT_ALTA_ID = "77777777-7777-7777-7777-777777777777";

const FF_BASICA = {
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

const FF_MEDIA = {
  ...FF_BASICA,
  categoria: "MEDIA",
  features: {
    ...FF_BASICA.features,
    basica_autoevaluacion: false,
    media_auditor_enac: true,
    media_auditoria_externa: true,
    refuerzos_r1: true,
  },
};

const FF_ALTA = {
  ...FF_BASICA,
  categoria: "ALTA",
  features: {
    ...FF_BASICA.features,
    basica_autoevaluacion: false,
    media_auditor_enac: true,
    media_auditoria_externa: true,
    refuerzos_r1: true,
    alta_pentest_cpstic: true,
    alta_productos_cpstic: true,
    alta_criptografia_807: true,
    alta_red_team: true,
    refuerzos_r2_r3_r4: true,
  },
};

const HEADER_STUB = {
  project: {
    id: "stub",
    nombre: "Test",
    fase: "conformidad",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "c",
    nombre: "Test",
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

test.describe("MB-17.7 · ConformityWizard adaptado per categoría", () => {
  test.beforeEach(async ({ page, context }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_BASICA_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_BASICA }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_MEDIA_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_MEDIA }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_ALTA_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_ALTA }),
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
            can_transition: true,
            target_phase: 9,
            target_phase_label: "conformidad",
            blocking_issues: [],
          },
        }),
    );
  });

  test("BASICA · muestra autoevaluación 809 · oculta Pentest + Auditor ENAC", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_BASICA_ID}/conformity`);

    await expect(
      // El h3 usa "BÁSICA" (acento) + <InfoTag> inyecta "Ayuda: Fase
      // Conformidad" en el accessible name → match exacto fallaba. Regex amplio
      // (sólo el título del wizard contiene "Camino a Conformidad"). Audit 2026-06-07.
      page.getByRole("heading", { name: /Camino a Conformidad/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Autoevaluación CCN-STIC 809/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Declaración de Conformidad \(Básica\)/i }),
    ).toBeVisible();

    await expect(page.getByText(/Pentest CPSTIC ejecutado/i)).toHaveCount(0);
    await expect(page.getByText(/Auditor externo ENAC asignado/i)).toHaveCount(
      0,
    );
    await expect(page.getByText(/Red Team E-704/i)).toHaveCount(0);
  });

  test("MEDIA · muestra Auditor ENAC + Auditoría externa · oculta Pentest", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_MEDIA_ID}/conformity`);

    await expect(
      page.getByText(/Auditor externo ENAC asignado/i),
    ).toBeVisible();
    await expect(page.getByText(/Auditoría externa ejecutada/i)).toBeVisible();
    await expect(page.getByText(/Pentest CPSTIC ejecutado/i)).toHaveCount(0);
    await expect(page.getByText(/Autoevaluación CCN-STIC 809/i)).toHaveCount(
      0,
    );
  });

  test("ALTA · muestra Pentest + Productos CPSTIC + Red Team + Cripto 807", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ALTA_ID}/conformity`);

    await expect(page.getByText(/Pentest CPSTIC ejecutado/i)).toBeVisible();
    await expect(
      page.getByText(/Productos certificados CPSTIC inventariados/i),
    ).toBeVisible();
    await expect(page.getByText(/Criptografía CCN-STIC 807/i)).toBeVisible();
    await expect(page.getByText(/Red Team E-704/i)).toBeVisible();
  });
});
