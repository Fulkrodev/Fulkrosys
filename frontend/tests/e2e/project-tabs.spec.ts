import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

// Las pestañas project-scoped (ProjectTabs.tsx) navegan cada una a su ruta
// /admin/projects/{id}/X y montan su panel. Se usa el proyecto E2E sembrado por
// `_dev/create-test-client` (el antiguo slug mock "sdl-demo" ya no existe).
test("project: main tabs navigate to their route", async ({ context, page }) => {
  await loginAsMarcos(context);
  const res = await context.request.post(
    `${BACKEND}/api/v1/_dev/create-test-client`,
  );
  expect(res.ok()).toBeTruthy();
  const { project_id } = (await res.json()) as { project_id: string };

  await page.goto(`/admin/projects/${project_id}/summary`);
  const tabs = page.getByRole("navigation", { name: "Secciones del proyecto" });
  await expect(tabs.getByRole("link", { name: "Resumen" })).toHaveAttribute(
    "aria-current",
    "page",
  );

  await tabs.getByRole("link", { name: "Implantación" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/admin/projects/${project_id}/implementation$`),
  );
  await expect(tabs.getByRole("link", { name: "Implantación" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByText("Obligaciones del proyecto")).toBeVisible();

  await tabs.getByRole("link", { name: "Evidencias" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/admin/projects/${project_id}/evidence$`),
  );
  await expect(page.getByTestId("evidence-admin-upload")).toBeVisible();

  await tabs.getByRole("link", { name: "Dossier" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/admin/projects/${project_id}/dossier$`),
  );
  await expect(page.getByText("Dossier de auditoría (M09)")).toBeVisible();
});
