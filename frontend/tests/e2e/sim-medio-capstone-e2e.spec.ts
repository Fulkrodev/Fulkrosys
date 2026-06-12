/**
 * CAPSTONE · Galería ENS MEDIO sobre un proyecto 100% IMPLANTADO.
 *
 * A diferencia de sim-medio-full-cloth (que recorría un proyecto a medio
 * implantar), aquí PRIMERO se implanta el proyecto al 100% vía el lever
 * `seed-full-implantation` y LUEGO se captura cada fase con DATOS REALES:
 *   - admin: implantación completa (DdA 68 · MAGERIT · plan · evidencias · conformidad)
 *   - cliente: portal (tareas · conformidad · firmas-hub · plan · certificación · retainer)
 *   - auditor: las 11 vistas con datos + el informe de auditoría ENAC
 *
 * Capturas a out/sim_medio_e2e/5x_*.png (numeradas, continúan la galería).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";
import {
  BACKEND_BASE,
  csrfHeader,
  gotoStable,
  mintAuditorToken,
  shot,
} from "./_helpers/sim-medio";

let PID = "";
let IMPL: { dda_aplicables: number; evidence_count: number } = {
  dda_aplicables: 0,
  evidence_count: 0,
};

test.describe.configure({ mode: "serial", timeout: 300_000 });

async function api(
  request: import("@playwright/test").APIRequestContext,
  path: string,
  opts: { headers?: Record<string, string>; data?: unknown; timeout?: number } = {},
) {
  return request.post(`${BACKEND_BASE}${path}`, {
    headers: opts.headers,
    data: opts.data as never,
    timeout: opts.timeout ?? 60_000,
  });
}

test.describe("CAPSTONE · ENS MEDIO implantado (galería)", () => {
  // ── ADMIN: implantación completa ──────────────────────────────────────
  test("admin · implantación 100% (DdA · MAGERIT · plan · evidencias · conformidad)", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    // bootstrap: proyecto default + reset + implantar al 100%
    const tc = await api(ctx.request, "/api/v1/_dev/create-test-client");
    PID = (await tc.json()).project_id;
    await api(ctx.request, `/api/v1/_dev/reset-test-cycle?project_id=${PID}`, { timeout: 40_000 });
    const implRes = await api(ctx.request, "/api/v1/_dev/seed-full-implantation?tier=MEDIA", { timeout: 200_000 });
    IMPL = await implRes.json();

    await loginAsMarcos(ctx);
    const page = await ctx.newPage();
    const detail = `MEDIA implantado · ${IMPL.dda_aplicables} medidas · ${IMPL.evidence_count} evidencias`;
    const views: Array<[number, string, string]> = [
      [50, "dimensiones", "admin_dimensiones"],
      [51, "magerit", "admin_magerit"],
      [52, "dda", "admin_dda"],
      [53, "risks", "admin_riesgos"],
      [54, "plan", "admin_plan"],
      [55, "evidence", "admin_evidencias"],
      [56, "conformity", "admin_conformidad"],
    ];
    for (const [n, slug, name] of views) {
      await gotoStable(page, `/admin/projects/${PID}/${slug}`);
      await page.waitForTimeout(900);
      await shot(page, n, name, "admin", detail);
    }
    await ctx.close();
  });

  // ── CLIENTE: portal + retainer (tras certificar) ──────────────────────
  test("cliente · portal con datos reales + oferta de retainer", async ({
    browser,
  }) => {
    // certificar (mark-passed) para que exista la oferta de retainer
    const adminCtx = await browser.newContext();
    await loginAsMarcos(adminCtx);
    const headers = await csrfHeader(adminCtx);
    await api(adminCtx.request, `/api/v1/projects/${PID}/audit/mark-passed`, {
      headers,
      data: {
        result: "passed",
        audit_report_ref: "E-702-ENAC-001",
        cascade_certify: true,
        cascade_retainer_offer: true,
      },
    });
    await adminCtx.close();

    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await ctx.newPage();
    await loginAsClient(page, { dismissTutorial: true });
    const views: Array<[number, string, string]> = [
      [57, "dashboard", "cliente_dashboard"],
      [58, "tasks", "cliente_tareas"],
      [59, "conformidad", "cliente_conformidad"],
      [60, "firmas-hub", "cliente_firmas_hub"],
      [61, "plan", "cliente_plan"],
      [62, "certificacion", "cliente_certificacion"],
      [63, "retainer", "cliente_retainer"],
    ];
    for (const [n, slug, name] of views) {
      await gotoStable(page, `/client-portal/${slug}`);
      await page.waitForTimeout(900);
      await shot(page, n, name, "cliente", slug);
    }
    await ctx.close();
  });

  // ── AUDITOR ENAC: 11 vistas con datos + informe ───────────────────────
  test("auditor ENAC · 11 vistas con datos reales + informe", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const at = await mintAuditorToken(ctx.request, PID);
    const page = await ctx.newPage();

    // entrada + OTP step-up
    await page.goto(`/auditor-portal/${at.token}/summary`, { waitUntil: "domcontentloaded" });
    if (at.otp) {
      const otpInput = page.getByLabel(/OTP|código|seguridad/i).first();
      if (await otpInput.isVisible().catch(() => false)) {
        await otpInput.fill(at.otp);
        const go = page.getByRole("button", { name: /Verificar|Entrar|Acceder/i }).first();
        if (await go.isVisible().catch(() => false)) await go.click();
      }
    }
    await page
      .getByTestId("auditor-summary-view")
      .waitFor({ state: "visible", timeout: 12_000 })
      .catch(() => {});

    const sections: Array<[number, string]> = [
      [64, "summary"],
      [65, "dda"],
      [66, "magerit"],
      [67, "plan"],
      [68, "evidence"],
      [69, "e041"],
      [70, "audit-log"],
      [71, "pentest"],
      [72, "documents"],
    ];
    for (const [n, slug] of sections) {
      await gotoStable(page, `/auditor-portal/${at.token}/${slug}`, "auditor-portal-main");
      await page.waitForTimeout(700);
      await shot(page, n, `auditor_${slug.replace("-", "_")}`, "auditor", `vista ${slug}`);
    }
    // heatmap de cobertura (100%) + informe
    await gotoStable(page, `/auditor-portal/${at.token}/audit/dda-evidence-gaps`, "gap-view");
    await shot(page, 73, "auditor_gaps_heatmap", "auditor", "cobertura 100%");
    await gotoStable(page, `/auditor-portal/${at.token}/draft-report`, "draft-report-view");
    await page.waitForTimeout(1000);
    await shot(page, 74, "auditor_informe_enac", "auditor", "informe de auditoría ENAC → APROBAR");
    await ctx.close();
    expect(PID).not.toBe("");
  });
});
