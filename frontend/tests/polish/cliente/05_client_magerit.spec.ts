/**
 * CLIENTE 05 · /client-portal/magerit · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · MAGERIT risk analysis cliente review.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/magerit", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "magerit",
      pageName: "client-portal-magerit",
    });
  });
});
