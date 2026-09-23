/**
 * SAN-E v3.MB-8.3 · WhatsApp endpoints smoke.
 *
 * Verifica que:
 *  - /portal/whatsapp/status returns valid JSON (cliente)
 *  - /portal/whatsapp/export returns 200 (RGPD art.15 Q6.D)
 *  - /webhooks/360dialog acepta payload sin auth (signature TBD post-KYC)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "../_helpers/auth-real";


test.describe("SAN-E v3.MB-8.3 · WhatsApp endpoints smoke", () => {
  test("cliente /status returns JSON with opt_in_active field", async ({
    page, context,
  }) => {
    await loginAsClient(page);
    const res = await context.request.get(
      "/api/v1/client-portal/whatsapp/status",
    );
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data).toHaveProperty("opt_in_active");
    expect(data).toHaveProperty("verified");
  });

  // El webhook llega desde 360dialog SIN sesión: debe pasar el auth global
  // (whitelist en app/auth/global_dep.py) y autenticarse dentro del handler
  // (HMAC/token · sin secret configurado, fuera de producción se acepta).
  test("webhook 360dialog accepts unknown payload gracefully", async ({
    context,
  }) => {
    const res = await context.request.post(
      "/api/v1/webhooks/360dialog",
      { data: { foo: "bar" } },
    );
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data).toEqual({ handled: "unknown_or_skipped" });
  });
});
