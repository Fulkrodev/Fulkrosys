import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// El pipeline comercial (kanban de leads m13) está DORMIDO a propósito (Batch 2):
// app/(admin)/admin/pipeline/layout.tsx hace redirect() server-side a
// /admin/projects y el enlace de navegación se retiró. El antiguo test del
// kanban de 8 columnas con leads mock se borró porque esa pantalla ya no es
// alcanzable; lo que existe hoy es el redirect, y eso es lo que se comprueba.
// Si el pipeline vuelve al flujo (borrar el layout), este test fallará a
// propósito y habrá que volver a escribir el del kanban.
test("pipeline dormido: /admin/pipeline y sus subrutas redirigen a /admin/projects", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);

  await page.goto("/admin/pipeline");
  await expect(page).toHaveURL(/\/admin\/projects$/);

  await page.goto("/admin/pipeline/leads/00000000-0000-4000-8000-000000000000");
  await expect(page).toHaveURL(/\/admin\/projects$/);
});
