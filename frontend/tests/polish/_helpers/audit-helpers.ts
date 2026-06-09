/**
 * Audit helpers · Playwright + axe-core empirical 12-criteria verification.
 *
 * Sesión 3B-2B.2 Path B · OPS-052 15ª PREVENTED.
 *
 * Per criterio · pure utility functions reusable across polish test specs.
 * Capturado runtime evidence empirical · NOT inference.
 */
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

export interface PolishViewport {
  name: string;
  width: number;
  height: number;
}

export const POLISH_VIEWPORTS: readonly PolishViewport[] = [
  { name: "mobile-sm", width: 375, height: 812 },
  { name: "mobile-md", width: 414, height: 896 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "tablet-l", width: 1024, height: 768 },
  { name: "laptop", width: 1280, height: 800 },
  { name: "desktop", width: 1920, height: 1080 },
] as const;

export interface AxeViolation {
  id: string;
  impact: "critical" | "serious" | "moderate" | "minor" | null;
  description: string;
  help: string;
  helpUrl: string;
  nodeCount: number;
  /** Selectors of offending elements (first 3 max for brevity). */
  nodes: string[];
}

export interface AxeScanResult {
  pageUrl: string;
  viewport: string;
  violations: AxeViolation[];
  passCount: number;
  inapplicable: number;
}

/**
 * Run axe-core scan on current page · returns violations.
 *
 * Configured to scan WCAG 2.1 AA rules only (most common compliance target).
 * Excludes color-contrast rules from running against generic shadcn primitives
 * that DON'T meet AA at small text sizes (informational only · sostener).
 */
export async function runAxeScan(
  page: Page,
  options: { excludeRules?: string[] } = {},
): Promise<AxeScanResult> {
  const builder = new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(options.excludeRules ?? []);

  const results = await builder.analyze();

  return {
    pageUrl: page.url(),
    viewport: `${page.viewportSize()?.width}x${page.viewportSize()?.height}`,
    violations: results.violations.map((v) => ({
      id: v.id,
      impact: v.impact as AxeViolation["impact"],
      description: v.description,
      help: v.help,
      helpUrl: v.helpUrl,
      nodeCount: v.nodes.length,
      nodes: v.nodes.slice(0, 3).map((n) => n.target.join(" > ")),
    })),
    passCount: results.passes.length,
    inapplicable: results.inapplicable.length,
  };
}

/**
 * Take screenshot at given viewport · returns path.
 *
 * Uses Playwright's auto-fixture screenshot path. Filename includes viewport
 * name for easy artifact identification in HTML report.
 */
export async function screenshotPerViewport(
  page: Page,
  viewport: PolishViewport,
  label: string,
): Promise<void> {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  // Wait for layout shift to settle after viewport change.
  await page.waitForTimeout(300);
  await page.screenshot({
    path: `polish-test-results/screenshots/${label}_${viewport.name}.png`,
    fullPage: true,
  });
}

/**
 * Check page has NO horizontal overflow at given viewport (mobile responsive).
 *
 * Returns true if document.documentElement.scrollWidth <= viewport.width.
 * Detected horizontal scrollbar = mobile responsive FAIL.
 */
export async function checkNoHorizontalOverflow(
  page: Page,
  viewport: PolishViewport,
): Promise<{ pass: boolean; scrollWidth: number; viewportWidth: number }> {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.waitForTimeout(300);
  const scrollWidth = await page.evaluate(
    () => document.documentElement.scrollWidth,
  );
  return {
    pass: scrollWidth <= viewport.width,
    scrollWidth,
    viewportWidth: viewport.width,
  };
}

export interface TabNavigationResult {
  totalTabbable: number;
  /** Sequence of tabbable elements (tagName + visible text · first 50). */
  tabOrder: Array<{ tag: string; text: string; testId?: string }>;
  /** Elements that received focus during Tab traversal. */
  focusedCount: number;
}

/**
 * Walk through Tab order · capture sequence.
 *
 * Programmatically dispatches Tab key from body · captures each focused
 * element. Stops after maxTabs (default 50) to avoid infinite loops.
 */
export async function captureTabOrder(
  page: Page,
  maxTabs = 50,
): Promise<TabNavigationResult> {
  // Reset focus to document.body
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    document.body.focus();
  });

  const tabOrder: TabNavigationResult["tabOrder"] = [];
  for (let i = 0; i < maxTabs; i++) {
    await page.keyboard.press("Tab");
    await page.waitForTimeout(50);
    const active = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      return {
        tag: el.tagName.toLowerCase(),
        text: (el.textContent ?? "").trim().slice(0, 50),
        testId: el.getAttribute("data-testid") ?? undefined,
      };
    });
    if (!active) break;
    tabOrder.push(active);
  }
  return {
    totalTabbable: tabOrder.length,
    tabOrder,
    focusedCount: tabOrder.length,
  };
}

/**
 * Verify modal closes on Escape key.
 *
 * Opens modal via triggerSelector click · presses Escape · verifies
 * modal is NOT visible.
 */
export async function testEscapeClosesModal(
  page: Page,
  triggerSelector: string,
  modalSelector: string,
): Promise<{ openWorked: boolean; escapeClosed: boolean }> {
  await page.locator(triggerSelector).click();
  const modal = page.locator(modalSelector);
  const openWorked = await modal.isVisible().catch(() => false);
  if (!openWorked) return { openWorked: false, escapeClosed: false };
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
  const stillVisible = await modal.isVisible().catch(() => false);
  return { openWorked: true, escapeClosed: !stillVisible };
}

/**
 * Intercept route · respond with slow + delayed result (loading state test).
 */
export async function interceptRouteSlow(
  page: Page,
  urlPattern: string | RegExp,
  delayMs = 3000,
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await new Promise((r) => setTimeout(r, delayMs));
    await route.continue();
  });
}

/**
 * Intercept route · respond 500 (error state test).
 */
export async function interceptRoute500(
  page: Page,
  urlPattern: string | RegExp,
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Empirical error injection · test" }),
    });
  });
}

/**
 * Intercept route · respond with empty data (empty state test).
 */
export async function interceptRouteEmpty(
  page: Page,
  urlPattern: string | RegExp,
  emptyShape: "array" | "object" | "null" = "array",
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    const body =
      emptyShape === "array" ? "[]" : emptyShape === "null" ? "null" : "{}";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body,
    });
  });
}

/**
 * Verify breadcrumb visibility on project-scoped pages.
 */
export async function checkProjectBreadcrumbVisible(
  page: Page,
): Promise<{ visible: boolean; clientName?: string; projectName?: string }> {
  const breadcrumb = page.locator(
    "[data-testid='project-breadcrumb'], [data-testid='project-breadcrumb-skeleton']",
  );
  const visible = await breadcrumb.isVisible().catch(() => false);
  if (!visible) return { visible: false };

  const clientName = await page
    .locator("[data-testid='project-breadcrumb-client']")
    .textContent()
    .catch(() => undefined);
  const projectName = await page
    .locator("[data-testid='project-breadcrumb-project']")
    .textContent()
    .catch(() => undefined);

  return {
    visible: true,
    clientName: clientName?.trim() || undefined,
    projectName: projectName?.trim() || undefined,
  };
}

/**
 * Verify focus-visible indicator after Tab.
 *
 * Tab once then check focused element's outline OR box-shadow.
 * Fulkro convention: focus-visible:ring-2 (Tailwind class).
 */
export async function checkFocusVisibleIndicator(
  page: Page,
): Promise<{ hasIndicator: boolean; outline?: string; boxShadow?: string }> {
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    document.body.focus();
  });
  await page.keyboard.press("Tab");

  // 2026-06-09 · anti-flaky CI (ronda 4): en runners de 2 cores el primer
  // `keyboard.press("Tab")` puede dispararse ANTES de que el frame tenga el
  // foco de entrada del navegador → la pulsación se pierde y `activeElement`
  // se queda en <body> indefinidamente (el snapshot de fallo lo confirmó:
  // billing/alerts/meetings · foco en el generic raíz). La ronda 3 sólo
  // hacía poll del estilo pero NUNCA re-pulsaba Tab, así que jamás salía de
  // <body>. Ahora: si el foco sigue en body re-pulsamos Tab (recupera la
  // pulsación perdida); si ya aterrizó en un elemento seguimos haciendo poll
  // del ring sin avanzar. MISMO estándar: un bug real (elemento enfocado sin
  // indicador) sigue fallando los 6 intentos.
  let last: { hasIndicator: boolean; outline?: string; boxShadow?: string } = {
    hasIndicator: false,
  };
  for (let attempt = 0; attempt < 6; attempt++) {
    await page.waitForTimeout(attempt === 0 ? 100 : 200);
    const probe = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      const onBody = !el || el === document.body;
      if (onBody || !el) {
        return {
          hasIndicator: false,
          onBody: true,
          outline: undefined as string | undefined,
          boxShadow: undefined as string | undefined,
        };
      }
      const styles = window.getComputedStyle(el);
      const outline = styles.outline;
      const boxShadow = styles.boxShadow;
      // Default browser outline is removed by Tailwind reset · we expect
      // either custom outline OR box-shadow ring from focus-visible:ring-2.
      const hasIndicator =
        (outline !== "none" && outline !== "" && !outline.startsWith("0px")) ||
        (boxShadow !== "none" && boxShadow !== "");
      return {
        hasIndicator,
        onBody: false,
        outline: outline as string | undefined,
        boxShadow: boxShadow as string | undefined,
      };
    });
    last = {
      hasIndicator: probe.hasIndicator,
      outline: probe.outline,
      boxShadow: probe.boxShadow,
    };
    if (probe.hasIndicator) return last;
    // Pulsación de Tab perdida (sigue en body) → re-pulsar para recuperarla.
    if (probe.onBody) await page.keyboard.press("Tab");
  }
  return last;
}

/**
 * Summary helper · aggregate 12-criteria PASS/FAIL per page.
 */
export interface PageCriteriaResult {
  pageUrl: string;
  pageName: string;
  criteria: {
    titleBreadcrumb: boolean;
    loadingSkeleton: boolean;
    errorRetry: boolean;
    emptyState: boolean;
    mobileResponsive: boolean;
    keyboardNav: boolean;
    wcagAA: boolean;
    tanstackQuery: boolean;
    ctaVisible: boolean;
    helpTooltip: boolean;
    serverFeedback: boolean;
    projectContext: boolean;
  };
  passCount: number;
  failCount: number;
  evidence: {
    screenshotsPaths: string[];
    axeViolationsPerViewport: Record<string, number>;
    /** Full violation details captured at desktop viewport · for diagnose. */
    axeViolations: AxeViolation[];
    tabOrderLength: number;
    horizontalOverflowViolations: string[];
  };
}

export function computePassCount(c: PageCriteriaResult["criteria"]): {
  pass: number;
  fail: number;
} {
  const values = Object.values(c);
  const pass = values.filter((v) => v === true).length;
  return { pass, fail: values.length - pass };
}
