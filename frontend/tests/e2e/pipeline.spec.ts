import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// SKIP: feature eliminada (pipeline comercial m13 desactivado · Batch 2). El
// layout /admin/pipeline/layout.tsx hace redirect() server-side a
// /admin/projects (nav link retirado + endpoints backend 404). Las páginas
// originales quedan dormidas/INTACTAS pero inalcanzables. Candidata a borrar
// tras contraste (Marcos) — o reactivar si el pipeline vuelve al flujo.
test.skip("pipeline: 8 kanban columns with mock leads", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/pipeline");

  await expect(
    page.getByRole("heading", { name: "Pipeline comercial" }),
  ).toBeVisible();

  const headers = [
    "Nuevo",
    "Cualificando",
    "Reunión explor.",
    "Propuesta enviada",
    "Negociación",
    "Cerrado ganado",
    "Cerrado perdido",
    "En pausa",
  ];
  for (const h of headers) {
    await expect(page.getByText(h, { exact: true }).first()).toBeVisible();
  }

  await expect(page.getByText("Soluciones Digitales Levante")).toBeVisible();
});
