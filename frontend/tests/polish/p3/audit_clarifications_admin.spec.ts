/**
 * ADMIN · /admin/projects/[id]/audit/clarifications · 12-criteria empirical sweep.
 *
 * Phase C2.3 SSE realtime inbox · admin reviews + responds clarifications.
 *
 * 2026-06-13 · alineado con los 74 specs hermanos (OPS-026 DRY + OPS-049 honesto):
 * usa runProjectScopedProbe (SEED_PROJECT_ID + redirect-aware) en vez del antiguo
 * gate manual por FULKRO_TEST_PROJECT_ID que lo dejaba SKIPPED en CI.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("ADMIN · /admin/projects/[id]/audit/clarifications", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "audit/clarifications",
      pageName: "admin-audit-clarifications",
    });
  });
});
