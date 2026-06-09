import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// SKIP: feature eliminada (fixture de proyecto mock "sdl-demo" / heading
// "Soluciones Digitales Levante"). Las pestañas project-scoped (Implantación /
// Evidencias / Dossier) siguen existiendo en ProjectTabs.tsx, PERO esta spec
// navega a /admin/projects/sdl-demo/summary asumiendo un proyecto mock llamado
// "Soluciones Digitales Levante". Ese slug ya no resuelve: ProjectHeader hace
// GET /api/v1/projects/sdl-demo/header contra el backend real (sin mock) → no hay
// heading con ese nombre (ProjectHeader renderiza cliente.nombre/project.nombre del
// proyecto sembrado, no el mock). "Soluciones Digitales Levante" solo vive ya en
// lib/mock.ts como LEAD del pipeline. Candidata a reescribir contra el proyecto
// E2E sembrado (create-test-client, UUID dinámico) tras contraste (Marcos).
test.skip("project: main tabs navigate to their route", async ({
  context,
  page,
}) => {
  await loginAsMarcos(context);
  await page.goto("/admin/projects/sdl-demo/summary");

  await expect(
    page.getByRole("heading", { name: "Soluciones Digitales Levante" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Implantación" }).click();
  await expect(page).toHaveURL(/\/implementation$/);
  await expect(page.getByText("Obligaciones ENS")).toBeVisible();

  await page.getByRole("link", { name: "Evidencias" }).click();
  await expect(page).toHaveURL(/\/evidence$/);
  await expect(page.getByText("Evidence Vault")).toBeVisible();

  await page.getByRole("link", { name: "Dossier" }).click();
  await expect(page).toHaveURL(/\/dossier$/);
});
