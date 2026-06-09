/**
 * CLIENTE 03 · /client-portal/evidencias · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · evidence upload + classifier AI cliente-facing.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/evidencias", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "evidencias",
      pageName: "client-portal-evidencias",
    });
  });
});
