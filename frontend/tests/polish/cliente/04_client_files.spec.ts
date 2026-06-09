/**
 * CLIENTE 04 · /client-portal/files · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · document vault cliente-facing.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/files", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "files",
      pageName: "client-portal-files",
    });
  });
});
