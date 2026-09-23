/**
 * E2E happy path · cliente firma magerit_validation ALTA.
 *
 * magerit_validation NO está en REQUIRES_STEP_UP_OTP (backend
 * m05_signing/signable_types.py): la firma es directa, sin código por email.
 * El antiguo paso OTP de esta spec esperaba un input que por diseño no existe.
 *
 * SAN-E v3.MB-5.4.D · drop-in pattern atom 5.3.D dda-firma-cliente-e2e.spec.ts.
 *
 * Pre-condiciones: idem atom 5.3.D + seed MAGERIT 8 assets + 12 risks.
 *
 * Flow validado:
 * 1. Seed DdA ALTA project (idempotent reusable) + MAGERIT data + reset emails
 * 2. Login cliente sintético via /client-portal/login
 * 3. Navigate /client-portal/magerit · verify summary 8 assets + 12 risks
 * 4. Bulk mark all assets 'revisada_ok' via portal API (focus en firma flow)
 * 5. Bulk mark all risks 'revisada_ok' via portal API
 * 6. Reload page · verify "Validar inventario MAGERIT" button enabled
 * 7. Click validar · confirm modal · "Continuar firma" (firma directa, sin OTP)
 * 8. Verify toast "MAGERIT validado" + summary "Última versión validada"
 * 9. Backend assertion · chain integrity intact + una firma más que antes
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";
import { seedDdaAltaProject } from "./_helpers/dda-seed";
import { seedMageritAltaData } from "./_helpers/magerit-seed";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


// Cliente DEDICADO (key) · con el cliente compartido, R27 (LIMIT 1 · proyecto
// más reciente) resolvía en el portal OTRO proyecto del mismo cliente (el fijo
// E2E o uno de sim-medio): la página salía con 0 activos y el botón "Validar
// inventario MAGERIT" nunca se montaba. Ese, y no la infra OTP, era el motivo
// del antiguo skip.
const SEED_KEY = "magerit-validation";

test.describe("Client Portal · MAGERIT · Firma validación E2E · ALTA happy path", () => {
  test("Cliente revisa 8 assets + 12 risks · firma magerit_validation · chain integrity intact", async ({
    page,
    request,
  }) => {
    // ────── Pre-condiciones · seed DdA project + MAGERIT data ──────
    const ddaSeed = await seedDdaAltaProject(request, SEED_KEY);
    const magerit = await seedMageritAltaData(request, SEED_KEY);
    expect(magerit.assets_count).toBeGreaterThanOrEqual(8);
    expect(magerit.risks_count).toBeGreaterThanOrEqual(12);
    expect(magerit.project_id).toBe(ddaSeed.project_id);

    // ────── Login cliente sintético ──────
    await loginAsClient(page, {
      email: ddaSeed.user_email,
      password: ddaSeed.user_password,
    });

    // ────── Navigate /client-portal/magerit ──────
    await page.goto("/client-portal/magerit");
    // El portal cliente monta SSE (useClientProject) → 'networkidle' desnudo
    // NUNCA settlea (conexión EventSource viva) y causaba timeout. Patrón
    // tolerante: domcontentloaded + networkidle best-effort acotado · el gate
    // real es el heading visible. (auditoría 2026-06-07)
    await page.waitForLoadState("domcontentloaded");
    await page
      .waitForLoadState("networkidle", { timeout: 5000 })
      .catch(() => {});
    await expect(
      page.getByRole("heading", { name: /MAGERIT/i }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // Bug #9 fix smoke 5.11.final: extract csrf token for POST requests.
    const cookies = await page.context().cookies();
    const csrfToken =
      cookies.find((c) => c.name === "fulkro_csrf")?.value ?? "";

    // ────── Bulk mark all assets 'revisada_ok' via portal API ──────
    const assetsRes = await page.request.get(
      `${BACKEND_BASE}/api/v1/portal/magerit/projects/${magerit.project_id}/assets`,
    );
    expect(assetsRes.ok()).toBeTruthy();
    const assets = (await assetsRes.json()) as Array<{ id: string }>;
    expect(assets.length).toBe(8);

    for (const a of assets) {
      const reviewRes = await page.request.post(
        `${BACKEND_BASE}/api/v1/portal/magerit/assets/${a.id}/review`,
        {
          data: { action: "revisada_ok", note: null },
          headers: { "X-Csrf-Token": csrfToken },
        },
      );
      expect(reviewRes.ok()).toBeTruthy();
    }

    // ────── Bulk mark all risks 'revisada_ok' via portal API ──────
    const risksRes = await page.request.get(
      `${BACKEND_BASE}/api/v1/portal/magerit/projects/${magerit.project_id}/risks`,
    );
    expect(risksRes.ok()).toBeTruthy();
    const risks = (await risksRes.json()) as Array<{ id: string }>;
    expect(risks.length).toBe(12);

    for (const r of risks) {
      const reviewRes = await page.request.post(
        `${BACKEND_BASE}/api/v1/portal/magerit/risks/${r.id}/review`,
        {
          data: { action: "revisada_ok", note: null },
          headers: { "X-Csrf-Token": csrfToken },
        },
      );
      expect(reviewRes.ok()).toBeTruthy();
    }

    // ────── Reload page · verify firma button enabled ──────
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await page
      .waitForLoadState("networkidle", { timeout: 5000 })
      .catch(() => {});
    await expect(
      page.getByRole("button", { name: /Validar inventario MAGERIT/i }).first(),
    ).toBeEnabled({ timeout: 10_000 });

    // ────── Firmas en la cadena ANTES de firmar (para exigir una más) ──────
    const chainTotal = async (): Promise<{
      chain_valid: boolean;
      broken_links: unknown[];
      total_signatures: number;
    }> => {
      const adminCtx = await page.context().browser()?.newContext();
      if (!adminCtx) throw new Error("Could not create admin context");
      try {
        await loginAsMarcos(adminCtx);
        const res = await adminCtx.request.get(
          `${BACKEND_BASE}/api/v1/admin/signing/projects/${magerit.project_id}/chain-integrity`,
        );
        expect(res.ok()).toBeTruthy();
        return await res.json();
      } finally {
        await adminCtx.close();
      }
    };
    const before = await chainTotal();

    // ────── Click firma · confirm dialog · firma directa ──────
    await page
      .getByRole("button", { name: /Validar inventario MAGERIT/i })
      .click();

    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /Continuar firma/i }).click();

    // ────── Verify success (toast onSuccess + summary) ──────
    await expect(page.getByText(/MAGERIT validado ·/i).first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(
      page.getByText(/Última versión validada/i).first(),
    ).toBeVisible({ timeout: 10_000 });

    // ────── Backend assertion · chain integrity + firma nueva ──────
    const after = await chainTotal();
    expect(after.chain_valid).toBe(true);
    expect(after.broken_links).toEqual([]);
    expect(after.total_signatures).toBe(before.total_signatures + 1);
  });
});
