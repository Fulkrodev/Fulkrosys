/**
 * E2E happy path · cliente firma DdA ALTA con OTP email · 73 medidas.
 *
 * SAN-E v3.MB-5.3.D · primer atom frontend cliente E2E real production-ready.
 *
 * Pre-condiciones:
 * - Backend running en BACKEND_BASE (default http://localhost:8000)
 *   con app_env != "production" (settings.is_production = false)
 * - Frontend served (Playwright webServer config: next start -p 3100)
 * - Email backend = "mock" (default settings.email_backend) · captura
 *   in-memory accesible vía /api/v1/_dev/captured-emails
 *
 * Flow validado:
 * 1. Seed DdA ALTA project + reset captured emails (test isolation)
 * 2. Login cliente sintético via /client-portal/login
 * 3. Navigate /client-portal/dda · verify summary 73 medidas + ALTA
 * 4. Bulk mark all entries as 'revisada_ok' via portal API (cliente click
 *    73 botones es lento · usamos API directa para test focus en firma flow)
 * 5. Refresh page · verify "lista para firmar" banner
 * 6. Click "Firmar Declaracion de Aplicabilidad"
 * 7. Confirm modal · click "Continuar firma"
 * 8. Wait OTP email captured · extract 6 digits
 * 9. Input OTP · click "Verificar y firmar"
 * 10. Verify success · "Documento firmado correctamente"
 * 11. Close modal · verify summary "Última versión firmada"
 * 12. Backend assertion · chain integrity intacta vía admin endpoint
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";
import { resetCapturedEmails, waitForOtp } from "./_helpers/email-mock";
import { seedDdaAltaProject } from "./_helpers/dda-seed";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


test.describe("Client Portal · DdA · Firma E2E ALTA happy path", () => {
  test("Cliente revisa 73 medidas · firma DdA con OTP · chain integrity intact", async ({
    page,
    request,
  }) => {
    // ────── Pre-condiciones · seed + reset ──────
    // Tarea C · client DEDICADO "dda-firma" → R27 LIMIT 1 resuelve SIEMPRE el
    // proyecto ALTA de esta spec (sin race cross-spec con las conformidad).
    const seed = await seedDdaAltaProject(request, "dda-firma");
    expect(seed.dda_entries_count).toBeGreaterThanOrEqual(70);
    expect(seed.categoria_objetivo).toBe("ALTA");
    await resetCapturedEmails(request);

    // ────── Login cliente sintético ──────
    await loginAsClient(page, {
      email: seed.user_email,
      password: seed.user_password,
    });

    // ────── Navigate /client-portal/dda + verify summary ──────
    await page.goto("/client-portal/dda");
    // Esperar render client-side (goto vuelve en 'load' antes del data fetch).
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: /Declaración de Aplicabilidad/i }).first(),
    ).toBeVisible();
    await expect(page.getByText(/Categoría Alta/i).first()).toBeVisible({
      timeout: 10_000,
    });

    // ────── Modelo cliente v3.11 "indispensable-cliente-only" ──────
    // El cliente NO revisa medida-por-medida (decisión técnica de Marcos en
    // M03 admin). El seed deja la DdA CONGELADA por Marcos (aprobado_por) y sin
    // firmar → ready_for_final_sign=true → DdaSignFinalButton se monta directo.
    // (El spec viejo testeaba la UI obsoleta DdaMeasureRow "Ver detalle" + un
    // bulk-review por API · ambos retirados con el rediseño · ver audit DdA.)
    const signButton = page.getByRole("button", {
      name: /Firmar Declaraci[oó]n de Aplicabilidad/i,
    });
    await expect(signButton).toBeEnabled({ timeout: 10_000 });

    // ────── Click firma · confirm dialog ──────
    await signButton.click();

    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /Continuar firma/i }).click();

    // ────── Wait OTP email · extract 6 digits ──────
    await expect(page.getByText(/Hemos enviado un codigo/i)).toBeVisible({
      timeout: 10_000,
    });
    const otpCode = await waitForOtp(request, seed.user_email, 10);
    expect(otpCode).toMatch(/^\d{6}$/);

    // ────── Input OTP · sign ──────
    await page.getByLabel(/Codigo de seguridad/i).fill(otpCode);
    await page.getByRole("button", { name: /Verificar y firmar/i }).click();

    // ────── Verify success ──────
    // SigningFlow modal renders "Documento firmado correctamente" pero parent
    // setSigningOpen(false) en onSuccess cierra modal en ms · race contra Playwright.
    // Fix smoke 5.11.final: regex flexible cubre modal text + post-firma summary.
    await expect(
      page
        .getByText(/firmado correctamente|Última versión firmada/i)
        .first(),
    ).toBeVisible({ timeout: 15_000 });

    // ────── Close modal si aún abierto · verify summary updated ──────
    const cerrarButton = page.getByRole("button", { name: /Cerrar/i });
    if (await cerrarButton.isVisible().catch(() => false)) {
      await cerrarButton.click();
    }
    await expect(page.getByText(/Última versión firmada/i)).toBeVisible({
      timeout: 5_000,
    });

    // ────── Backend assertion · chain integrity ──────
    const adminContext = await test.info().project.use.contextOptions;
    void adminContext; // unused but keeps fixture init explicit

    const adminCtx = await page.context().browser()?.newContext();
    if (!adminCtx) {
      throw new Error("Could not create admin context for chain check");
    }
    try {
      await loginAsMarcos(adminCtx);
      const adminPage = await adminCtx.newPage();
      const chainRes = await adminPage.request.get(
        `${BACKEND_BASE}/api/v1/admin/signing/projects/${seed.project_id}/chain-integrity`,
      );
      expect(chainRes.ok()).toBeTruthy();
      const chain = (await chainRes.json()) as {
        chain_valid: boolean;
        broken_links: unknown[];
        total_signatures: number;
      };
      expect(chain.chain_valid).toBe(true);
      expect(chain.broken_links).toEqual([]);
      expect(chain.total_signatures).toBeGreaterThanOrEqual(1);
    } finally {
      await adminCtx.close();
    }
  });
});
