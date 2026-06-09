/**
 * CLIENTE 02 · /client-portal/conformidad · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · tier-aware firma ENS declaration cliente-facing.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/conformidad", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "conformidad",
      pageName: "client-portal-conformidad",
    });
  });
});
