/**
 * MB-17.8 · Suite E2E completa Categoría MEDIA Genérico.
 *
 * Cliente MEDIA + archetype generico · verifica que UI muestra Auditor
 * ENAC + Auditoría externa pero oculta features ALTA (Pentest CPSTIC
 * · Red Team · Productos CPSTIC · Criptografía 807).
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "bbbbbbbb-1111-2222-3333-444444444444";

const FF_MEDIA = {
  categoria: "MEDIA",
  archetype: "generico",
  employee_count: 60,
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
    art9_rgpd_data: false,
    pre_categorizacion_alta_salud: false,
    pce_universidades: false,
    cra_sdlc_seguro: false,
    dora_dual_compliance: false,
    skip_mp_if_instalaciones: false,
    ztna_mfa_obligatorio: false,
    pce_nis2: false,
  },
};

const HEADER_STUB = {
  project: {
    id: PROJECT_ID,
    nombre: "Test MEDIA",
    fase: "verificacion",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "cm",
    nombre: "Cliente MEDIA",
    cif: "B22222222",
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

test.describe("MB-17.8 · MEDIA · flujo completo", () => {
  test.beforeEach(async ({ page, context }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/feature-flags`,
      (route) => route.fulfill({ status: 200, json: FF_MEDIA }),
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
                description:
                  "Asignar auditor externo ENAC obligatorio (Media+) antes de Conformidad",
                target_phase: 9,
                fix_url: `/admin/projects/${PROJECT_ID}/roles?role=auditor_externo`,
              },
            ],
          },
        }),
    );
  });

  test("Sidebar admin · muestra Verificación + Auditoría · oculta Alta", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    await expect(page.getByText(/ENS Categoría MEDIA/i)).toBeVisible();
    await expect(
      page.getByText(/Auditoría externa ENAC/i),
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: /Verificación/i }),
    ).toBeVisible();
    // Anclado: existen 2 links que matchean /Auditoría/i ("Auditoría" +
    // "Auditoría seca") → strict-mode violation. /^Auditoría$/i desambigua
    // (espejo de /^DORA$/i en el spec ALTA · auditoría 2026-06-07).
    await expect(
      page.getByRole("link", { name: /^Auditoría$/i }),
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: /Pentest CPSTIC/i }),
    ).toHaveCount(0);
    await expect(page.getByRole("link", { name: /Red Team/i })).toHaveCount(0);
  });

  test("WorkflowBlockingAlert · muestra bloqueo auditor ENAC", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    await expect(page.getByText(/Transición bloqueada/i)).toBeVisible();
    await expect(page.getByText(/auditor externo ENAC obligatorio/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Resolver/i })).toBeVisible();
  });

  test("ConformityWizard · auditor ENAC visible · pentest oculto", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/conformity`);

    await expect(
      page.getByText(/Auditor externo ENAC asignado/i),
    ).toBeVisible();
    await expect(page.getByText(/Auditoría externa ejecutada/i)).toBeVisible();
    await expect(page.getByText(/Pentest CPSTIC ejecutado/i)).toHaveCount(0);
  });
});
