/**
 * E2E AlertBell top nav admin (MB-13.4 · ADR-035).
 *
 * Cobertura:
 *   1. AlertBell visible en chrome admin (Header.tsx)
 *   2. Badge count visible si hay alertas activas
 *   3. Popover abre on click · muestra alertas con CTA
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const ALERTS_FIXTURE = [
  {
    id: "11111111-aaaa-bbbb-cccc-111111111111",
    project_id: "22222222-aaaa-bbbb-cccc-222222222222",
    severity: "critical",
    category: "bienal_art31",
    title: "Auditoría bienal próxima (15 días)",
    description: "Art. 31 RD 311/2022 · auditoría obligatoria",
    action_url: "/admin/projects/22222222-aaaa-bbbb-cccc-222222222222/conformity",
    triggered_by: "check_biannual_audits_due",
    triggered_at: new Date().toISOString(),
    acknowledged_at: null,
    metadata_jsonb: { days_remaining: 15 },
  },
  {
    id: "22222222-aaaa-bbbb-cccc-222222222222",
    project_id: "22222222-aaaa-bbbb-cccc-222222222222",
    severity: "warning",
    category: "evidence_stale",
    title: "Evidencia próxima a expirar",
    description: "PSI vence en 30 días",
    action_url: "/admin/projects/test/evidence",
    triggered_by: "evidence_freshness_check",
    triggered_at: new Date().toISOString(),
    acknowledged_at: null,
    metadata_jsonb: {},
  },
];

test.describe("MB-13.4 · AlertBell top nav admin", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.route("**/api/v1/alerts/active", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(ALERTS_FIXTURE),
      });
    });
  });

  test("bell visible en chrome admin con badge count", async ({ page }) => {
    await page.goto("/admin/dashboard");

    const bell = page.getByTestId("alert-bell");
    await expect(bell).toBeVisible({ timeout: 10_000 });

    // Badge count >= 2 (fixture tiene 2 alerts)
    await expect(bell).toContainText("2");
  });

  test("popover abre con alertas y CTAs", async ({ page }) => {
    await page.goto("/admin/dashboard");

    const bell = page.getByTestId("alert-bell");
    await expect(bell).toBeVisible({ timeout: 10_000 });
    await bell.click();

    await expect(page.getByText("Alertas activas")).toBeVisible();
    await expect(
      page.getByText(/Auditoría bienal próxima/),
    ).toBeVisible();
    await expect(
      page.getByText(/Evidencia próxima a expirar/),
    ).toBeVisible();
  });

  test("sin alertas muestra mensaje vacio", async ({ page }) => {
    // Override mock para alerts vacías en este test
    await page.route("**/api/v1/alerts/active", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/admin/dashboard");

    const bell = page.getByTestId("alert-bell");
    await expect(bell).toBeVisible({ timeout: 10_000 });
    await bell.click();

    await expect(page.getByText(/Sin alertas activas/)).toBeVisible();
  });
});
