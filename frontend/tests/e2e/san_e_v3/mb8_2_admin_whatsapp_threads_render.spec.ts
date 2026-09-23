/**
 * SAN-E v3.MB-8.2 · admin WhatsApp threads list renders.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


test.describe("SAN-E v3.MB-8.2 · admin /admin/whatsapp", () => {
  test("threads list pane visible", async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/whatsapp");
    // `load` y no `networkidle`: el portal mantiene abierta la conexion SSE de
    // eventos, y con ella la red nunca queda inactiva (la espera no acaba nunca).
    await page.waitForLoadState("load");

    await expect(page.getByTestId("admin-wa-threads-list")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("/api/v1/admin/whatsapp/threads endpoint returns 200 JSON", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const res = await context.request.get("/api/v1/admin/whatsapp/threads");
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data).toHaveProperty("threads");
    expect(Array.isArray(data.threads)).toBe(true);
  });
});
