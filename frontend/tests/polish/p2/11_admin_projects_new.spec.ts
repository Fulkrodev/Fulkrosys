/**
 * P2 11 · /admin/projects/new · create project form.
 *
 * Sesión 3B-2B.3 Cluster C.1.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/new", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/projects/new",
      pageName: "admin-projects-new",
    });
  });
});
