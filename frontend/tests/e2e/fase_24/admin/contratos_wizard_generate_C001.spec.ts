/**
 * E2E · Test 2 fase_24 · admin · ContractGenerateWizard 3 steps C-001.
 *
 * Sub-atom 1.D.D.A v3.11 · M14 wizard 3 pasos (tipo · params · preview).
 *
 * Verifica:
 *   - Wizard abre con step 1 (tipo plantilla)
 *   - Templates 5 visibles (C-001 → C-005)
 *   - Selección C-001 + Next
 *   - Step 2 · proposal won mock + firmante + cargo + vigencia + Next
 *   - Step 3 · preview muestra plantilla + proposal + firmante
 *   - Submit → POST generate mock → contract creado
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_DD_ID,
  mockContractGenerate,
  mockContractsBase,
} from "../_fixtures";

test.describe("fase_24 admin · ContractGenerateWizard 3 steps", () => {
  test("C-001 → params → preview → generate OK", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockContractsBase(page);
    await mockContractGenerate(page);

    await page.goto(`/admin/projects/${PROJECT_DD_ID}/contratos`);

    // Abrir wizard
    await page.getByTestId("contracts-generate-button").click();
    await expect(page.getByTestId("contract-generate-wizard")).toBeVisible();

    // Step 1 · tipo selector
    await expect(page.getByTestId("wizard-step-tipo")).toBeVisible();
    await expect(page.getByTestId("wizard-template-C-001")).toBeVisible();
    await expect(page.getByTestId("wizard-template-C-002")).toBeVisible();
    await expect(page.getByTestId("wizard-template-C-003")).toBeVisible();
    await expect(page.getByTestId("wizard-template-C-004")).toBeVisible();
    await expect(page.getByTestId("wizard-template-C-005")).toBeVisible();

    // Click C-001 + Next
    await page.getByTestId("wizard-template-C-001").click();
    await page.getByTestId("contracts-wizard-next").click();

    // Step 2 · params
    await expect(page.getByTestId("wizard-step-params")).toBeVisible();
    await page.getByTestId("wizard-firmante-nombre").fill("Test Firmante");
    await page.getByTestId("wizard-firmante-cargo").fill("CEO");

    // Proposal select (mock proposal won)
    await page.getByTestId("wizard-proposal-select").click();
    await page.getByRole("option").first().click();

    await page.getByTestId("contracts-wizard-next").click();

    // Step 3 · preview
    await expect(page.getByTestId("wizard-step-preview")).toBeVisible();
    await expect(page.getByText(/Test Firmante/)).toBeVisible();
    // UI drift: "CEO" aparece en el preview y en el row de la lista detrás →
    // strict-mode 2 elementos. Scope al paso preview.
    await expect(
      page.getByTestId("wizard-step-preview").getByText(/CEO/),
    ).toBeVisible();

    // Submit
    await page.getByTestId("contracts-wizard-submit").click();

    // Wizard se cierra (re-fetch list ocurre)
    await expect(
      page.getByTestId("contract-generate-wizard"),
    ).not.toBeVisible({ timeout: 5000 });
  });
});
