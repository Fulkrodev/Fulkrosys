import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// SKIP: feature eliminada (consola cross-cliente /admin/retainers · "Consola Retainer"
// con grid RAG-filtrable de clientes mock). La ruta /admin/retainers ahora hace
// redirect() server-side hacia /admin/projects (consolidación R23 retainer
// per-project · Sesión 3B-2B.3 Phase X.3). El retainer ahora vive en
// /admin/projects/[id]/retainer (RetainerProjectDashboard). El heading "Consola
// Retainer", el grid cross-cliente y el contador "N/N clientes" no existen ya.
// Candidata a borrar tras contraste (Marcos).
test.skip("retainer: RAG filter narrows the client grid", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/retainers");

  await expect(
    page.getByRole("heading", { name: "Consola Retainer" }),
  ).toBeVisible();

  // The grid shows every mock client before filtering.
  const sdlChip = page.getByText("Soluciones Digitales Levante").first();
  await expect(sdlChip).toBeVisible();
  await expect(page.getByText("Ayuntamiento de Valencia").first()).toBeVisible();
  await expect(page.getByText("DataForma Galicia").first()).toBeVisible();

  // The matches counter tells us how many clients passed the filter.
  const counter = page.getByText(/\d+\/\d+ clientes/);
  const before = await counter.textContent();

  // The only <select> elements on the page are the RAG and plan filters.
  const ragSelect = page.locator("select").first();
  await ragSelect.selectOption("red");

  await expect(counter).not.toHaveText(before ?? "");
  await expect(counter).toContainText("1/6");
});
