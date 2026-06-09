/**
 * CLIENTE 01 · /client-portal/dashboard · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · cliente portal core polish batch 1/10.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/dashboard", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "dashboard",
      pageName: "client-portal-dashboard",
    });
  });
});
