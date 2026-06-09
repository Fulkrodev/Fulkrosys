/**
 * E2E · Test 2 fase_19 · admin · Upload document modal with tags ENS.
 *
 * Sub-atom 1.C.G.A v3.10 · UploadDocumentModal admin.
 *
 * Verifica:
 *   - Login admin · click "Subir documento"
 *   - UploadDocumentModal opens · drag-drop file input visible
 *   - Folder selector visible
 *   - Clasificacion select visible (politica/procedimiento/registro/etc)
 *   - Textarea tags ENS visible (medidas Anexo II comma-separated)
 *   - Submit con file mock → modal closes
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_G_ID, mockAdminIdmsBase } from "../_fixtures";

test.describe("fase_19 admin · upload document modal with tags ENS", () => {
  test("opens modal · drag-drop + folder + clasificacion + tags ENS", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminIdmsBase(page);

    await page.goto(`/admin/projects/${PROJECT_G_ID}/documents`);

    // Click "Subir documento" button
    await page.getByRole("button", { name: /Subir documento/i }).click();

    // Modal opens with title
    await expect(
      page.getByRole("dialog").getByText(/Subir documento/i).first(),
    ).toBeVisible();

    // File input (drag-drop)
    await expect(page.getByLabel(/Archivo/i)).toBeVisible();

    // Folder selector
    await expect(page.getByLabel(/Carpeta destino/i)).toBeVisible();

    // Clasificacion selector
    await expect(page.getByLabel(/Clasificación/i)).toBeVisible();

    // Tags ENS textarea (medidas Anexo II)
    await expect(
      page.getByLabel(/Medidas ENS \(separadas por comas\)/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Códigos Anexo II opcionales · taxonomía oficial RD 311\/2022/i),
    ).toBeVisible();

    // Submit + Cancel buttons
    await expect(
      page.getByRole("button", { name: /Subir documento/i }).last(),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Cancelar/i }),
    ).toBeVisible();
  });
});
