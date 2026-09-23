import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

test("command palette: Cmd+K opens and navigates to a route", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/dashboard");

  // ⌘K / Ctrl+K es un TOGGLE (CommandPalette acepta metaKey o ctrlKey). Antes
  // se pulsaba Meta+K y luego Control+K: si ambas llegaban al listener se abría
  // y se volvía a cerrar. Y si se pulsaba antes de hidratar no había listener.
  // Una sola pulsación por intento, reintentada sólo mientras siga cerrada.
  const dialog = page.getByRole("dialog", { name: /Buscar o ejecutar/ });
  await expect(async () => {
    if (!(await dialog.isVisible())) {
      await page.keyboard.press("Control+K");
    }
    await expect(dialog).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });

  // Destino: "Ajustes" (ROUTES.settings = /admin/settings), ruta viva. Antes se
  // usaba "Ir al pipeline comercial", pero /admin/pipeline está dormido
  // (app/(admin)/admin/pipeline/layout.tsx redirige a /admin/projects): el test
  // sólo pasaba si toHaveURL veía /pipeline un instante antes del redirect.
  // Click sobre el item concreto (no Enter + auto-highlight de cmdk).
  await page.keyboard.type("ajustes");
  await dialog.getByRole("option", { name: /^Ajustes$/ }).click();

  await expect(page).toHaveURL(/\/admin\/settings$/);
  await expect(
    page.getByRole("heading", { name: /^Ajustes$/, level: 1 }),
  ).toBeVisible();
  await expect(dialog).toBeHidden();
});
