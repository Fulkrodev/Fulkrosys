/**
 * E2E /client-portal/files extended · SAN-E v3.MB-6 atom 7.
 *
 * Validates cliente UX files extended:
 *  1. /files renders tabs Documentos + Evidencias
 *  2. SearchBar visible · debounced search input
 *  3. Tab switch toggles active state + scan_clean_only toggle visible solo evidence
 *  4. Sidebar nav 'Documentos' link visible
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Files extended · MB-6 atom 7", () => {
  test("Cliente VE page · header + tabs + search bar", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/files");

    // UI evolucionó: el h1 de la página de archivos cliente pasó de
    // "Mis archivos" a "Mis Documentos" (app/(client-portal)/.../files/page.tsx
    // línea 167-169). Feature intacta · solo cambió el copy del heading.
    await expect(
      page.getByRole("heading", { name: "Mis Documentos" }),
    ).toBeVisible();

    // Tabs Q7 B separated cement
    const tabs = page.getByTestId("files-tabs");
    await expect(tabs).toBeVisible();
    const docTab = page.getByTestId("files-tab-documents");
    const evTab = page.getByTestId("files-tab-evidence");
    await expect(docTab).toBeVisible();
    await expect(evTab).toBeVisible();
    await expect(docTab).toHaveAttribute("data-active", "true");
    await expect(evTab).toHaveAttribute("data-active", "false");

    // SearchBar
    await expect(page.getByTestId("files-search-bar")).toBeVisible();

    // scan_clean_only toggle hidden en documents tab (Q5 A · solo evidence)
    await expect(page.getByTestId("evidence-scan-clean-toggle")).toHaveCount(0);
  });

  test("Tab switch documents → evidence reveals scan_clean_only toggle", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/files");

    const evTab = page.getByTestId("files-tab-evidence");
    await evTab.click();
    await expect(evTab).toHaveAttribute("data-active", "true");
    await expect(page.getByTestId("files-tab-documents")).toHaveAttribute(
      "data-active",
      "false",
    );

    // scan_clean_only toggle ahora visible (Q5 A)
    await expect(page.getByTestId("evidence-scan-clean-toggle")).toBeVisible();
  });

  test("Sidebar nav 'Subir documentos' visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/files");

    // UI evolucionó: la entrada de sidebar que apunta a /client-portal/files
    // pasó de "Documentos" a "Subir documentos" (ClientSidebar.tsx línea 113).
    // Misma feature/href · solo cambió el label. data-testid estable:
    // cliente-nav-subir-documentos.
    const nav = page.getByTestId("cliente-nav-subir-documentos");
    await expect(nav).toBeVisible();
  });
});
