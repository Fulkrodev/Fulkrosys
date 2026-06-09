/**
 * CLIENTE 09 · /client-portal/account · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · profile + notifications preferences cliente.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/account", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "account",
      pageName: "client-portal-account",
    });
  });
});
