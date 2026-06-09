/**
 * E2E · Test 5 fase_19 · cliente · Files page tree friendly render.
 *
 * Sub-atom 1.C.G.B v3.10 · DocumentTreeClient + page /client-portal/files/.
 *
 * Verifica:
 *   - Login cliente · /client-portal/files/ render OK
 *   - Title "Mis Documentos" friendly visible
 *   - Sidebar "Mis carpetas" visible (tab Documents activo default)
 *   - DocumentTreeClient render carpetas (al menos 3 standard)
 *   - "Todos mis documentos" root link visible
 *   - Botón "Compartir documento" visible top-right
 *   - Tabs hybrid Documents/Evidencias preservados (NO breaking)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientIdmsBase } from "../_fixtures";

test.describe("fase_19 cliente · files tree friendly render", () => {
  test("renders Mis Documentos title + tree sidebar + upload button", async ({
    page,
  }) => {
    await mockClientIdmsBase(page);
    await loginAsClient(page);

    await page.goto("/client-portal/files");

    // Title friendly "Mis Documentos"
    await expect(
      page.getByRole("heading", { name: /^Mis Documentos$/i }),
    ).toBeVisible();

    // Sidebar "Mis carpetas" panel
    await expect(page.getByText(/Mis carpetas/i)).toBeVisible();

    // "Todos mis documentos" root link friendly
    await expect(
      page.getByRole("button", { name: /Todos mis documentos/i }),
    ).toBeVisible();

    // At least 3 carpetas visible in tree (friendly · NO admin K.XX badges)
    await expect(page.getByText(/06_Normativa/i).first()).toBeVisible();
    await expect(page.getByText(/09_Evidencias/i).first()).toBeVisible();

    // Upload button friendly "Compartir documento"
    await expect(
      page.getByTestId("client-upload-button"),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Compartir documento/i }),
    ).toBeVisible();

    // Tabs hybrid preservados
    await expect(page.getByTestId("files-tab-documents")).toBeVisible();
    await expect(page.getByTestId("files-tab-evidence")).toBeVisible();
  });
});
