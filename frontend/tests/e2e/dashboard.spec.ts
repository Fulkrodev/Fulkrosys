import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

test("dashboard: KPI row + quick actions visible", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/dashboard");

  await expect(
    page.getByRole("heading", { name: /Buenas, Marcos/ }),
  ).toBeVisible();
  await expect(page.getByText("Proyectos activos")).toBeVisible();
  await expect(page.getByText("Leads en pipeline")).toBeVisible();
  await expect(page.getByText("Retainers activos")).toBeVisible();
  await expect(page.getByText("Tesorería 30d")).toBeVisible();

  await expect(
    page.getByRole("link", { name: /Nuevo proyecto/ }),
  ).toHaveAttribute("href", "/admin/projects/new");
  // El pipeline comercial esta dormido (redirige al selector): sus accesos
  // rapidos se retiraron para que ningun boton acabe en el selector.
  for (const retirado of [/Nuevo lead/, /Generar propuesta/, /Consola retainer/]) {
    await expect(page.getByRole("link", { name: retirado })).toHaveCount(0);
  }
  await expect(
    page.getByRole("link", { name: /Nueva reunión/ }),
  ).toBeVisible();
});
