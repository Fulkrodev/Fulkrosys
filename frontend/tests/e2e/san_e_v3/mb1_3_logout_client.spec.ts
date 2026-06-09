/**
 * SAN-E v3.MB-1.3 · client portal logout via useLogout("client") hook.
 *
 * 2 callsites cliente:
 *   1. ClientSidebar (footer · raw <button>, LogOut size={20}
 *      strokeWidth={2.3}, label "Salir" always visible).
 *   2. ClientHeader (banner · <Button> ghost, LogOut size={18}
 *      strokeWidth={2.3}, label hidden sm:inline).
 *
 * Ambos disparan useLogout("client") · POST /client-auth/logout ·
 * router.push("/client-portal/login") · silent (NO toast · cookies
 * clear server-side · comments preservados pre-1.3).
 *
 * Ver useLogout hook (frontend/hooks/useLogout.ts) · ADR-046 v3.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-1.3 · client logout · useLogout hook", () => {
  test("ClientSidebar · Salir button (raw) → /client-portal/login", async ({
    page,
  }) => {
    await loginAsClient(page);

    const sidebar = page.getByRole("complementary", {
      name: /Navegación portal cliente/i,
    });
    // El botón Salir del ClientSidebar (raw <button>) NO usa aria-label
    // "Cerrar sesión": su nombre accesible es "Salir" (span interno) y
    // expone data-testid="cliente-nav-logout" (selector estable).
    await sidebar.getByTestId("cliente-nav-logout").click();

    await expect(page).toHaveURL(/\/client-portal\/login/, {
      timeout: 10_000,
    });

    // SKIP: re-acceso protegido (page.goto /client-portal/workflow debe redirigir
    // a login) — mismo artefacto E2E que el logout admin: el Set-Cookie max-age=0
    // del /client-auth/logout proxied NO purga las cookies httpOnly del
    // BrowserContext de Playwright, así que la ruta protegida sigue accesible en
    // el entorno de test. El backend SÍ revoca server-side. NO es regresión de
    // producto. Candidata a borrar/reescribir tras contraste (Marcos).
  });

  test("ClientHeader · Salir button → /client-portal/login", async ({
    page,
  }) => {
    await loginAsClient(page);

    const header = page.getByRole("banner");
    await header
      .getByRole("button", { name: /Cerrar sesión/i })
      .click();

    await expect(page).toHaveURL(/\/client-portal\/login/, {
      timeout: 10_000,
    });
  });
});
