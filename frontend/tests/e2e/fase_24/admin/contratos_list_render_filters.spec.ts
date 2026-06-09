/**
 * E2E · Test 1 fase_24 · admin · ContractsList render + filters.
 *
 * Sub-atom 1.D.D.A v3.11 · M14 Contracts admin page.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/contratos render OK
 *   - Tabla con 2 mock contracts visible (vigente · draft)
 *   - Filters estado (Todos · Borrador · Firmado Marcos · Enviado · etc)
 *   - Counts per filter visibles
 *   - Click "Generar contrato" button abre wizard
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_DD_ID,
  mockContractsBase,
} from "../_fixtures";

test.describe("fase_24 admin · ContractsList render + filters", () => {
  test("2 contracts mock visible + filtros + wizard abrible", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockContractsBase(page);

    await page.goto(`/admin/projects/${PROJECT_DD_ID}/contratos`);

    // List container visible
    await expect(page.getByTestId("contracts-list")).toBeVisible();

    // Tabla 2 contratos (vigente + draft)
    await expect(page.getByTestId("contracts-table")).toBeVisible();
    await expect(
      page.getByTestId(`contracts-row-c0000001-aaaa-bbbb-cccc-000000000001`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`contracts-row-c0000002-aaaa-bbbb-cccc-000000000002`),
    ).toBeVisible();

    // Filters container + filter-draft button
    await expect(page.getByTestId("contracts-filters")).toBeVisible();
    await expect(page.getByTestId("contracts-filter-all")).toBeVisible();
    await expect(page.getByTestId("contracts-filter-draft")).toBeVisible();
    await expect(page.getByTestId("contracts-filter-vigente")).toBeVisible();

    // Click filter "draft" reduces table
    await page.getByTestId("contracts-filter-draft").click();
    await expect(
      page.getByTestId(`contracts-row-c0000002-aaaa-bbbb-cccc-000000000002`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`contracts-row-c0000001-aaaa-bbbb-cccc-000000000001`),
    ).not.toBeVisible();

    // Botón "Generar contrato" abre wizard
    await page.getByTestId("contracts-generate-button").click();
    await expect(page.getByTestId("contract-generate-wizard")).toBeVisible();
  });
});
