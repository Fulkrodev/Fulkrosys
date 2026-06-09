import { expect, test } from "@playwright/test";

/**
 * E2E /download/[token] · dispatcher 3 purposes (M25 public_api).
 *
 * Cobertura mínima sin backend seeded: render del estado de error con
 * un token sintético + verifica layout público intacto.
 */

test("download portal · token inválido muestra alert sin crashear", async ({
  page,
}) => {
  await page.goto("/download/e2e-token-not-real-download");

  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: /Enlace no disponible|caducado|otra funcionalidad/ }),
  ).toBeVisible({ timeout: 5_000 });

  await expect(page.getByText(/Enlace seguro FULKRO/)).toBeVisible();
});
