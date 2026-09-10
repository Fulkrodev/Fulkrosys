// Visual audit w3 · capturas + deteccion de overflow horizontal por viewport.
// Autonomo: auth admin via cookies _dev/login-as-marcos, cliente via form login.
// Uso: cd frontend && node scripts/visual-audit.mjs
import { chromium, request as pwRequest } from "@playwright/test";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const FRONT = process.env.FRONT ?? "http://localhost:3000";
const BACK = process.env.BACK ?? "http://localhost:8000";
// Raíz del repo derivada de la ubicación de este fichero (frontend/scripts → ../../),
// no de una ruta absoluta de una máquina concreta. Override: FULKRO_OUT_DIR.
const REPO_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const OUT = process.env.FULKRO_OUT_DIR ?? `${REPO_ROOT}out/visual`;
const WIDTHS = [375, 768, 1280, 1920];
const report = [];

fs.mkdirSync(OUT, { recursive: true });

const api = await pwRequest.newContext();
await api.post(`${BACK}/api/v1/_dev/create-test-client`).catch(() => {});
let projectId = "00000000-0000-0000-0000-000000000001";
try {
  const r = await api.post(`${BACK}/api/v1/_dev/create-test-client`);
  if (r.ok()) projectId = (await r.json()).project_id ?? projectId;
} catch {}
await api.post(`${BACK}/api/v1/_dev/seed-rich-demo-project`).catch(() => {});

// Admin cookies
let adminCookies = [];
try {
  await api.post(`${BACK}/api/v1/_dev/login-as-marcos`);
  const st = await api.storageState();
  adminCookies = st.cookies.filter((c) =>
    ["fulkro_session", "fulkro_csrf"].includes(c.name),
  );
} catch (e) {
  console.log("ADMIN AUTH FAIL", String(e).slice(0, 140));
}

const P = (id) => `/admin/projects/${id}`;
const ADMIN_PAGES = [
  "/admin/dashboard", "/admin/projects", "/admin/finance", "/admin/clients",
  "/admin/compliance", "/admin/operations", "/admin/pipeline",
  "/admin/notifications", "/admin/whatsapp", "/admin/retainers",
  "/admin/system-health", "/admin/settings",
  `${P(projectId)}/summary`, `${P(projectId)}/dda`, `${P(projectId)}/magerit`,
  `${P(projectId)}/plan`, `${P(projectId)}/audit`, `${P(projectId)}/evidence`,
  `${P(projectId)}/chat`, `${P(projectId)}/financial`, `${P(projectId)}/documents`,
  `${P(projectId)}/verification`, `${P(projectId)}/risks`, `${P(projectId)}/conformity`,
];
const CLIENT_PAGES = [
  "/client-portal/dashboard", "/client-portal/plan", "/client-portal/dda",
  "/client-portal/magerit", "/client-portal/cumplimiento", "/client-portal/remediaciones",
  "/client-portal/files", "/client-portal/firmas-pendientes", "/client-portal/account",
  "/client-portal/billing", "/client-portal/conformidad", "/client-portal/actas",
  "/client-portal/retainer-checkin", "/client-portal/whatsapp",
];
const PUBLIC_PAGES = [
  "/login", "/client-portal/login", "/trust", "/privacy", "/terms", "/cookies",
  "/sub-processors", "/imprint", "/dpa-template", "/derechos-rgpd",
];
const ONLY_PUBLIC = process.env.ONLY_PUBLIC === "1";

async function sweep(label, ctx, pages) {
  const page = await ctx.newPage();
  for (const url of pages) {
    for (const w of WIDTHS) {
      await page.setViewportSize({ width: w, height: 900 });
      let err = null;
      try {
        await page.goto(FRONT + url, { waitUntil: "networkidle", timeout: 25000 });
      } catch (e) {
        try { await page.goto(FRONT + url, { waitUntil: "domcontentloaded", timeout: 20000 }); }
        catch (e2) { err = String(e2).slice(0, 120); }
      }
      await page.waitForTimeout(500);
      let m = { sw: 0, iw: w, p: url };
      try {
        m = await page.evaluate(() => ({
          sw: document.documentElement.scrollWidth,
          iw: window.innerWidth,
          p: location.pathname,
        }));
      } catch {}
      const dir = `${OUT}/${label}`;
      fs.mkdirSync(dir, { recursive: true });
      const fname = `${(url.replace(`/admin/projects/${projectId}`, "PROJ").replace(/[^\w]+/g, "_") || "root")}__${w}.png`;
      try { await page.screenshot({ path: `${dir}/${fname}`, fullPage: true }); } catch {}
      const redirected = m.p && !url.endsWith(m.p) && m.p !== url ? m.p : null;
      report.push({
        label, url, w, scrollWidth: m.sw, innerWidth: m.iw,
        overflowPx: m.sw - m.iw, redirected, err, file: `${label}/${fname}`,
      });
    }
  }
  await page.close();
}

const browser = await chromium.launch();

// ADMIN
if (adminCookies.length && !ONLY_PUBLIC) {
  const ctx = await browser.newContext();
  await ctx.addCookies(adminCookies);
  await ctx.addInitScript(() => { try { localStorage.setItem("fulkro_admin_tour_completed", "1"); } catch {} });
  await sweep("admin", ctx, ADMIN_PAGES);
  await ctx.close();
} else {
  console.log("SKIP admin (no cookies)");
}

// CLIENTE (form login)
if (!ONLY_PUBLIC) {
  const ctx = await browser.newContext();
  await ctx.addInitScript(() => { try { localStorage.setItem("fulkro_tutorial_completed", "1"); localStorage.setItem("fulkro_client_onboarding_dismissed", "1"); } catch {} });
  const lp = await ctx.newPage();
  let clientOk = false;
  try {
    await lp.goto(`${FRONT}/client-portal/login`, { waitUntil: "networkidle", timeout: 25000 });
    await lp.locator("#email").waitFor({ state: "visible", timeout: 15000 });
    await lp.waitForTimeout(2500); // dejar hidratar el handler JS (dev server)
    await lp.locator("#email").fill("test-client-e2e@example.com");
    await lp.locator("#password").fill("TestP@ssw0rd123!");
    await lp.getByRole("button", { name: /Entrar/i }).click();
    await lp.waitForURL(/\/client-portal\/(dashboard|account)/, { timeout: 15000 });
    clientOk = true;
  } catch (e) {
    console.log("CLIENT AUTH FAIL", String(e).slice(0, 160));
  }
  await lp.close();
  if (clientOk) await sweep("cliente", ctx, CLIENT_PAGES);
  else report.push({ label: "cliente", url: "(auth)", w: 0, err: "login failed (env-key blocker?)" });
  await ctx.close();
}

// PUBLIC
{
  const ctx = await browser.newContext();
  await sweep("public", ctx, PUBLIC_PAGES);
  await ctx.close();
}

await browser.close();
await api.dispose();

fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
const over = report.filter((r) => r.overflowPx > 2 && !r.err);
const errs = report.filter((r) => r.err);
console.log(`\n=== VISUAL AUDIT DONE · ${report.length} shots ===`);
console.log(`OVERFLOW (>2px horizontal) · ${over.length}:`);
for (const o of over) console.log(`  [${o.label}] ${o.url} @${o.w}  overflow=${o.overflowPx}px (sw=${o.scrollWidth})`);
console.log(`ERRORS · ${errs.length}:`);
for (const e of errs) console.log(`  [${e.label}] ${e.url} @${e.w}  ${e.err}`);
const reds = report.filter((r) => r.redirected);
console.log(`REDIRECTS · ${reds.length}: ${[...new Set(reds.map((r) => `${r.url}->${r.redirected}`))].slice(0, 12).join(" | ")}`);
