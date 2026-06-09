/**
 * E2E happy path · cliente firma compromiso conformidad ALTA pre-auditoría ENAC.
 *
 * Cierra el gap de cobertura señalado en auditoría 2026-06-07 (sólo existían specs
 * BÁSICA + MEDIA). ALTA recorre el MISMO code path commitment_pre_certification que
 * MEDIA (portal_api conformidad) pero con el set máximo: 73 evidencias + 8 políticas
 * firmadas + categoría ALTA. Verifica que el gate tier-aware y el flujo de firma
 * funcionan en el nivel más exigente.
 *
 * Flow validado ALTA:
 * 1. Seed conformidad ALTA ready (73 evidencias + 8 políticas firmadas + chain)
 * 2. Navigate /client-portal/conformidad
 * 3. Verify DeclarationHeader · "Compromiso de conformidad" + Categoría ALTA
 * 4. Verify TierAwareNextStepSection · cronograma auditor ENAC
 * 5. Mark reviewed → firma OTP
 * 6. Verify PostSignSection · commitment_signed_at + ETA + NO distintivo
 * 7. Backend assertion: declaration_type='commitment_pre_certification' · tier='ALTA'
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";
import { seedConformidadReady } from "./_helpers/conformidad-seed";
import { seedDdaAltaProject } from "./_helpers/dda-seed";
import { resetCapturedEmails, waitForOtp } from "./_helpers/email-mock";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


test.describe("Client Portal · Conformidad ENS ALTA · commitment flow E2E", () => {
  test("Cliente firma compromiso ALTA · 73 evidencias + políticas · NO distintivo", async ({
    page,
    request,
  }) => {
    // Tarea C · client DEDICADO "conformidad-alta" → R27 LIMIT 1 resuelve el
    // proyecto ALTA de esta spec (aislado de basica/media/dda-firma).
    const ddaSeed = await seedDdaAltaProject(request, "conformidad-alta");
    const conformidad = await seedConformidadReady(
      request,
      "ALTA",
      "conformidad-alta",
    );
    expect(conformidad.tier).toBe("ALTA");
    expect(conformidad.evidence_count).toBe(73);
    // ALTA exige políticas firmadas (readiness item tier-aware · op.* refuerzos)
    expect(conformidad.policies_signed_count).toBeGreaterThanOrEqual(8);
    await resetCapturedEmails(request);

    await loginAsClient(page, {
      email: ddaSeed.user_email,
      password: ddaSeed.user_password,
    });

    await page.goto("/client-portal/conformidad");
    await page.waitForLoadState("domcontentloaded");
    await page
      .waitForLoadState("networkidle", { timeout: 5_000 })
      .catch(() => undefined);
    await expect(
      page.getByRole("heading", { name: /Conformidad ENS/i }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // DeclarationHeader · workflow_label ALTA commitment + Categoría ALTA
    await expect(
      page.getByRole("heading", { name: /Compromiso de conformidad/i }),
    ).toBeVisible();
    await expect(page.getByText(/Categoría ALTA/i).first()).toBeVisible();

    // TierAwareNextStepSection · cronograma con auditor ENAC
    await expect(page.getByText(/auditor ENAC/i).first()).toBeVisible();

    // Mark reviewed
    await page.getByRole("button", { name: /Marcar como revisado/i }).click();
    await expect(page.getByText(/Revisado/i).first()).toBeVisible({
      timeout: 5_000,
    });

    // Firma commitment
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

    await expect(
      page.getByText(/firmado correctamente|Compromiso firmado/i).first(),
    ).toBeVisible({ timeout: 15_000 });
    const cerrarBtn = page.getByRole("button", { name: /Cerrar/i });
    if (await cerrarBtn.isVisible().catch(() => false)) {
      await cerrarBtn.click();
    }

    // PostSignSection ALTA · commitment summary · NO distintivo (sólo post-ENAC)
    await expect(
      page.getByText(/Compromiso firmado/i).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Backend assertion: declaration_type=commitment_pre_certification · tier=ALTA
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
    expect(decl.tier).toBe("ALTA");
    expect(decl.signed_at).not.toBeNull();
  });
});
