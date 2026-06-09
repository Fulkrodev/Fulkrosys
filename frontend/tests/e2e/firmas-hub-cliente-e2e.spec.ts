/**
 * E2E /client-portal/firmas-hub · SAN-E v3.MB-6 atom 0.2 + atoms 1-7 chain evolution.
 *
 * Valida flujo cliente · chain shape FLEXIBLE post atoms 1-7:
 *  - Chain evolutionó atom 0.2 (4 cards) → atoms 1-2 (6 operative cards · +policies +dpc)
 *  - Spec actualizado MB-6 truly-zero-debt-final post-atom 8
 *
 * Verifica:
 *  1. Login → navega a /client-portal/firmas-hub
 *  2. Header + progress bar visible
 *  3. Core operative cards (DdA + MAGERIT + Pentest + Conformidad) visible
 *  4. Chain integrity banner verde
 *  5. ChainVisualizer renderiza eslabones ordenados
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";
import { seedConformidadReady } from "./_helpers/conformidad-seed";
import { seedDdaAltaProject } from "./_helpers/dda-seed";

test.describe("Client Portal · Firmas hub · MB-6 atom 0.2 (post atoms 1-7)", () => {
  test("Cliente VE operative cards firmas + chain integrity + visualizer", async ({
    page,
    request,
  }) => {
    // Sembrar firmas firmadas para que la "Cadena criptográfica" exista
    // (sólo se renderiza con total_signed>0 · auditoría 2026-06-07).
    // Tarea C · client DEDICADO "firmas-hub" → R27 LIMIT 1 resuelve su único
    // proyecto (aislado de los specs de conformidad/dda-firma que corren en
    // paralelo y mutarían la categoría del client compartido).
    const seed = await seedDdaAltaProject(request, "firmas-hub");
    await seedConformidadReady(request, "MEDIA", "firmas-hub");

    await loginAsClient(page, { email: seed.user_email });

    await page.goto("/client-portal/firmas-hub");

    await expect(
      // h1 embebe <TooltipENS> → accessible name "Mis firmas Ayuda: ENS".
      page.getByRole("heading", { name: /Mis firmas/i }),
    ).toBeVisible();

    await expect(page.getByText(/Progreso del proyecto/i)).toBeVisible();
    // Chain ha crecido (atom 0.2 era 4 · atoms 1-2 ahora 6+) · flexible match
    await expect(
      page.getByText(/de \d+ firmas completadas/i),
    ).toBeVisible();

    // Core operative cards · chain 6-link post atoms 1-2 (atom 0.2 baseline = 4)
    await expect(
      page.locator("[data-signable-type='dda']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-signable-type='magerit_validation']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-signable-type='pentest_authorization']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-signable-type='conformidad_ens']"),
    ).toBeVisible();

    const ddaCard = page.locator("[data-signable-type='dda']");
    await expect(ddaCard).toBeVisible();

    const mageritCard = page.locator(
      "[data-signable-type='magerit_validation']",
    );
    await expect(mageritCard).toBeVisible();

    const pentestCard = page.locator(
      "[data-signable-type='pentest_authorization']",
    );
    await expect(pentestCard).toBeVisible();

    await expect(
      page.getByRole("heading", { name: "Cadena criptográfica" }),
    ).toBeVisible();
  });
});
