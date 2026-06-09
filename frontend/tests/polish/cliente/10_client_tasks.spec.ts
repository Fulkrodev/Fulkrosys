/**
 * CLIENTE 10 · /client-portal/tasks · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.4 Phase 3 · workflow actions cliente-facing.
 */
import { test } from "../_helpers/polish-cliente-fixture";
import { runClientPortalProbe } from "../_helpers/spec-template-cliente";

test.describe("CLIENTE · /client-portal/tasks", () => {
  test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
    await runClientPortalProbe(clientPage, testInfo, {
      subPath: "tasks",
      pageName: "client-portal-tasks",
    });
  });
});
