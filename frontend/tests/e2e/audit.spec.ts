import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// Proyecto fijo E2E sembrado por globalSetup (existe en la BD de test, así que
// ActiveProjectSync no redirige al selector).
const PROJECT_ID =
  process.env.POLISH_TEST_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

// "Modo auditoría" (components/audit/AuditMode.tsx) · búsqueda live (debounce
// 300 ms) contra GET /api/v1/audit/search. El proyecto sembrado no tiene
// findings/evidencias/documentos, así que la respuesta del buscador se fija con
// un mock; lo que se prueba es que el texto tecleado viaja al backend acotado al
// proyecto y que los hits devueltos se pintan.
test("audit: search produces hits", async ({ context, page }) => {
  await loginAsMarcos(context);

  const queries: URLSearchParams[] = [];
  await page.route("**/api/v1/audit/search?**", async (route) => {
    const sp = new URL(route.request().url()).searchParams;
    queries.push(sp);
    const q = sp.get("q") ?? "";
    const hits = q.toLowerCase().includes("backup")
      ? [
          {
            type: "evidence",
            id: "e0000000-0000-4000-8000-000000000001",
            project_id: PROJECT_ID,
            title: "Prueba de restauración backup",
            snippet: "mp.info.6",
            severity: null,
            estado: "vigente",
            measure_code: "mp.info.6",
            created_at: "2026-05-01T10:00:00Z",
          },
        ]
      : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: q,
        types_filter: sp.getAll("types"),
        total: hits.length,
        hits,
      }),
    });
  });

  await page.goto(`/admin/projects/${PROJECT_ID}/audit`);
  await expect(page.getByText("Modo auditoría · cross-motor search")).toBeVisible();
  await expect(page.getByText("Empieza a escribir")).toBeVisible();

  await page.getByLabel("Buscar").fill("prueba de restauración backup");

  await expect(page.getByText("Prueba de restauración backup")).toBeVisible();
  await expect(page.getByText("Resultados (1)")).toBeVisible();

  const last = queries.at(-1);
  expect(last?.get("q")).toBe("prueba de restauración backup");
  expect(last?.get("project_id")).toBe(PROJECT_ID);
});
