import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// SKIP: feature eliminada/remodelada (el "Modo auditoría" de /admin/projects/[id]/audit
// se rediseñó · AuditMode.tsx). Ya NO existen: el input con placeholder "pregunta del
// auditor" (ahora "palabra clave, código de medida, host afectado…"), el botón submit
// "Buscar evidencia" (la búsqueda es live onChange contra GET /api/v1/audit/search) ni
// el panel timeline lateral. Además el sample mock AUDIT_SAMPLE_HITS desapareció del
// producto, así que el hit determinista "Prueba de restauración backup" requeriría datos
// sembrados reales. Candidata a reescribir contra el search real tras contraste (Marcos).
test.skip("audit: search produces hits and timeline entry", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/projects/sdl-demo/audit");

  await expect(page.getByText("Modo auditoría")).toBeVisible();

  await page
    .getByPlaceholder(/pregunta del auditor/i)
    .fill("prueba de restauración backup");
  await page.getByRole("button", { name: "Buscar evidencia" }).click();

  // At least one hit from the mock (AUDIT_SAMPLE_HITS contains "backup" keyword).
  await expect(
    page.getByRole("heading", {
      name: /Prueba de restauración backup/i,
    }),
  ).toBeVisible();
  // Timeline side panel picked up the query.
  await expect(
    page.getByText("prueba de restauración backup").first(),
  ).toBeVisible();
});
