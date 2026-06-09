/**
 * FASE 11.A · Sub-atom 1.C.B fase 5 · Registros vivos cliente portal E2E.
 *
 * Cobertura workflow CRUD completo (Plan v3.3 §1.C.B fase 5):
 *   1. Dashboard /client-portal/registros · 26 cards · 9 bloques (BLOQUE_LABELS)
 *   2. Crear entrada E-303 empleado · Dialog dinámico FIELD_CONFIGS · persiste
 *   3. Archivar entrada · Sheet detail · cambia status · filter Archivadas
 *   4. Export CSV E-308 · triggerBlobDownload anchor click · filename match
 *   5. register_type inválido E-999 · notFound() · not-found.tsx renderizada
 *
 * Tests 2 y 3 comparten state vía RUN_ID único por ejecución → `describe.serial`.
 * Cliente sintético `test-client-e2e@example.com` + project demo via globalSetup
 * (/api/v1/_dev/create-test-client · idempotente).
 *
 * Ver: ADR-013 (separación portales), OPS-034 (discriminator + FIELD_CONFIGS),
 * OPS-038 (FK columns audit), OPS-040 (auto-population non-invasive).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

// Sufijo único por run: evita colisión con entradas de runs previos en el
// mismo cliente E2E (no hay cleanup entre runs · dev endpoint idempotente).
const RUN_ID = Date.now().toString(36);
const EMPLEADO_NAME = `Test E2E Empleado ${RUN_ID}`;

test.describe.serial("FASE 11.A · client-portal registros vivos · 1.C.B fase 5", () => {
  // SKIP: feature eliminada (dashboard índice /client-portal/registros con grid
  // de 26 cards + grouping por 9 bloques + heading "Registros operativos ENS" +
  // subtitle "cobertura N bloques"). Sub-atom 1.D.F.bis.III.B v3.11 modelo
  // "indispensable-cliente-only": el índice ahora REDIRIGE a /client-portal/tasks
  // (el cliente NO gestiona registros vivos · Marcos los opera en admin). La
  // página real renderiza "Los registros los lleva tu consultor" + redirect.
  // El redirect está cubierto por fase_30/client/cliente_registros_redirect_tasks.
  // Candidata a borrar tras contraste (Marcos). Los tests 2-5 siguen vivos:
  // la página dinámica /client-portal/registros/[tipo] (crear/archivar/exportar/404)
  // NO es redirect y mantiene su funcionalidad accesible por URL directa.
  test.skip("dashboard registros · 26 tipos agrupados en 9 bloques", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/registros");

    await expect(
      page.getByRole("heading", { name: /Registros operativos ENS/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Esperar carga dashboard (texto subtitle sólo aparece tras fetch OK).
    await expect(page.getByText(/cobertura 9 bloques/i)).toBeVisible({
      timeout: 10_000,
    });

    // 26 cards register_type linkadas (E-300..E-325).
    const cards = page.locator('a[href^="/client-portal/registros/E-3"]');
    await expect(cards).toHaveCount(26);

    // 3 headings representativos (verifica grouping BLOQUE_LABELS · sin tildes).
    await expect(page.getByRole("heading", { name: /^Activos$/i })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /^Incidentes$/i }),
    ).toBeVisible();
    // `exact: true` evita colisión con E-323 "Actas Comite SGSI" (h3 card).
    await expect(
      page.getByRole("heading", { name: "Comite SGSI", exact: true }),
    ).toBeVisible();
  });

  test("crear entrada E-303 empleado · aparece en lista", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/registros/E-303");

    // Boton "Nueva entrada" disabled hasta projectId resuelto + records cargados.
    const nuevaBtn = page.getByRole("button", { name: /Nueva entrada/i });
    await expect(nuevaBtn).toBeEnabled({ timeout: 10_000 });
    await nuevaBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByText(/Nueva entrada · E-303/i),
    ).toBeVisible();

    // Fill 6 campos required E-303 (FIELD_CONFIGS · etiquetas exactas).
    await dialog.getByLabel("DNI (hash)").fill(`HASH-E2E-${RUN_ID}`);
    await dialog.getByLabel("Nombre completo").fill(EMPLEADO_NAME);
    await dialog
      .getByLabel("Email corporativo")
      .fill(`e2e+${RUN_ID}@ejemplo.test`);
    await dialog.getByLabel("Rol principal").fill("QA Engineer");
    await dialog.getByLabel("Departamento").fill("Engineering");
    // "Fecha alta" (substring match): label real es "Fecha alta*" (required
    // asterisk). Substring match es único · "Fecha baja" no contiene "Fecha alta".
    await dialog.getByLabel("Fecha alta").fill("2026-01-15");

    await dialog.getByRole("button", { name: /Crear entrada/i }).click();

    // Dialog cierra (Radix unmounts content cuando open=false).
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });

    // Reload para evitar carrera con el refresh interno del hook · valida
    // persistencia backend de forma robusta (POST commit ya verificado).
    await page.reload();

    // Row aparece con el nombre que pusimos (campo summarize → nombre_completo).
    await expect(page.getByText(EMPLEADO_NAME).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("archivar entrada · Sheet detail · filter Archivadas", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/registros/E-303");

    // Entrada de test previo debe estar visible (filter "Activas" default).
    await expect(page.getByText(EMPLEADO_NAME).first()).toBeVisible({
      timeout: 10_000,
    });

    // Click row · abre Sheet drawer (Radix Dialog primitive con role="dialog").
    await page.getByText(EMPLEADO_NAME).first().click();

    // El Sheet es el último dialog renderizado (no hay Create abierto aquí).
    const sheet = page.locator('[role="dialog"]').last();
    await expect(sheet).toBeVisible();

    await sheet.getByRole("button", { name: /Archivar entrada/i }).click();

    // Sheet cierra tras archive successful (LiveRecordDetail.handleArchive).
    await expect(sheet).not.toBeVisible({ timeout: 10_000 });

    // Reload por consistencia con test 2 (refresh interno del hook puede
    // tener race condition · forzamos fresh fetch para validar persistencia).
    await page.reload();

    // Cambiar a filter Archivadas · entry debe aparecer.
    await page.getByRole("button", { name: /^Archivadas$/ }).click();
    await expect(page.getByText(EMPLEADO_NAME).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("export CSV E-308 · download triggered", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/registros/E-308");

    // Esperar projectId loaded → boton CSV enabled.
    const csvBtn = page.getByRole("button", { name: /^CSV$/ });
    await expect(csvBtn).toBeEnabled({ timeout: 10_000 });

    const downloadPromise = page.waitForEvent("download", { timeout: 15_000 });
    await csvBtn.click();
    const download = await downloadPromise;

    // Filename: `${registerType}_${projectId}.csv` (triggerBlobDownload).
    expect(download.suggestedFilename()).toMatch(/^E-308_.*\.csv$/i);
  });

  test("register_type invalido E-999 · 404 renderizado", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/registros/E-999", { waitUntil: "load" });

    // not-found.tsx renderiza heading "Página no encontrada" + paragraph "404".
    // Next.js 14 notFound() en client component renderiza la página 404 con
    // status 200 tras hydration (no 404 a nivel HTTP). Validamos el render UI.
    await expect(
      page.getByRole("heading", { name: /no encontrada/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
