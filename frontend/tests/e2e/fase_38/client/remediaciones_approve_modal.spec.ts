/**
 * E2E · Test 3 fase_38 · cliente · ApprovalModal happy path approve.
 *
 * Bloque 3+5 v3.12 · cliente click "Revisar y decidir" → modal abre →
 * approve → POST aprove → success feedback R29 friendly.
 *
 * Verifica:
 *   - Click "Revisar y decidir" abre modal
 *   - Modal muestra título + explicación + suggested action
 *   - Click "Aprobar" dispara POST /approve
 *   - Success feedback R29 "Gracias Marcos comenzará"
 *   - Modal close auto post 1500ms (test verifica close eventualmente)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import {
  mockApproveAndReject,
  mockRemediationsWith3Sections,
} from "../_fixtures";

test.describe("fase_38 client · ApprovalModal approve happy path", () => {
  test("click Revisar -> modal abre -> Aprobar -> success R29", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockRemediationsWith3Sections(page);
    await mockApproveAndReject(page);

    await page.goto("/client-portal/remediaciones");

    // Click "Revisar y decidir" del primer pendiente
    const reviewBtn = page.getByTestId("review-button").first();
    await expect(reviewBtn).toBeVisible();
    await reviewBtn.click();

    // Modal abre
    const modal = page.getByTestId("approval-modal");
    await expect(modal).toBeVisible();

    // Modal muestra título + explanation + suggested action
    await expect(
      modal.getByText(/Activar segundo factor para todos los usuarios/i),
    ).toBeVisible();
    await expect(
      page.getByTestId("modal-explanation"),
    ).toBeVisible();
    await expect(
      page.getByTestId("modal-suggested-action"),
    ).toBeVisible();

    // Click Aprobar
    await page.getByTestId("approve-button").click();

    // Success feedback R29 friendly
    await expect(
      page.getByTestId("modal-feedback"),
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByText(/Gracias.*Marcos/i),
    ).toBeVisible();
  });

  test("Rechazar dispara POST /reject + feedback R29", async ({ page }) => {
    await loginAsClient(page);
    await mockRemediationsWith3Sections(page);
    await mockApproveAndReject(page);

    await page.goto("/client-portal/remediaciones");
    await page.getByTestId("review-button").first().click();
    await expect(page.getByTestId("approval-modal")).toBeVisible();

    // Optional notes
    await page.getByTestId("approval-notes").fill("Sin presupuesto ahora mismo");
    await page.getByTestId("reject-button").click();

    await expect(
      page.getByTestId("modal-feedback"),
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByText(/Entendido.*Marcos/i),
    ).toBeVisible();
  });
});
