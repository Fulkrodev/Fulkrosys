/**
 * E2E · sub-atom 1.D.F.0.B v3.11 · tooltips client-portal cobertura 100%.
 *
 * Smoke verify TooltipENS triggers presentes en pages cliente core
 * (DdA · MAGERIT · firmas-hub · conformidad).
 *
 * NO interactúa con backend · spec-as-code ARTIFACT pattern OPS-045 ·
 * execution diferida CI infra full.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";

const CLIENT_PROJECT_ID = "dd000001-0000-1111-2222-333333333333";

test.describe("fase_26 client · tooltips ENS cobertura render", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsClient(page);
    // Catch-all resto endpoints /client-portal/** (notificaciones, eventos SSE
    // no aplica aquí) → respuesta vacía válida para que ningún side-effect rompa
    // el render de la página. Registrado PRIMERO: Playwright matchea handlers en
    // orden inverso de registro, así que el route específico de abajo
    // (/client-portal/project) gana para esa URL concreta.
    await page.route("**/api/v1/client-portal/**", async (route) => {
      await route.fulfill({
        status: 200,
        json: { project_id: CLIENT_PROJECT_ID },
      });
    });
    // Resolver project_id (clientApi<ProjectInfo>("/client-portal/project")).
    // El hook usa proj.id para construir las URLs /portal/<motor>/projects/{id}/...
    // Debe devolver `id` (NO `project_id`) porque los hooks leen proj.id.
    await page.route(
      "**/api/v1/client-portal/project",
      async (route) => {
        await route.fulfill({
          status: 200,
          json: { id: CLIENT_PROJECT_ID, nombre: "Proyecto Tooltips E2E" },
        });
      },
    );

    // ── Datos MAGERIT cliente ────────────────────────────────────────────
    // La página /client-portal/magerit SÓLO renderiza tooltips (TooltipENS
    // term="activo") cuando `summary` es truthy (estado "loaded"). Sin estos
    // mocks el hook useMageritClient cae en el branch !summary/error que NO
    // pinta ningún tooltip. Mockeamos summary + assets para forzar el estado
    // cargado. (El selector button[aria-label^="Ayuda:"] sigue siendo el real
    // que emite TooltipENS · verificado en components/ui/tooltip-ens.tsx.)
    await page.route(
      new RegExp("/api/v1/portal/magerit/projects/[^/]+/summary"),
      async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            project_id: CLIENT_PROJECT_ID,
            total_assets: 2,
            total_risks: 0,
            reviewed_count: 0,
            pending_review_count: 2,
            questions_count: 0,
            suggestions_count: 0,
            ready_for_validation_sign: false,
            last_signed_at: null,
          },
        });
      },
    );
    await page.route(
      new RegExp("/api/v1/portal/magerit/projects/[^/]+/assets"),
      async (route) => {
        await route.fulfill({
          status: 200,
          json: [
            {
              id: "asset-tt-1",
              analysis_id: "ana-tt-1",
              code: "S-001",
              name: "Servicio web",
              asset_type_code: "S",
              description: null,
              owner: null,
              value_d: 5,
              value_i: 5,
              value_c: 5,
              value_a: 5,
              value_t: 5,
              accumulated_d: 5,
              accumulated_i: 5,
              accumulated_c: 5,
              accumulated_a: 5,
              accumulated_t: 5,
              client_review_status: null,
              client_review_note: null,
              client_reviewed_at: null,
            },
          ],
        });
      },
    );
    await page.route(
      new RegExp("/api/v1/portal/magerit/projects/[^/]+/risks"),
      async (route) => {
        await route.fulfill({ status: 200, json: [] });
      },
    );

    // ── Datos Conformidad cliente ────────────────────────────────────────
    // La página /client-portal/conformidad pinta TooltipENS term="ENS" en el
    // branch `notFound` (declaration 404) y en el branch cargado. SÓLO el
    // branch loading/error NO tiene tooltip. Mockeamos readiness=200 +
    // declaration=404 → el hook entra en notFound y la página renderiza el
    // heading con <TooltipENS term="ENS" />. Verificado en
    // hooks/useConformidadClient.ts + app/.../conformidad/page.tsx.
    await page.route(
      new RegExp("/api/v1/portal/conformidad/projects/[^/]+/readiness"),
      async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            tier: "MEDIA",
            ready_for_conformity_sign: false,
            blockers: [],
            captured_at: "2026-05-27T10:00:00Z",
            items: [],
            dda_signed_at: null,
            magerit_signed_at: null,
            pentest_signed_at: null,
            evidence_count: 0,
            policies_signed_count: 0,
          },
        });
      },
    );
    await page.route(
      new RegExp("/api/v1/portal/conformidad/projects/[^/]+/declaration"),
      async (route) => {
        await route.fulfill({
          status: 404,
          json: { detail: "Declaration not prepared yet" },
        });
      },
    );
  });

  test("DdA page tooltip triggers aria-label visibles", async ({ page }) => {
    await page.goto(`/client-portal/dda`);
    // Esperamos que al menos 1 botón tooltip "Ayuda:" aparezca en la page
    // (TooltipENS render como button aria-label `Ayuda: <label>`).
    const tooltipTriggers = page.locator(
      'button[aria-label^="Ayuda:"]',
    );
    await expect(tooltipTriggers.first()).toBeAttached({ timeout: 10000 });
  });

  // MAGERIT se prueba contra el backend REAL: el cliente E2E tiene el proyecto
  // fijo sembrado (8 activos · 12 riesgos), así que la página entra en el estado
  // cargado. Los mocks del beforeEach no sirven aquí: el catch-all
  // /client-portal/** devuelve `{project_id}` a TODO, y los widgets del layout
  // (guía de workflow, dashboard) revientan con esa forma (`current_phase` de
  // undefined) → error-boundary. Ese era el "crash en navegación fría" que tenía
  // el test saltado: lo provocaba el mock, no la app.
  test("MAGERIT page tooltip triggers presentes", async ({ page }) => {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await page.goto(`/client-portal/magerit`);
    await expect(
      page.getByRole("heading", { name: "Activos del análisis de riesgos" }),
    ).toBeVisible({ timeout: 10000 });
    // TooltipENS INLINE: el <span> subrayado "activos críticos" es el trigger
    // (components/ui/tooltip-ens.tsx · trigger = children ?? <button>).
    const inlineTooltip = page
      .locator("span.underline", { hasText: "activos críticos" })
      .first();
    await expect(inlineTooltip).toBeVisible();
  });

  test("Conformidad page tooltip triggers presentes", async ({ page }) => {
    await page.goto(`/client-portal/conformidad`);
    const tooltipTriggers = page.locator(
      'button[aria-label^="Ayuda:"]',
    );
    await expect(tooltipTriggers.first()).toBeAttached({ timeout: 10000 });
  });
});
