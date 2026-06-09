/**
 * FASE 12.A · Sub-atom 1.C.C.C · Category gating cliente portal · CIERRE 1.C.C.
 *
 * ACTUALIZACIÓN (sub-atom 1.D.F.bis.III.B v3.11 · modelo indispensable-only):
 * el índice /client-portal/registros ya NO muestra el grid de cards por
 * categoría · ahora REDIRIGE a /client-portal/tasks (el cliente NO gestiona
 * registros vivos; Marcos los opera en admin). El subtitle "cobertura N
 * bloques" desapareció. Por eso los 3 primeros tests (conteo de cards por
 * tier en el índice) quedan skip · documentados abajo. La cobertura del
 * redirect está en fase_30/client/cliente_registros_redirect_tasks.spec.ts.
 *
 * El gating per register_type SIGUE vivo en la página dinámica
 * /client-portal/registros/[tipo] (banner inline "no aplica a su categoría"
 * + acciones disabled), que NO es redirect · el 4º test lo cubre.
 *
 * Dev endpoint /api/v1/_dev/set-test-project-category permite cambiar el
 * tier del test project E2E sin invocar el heavy seed-conformidad-ready.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

test.use({ viewport: { width: 1280, height: 800 } });

async function setTestProjectCategory(
  request: import("@playwright/test").APIRequestContext,
  tier: "BASICA" | "MEDIA" | "ALTA",
): Promise<void> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/set-test-project-category?tier=${tier}`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/set-test-project-category devolvió ${res.status()} para tier ${tier}`,
    );
  }
}

test.describe.serial(
  "FASE 12.A · client-portal category gating · 1.C.C.C cierre",
  () => {
    // Restaura categoría=ALTA tras la suite para no afectar otros specs (ej.
    // fase_11/01-live-records.spec.ts asume test client en ALTA · 26 cards).
    test.afterAll(async ({ request }) => {
      await setTestProjectCategory(request, "ALTA");
    });

    // OBSOLETO (1.D.F.bis.III.B): el índice /client-portal/registros ya NO
    // muestra el grid de cards por categoría · ahora redirige a /tasks. El
    // conteo de cards por tier (17/24/26) y el subtitle "cobertura N bloques"
    // dejaron de existir en el portal cliente. El gating per-tipo se conserva
    // en la página dinámica [tipo] (cubierta por el 4º test). El redirect está
    // cubierto en fase_30/client/cliente_registros_redirect_tasks.spec.ts.
    test.skip(
      "BÁSICA · subset reducido (índice obsoleto · redirige a /tasks)",
      async () => {},
    );
    test.skip(
      "MEDIA · subset intermedio (índice obsoleto · redirige a /tasks)",
      async () => {},
    );
    test.skip(
      "ALTA · 26 cards (índice obsoleto · redirige a /tasks)",
      async () => {},
    );

    test("[tipo] banner inline si register_type no aplica a la categoría", async ({
      page,
      request,
    }) => {
      // Cambiar a BÁSICA · navegar a E-318 (ALTA-only) directamente · verificar
      // que el banner inline informativo se muestra y la tabla está oculta.
      await setTestProjectCategory(request, "BASICA");
      await loginAsClient(page);
      await page.goto("/client-portal/registros/E-318");

      // Header sigue mostrándose (el registro existe, solo no aplica).
      await expect(
        page.getByRole("heading", { name: /DRP|continuidad/i }),
      ).toBeVisible({ timeout: 10_000 });

      // Banner inline visible con la categoría actual. El copy real intercala
      // un <TooltipENS term="ENS" /> (icono de ayuda, NO la palabra "ENS") entre
      // "categoría" y la categoría → el texto del <p> es
      //   "Este registro (E-318) no es obligatorio para su categoría {icono} BASICA."
      // Por eso afirmamos sobre el párrafo del banner (anclado por su texto de
      // cabecera) y comprobamos que CONTIENE la categoría, en vez de un único
      // regex que cruce el icono. Source-of-truth:
      // app/(client-portal)/client-portal/registros/[tipo]/page.tsx (notApplicable).
      const gateBanner = page.getByText(/no es obligatorio para su categoría/i);
      await expect(gateBanner).toBeVisible({ timeout: 10_000 });
      await expect(gateBanner).toContainText(/BASICA/i);

      // Botón "Volver al dashboard" presente en el banner.
      await expect(
        page.getByRole("link", { name: /Volver al dashboard/i }).first(),
      ).toBeVisible();

      // El botón "Nueva entrada" está disabled (pointer-events-none aplica al
      // contenedor de actions cuando notApplicable).
      const nuevaBtn = page.getByRole("button", { name: /Nueva entrada/i });
      // Verifica que el contenedor padre tiene `pointer-events-none` aplicado.
      const containerHasGate = await nuevaBtn.evaluate((el) => {
        const parent = el.closest('div[class*="pointer-events-none"]');
        return parent !== null;
      });
      expect(containerHasGate).toBeTruthy();
    });
  },
);
