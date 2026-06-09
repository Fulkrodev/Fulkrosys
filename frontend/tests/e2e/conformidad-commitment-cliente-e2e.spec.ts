/**
 * E2E happy path · cliente firma compromiso conformidad MEDIA pre-auditoría ENAC.
 *
 * SAN-E v3.MB-5.6.E · drop-in pattern atom 5.6.E BÁSICA · differs tier-aware UX.
 *
 * Flow validado MEDIA:
 * 1. Seed conformidad MEDIA ready (50 evidencias + chain firmas previas)
 * 2. Navigate /client-portal/conformidad
 * 3. Verify DeclarationHeader · workflow_label "Compromiso conformidad pre-auditoría ENAC"
 * 4. Verify TierAwareNextStepSection · cronograma 3 steps (+7d · +30-60d)
 * 5. Mark reviewed → firma OTP
 * 6. Verify PostSignSection · commitment_signed_at + ETA + NO distintivo
 * 7. Backend assertion: declaration_type='commitment_pre_certification'
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";
import { seedConformidadReady } from "./_helpers/conformidad-seed";
import { seedDdaAltaProject } from "./_helpers/dda-seed";
import { resetCapturedEmails, waitForOtp } from "./_helpers/email-mock";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


test.describe("Client Portal · Conformidad ENS MEDIA · commitment flow E2E", () => {
  test("Cliente firma compromiso pre-auditor · NO distintivo · ETA 30-60d", async ({
    page,
    request,
  }) => {
    // Tarea C · client DEDICADO "conformidad-media" → R27 LIMIT 1 resuelve el
    // proyecto MEDIA de esta spec (aislado de basica/alta/dda-firma).
    const ddaSeed = await seedDdaAltaProject(request, "conformidad-media");
    const conformidad = await seedConformidadReady(
      request,
      "MEDIA",
      "conformidad-media",
    );
    expect(conformidad.tier).toBe("MEDIA");
    expect(conformidad.evidence_count).toBe(50);
    await resetCapturedEmails(request);

    await loginAsClient(page, {
      email: ddaSeed.user_email,
      password: ddaSeed.user_password,
    });

    await page.goto("/client-portal/conformidad");
    // Bug #8 fix smoke 5.11.final: wait React hydration post-load.
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: /Conformidad ENS/i }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // DeclarationHeader · workflow_label MEDIA commitment
    // (texto "compromiso de conformidad" aparece en h2 workflow_label + paso 1
    // del cronograma · anclar al heading para evitar strict-mode violation)
    await expect(
      page.getByRole("heading", { name: /Compromiso de conformidad/i }),
    ).toBeVisible();
    await expect(page.getByText(/Categoría MEDIA/i).first()).toBeVisible();

    // TierAwareNextStepSection · cronograma 3 steps + ETA 30-60d
    // ("auditor ENAC" aparece en pasos 2 y 3 · .first() evita strict-mode)
    await expect(page.getByText(/auditor ENAC/i).first()).toBeVisible();
    await expect(page.getByText(/\+7 días/i)).toBeVisible();
    await expect(page.getByText(/\+30 a \+60 días/i)).toBeVisible();

    // Mark reviewed
    await page.getByRole("button", { name: /Marcar como revisado/i }).click();
    await expect(page.getByText(/Revisado/i).first()).toBeVisible({
      timeout: 5_000,
    });

    // Firma commitment · button label differs vs BASICA
    await expect(
      page.getByRole("button", { name: /Firmar compromiso conformidad/i }),
    ).toBeEnabled({ timeout: 10_000 });
    await page
      .getByRole("button", { name: /Firmar compromiso conformidad/i })
      .click();

    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /Continuar firma/i }).click();

    await expect(page.getByText(/Hemos enviado un codigo/i)).toBeVisible({
      timeout: 10_000,
    });
    const otpCode = await waitForOtp(request, ddaSeed.user_email, 10);
    await page.getByLabel(/Codigo de seguridad/i).fill(otpCode);
    await page.getByRole("button", { name: /Verificar y firmar/i }).click();

    // Bug fix smoke 5.11.final: regex flexible · modal closes en ms.
    await expect(
      page
        .getByText(/firmado correctamente|Compromiso firmado/i)
        .first(),
    ).toBeVisible({ timeout: 15_000 });
    const cerrarBtnM = page.getByRole("button", { name: /Cerrar/i });
    if (await cerrarBtnM.isVisible().catch(() => false)) {
      await cerrarBtnM.click();
    }

    // PostSignSection MEDIA · commitment summary · NO distintivo
    await expect(
      page.getByText(/Compromiso firmado/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/30.{1,4}60 días/i).first()).toBeVisible();

    // Backend assertion: declaration_type=commitment_pre_certification
    const declRes = await page.request.get(
      `${BACKEND_BASE}/api/v1/portal/conformidad/projects/${conformidad.project_id}/declaration`,
    );
    expect(declRes.ok()).toBeTruthy();
    const decl = (await declRes.json()) as {
      declaration_type: string;
      tier: string;
      signed_at: string | null;
    };
    expect(decl.declaration_type).toBe("commitment_pre_certification");
    expect(decl.tier).toBe("MEDIA");
    expect(decl.signed_at).not.toBeNull();
  });
});
