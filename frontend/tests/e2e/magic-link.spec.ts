import { expect, test } from "@playwright/test";

// El token mock `e2e-token-abc` NO existe en el backend → el dispatcher
// /sign/[token] muestra la página de error honesta. Antes renderizaba un
// formulario de firma MOCK (LegacyDocumentSignFlow), ya borrado: un enlace
// inválido no debe simular una firma.
test("magic link sign: token inválido muestra página de error", async ({
  page,
}) => {
  await page.goto("/sign/e2e-token-abc");

  await expect(
    page.getByText(/Enlace no válido o expirado/i),
  ).toBeVisible();
  await expect(
    page.getByText(/El enlace de firma no pudo procesarse/i),
  ).toBeVisible();
});
