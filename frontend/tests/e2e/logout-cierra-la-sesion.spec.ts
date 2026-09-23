/**
 * Cerrar sesion tiene que cerrar la sesion, en los dos portales.
 *
 * Hasta 2026-09-23 no lo hacia: el cliente llamaba a "/client-auth/logout"
 * (sin /api/v1 · 404 en Next, nunca llegaba al backend) y el admin mandaba el
 * POST sin X-CSRF-Token (403). En ambos casos la interfaz redirigia al login,
 * la cookie httpOnly seguia en el navegador y volver a la pagina protegida
 * entraba sin pedir nada. En un equipo compartido, el siguiente usaba la
 * sesion del anterior.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";

const CASOS = [
  { portal: "cliente", casa: "/client-portal/dashboard", login: /\/client-portal\/login/ },
  { portal: "admin", casa: "/admin/dashboard", login: /\/login/ },
] as const;

for (const caso of CASOS) {
  test(`logout ${caso.portal} · revoca la sesion y exige login otra vez`, async ({ page, context }) => {
    if (caso.portal === "cliente") await loginAsClient(page);
    else await loginAsMarcos(context);
    await page.goto(caso.casa);
    await expect(page).toHaveURL(new RegExp(caso.casa));

    const respuesta = page.waitForResponse((r) => r.url().includes("/logout"));
    await page.getByRole("button", { name: /cerrar sesi|salir/i }).first().click();
    expect((await respuesta).status()).toBe(200);
    await expect(page).toHaveURL(caso.login);

    const nombres = (await context.cookies()).map((c) => c.name);
    expect(nombres).not.toContain("fulkro_session");

    await page.goto(caso.casa);
    await expect(page).toHaveURL(caso.login);
  });
}
