/**
 * SAN-E v3.MB-7.bis.4 · /admin/timesheet UI smoke + summary endpoint.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


test.describe("SAN-E v3.MB-7.bis.4 · timesheet UI + summary", () => {
  test("/admin/timesheet renders header + monthly tile", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/timesheet");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: /Mi timesheet/i }),
    ).toBeVisible({ timeout: 10_000 });
    // Monthly tile + Top 3 card + entries table
    await expect(page.getByText(/Total este mes/i)).toBeVisible();
    await expect(page.getByText(/Top 3 clientes/i)).toBeVisible();
  });

  test("manual entry form opens when Añadir manual is clicked", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/timesheet");
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: /Añadir manual/i }).click();
    await expect(page.getByTestId("timesheet-client-id")).toBeVisible();
  });

  test("/admin/timesheet/summary endpoint returns valid JSON", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const res = await context.request.get("/api/v1/admin/timesheet/summary");
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data).toHaveProperty("monthly_total_minutes");
    expect(data).toHaveProperty("monthly_total_hours");
    expect(data).toHaveProperty("top_clients");
    expect(Array.isArray(data.top_clients)).toBe(true);
  });
});
