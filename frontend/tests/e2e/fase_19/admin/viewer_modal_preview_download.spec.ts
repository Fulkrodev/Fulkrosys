/**
 * E2E · Test 3 fase_19 · admin · Document viewer modal · metadata + tags + versions.
 *
 * Sub-atom 1.C.G.A v3.10 · DocumentViewerModal admin.
 *
 * Verifica:
 *   - Login admin · click row documento (eye icon)
 *   - DocumentViewerModal opens · nombre header visible
 *   - Metadata section: Tipo · Estado · Clasificación · Tamaño · Hash SHA-256 · Carpeta · Creado
 *   - Tags section visible con tags ENS (op.pl.1 · org.1)
 *   - Versiones section visible (v2.0 · v1.0)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_G_ID, mockAdminIdmsBase } from "../_fixtures";

test.describe("fase_19 admin · viewer modal preview + metadata", () => {
  test("opens viewer · metadata + tags ENS + versiones visible", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminIdmsBase(page);

    await page.goto(`/admin/projects/${PROJECT_G_ID}/documents`);

    // Click on document name PSI_v2.docx → opens viewer
    await page.getByRole("button", { name: /PSI_v2\.docx/i }).first().click();

    // Dialog opens
    await expect(page.getByRole("dialog")).toBeVisible();

    // Metadata fields visible
    await expect(
      page.getByText(/Metadatos/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Hash SHA-256/i).first(),
    ).toBeVisible();

    // Folder name in dialog
    await expect(
      page.getByRole("dialog").getByText(/06_Normativa/i).first(),
    ).toBeVisible();

    // Tags ENS section
    await expect(page.getByText(/Etiquetas \(2\)/i)).toBeVisible();
    await expect(page.getByText(/measure_ens: op\.pl\.1/i)).toBeVisible();
    await expect(page.getByText(/measure_ens: org\.1/i)).toBeVisible();

    // Versions section
    await expect(page.getByText(/Versiones \(2\)/i)).toBeVisible();
    await expect(
      page.getByRole("dialog").getByText(/^v2\.0$/).first(),
    ).toBeVisible();
  });
});
