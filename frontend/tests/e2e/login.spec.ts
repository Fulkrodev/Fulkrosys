import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

test("login: password + TOTP flow redirects to dashboard", async ({
  context,
  page,
}) => {
  // Pattern híbrido post-MF3.5 BLOQUE 7: cookies Ed25519 reales para que
  // middleware acepte el redirect a /admin/dashboard tras submit form.
  // Mocks `/auth/login` + `/auth/totp/verify` aíslan el form flow del
  // backend real (no requiere password+TOTP correctos), pero SIN
  // Set-Cookie que sobrescriba las cookies reales de loginAsMarcos.
  await loginAsMarcos(context);

  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mfa_ticket: "test-mfa-ticket",
        webauthn: null,
        totp_available: true,
        webauthn_available: false,
      }),
    });
  });
  await page.route("**/api/v1/auth/totp/verify", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        csrf_token: "csrf",
        expires_at: new Date(Date.now() + 8 * 3_600_000).toISOString(),
      }),
    });
  });

  // UI drift (Sesión 3B-2B.9): el destino post-login admin YA NO es
  // /admin/dashboard. resolvePostLoginRedirect("owner") devuelve
  // /admin/projects (selector landing) cuando NO hay lastUsedProjectId, o
  // /admin/projects/{id}/dashboard si lo hay. Limpiamos localStorage para
  // forzar el landing determinista = selector /admin/projects, y aseramos
  // ahí en lugar del viejo greeting "Buenas, Marcos" de /admin/dashboard.
  // lastUsedProjectId vive dentro de la key zustand "fulkro-active-project".
  await page.addInitScript(() => {
    window.localStorage.removeItem("fulkro-active-project");
  });

  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "Acceso restringido" })).toBeVisible();

  await page.getByLabel(/Email/).fill("marcos@fulkro.es");
  await page.getByLabel(/Contraseña/).fill("changeme_on_first_login");
  await page.getByRole("button", { name: /Acceder/ }).click();

  await page.getByPlaceholder("000000").fill("123456");
  await page.getByRole("button", { name: /Validar código/ }).click();

  // Landing real post-login admin = selector de proyectos /admin/projects.
  await expect(page).toHaveURL(/\/admin\/projects(\/)?$/);
});
