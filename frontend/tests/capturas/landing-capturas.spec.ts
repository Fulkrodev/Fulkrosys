/**
 * Capturas reales del producto para la landing (landing/assets/capturas/).
 *
 * Recorre el PORTAL CLIENTE (autenticado como la usuaria demo "Laura" del
 * proyecto NovaEdge S.L., nivel MEDIA) y el PORTAL AUDITOR (solo lectura, vía
 * magic-link AUDITOR_PORTAL_ENAC), y guarda un PNG por pantalla en dos viewports
 * (desktop 1440 + móvil 390), tema claro, sin barras de scroll.
 *
 * El proyecto demo, los datos sembrados (DdA MEDIA, MAGERIT, evidencias,
 * conformidad, pentest), el renombrado a NovaEdge/Laura y el token de auditor
 * los prepara `scripts/capturas_landing.py`, que deja la config en
 * tests/capturas/.capturas-config.json. La conversión a WebP la hace ese mismo
 * orquestador (Pillow) tras esta corrida.
 *
 * RGPD: cero datos reales. Todo proviene del proyecto demo ficticio sembrado.
 */
import fs from "node:fs";
import path from "node:path";

import { test, expect } from "@playwright/test";

import { loginAsClient } from "../e2e/_helpers/auth-real";

interface CapturasConfig {
  clientEmail: string;
  clientPassword: string;
  projectId: string;
  auditorToken: string;
  auditorOtp: string | null;
  outDir: string;
}

const CONFIG_PATH = path.join(__dirname, ".capturas-config.json");
const cfg: CapturasConfig = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));

fs.mkdirSync(cfg.outDir, { recursive: true });

// Desktop 1440 + móvil 390 (alturas elegidas para un encuadre limpio "ventana").
const VIEWPORTS = [
  { w: 1440, h: 900, suffix: "" },
  { w: 390, h: 844, suffix: "-mobile" },
] as const;

// Oculta scrollbars + cualquier overlay de onboarding/tour que pudiera quedar,
// para recortes limpios. No altera el contenido de producto.
const CLEANUP_CSS = `
  *::-webkit-scrollbar { width: 0 !important; height: 0 !important; display: none !important; }
  * { scrollbar-width: none !important; }
  [data-testid="admin-tour-overlay"],
  [data-onboarding-overlay],
  .fulkro-onboarding-overlay { display: none !important; }
  /* Oculta el banner de sugerencia del copiloto: en la demo sembrada muestra
     un estado degradado con jerga interna del motor (no apto para marketing). */
  [data-testid="agent-suggestion-banner"],
  [data-testid="agent-suggestion-tier-gated"] { display: none !important; }
  /* Lanzador flotante del copiloto (dock cliente + panel admin): fuera del
     material de marketing. */
  [data-testid="copiloto-dock-toggle"],
  [data-testid="copiloto-dock-open"],
  [aria-label^="Abrir copiloto"] { display: none !important; visibility: hidden !important; }
  /* Oculta el indicador dev de Next.js (badge "N error", toasts, build-watcher,
     dev-tools button): no debe aparecer en capturas de marketing. */
  nextjs-portal,
  [data-nextjs-toast],
  [data-nextjs-toast-wrapper],
  #__next-build-watcher,
  #__next-prerender-indicator,
  [data-next-badge-root],
  [data-next-badge],
  [data-nextjs-dev-tools-button],
  [data-nextjs-dev-tools] { display: none !important; visibility: hidden !important; }
`;

/** Limpieza in-DOM: elimina restos de jerga interna y sustituye el email de
 * test por uno ficticio limpio, para que las capturas no muestren datos de
 * test ni terminología de motor. */
async function scrubDom(page: import("@playwright/test").Page) {
  await page
    .evaluate(() => {
      document
        .querySelectorAll(
          '[data-testid="agent-suggestion-banner"],[data-testid="agent-suggestion-tier-gated"]',
        )
        .forEach((el) => el.remove());
      const EMAIL = "test-client-e2e@example.com";
      const CLEAN = "laura@novaedge.es";
      const GMAIL = /matagarciamarcos@gmail\.com/gi;
      const FULKRO_MAIL = "marcosmata@fulkro.es";
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
      );
      while (walker.nextNode()) {
        const n = walker.currentNode;
        if (!n.nodeValue) continue;
        let v = n.nodeValue;
        if (v.includes(EMAIL)) v = v.split(EMAIL).join(CLEAN);
        v = v.replace(GMAIL, FULKRO_MAIL);
        if (v !== n.nodeValue) n.nodeValue = v;
      }
    })
    .catch(() => {});
}

async function settle(page: import("@playwright/test").Page) {
  // El portal mantiene streams SSE abiertos · networkidle nunca llega: espera
  // breve y seguimos (no malgastar 9s por captura).
  await page.waitForLoadState("networkidle", { timeout: 2500 }).catch(() => {});
  // Espera a que haya un encabezado real renderizado (no esqueleto).
  await page
    .locator("h1, h2, [role='heading']")
    .first()
    .waitFor({ state: "visible", timeout: 4000 })
    .catch(() => {});
  await page.waitForTimeout(800);
  await page.addStyleTag({ content: CLEANUP_CSS }).catch(() => {});
  await scrubDom(page);
  await page.waitForTimeout(250);
}

async function shoot(
  page: import("@playwright/test").Page,
  url: string,
  base: string,
) {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    } catch {
      // reintento simple
      await page.goto(url, { waitUntil: "commit", timeout: 30000 }).catch(() => {});
    }
    await settle(page);
    const file = path.join(cfg.outDir, `${base}${vp.suffix}.png`);
    await page.screenshot({ path: file });
    // eslint-disable-next-line no-console
    console.log(`  ✓ ${base}${vp.suffix}.png`);
  }
}

// ─── Portal CLIENTE (usuaria Laura · NovaEdge S.L.) ────────────────────────
const CLIENTE_PAGES: Array<[string, string]> = [
  ["dashboard", "cliente-dashboard"],
  ["categorizacion", "cliente-categorizacion"],
  ["magerit", "cliente-magerit"],
  ["dda", "cliente-dda"],
  ["plan", "cliente-plan"],
  ["evidencias", "cliente-evidencias"],
  ["files", "cliente-files"],
  ["pentest-authorization", "cliente-pentest"],
  ["firmas-hub", "cliente-firmas"],
  ["conformidad", "cliente-conformidad"],
  ["chat", "cliente-chat"],
];

// ─── Portal AUDITOR (solo lectura · magic-link ENAC) ───────────────────────
const AUDITOR_PAGES: Array<[string, string]> = [
  ["summary", "auditor-dossier"],
  ["evidence", "auditor-evidence"],
  ["audit/dda-evidence-gaps", "auditor-gaps"],
  ["audit-log", "auditor-audit-log"],
];

test("capturas portal cliente", async ({ page }) => {
  await loginAsClient(page, {
    email: cfg.clientEmail,
    password: cfg.clientPassword,
    dismissTutorial: true,
  });
  // eslint-disable-next-line no-console
  console.log("Login cliente OK · capturando portal cliente…");
  for (const [sub, base] of CLIENTE_PAGES) {
    await shoot(page, `/client-portal/${sub}`, base);
  }
  expect(true).toBe(true);
});

// El portal auditor es STATELESS (sin cookie de sesión · public_api.py): el gate
// OTP step-up reaparece en CADA carga de página. El magic-link AUDITOR_PORTAL_ENAC
// permite max_uses=9999 y el OTP es reutilizable, así que pasamos el gate en cada
// navegación.
async function passAuditorGate(page: import("@playwright/test").Page) {
  const otpInput = page.getByTestId("auditor-otp-input");
  const gate = await otpInput
    .waitFor({ state: "visible", timeout: 10000 })
    .then(() => true)
    .catch(() => false);
  if (gate) {
    await otpInput.fill(cfg.auditorOtp ?? "");
    await page.getByTestId("auditor-otp-submit").click();
    await otpInput.waitFor({ state: "hidden", timeout: 12000 }).catch(() => {});
    await page.waitForLoadState("networkidle", { timeout: 4000 }).catch(() => {});
  }
}

async function shootAuditor(
  page: import("@playwright/test").Page,
  token: string,
  sub: string,
  base: string,
) {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    await page
      .goto(`/auditor-portal/${token}/${sub}`, {
        waitUntil: "domcontentloaded",
        timeout: 30000,
      })
      .catch(() => {});
    await passAuditorGate(page);
    await settle(page);
    await page.screenshot({ path: path.join(cfg.outDir, `${base}${vp.suffix}.png`) });
    // eslint-disable-next-line no-console
    console.log(`  ✓ ${base}${vp.suffix}.png`);
  }
}

test("capturas portal auditor", async ({ page }) => {
  const token = cfg.auditorToken;
  // eslint-disable-next-line no-console
  console.log("Capturando portal auditor (gate OTP por vista)…");
  for (const [sub, base] of AUDITOR_PAGES) {
    await shootAuditor(page, token, sub, base);
  }
  expect(true).toBe(true);
});
