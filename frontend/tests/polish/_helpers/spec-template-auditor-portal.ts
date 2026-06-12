/**
 * Reusable spec template para auditor portal polish specs.
 *
 * Sesión 3B-2B.6 CLUSTER 2 Phase 5.10 · pattern espejo de runClientPortalProbe
 * adaptado a auditor portal token-bounded flow (NO ClientUser cookie auth ·
 * URL-embedded JWT magic link AUDITOR_PORTAL_ENAC purpose).
 *
 * SCAFFOLD mode (current): spec collect-clean + runtime PASS pending generación
 * de magic link AUDITOR_PORTAL_ENAC vía backend script + URL load. Pattern mirror
 * cliente portal sweep Phase 3 (Sesión 3B-2B.4) scaffold flow.
 *
 * Usage:
 *   import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";
 *   test("12-criteria empirical sweep", async ({ page }, testInfo) => {
 *     await runAuditorPortalProbe(page, testInfo, {
 *       subPath: "summary",
 *       pageName: "auditor-portal-summary",
 *     });
 *   });
 *
 * Runtime requirement:
 * - AUDITOR_PORTAL_TOKEN env var: JWT token con AUDITOR_PORTAL_ENAC purpose
 * - Backend dev running + magic_link row con max_usos=9999
 * - Frontend dev running (port 3000) con backend proxy
 */
import type { Page, TestInfo } from "@playwright/test";
import { expect } from "@playwright/test";

import { runFullPolishSweep } from "./polish-test-fixture";

export interface AuditorPortalProbeConfig {
  /** Sub-path after /auditor-portal/{token}/ (e.g. "summary", "dda"). */
  subPath: string;
  /** Stable label · used for screenshots + artifacts. */
  pageName: string;
}

/**
 * Drives an auditor portal page through standard 12-criteria sweep.
 *
 * R23 NO admin nav leak (auditor sees ONLY auditor portal chrome · no breadcrumb
 * project switcher · no admin sidebar). isProjectScoped=false · auditor scope
 * bounded por token (single project per magic link · TTL 336h).
 *
 * WCAG cross-views enforce via pattern library Sesión 3B-2B:
 * 1. Card solid white bg (Phase A.1 contrast fix)
 * 2. Badge -700 shade variants (AA contrast preserved)
 * 3. Alert role="alert" via primitive
 * 4. Sidebar aria-label + aria-current per link
 * 5. Input + Select with aria-label explicit
 */
export async function runAuditorPortalProbe(
  page: Page,
  testInfo: TestInfo,
  config: AuditorPortalProbeConfig,
): Promise<void> {
  const token = process.env.AUDITOR_PORTAL_TOKEN;
  if (!token) {
    testInfo.skip(true, "AUDITOR_PORTAL_TOKEN env var required");
    return;
  }
  const otp = process.env.AUDITOR_PORTAL_OTP;
  const targetUrl = `/auditor-portal/${token}/${config.subPath}`;

  await page.goto(targetUrl);
  await page.waitForLoadState("domcontentloaded");

  // OTP step-up gate (feat/fulkro-100): si aparece el gate y tenemos el código,
  // lo pasamos para llegar a la vista real. Robusto: si no hay gate, continúa.
  const otpInput = page.getByTestId("auditor-otp-input");
  if (otp && (await otpInput.isVisible().catch(() => false))) {
    await otpInput.fill(otp);
    await page.getByTestId("auditor-otp-submit").click();
    await otpInput.waitFor({ state: "hidden", timeout: 8000 }).catch(() => {});
  }

  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(500);

  const result = await runFullPolishSweep(page, {
    pageUrl: targetUrl,
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
    result.criteria.wcagAA,
    `WCAG AA · ${result.evidence.axeViolations.length} violations: ${result.evidence.axeViolations
      .map((v) => `[${v.impact}] ${v.id}`)
      .join(", ")}`,
  ).toBe(true);
  expect(result.criteria.keyboardNav, "keyboard navigation").toBe(true);
  expect(result.passCount, `passCount ${result.passCount}/12`).toBeGreaterThanOrEqual(9);
}
