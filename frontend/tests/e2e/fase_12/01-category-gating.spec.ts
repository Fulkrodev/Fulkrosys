/**
 * FASE 12.A · Sub-atom 1.C.C.C · Category gating cliente portal · CIERRE 1.C.C.
 *
 * ACTUALIZACIÓN (sub-atom 1.D.F.bis.III.B v3.11 · modelo indispensable-only):
 * el índice /client-portal/registros ya NO muestra el grid de cards por
 * categoría · ahora REDIRIGE a /client-portal/tasks (el cliente NO gestiona
 * registros vivos; Marcos los opera en admin). El subtitle "cobertura N
 * bloques" desapareció, y con él los 3 tests de conteo de cards por tier
 * (eran placeholders vacíos · borrados). La cobertura del redirect está en
 * fase_30/client/cliente_registros_redirect_tasks.spec.ts.
 *
 * El gating per register_type SIGUE vivo en la página dinámica
 * /client-portal/registros/[tipo] (banner inline "no aplica a su categoría"
 * + acciones disabled), que NO es redirect · lo cubre el test de abajo.
 *
 * El test usa el cliente `secondary` aislado (ver ensureSecondaryClient) en
 * vez de mutar con _dev/set-test-project-category el cliente compartido, cuyo
 * proyecto visible en el portal depende de lo que hayan sembrado otros specs.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

test.use({ viewport: { width: 1280, height: 800 } });

// Identidad AISLADA: el cliente de test COMPARTIDO (B00000000) deja de ser
// determinista en cuanto sim-medio firma un contrato (contract_signing_flow
// crea el proyecto "ENS · <empresa>" para ese mismo cliente). El portal resuelve
// por R27 el proyecto MÁS RECIENTE (ORDER BY created_at DESC LIMIT 1), así que
// `_dev/set-test-project-category` mutaba un proyecto que el portal ya no
// mostraba (medido: banner "MEDIA" tras fijar BASICA). El cliente `secondary`
// (B00000001) tiene un único proyecto MEDIA que ningún spec toca → la categoría
// que ve el portal es la que sembramos, sin mutar estado compartido.
const SECONDARY_EMAIL = "test-client-e2e-secondary@example.com";

async function ensureSecondaryClient(
  request: import("@playwright/test").APIRequestContext,
): Promise<void> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/create-test-client?secondary=true`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/create-test-client?secondary=true devolvió ${res.status()}`,
    );
  }
}

test.describe.serial(
  "FASE 12.A · client-portal category gating · 1.C.C.C cierre",
  () => {
    // (El índice /client-portal/registros con conteo de cards por tier se
    // retiró en 1.D.F.bis.III.B · redirige a /tasks, cubierto por
    // fase_30/client/cliente_registros_redirect_tasks.spec.ts. El gating
    // per-tipo sigue vivo en la página dinámica [tipo]: es lo que se prueba.)
    test("[tipo] banner inline si register_type no aplica a la categoría", async ({
      page,
      request,
    }) => {
      // Cliente aislado en MEDIA · navegar a E-318 (ALTA-only) directamente ·
      // verificar que el banner inline informativo se muestra y la tabla está
      // oculta.
      await ensureSecondaryClient(request);
      await loginAsClient(page, { email: SECONDARY_EMAIL });

      // Precondición explícita: el proyecto que resuelve el portal (R27) es
      // MEDIA. Si alguien lo cambia, que falle aquí con un mensaje claro y no
      // en la aserción del banner.
      const projRes = await page.request.get(
        `${BACKEND_BASE}/api/v1/client-portal/project`,
      );
      expect(projRes.ok()).toBeTruthy();
      const proj = (await projRes.json()) as { categoria_objetivo: string };
      expect(proj.categoria_objetivo, "categoría del proyecto del portal").toBe(
        "MEDIA",
      );

      await page.goto("/client-portal/registros/E-318");

      // Header sigue mostrándose (el registro existe, solo no aplica).
      await expect(
        page.getByRole("heading", { name: /DRP|continuidad/i }),
      ).toBeVisible({ timeout: 10_000 });

      // Banner inline visible con la categoría actual. El copy real intercala
      // un <TooltipENS term="ENS" /> (icono de ayuda, NO la palabra "ENS") entre
      // "categoría" y la categoría → el texto del <p> es
      //   "Este registro (E-318) no es obligatorio para su categoría {icono} MEDIA."
      // Por eso afirmamos sobre el párrafo del banner (anclado por su texto de
      // cabecera) y comprobamos que CONTIENE la categoría, en vez de un único
      // regex que cruce el icono. Source-of-truth:
      // app/(client-portal)/client-portal/registros/[tipo]/page.tsx (notApplicable).
      const gateBanner = page.getByText(/no es obligatorio para su categoría/i);
      await expect(gateBanner).toBeVisible({ timeout: 10_000 });
      await expect(gateBanner).toContainText(/MEDIA/);

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
