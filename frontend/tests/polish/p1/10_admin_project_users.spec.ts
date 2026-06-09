/**
 * P1 10 · /admin/projects/[id]/users · cockpit user management.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/users", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "users",
      pageName: "admin-project-users",
      contentText: "Usuario",
    });
  });
});
