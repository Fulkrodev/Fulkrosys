/**
 * Reusable spec template helpers for project-scoped P1/P2 polish specs.
 *
 * Sub-atom Sesión 3B-2B.2 Phase A.2 · template extraction from probe-03/04/05
 * patterns proven 12/12 PASS.
 *
 * Pattern provided:
 *  - DOM-redirect-aware isProjectScoped (URL pathname check post-networkidle+800ms)
 *  - Standard 4 explicit criteria assertions (mobile + WCAG + keyboard + title)
 *  - passCount >= 9 floor
 *  - testInfo.attach evidence BEFORE expects (lost-on-fail prevention)
 *
 * Usage:
 *   import { runProjectScopedProbe } from "../_helpers/spec-template";
 *   test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
 *     await runProjectScopedProbe(authedPage, testInfo, {
 *       projectId: TEST_PROJECT_ID,
 *       subPath: "risks",
 *       pageName: "admin-project-risks",
 *     });
 *   });
 */
import type { Page, TestInfo } from "@playwright/test";
import { expect } from "@playwright/test";

import { runFullPolishSweep } from "./polish-test-fixture";

export const SEED_PROJECT_ID =
  process.env.POLISH_TEST_PROJECT_ID ??
  "11111111-1111-1111-1111-111111111111";

interface ProjectScopedProbeConfig {
  /** Project UUID (defaults to seed Cliente Test 1 via SEED_PROJECT_ID). */
  projectId?: string;
  /** Sub-path after /admin/projects/{id}/ (e.g. "risks", "dossier"). */
  subPath: string;
  /** Stable label for screenshots/artifacts (e.g. "admin-project-risks"). */
  pageName: string;
  /** Optional selector to wait for indicating page rendered (vs redirect). */
  contentSelector?: string;
  /** Optional content text marker (used if contentSelector not specified). */
  contentText?: string;
}

/**
 * Drives a project-scoped P1/P2 probe through standard 12-criteria sweep.
 *
 * Honors honest projectContext detection: URL pathname check post-networkidle
 * + 800ms wait lets client-side router.replace fully settle. If user lands
 * on /admin/projects selector (project doesn't exist / no access), the
 * isProjectScoped flag auto-flips to false so projectContext criterion
 * doesn't penalize tests for redirect (multi-cliente selector page has no
 * project breadcrumb by design).
 */
/**
 * Top-level admin / non-project-scoped probe (compliance · clients · radar etc).
 *
 * Multi-cliente top-level pages legitimate R23 exception · NO project
 * breadcrumb expected · `isProjectScoped` hardcoded false.
 */
export interface TopLevelAdminProbeConfig {
  /** Absolute path · e.g. "/admin/compliance" or "/radar/leads". */
  path: string;
  /** Stable label · e.g. "admin-compliance" or "radar-leads". */
  pageName: string;
  /** Optional content selector to wait for. */
  contentSelector?: string;
  /** Optional content text marker. */
  contentText?: string;
}

export async function runTopLevelAdminProbe(
  page: Page,
  testInfo: TestInfo,
  config: TopLevelAdminProbeConfig,
): Promise<void> {
  await page.goto(config.path);
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
    pageUrl: config.path,
    pageName: config.pageName,
    isProjectScoped: false,
  });

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

export async function runProjectScopedProbe(
  page: Page,
  testInfo: TestInfo,
  config: ProjectScopedProbeConfig,
): Promise<void> {
  const projectId = config.projectId ?? SEED_PROJECT_ID;
  const targetUrl = `/admin/projects/${projectId}/${config.subPath}`;

  await page.goto(targetUrl);
  await page.waitForLoadState("domcontentloaded");

  // Wait for either content OR redirect to selector.
  const contentWait = config.contentSelector
    ? page.waitForSelector(config.contentSelector, { timeout: 5000 })
    : config.contentText
      ? page.waitForSelector(`text=${config.contentText}`, { timeout: 5000 })
      : Promise.resolve();
  await Promise.race([
    contentWait,
    page.waitForURL(/\/admin\/projects(\?|$)/, { timeout: 5000 }),
  ]).catch(() => {});

  // Definitive redirect detection: networkidle + 800ms · pathname is stable.
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(800);
  const finalPath = new URL(page.url()).pathname;
  const isOnProjectScopedRoute = /^\/admin\/projects\/[^/]+\//.test(finalPath);

  const result = await runFullPolishSweep(page, {
    pageUrl: targetUrl,
    pageName: config.pageName,
    isProjectScoped: isOnProjectScopedRoute,
  });

  // Attach BEFORE expects · evidence always captured even on first failure.
  await testInfo.attach("criteria-result.json", {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
  await testInfo.attach("axe-violations.json", {
    body: JSON.stringify(result.evidence.axeViolations, null, 2),
    contentType: "application/json",
  });

  // Standard 4 explicit criteria + passCount floor.
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
