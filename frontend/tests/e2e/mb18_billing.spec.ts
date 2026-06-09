/**
 * E2E tests MB-18 auto-billing + retainer churn (ADR-040).
 *
 * Cobertura 6 specs:
 * 1. Admin /admin/finance · KPI cards visibles + ReconciliationManualPanel
 * 2. Admin pending payments listado + Mark paid Dialog flow
 * 3. Admin /admin/retainers/churn-risk renderiza scores + recommended actions
 * 4. Cliente /client-portal/billing renderiza IBAN info-mode (NO botón)
 * 5. Cliente /client-portal/billing pending invoice muestra strong IBAN
 * 6. Account page CTA links notifications + billing
 *
 * Pattern stack real (MB-13/14/15/16/17 acumulado):
 * - loginAsMarcos cookies reales backend
 * - loginAsClient form fill real /client-portal/login
 * - page.route mocks API responses específicas
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import {
  loginAsClient,
  loginAsMarcos,
} from "./_helpers/auth-real";


const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const MILESTONE_ID = "22222222-2222-2222-2222-222222222222";
const INVOICE_ID = "33333333-3333-3333-3333-333333333333";
const RETAINER_ID = "44444444-4444-4444-4444-444444444444";


const KPIS_RESPONSE = {
  billed_this_month_eur: "5400.00",
  paid_this_month_eur: "1500.00",
  pending_total_eur: "3900.00",
  overdue_count: 1,
};


const PENDING_RESPONSE = [
  {
    milestone_id: MILESTONE_ID,
    milestone_name: "hito_2_dda_politicas",
    milestone_index: 1,
    project_id: PROJECT_ID,
    project_name: "Cliente Test SA",
    invoice_id: INVOICE_ID,
    invoice_number: "FULKRO-2026-0042",
    amount_eur: "1200.00",
    billed_at: "2026-04-15T10:00:00Z",
    days_pending: 22,
  },
];


const CHURN_RESPONSE = [
  {
    signal_id: "55555555-5555-5555-5555-555555555555",
    retainer_id: RETAINER_ID,
    project_id: PROJECT_ID,
    computed_at: "2026-05-06T09:30:00Z",
    churn_risk_score: "85.00",
    risk_level: "critical",
    days_since_portal_login: 75,
    days_since_chat_msg_client: 60,
    tasks_overdue_count: 4,
    invoices_overdue_count: 1,
    primary_risk_factors: [
      "days_since_portal_login>60 (actual: 75)",
      "tasks_overdue>3 (actual: 4)",
    ],
    recommended_action: "Contacto urgente Marcos · agendar check-in directo",
  },
];


const CLIENT_INVOICES_RESPONSE = [
  {
    invoice_id: INVOICE_ID,
    invoice_number: "FULKRO-2026-0042",
    concepto: "Hito 2: hito_2_dda_politicas",
    base_imponible: "1000.00",
    iva_importe: "210.00",
    total: "1210.00",
    fecha_emision: "2026-04-15",
    fecha_vencimiento: "2026-05-15",
    estado_pago: "pendiente",
    bank_instructions_html: (
      "<div><h4>📋 Instrucciones para la transferencia</h4>" +
      "<p>💶 Importe: <strong>1210.00 EUR</strong></p>" +
      "<p>📋 IBAN: <strong>ES12 1234 5678 9012 3456 7890</strong></p>" +
      "<p>👤 Titular: <strong>Marcos Mata Vega</strong></p>" +
      "<p>🔖 Concepto: <strong>Factura FULKRO-2026-0042</strong></p>" +
      "</div>"
    ),
    bank_instructions_text:
      "📋 INSTRUCCIONES · IBAN ES12 1234 5678 9012 3456 7890",
  },
];


async function stubAdminFinance(page: Page): Promise<void> {
  await page.route(
    "**/api/v1/admin/finance/kpis",
    (route) => route.fulfill({ status: 200, json: KPIS_RESPONSE }),
  );
  await page.route(
    "**/api/v1/admin/finance/pending-payments",
    (route) => route.fulfill({ status: 200, json: PENDING_RESPONSE }),
  );
  await page.route(
    `**/api/v1/admin/finance/milestones/${MILESTONE_ID}/mark-paid`,
    (route) =>
      route.fulfill({
        status: 200,
        json: {
          milestone_id: MILESTONE_ID,
          status: "paid",
          paid_at: "2026-05-06T12:00:00Z",
          payment_reference: "REF-TEST-123",
          workflow_advanced_to_phase: 5,
        },
      }),
  );
}


async function stubAdminChurn(page: Page): Promise<void> {
  await page.route(
    "**/api/v1/admin/retainers/churn-risk*",
    (route) => route.fulfill({ status: 200, json: CHURN_RESPONSE }),
  );
  await page.route(
    "**/api/v1/admin/retainers/scan-churn",
    (route) =>
      route.fulfill({
        status: 200,
        json: {
          total_scanned: 1,
          critical_count: 1,
          high_count: 0,
          medium_count: 0,
          low_count: 0,
          alerts_created: 1,
        },
      }),
  );
}


async function stubClientBilling(page: Page): Promise<void> {
  await page.route(
    "**/api/v1/portal/billing/invoices",
    (route) => route.fulfill({ status: 200, json: CLIENT_INVOICES_RESPONSE }),
  );
}


test.describe("MB-18.5 · Admin finance dashboard", () => {
  test.beforeEach(async ({ page, context }) => {
    await stubAdminFinance(page);
    await loginAsMarcos(context);
  });

  test("renderiza KPI cards + ReconciliationManualPanel", async ({ page }) => {
    await page.goto("/admin/finance");

    await expect(page.getByTestId("finance-kpis")).toBeVisible();
    await expect(page.getByTestId("kpi-billed")).toContainText("5400.00 €");
    await expect(page.getByTestId("kpi-paid")).toContainText("1500.00 €");
    await expect(page.getByTestId("kpi-pending")).toContainText("3900.00 €");
    await expect(page.getByTestId("kpi-overdue")).toContainText("1");

    await expect(page.getByTestId("reconciliation-panel")).toBeVisible();
    await expect(
      page.getByTestId(`pending-row-${MILESTONE_ID}`),
    ).toBeVisible();
  });

  test("Mark paid Dialog flow funciona", async ({ page }) => {
    await page.goto("/admin/finance");
    await page.getByTestId(`btn-mark-paid-${MILESTONE_ID}`).click();
    await page
      .getByTestId(`input-reference-${MILESTONE_ID}`)
      .fill("REF-TEST-123");
    await page
      .getByTestId(`input-notes-${MILESTONE_ID}`)
      .fill("Confirmado en extracto banco");
    await page.getByTestId(`btn-confirm-${MILESTONE_ID}`).click();
    await expect(
      page.getByTestId(`feedback-${MILESTONE_ID}`),
    ).toContainText(/siguiente fase desbloqueada/i);
  });
});


test.describe("MB-18.5 · Admin churn risk", () => {
  test.beforeEach(async ({ page, context }) => {
    await stubAdminChurn(page);
    await loginAsMarcos(context);
  });

  test("dashboard widget churn renderiza retainer crítico + acción", async ({
    page,
  }) => {
    // La página standalone /admin/retainers/churn-risk fue migrada (Sesión
    // 3B-2B.3 Phase X.4d): ahora redirige a /admin/dashboard, donde vive el
    // ChurnRiskWidget compacto (top-3 critical+high). La tabla completa
    // ChurnRiskList se ve vía "Ver todos en Finanzas". Aquí verificamos el
    // widget del dashboard (recommended_action + badge nivel).
    await page.goto("/admin/dashboard");

    const widget = page.getByTestId("dashboard-churn-risk-widget");
    await expect(widget).toBeVisible();
    // recommended_action del mock CHURN_RESPONSE
    await expect(widget).toContainText(/Contacto urgente Marcos/i);
    // Badge nivel = "critical" (el widget muestra el risk_level crudo)
    await expect(widget).toContainText(/critical/i);
    // Drill-down a la vista completa en Finanzas
    await expect(
      widget.getByRole("link", { name: /Ver todos en Finanzas/i }),
    ).toBeVisible();
  });
});


test.describe("MB-18.5 · Cliente billing IBAN info-mode", () => {
  test.beforeEach(async ({ page }) => {
    await stubClientBilling(page);
  });

  test("renderiza listado facturas con IBAN strong sin botón", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/billing");

    await expect(page.getByTestId("billing-list")).toBeVisible();
    await expect(
      page.getByTestId(`invoice-card-${INVOICE_ID}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`invoice-total-${INVOICE_ID}`),
    ).toContainText("1210.00 €");

    const bankBlock = page.getByTestId(`invoice-bank-${INVOICE_ID}`);
    await expect(bankBlock).toBeVisible();
    // IBAN visible como strong (cliente selecciona y copia manualmente)
    await expect(bankBlock).toContainText("ES12 1234 5678 9012 3456 7890");
    // Filter strong tag conteniendo IBAN (multiple <strong> en el bloque)
    await expect(
      bankBlock
        .locator("strong")
        .filter({ hasText: "ES12 1234 5678 9012 3456 7890" }),
    ).toBeVisible();
  });

  test("NO botón Copiar IBAN · NO clipboard.writeText", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/billing");

    const bankBlock = page.getByTestId(`invoice-bank-${INVOICE_ID}`);
    await expect(bankBlock).toBeVisible();
    // Directiva Marcos: cero botón clipboard · cliente selecciona manual
    await expect(bankBlock.locator("button")).toHaveCount(0);
    const html = await bankBlock.innerHTML();
    expect(html).not.toContain("clipboard");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("navigator.");
  });
});


test.describe("MB-18.5 · Cliente account CTA billing", () => {
  test("Account page muestra link a billing", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/account");
    await expect(
      page.getByTestId("link-account-billing"),
    ).toBeVisible();
    await expect(
      page.getByTestId("link-account-billing"),
    ).toHaveAttribute("href", "/client-portal/billing");
  });
});
