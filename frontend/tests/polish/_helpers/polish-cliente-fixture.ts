/**
 * Polish test fixture for cliente portal · Sesión 3B-2B.4 Phase 3.
 *
 * Sister of polish-test-fixture.ts (admin Marcos auth) · uses loginAsClient
 * para autenticar usuario cliente piloto sintético (test-client-e2e@example.com).
 *
 * Reuses runFullPolishSweep + screenshot 6-viewport sweep · same 12-criteria
 * acceptance pattern as admin polish suite. Cliente portal routes start con
 * /client-portal/* y sostienen R29 single-project per cliente (LIMIT 1 backend
 * lookups · NO project switcher visible cliente).
 */
import { test as base, type Page } from "@playwright/test";

import { loginAsClient } from "../../e2e/_helpers/auth-real";

interface ClientAuthedFixtures {
  clientPage: Page;
}

export const test = base.extend<ClientAuthedFixtures>({
  clientPage: async ({ browser }, use) => {
    const context = await browser.newContext();

    // Suppress cliente onboarding tutorial overlay · pattern reused desde
    // loginAsClient (dismissTutorial true default) · localStorage flag set
    // antes navegar evita modal blocking axe scan.
    await context.addInitScript(() => {
      try {
        window.localStorage.setItem("fulkro_tutorial_completed", "1");
        window.localStorage.setItem("fulkro_client_onboarding_dismissed", "1");
      } catch {
        // storage unavailable · ignore
      }
    });

    const page = await context.newPage();
    await loginAsClient(page, { dismissTutorial: true });
    await use(page);
    await context.close();
  },
});

export { expect } from "@playwright/test";
export { runFullPolishSweep } from "./polish-test-fixture";
