import { expect, test } from "@playwright/test";

test("magic link sign: public page renders preview + disabled submit", async ({
  page,
}) => {
  await page.goto("/sign/e2e-token-abc");

  await expect(
    page.getByRole("heading", { name: "Firma de documento" }),
  ).toBeVisible();
  await expect(page.getByText("E-200")).toBeVisible();
  await expect(page.getByText(/Procedimiento de Gestión de Riesgos/)).toBeVisible();

  const signBtn = page.getByRole("button", { name: /Firmar con Ed25519/ });
  await expect(signBtn).toBeDisabled();

  await page.getByPlaceholder("000000").fill("123456");
  await page
    .getByText(/He leído el documento y firmo conforme/)
    .locator("xpath=preceding-sibling::input")
    .check();
  await expect(signBtn).toBeEnabled();
});
