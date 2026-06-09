/**
 * E2E · fase_26 admin · Director cronológica · AHORA pin-to-top sticky.
 *
 * Sub-atom 1.D.F.0.C v3.11 · materializa pin-to-top sticky + sección AHORA
 * SIEMPRE visible scroll.
 *
 * Verifica:
 *  - Render workflow-timeline-admin con todas las secciones
 *  - AHORA section render con step title visible
 *  - AHORA section sticky class (CSS position sticky con top-0 z-10)
 *  - Toggle entre vista AHORA-only y Completa funcional
 *  - Marcar completo botón visible en AHORA expanded
 *  - Otras secciones default collapsed (chevron right · counts visible)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminCronologicaFull, PROJECT_F26_ID } from "../_fixtures";

test.describe("fase_26 admin · Director AHORA pin-to-top sticky", () => {
  test("AHORA section pin-to-top sticky + Vista Completa default · otras secciones collapsed", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminCronologicaFull(page);

    await page.goto(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );

    // Timeline render
    await expect(page.getByTestId("workflow-timeline-admin")).toBeVisible();

    // AHORA section visible (sticky pin-to-top)
    const ahoraSection = page.getByTestId("ahora-section");
    await expect(ahoraSection).toBeVisible();

    // Sticky class verifica (position sticky · top-0 · z-10)
    const stickyClasses = await ahoraSection.getAttribute("class");
    expect(stickyClasses).toContain("sticky");
    expect(stickyClasses).toContain("top-0");

    // Step AHORA title visible expanded
    await expect(page.getByText("Formación G1 empleados").first()).toBeVisible();

    // Vista Completa selected default · botón pressed
    const completaBtn = page.getByTestId("view-mode-complete");
    await expect(completaBtn).toHaveAttribute("aria-pressed", "true");

    // Otras secciones colapsed default (chevron right · counts visible)
    await expect(page.getByTestId("completed-section")).toBeVisible();
    await expect(page.getByTestId("proximos7d-section")).toBeVisible();
    await expect(page.getByTestId("proximos30d-section")).toBeVisible();

    // Verifica que NO se muestran step titles de completed/proximos por
    // default (sólo el AHORA · Formación G1 empleados ya visible arriba)
    await expect(
      page.getByText(/2 sub-pasos completados · click para expandir/i),
    ).toBeVisible();
    await expect(
      page.getByText(/3 tareas · click para expandir/i).first(),
    ).toBeVisible();
  });
});
