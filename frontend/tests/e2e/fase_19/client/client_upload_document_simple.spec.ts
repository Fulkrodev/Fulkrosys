/**
 * E2E · Test 6 fase_19 · cliente · Upload modal permission-limited friendly.
 *
 * Sub-atom 1.C.G.B v3.10 · ClientUploadModal permission-limited.
 *
 * Verifica:
 *   - Login cliente · click "Compartir documento"
 *   - ClientUploadModal opens · title "Compartir un documento" friendly
 *   - File input + Folder selector + Description optional visible
 *   - NO tags ENS visible (R30 inverso · admin gestiona)
 *   - NO clasificacion B/M/A selector visible (R30 inverso)
 *   - Hints friendly visible ("Si no estás seguro, déjalo vacío…")
 *   - Cancel + Subir buttons visible
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientIdmsBase } from "../_fixtures";

test.describe("fase_19 cliente · upload modal permission-limited", () => {
  test("opens modal · friendly fields · NO admin lingo", async ({ page }) => {
    await mockClientIdmsBase(page);
    await loginAsClient(page);

    await page.goto("/client-portal/files");

    // Click upload button friendly
    await page.getByTestId("client-upload-button").click();

    // Modal title friendly
    await expect(
      page.getByRole("dialog").getByText(/Compartir un documento/i).first(),
    ).toBeVisible();

    // File input
    await expect(page.getByLabel(/^Archivo$/i)).toBeVisible();

    // Folder selector (friendly placeholder · NO técnico admin)
    await expect(page.getByLabel(/Carpeta \(opcional\)/i)).toBeVisible();

    // Description optional (cliente puede explicar contenido)
    await expect(page.getByLabel(/Descripción \(opcional\)/i)).toBeVisible();

    // Friendly hint visible
    await expect(
      page.getByText(/Si no estás seguro, déjalo vacío/i),
    ).toBeVisible();

    // Cancel + Subir buttons
    await expect(
      page.getByRole("button", { name: /Cancelar/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^Subir$/i }),
    ).toBeVisible();

    // CRÍTICO R30 inverso · NO admin fields:
    // NO tags ENS textarea ("Medidas ENS · separadas por comas")
    await expect(
      page.getByLabel(/Medidas ENS/i),
    ).not.toBeVisible();

    // NO clasificacion admin selector ("politica/procedimiento/registro/etc")
    await expect(
      page.getByLabel(/^Clasificación$/i),
    ).not.toBeVisible();
  });
});
