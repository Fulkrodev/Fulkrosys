/**
 * CLIENTE 08 · /client-portal/billing · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · invoices + retainer cliente-facing.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/billing", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "billing",
      pageName: "client-portal-billing",
    });
  });
});
