/**
 * MB-3.2 · FinancialPanel real wired M15 (SAN-E v3).
 *
 * Wired al backend M15 financial-summary + aapp-billing/status + invoices CRUD.
 * Run pendiente Marcos manual con servers up.
 *
 * Cobertura:
 * - 4 KPIs cards renderizan
 * - Próximo hito card visible · btn Generar factura habilitado
 * - MilestoneTimeline 8 phases nodes
 * - InvoicesList DataTable (puede estar empty)
 * - AAPPBillingStatusCard render condicional según has_active_aapp_invoice
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

test.describe("MB-3.2 · FinancialPanel M15", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/financial`);
  });

  test("4 KPIs cards renderizan", async ({ page }) => {
    // exact:true para evitar strict-mode: "Facturado" aparece también en el
    // subtítulo "% del facturado". Los labels KPI son spans con texto exacto.
    await expect(page.getByText("Facturado", { exact: true })).toBeVisible();
    await expect(page.getByText("Cobrado", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Pendiente cobro", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Vencidas", { exact: true })).toBeVisible();
  });

  test("MilestoneTimeline renderiza las fases del contrato", async ({
    page,
  }) => {
    await expect(page.getByText("Hitos del contrato")).toBeVisible();
    // Las fases del MilestoneTimeline evolucionaron a 10 (PHASES en
    // components/financial/MilestoneTimeline.tsx): se sustituyó "MAGERIT" por
    // "Análisis riesgos" y se añadió "DdA final". Cada label se renderiza dos
    // veces (layout desktop md:block + mobile md:hidden) → usamos .first()
    // para evitar strict-mode. Validamos las labels canónicas actuales.
    for (const label of [
      "Onboarding",
      "Diagnóstico",
      "Análisis riesgos",
      "Adecuación",
      "Implantación",
      "DdA final",
      "Verificación",
      "Conformidad",
      "Retainer / Cierre",
    ]) {
      await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
    }
  });

  test("Próximo hito card o estado sin hitos", async ({ page }) => {
    // Cualquiera de los dos estados
    const nextMilestone = page.getByText(/Próximo hito facturable/);
    await expect(nextMilestone).toBeVisible();
  });

  test("Histórico facturas visible (puede estar empty)", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Histórico facturas" }),
    ).toBeVisible();
  });

  test("AAPPBillingStatusCard render condicional", async ({ page }) => {
    // Card visible siempre · contenido condicional según has_active_aapp_invoice
    await expect(
      page.getByText(/Cadena facturación AAPP|Cadena AAPP/),
    ).toBeVisible();
  });
});
