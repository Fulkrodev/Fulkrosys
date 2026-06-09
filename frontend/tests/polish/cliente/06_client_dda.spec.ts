/**
 * CLIENTE 06 · /client-portal/dda · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · Declaración de Aplicabilidad cliente firma.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/dda", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "dda",
      pageName: "client-portal-dda",
    });
  });
});
