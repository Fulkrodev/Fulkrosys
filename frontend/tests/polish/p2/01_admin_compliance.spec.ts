/**
 * P2 01 · /admin/compliance · FULKRO compliance landing.
 *
 * R23 multi-cliente exception · top-level admin dashboard for self-compliance.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/compliance", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/compliance",
      pageName: "admin-compliance",
      contentText: "Compliance",
    });
  });
});
