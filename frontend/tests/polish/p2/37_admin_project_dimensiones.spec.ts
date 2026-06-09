/**
 * P2 37 · /admin/projects/[id]/dimensiones · M01 dimensiones.
 *
 * Sesión 3B-2B.3 Cluster C.6.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/dimensiones", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "dimensiones",
      pageName: "admin-project-dimensiones",
    });
  });
});
