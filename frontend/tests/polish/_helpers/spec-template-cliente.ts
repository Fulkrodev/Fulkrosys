/**
 * Reusable spec template para cliente portal polish specs.
 *
 * Sesión 3B-2B.4 Phase 3 · pattern espejo de runProjectScopedProbe pero
 * adaptado a cliente portal R29 isolation (NO project-scoped concept ·
 * cliente ve SU proyecto natively · single LIMIT 1 backend).
 *
 * Usage:
 *   import { runClientPortalProbe } from "../_helpers/spec-template-cliente";
 *   test("12-criteria empirical sweep", async ({ clientPage }, testInfo) => {
 *     await runClientPortalProbe(clientPage, testInfo, {
 *       subPath: "dashboard",
 *       pageName: "client-portal-dashboard",
 *     });
 *   });
 */
import type { Page, TestInfo } from "@playwright/test";
import { expect } from "@playwright/test";

import { runFullPolishSweep } from "./polish-test-fixture";

export interface ClientPortalProbeConfig {
  /** Sub-path after /client-portal/ (e.g. "dashboard", "conformidad"). */
  subPath: string;
  /** Stable label · used for screenshots + artifacts. */
  pageName: string;
  /** Optional selector to wait for indicating page rendered. */
  contentSelector?: string;
  /** Optional content text marker (used if contentSelector not specified). */
  contentText?: string;
}

/**
 * Drives a cliente portal page through standard 12-criteria sweep.
 *
 * R29 cliente friendly tone enforce automático vía axe (color contrast +
 * heading order + ARIA labels) + esta probe (mobile + keyboard + WCAG floor).
 * isProjectScoped=false por design (cliente NO ve project breadcrumb · LIMIT 1
 * single-project per cliente backend assumption R27).
 */
export async function runClientPortalProbe(
  page: Page,
  testInfo: TestInfo,
  config: ClientPortalProbeConfig,
): Promise<void> {
  const targetUrl = `/client-portal/${config.subPath}`;

  await page.goto(targetUrl);
  await page.waitForLoadState("domcontentloaded");

  const contentWait = config.contentSelector
    ? page.waitForSelector(config.contentSelector, { timeout: 5000 })
    : config.contentText
      ? page.waitForSelector(`text=${config.contentText}`, { timeout: 5000 })
      : Promise.resolve();
  await contentWait.catch(() => {});

  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(500);

  const result = await runFullPolishSweep(page, {
    pageUrl: targetUrl,
    pageName: config.pageName,
    isProjectScoped: false,
  });

  // Attach evidence BEFORE expects · OPS-052 16ª lesson honored.
  await testInfo.attach("criteria-result.json", {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
  await testInfo.attach("axe-violations.json", {
    body: JSON.stringify(result.evidence.axeViolations, null, 2),
    contentType: "application/json",
  });

  expect(
    result.criteria.mobileResponsive,
    `mobile responsive · violations: ${JSON.stringify(result.evidence.horizontalOverflowViolations)}`,
  ).toBe(true);
  expect(
    result.criteria.wcagAA,
    `WCAG AA · ${result.evidence.axeViolations.length} violations: ${result.evidence.axeViolations
      .map((v) => `[${v.impact}] ${v.id}`)
      .join(", ")}`,
  ).toBe(true);
  expect(result.criteria.keyboardNav, "keyboard navigation").toBe(true);
  expect(result.passCount, `passCount ${result.passCount}/12`).toBeGreaterThanOrEqual(9);
}
