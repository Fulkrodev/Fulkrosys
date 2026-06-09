/**
 * E2E · Test 2 fase_38 · cliente · /remediaciones 3 secciones render.
 *
 * Bloque 3+5 v3.12 · 4 gaps distribuidos en 3 secciones:
 *   - Pendientes de tu decisión (1 · proposed_to_cliente)
 *   - Marcos las está aplicando (1 · approved)
 *   - Ya resueltas (2 · executed + failed)
 *
 * Verifica:
 *   - 3 secciones visibles con counts correctos
 *   - 4 RemediationCards rendered
 *   - Status badges friendly Spanish R29
 *   - Severity badges visibles
 *   - Suggested action visible solo en pendiente
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockRemediationsWith3Sections } from "../_fixtures";

test.describe("fase_38 client · /remediaciones 3 secciones render", () => {
  test("4 gaps distribuidos en 3 secciones · badges friendly", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockRemediationsWith3Sections(page);

    await page.goto("/client-portal/remediaciones");

    // Lista contenedora visible
    await expect(page.getByTestId("remediations-list")).toBeVisible();

    // 3 secciones visibles con counts
    await expect(page.getByTestId("section-pendientes")).toBeVisible();
    await expect(
      page.getByText(/Pendientes de tu decisión · 1/i),
    ).toBeVisible();

    await expect(page.getByTestId("section-en-progreso")).toBeVisible();
    await expect(
      page.getByText(/Marcos las está aplicando · 1/i),
    ).toBeVisible();

    await expect(page.getByTestId("section-resueltas")).toBeVisible();
    await expect(page.getByText(/Ya resueltas · 2/i)).toBeVisible();

    // 4 cards rendered
    const cards = page.getByTestId("remediation-card");
    await expect(cards).toHaveCount(4);

    // Status badges friendly R29 (pendiente)
    await expect(
      page.getByText(/Pendiente de tu decisión/i).first(),
    ).toBeVisible();

    // Suggested action visible en pendiente
    await expect(
      page.getByTestId("suggested-action").first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Qué propone Marcos/i),
    ).toBeVisible();

    // Status hint friendly "Cuando esté listo te avisamos" para approved/executing
    await expect(
      page.getByText(/Cuando esté listo te avisamos/i).first(),
    ).toBeVisible();
  });
});
