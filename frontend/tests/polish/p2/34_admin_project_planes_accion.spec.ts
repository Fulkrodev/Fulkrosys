/**
 * P2 34 · /admin/projects/[id]/planes-accion · cross-motor action plans.
 *
 * Sesión 3B-2B.3 Cluster C.6.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/planes-accion", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "planes-accion",
      pageName: "admin-project-planes-accion",
    });
  });
});
