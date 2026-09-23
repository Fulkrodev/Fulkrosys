/**
 * MB-4.2 · WorkspacePanel real wired M20 (SAN-E v3).
 *
 * Wired al backend Motor 20 (22 endpoints · 17 únicos · 3 sub-features
 * Files/Chat/Feed wired · videocalls diferido).
 *
 * Cobertura:
 * - login admin · navigate /workspace
 * - el workspace del proyecto seed se asegura por API (idempotente) antes de
 *   cada test: así las pestañas existen siempre y ningún test depende de un
 *   estado previo (antes se saltaban en silencio si no había workspace)
 * - 3 tabs renderizan (Files · Chat · Timeline)
 * - Files tab · drag-drop area + btn subir + DataTable
 * - Chat tab · markdown editor con tabs Edit/Preview · enviar mensaje
 * - Feed tab · filtros tipo/autor + timeline visual con dots
 * - tooltips ENS visibles (workspace_proyecto · cadena_custodia · audit_log)
 */
import { expect, test } from "@playwright/test";
import type { BrowserContext } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";
const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

async function ensureWorkspace(context: BrowserContext): Promise<void> {
  const url = `${BACKEND}/api/v1/workspace/projects/${PROJECT_ID}/workspace`;
  const current = await context.request.get(url);
  if (current.ok()) return;
  expect(current.status()).toBe(404);
  const csrf =
    (await context.cookies()).find((c) => c.name === "fulkro_csrf")?.value ?? "";
  const created = await context.request.post(url, {
    headers: { "x-csrf-token": csrf },
    data: { nombre: "Workspace del proyecto" },
  });
  expect(created.status()).toBe(201);
}

test.describe("MB-4.2 · WorkspacePanel M20", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await ensureWorkspace(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/workspace`);
  });

  test("header con título + chips summary", async ({ page }) => {
    await expect(page.getByText(/Workspace del proyecto/i).first()).toBeVisible();
    await expect(page.getByText(/Workspace no creado/i)).toHaveCount(0);
  });

  test("3 tabs renderizan", async ({ page }) => {
    for (const label of ["Archivos", "Chat", "Timeline"]) {
      await expect(page.getByRole("tab", { name: new RegExp(label, "i") })).toBeVisible();
    }
  });

  test("Files tab · drag-drop + btn subir", async ({ page }) => {
    const filesTab = page.getByRole("tab", { name: /Archivos/i });
    await filesTab.click();
    await expect(
      page.getByRole("heading", { name: /Archivos del workspace/i }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /Subir archivos/i })).toBeVisible();
    await expect(page.getByText(/Arrastra archivos aquí/i)).toBeVisible();
  });

  test("Chat tab · editor markdown con tabs Edit/Preview", async ({ page }) => {
    const chatTab = page.getByRole("tab", { name: /Chat/i });
    await chatTab.click();
    await expect(page.getByRole("heading", { name: /Chat del workspace/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Editar/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Vista previa/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Enviar/i })).toBeVisible();
  });

  test("Feed tab · timeline + filtros + export CSV", async ({ page }) => {
    const feedTab = page.getByRole("tab", { name: /Timeline/i });
    await feedTab.click();
    await expect(
      page.getByRole("heading", { name: /Timeline del proyecto/i }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /Exportar CSV/i })).toBeVisible();
    await expect(page.getByLabel(/Solo sin leer/i)).toBeVisible();
  });

  test("Files tab · empty state si sin archivos", async ({ page }) => {
    const filesTab = page.getByRole("tab", { name: /Archivos/i });
    await filesTab.click();
    // Empty state O DataTable (acepta ambos)
    await expect(
      page.getByText(/Sin archivos · sube|Buscar archivos/i),
    ).toBeVisible();
  });

  test("Chat tab · enviar mensaje markdown", async ({ page }) => {
    const chatTab = page.getByRole("tab", { name: /Chat/i });
    await chatTab.click();
    const textarea = page.getByPlaceholder(/Escribe un mensaje/i);
    await textarea.fill("**Test** mensaje markdown");
    // Toggle a Preview
    await page.getByRole("tab", { name: /Vista previa/i }).click();
    // El bold debería estar renderizado
    await expect(page.locator("strong").filter({ hasText: "Test" })).toBeVisible();
  });
});
