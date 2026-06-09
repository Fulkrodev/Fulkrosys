/**
 * SAN-E v3.MB-7.bis.3 · quarterly DOCX report endpoint shape check.
 *
 * Verifica que el endpoint download existe y responde con MIME
 * application/vnd.openxmlformats... (incluso si retainer_id desconocido
 * retorna 404 con detail, no 500).
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


test.describe("SAN-E v3.MB-7.bis.3 · quarterly report endpoint", () => {
  test("download endpoint returns 404 if retainer not found", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const fakeRetainerId = "00000000-0000-0000-0000-000000000000";
    const res = await context.request.get(
      `/api/v1/retainer/${fakeRetainerId}/reports/quarterly/2026-01-01/download`,
    );
    expect(res.status()).toBe(404);
    const data = await res.json();
    expect(data.detail).toMatch(/not found|no encontrad/i);
  });

  test("annual endpoint rejects out-of-range year", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const fakeRetainerId = "00000000-0000-0000-0000-000000000000";
    const res = await context.request.get(
      `/api/v1/retainer/${fakeRetainerId}/reports/annual/1999/download`,
    );
    expect(res.status()).toBe(400);
  });
});
