/**
 * SAN-E v3.MB-7.bis.2 · drift compute endpoints smoke.
 *
 * Backend endpoint smoke check for retainer drift catalog (existing) +
 * verify dimensions exposed match the 10 cementadas DRIFT_DIMENSIONS.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


const EXPECTED_DIMS = [
  "infraestructura", "identidad", "proveedores", "normativa", "overlay",
  "cpstic", "roles", "continuidad", "evidencias", "contratos",
];


test.describe("SAN-E v3.MB-7.bis.2 · drift catalog + ccn_stic alerts", () => {
  test("/retainer/drift-catalog returns 10 dimensiones cementadas", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const res = await context.request.get("/api/v1/retainer/drift-catalog");
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data.dimensions).toEqual(expect.arrayContaining(EXPECTED_DIMS));
    expect(data.severities).toEqual(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
  });
});
