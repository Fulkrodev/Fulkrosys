/**
 * ADMIN · /admin/projects/[id]/audit/clarifications · 12-criteria empirical sweep.
 *
 * Phase C2.3 SSE realtime inbox · admin reviews + responds clarifications.
 * SCAFFOLD mode · requires FULKRO_TEST_PROJECT_ID env var at runtime.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runFullPolishSweep } from "../_helpers/polish-test-fixture";
import { expect } from "@playwright/test";

const PROJECT_ID = process.env.FULKRO_TEST_PROJECT_ID;

test.describe("ADMIN · /admin/projects/[id]/audit/clarifications", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    if (!PROJECT_ID) {
      testInfo.skip(true, "FULKRO_TEST_PROJECT_ID env required");
      return;
    }
    const url = `/admin/projects/${PROJECT_ID}/audit/clarifications`;
    await authedPage.goto(url);
    await authedPage.waitForLoadState("domcontentloaded");
    await authedPage.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});

    const result = await runFullPolishSweep(authedPage, {
      pageUrl: url,
      pageName: "admin-audit-clarifications",
      isProjectScoped: true,
    });

    await testInfo.attach("axe-violations.json", {
      body: JSON.stringify(result.evidence.axeViolations, null, 2),
      contentType: "application/json",
    });

    expect(result.criteria.wcagAA, "WCAG AA").toBe(true);
    expect(result.criteria.keyboardNav, "keyboard navigation").toBe(true);
  });
});
