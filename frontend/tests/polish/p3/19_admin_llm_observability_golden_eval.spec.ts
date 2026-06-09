/**
 * P3 19 · /admin/llm-observability/golden-eval · B.3.D evaluator.
 *
 * Sesión 3B-2B.3 Cluster D.4.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/llm-observability/golden-eval", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/llm-observability/golden-eval",
      pageName: "admin-llm-observability-golden-eval",
    });
  });
});
