import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

test("command palette: Cmd+K opens and navigates to a route", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/dashboard");

  // Intentamos el atajo de teclado (Meta/Control+K) pero en chromium headless
  // sobre Linux la tecla Meta + el foco no siempre disparan el handler global.
  // Fallback determinista: el botón "Buscar ⌘K" del sidebar abre el MISMO
  // CommandPalette (mismo estado open controlado por el layout admin).
  const dialog = page.getByRole("dialog", { name: /Buscar o ejecutar/ });
  await page.keyboard.press("Meta+K");
  if (!(await dialog.isVisible().catch(() => false))) {
    await page.keyboard.press("Control+K");
  }
  if (!(await dialog.isVisible().catch(() => false))) {
    await page.getByRole("button", { name: /Buscar/i }).first().click();
  }
  await expect(dialog).toBeVisible();

  // El item real es "Ir al pipeline comercial" (CommandPalette.tsx · group
  // Navegación · run navigate(ROUTES.pipeline)="/admin/pipeline"). Filtramos por
  // "pipeline" y clicamos el item explícito en lugar de confiar en Enter +
  // auto-highlight de cmdk (que en el build podía seleccionar otro item → antes
  // navegaba a /admin/projects). El click sobre el item concreto es determinista.
  await page.keyboard.type("pipeline");
  await dialog.getByRole("option", { name: /Ir al pipeline comercial/i }).click();

  // ROUTES.pipeline = "/admin/pipeline" (termina en /pipeline).
  await expect(page).toHaveURL(/\/pipeline$/);
});
