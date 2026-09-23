/**
 * E2E · Sesión 3B-2B.8 CLUSTER 8 Phase 8A · cross-cluster integration scaffold.
 *
 * 32-step cliente portal piloto MEDIA dogfooding flow cross 7 CLUSTERS:
 *   CLUSTER 1 (steps 1-6)  · login MFA + admin sync events + cloud + copilot + plan
 *   CLUSTER 2 (steps 7-11) · notifications + coach + reports + Q&A + DRP/BIA
 *   CLUSTER 3 (steps 12-14) · evidence request + doc approval + gap translation
 *   CLUSTER 4 (steps 15-19) · LLM coach + AI classify + mobile + branding + continuity
 *   CLUSTER 5 (steps 20-22) · chat realtime + WhatsApp fan-out + preferences
 *   CLUSTER 6 (steps 23-25) · mode MINIMAL/SUPERVISED toggle render
 *   CLUSTER 7 (steps 26-32) · bulk upload + classify + OCR + search + preview +
 *     SSE per file + soft-delete
 *
 * Solo quedan los smoke tests reales (login · ajustes · MFA · R29). Los pasos
 * que eran placeholders vacíos (`async () => {}`) se borraron: no probaban nada.
 * Las funcionalidades que sí existen tienen su spec dedicada (p. ej. fase_36
 * plan Gantt y copiloto cliente).
 *
 * Run command (Marcos WSL2 native · dev server + backend uvicorn started):
 *   cd frontend && npx playwright test fase_39/client/ --headed
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";

test.describe("Sesión 3B-2B.8 cross-cluster integration · CLUSTER 1-7", () => {
  test.describe("CLUSTER 1 · login MFA + sync events + cloud + copilot + plan", () => {
    test("Step 1 · Cliente login functional (smoke)", async ({ page }) => {
      await loginAsClient(page);
      await expect(page).toHaveURL(/\/client-portal/);
    });
  });

  test.describe("CLUSTER 6 · mode MINIMAL/SUPERVISED toggle render", () => {
    test("Step 23 · Cliente settings hub renders (smoke)", async ({ page }) => {
      await loginAsClient(page);
      await page.goto("/client-portal/settings");
      // testid real del hub de ajustes = "client-settings-hub" (NO "settings-hub").
      await expect(page.getByTestId("client-settings-hub")).toBeVisible();
      // El hub enlaza a las sub-páginas reales (avisos · MFA · cuenta · WhatsApp).
      // El supervision-mode NO se muestra aquí · se mantiene fuera de scope.
      await expect(
        page.getByTestId("client-settings-link-mfa"),
      ).toBeVisible();
    });
  });

  test.describe("CLUSTER 7 · bulk + classify + OCR + search + preview + sync + soft-delete", () => {
    test("Step 26 · MFA enrollment page renders (smoke)", async ({ page }) => {
      await loginAsClient(page);
      await page.goto("/client-portal/settings/mfa");
      await expect(page.getByTestId("mfa-status")).toBeVisible();
    });
  });
});

test.describe("Sesión 3B-2B.8 · cliente-mínimo filosofía retrospective", () => {
  test("Cliente settings page hides admin lingo (R29 sostained)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/settings");

    // El layout cliente expone >1 <main> (locator laxo → strict-mode). Anclamos
    // al contenido real del hub de ajustes vía su testid estable.
    const body = page.getByTestId("client-settings-hub");
    await expect(body).toBeVisible();
    const text = await body.innerText();

    // R29 enforce · NO admin lingo cliente facing
    expect(text.toLowerCase()).not.toContain("supersedes");
    expect(text.toLowerCase()).not.toContain("orchestrator");
    expect(text.toLowerCase()).not.toContain("audit-log");
  });
});
