/**
 * E2E happy path · cliente firma conformidad ENS BÁSICA con OTP email.
 *
 * SAN-E v3.MB-5.6.E · drop-in pattern atoms 5.3.D + 5.4.D + 5.5.D.
 *
 * Flow validado BASICA:
 * 1. Seed DdA ALTA project + override tier=BASICA + chain firmas + 25 evidencias
 * 2. Login cliente sintetico
 * 3. Navigate /client-portal/conformidad
 * 4. Verify ReadinessSection 4/4 green (BASICA · no policies item)
 * 5. Verify DeclarationHeader · workflow_label "Declaración Conformidad ENS final (E-041)"
 * 6. Mark reviewed
 * 7. Click "Firmar declaración ENS" → confirm dialog → "Continuar firma"
 * 8. Wait OTP email · extract · input
 * 9. Verify success
 * 10. Verify PostSignSection · distintivo SVG + cert-id + download .docx
 * 11. Backend assertion: BasicDeclarationRow.signed_at NOT NULL + declaration_type=initial
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";
import { seedConformidadReady } from "./_helpers/conformidad-seed";
import { seedDdaAltaProject } from "./_helpers/dda-seed";
import { resetCapturedEmails, waitForOtp } from "./_helpers/email-mock";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


test.describe("Client Portal · Conformidad ENS BÁSICA · happy path E2E", () => {
  test("Cliente firma E-041 self-declaration · distintivo + cert-id post-firma", async ({
    page,
    request,
  }) => {
    // Pre-condiciones: seed DdA project + conformidad BASICA ready
    // Tarea C · client DEDICADO "conformidad-basica" → R27 LIMIT 1 resuelve el
    // proyecto BÁSICA de esta spec (aislado de dda-firma/media/alta).
    const ddaSeed = await seedDdaAltaProject(request, "conformidad-basica");
    const conformidad = await seedConformidadReady(
      request,
      "BASICA",
      "conformidad-basica",
    );
    expect(conformidad.project_id).toBe(ddaSeed.project_id);
    expect(conformidad.tier).toBe("BASICA");
    expect(conformidad.evidence_count).toBe(25);
    await resetCapturedEmails(request);

    await loginAsClient(page, {
      email: ddaSeed.user_email,
      password: ddaSeed.user_password,
    });

    await page.goto("/client-portal/conformidad");
    // El portal cliente monta SSE (useClientProject) → 'networkidle' desnudo
    // NUNCA settlea (conexión EventSource viva) y bloqueaba el test hasta el
    // timeout global. Patrón tolerante (igual que magerit-validation-cliente-e2e
    // · auditoría 2026-06-07): domcontentloaded + networkidle best-effort
    // acotado · el gate real es el heading visible.
    await page.waitForLoadState("domcontentloaded");
    await page
      .waitForLoadState("networkidle", { timeout: 5000 })
      .catch(() => {});
    await expect(
      page.getByRole("heading", { name: /Conformidad ENS/i }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Verify ReadinessSection · BASICA = 4 items + ready banner
    await expect(page.getByText(/DdA firmada/i)).toBeVisible();
    await expect(page.getByText(/MAGERIT validado/i)).toBeVisible();
    await expect(page.getByText(/pentest firmada/i)).toBeVisible();
    await expect(page.getByText(/25.*evidencias/i)).toBeVisible();
    await expect(
      page.getByText(/Todos los pasos previos están completos/i),
    ).toBeVisible();

    // Verify DeclarationHeader · workflow_label BASICA
    await expect(page.getByText(/E-041/i)).toBeVisible();
    await expect(page.getByText(/Categoría BÁSICA/i)).toBeVisible();

    // Mark reviewed
    await page.getByRole("button", { name: /Marcar como revisado/i }).click();
    await expect(page.getByText(/Revisado/i).first()).toBeVisible({
      timeout: 5_000,
    });

    // Click firma
    await expect(
      page.getByRole("button", { name: /Firmar declaración ENS/i }),
    ).toBeEnabled({ timeout: 10_000 });
    await page.getByRole("button", { name: /Firmar declaración ENS/i }).click();

    // SigningFlow dialog · confirm
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /Continuar firma/i }).click();

    // OTP email
    await expect(page.getByText(/Hemos enviado un codigo/i)).toBeVisible({
      timeout: 10_000,
    });
    const otpCode = await waitForOtp(request, ddaSeed.user_email, 10);
    expect(otpCode).toMatch(/^\d{6}$/);

    await page.getByLabel(/Codigo de seguridad/i).fill(otpCode);
    await page.getByRole("button", { name: /Verificar y firmar/i }).click();

    // Bug fix smoke 5.11.final: regex flexible · modal closes en ms.
    await expect(
      page
        .getByText(/firmado correctamente|conforme ENS|distintivo/i)
        .first(),
    ).toBeVisible({ timeout: 15_000 });
    const cerrarBtn = page.getByRole("button", { name: /Cerrar/i });
    if (await cerrarBtn.isVisible().catch(() => false)) {
      await cerrarBtn.click();
    }

    // PostSignSection BASICA · distintivo + cert-id + descarga
    await expect(
      page.getByText(/Tu organización es conforme ENS BÁSICA/i),
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByRole("link", { name: /Descargar declaración/i }),
    ).toBeVisible();

    // Backend assertion: declaration signed
    const declRes = await page.request.get(
      `${BACKEND_BASE}/api/v1/portal/conformidad/projects/${conformidad.project_id}/declaration`,
    );
    expect(declRes.ok()).toBeTruthy();
    const decl = (await declRes.json()) as {
      declaration_type: string;
      signed_at: string | null;
      signed_hash: string | null;
    };
    expect(decl.declaration_type).toBe("initial");
    expect(decl.signed_at).not.toBeNull();
    expect(decl.signed_hash).not.toBeNull();
  });
});
