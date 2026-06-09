/**
 * Dev UX review: log in as Marcos (password + TOTP) and screenshot every admin
 * tool full-page, capturing console errors + final URL (redirect-to-login =
 * broken gate). For the "ponte en la piel de ingeniero/diseñador top" review.
 *
 * Run: node scripts/dev_ux_review.cjs
 */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = "http://localhost:3000";
const EMAIL = process.env.MARCOS_EMAIL || "marcosmata@fulkro.es";
const PASSWORD = process.env.MARCOS_PASSWORD || "";
const TOTP_SECRET = process.env.MARCOS_TOTP_SECRET || "";
const OUT = path.resolve(__dirname, "..", "out", "ux_review");

function base32Decode(s) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of s.replace(/=+$/, "").toUpperCase().replace(/\s/g, "")) {
    const idx = alphabet.indexOf(c);
    if (idx >= 0) bits += idx.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}
function totp(secret) {
  const key = base32Decode(secret);
  const counter = Math.floor(Date.now() / 1000 / 30);
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(counter));
  const h = crypto.createHmac("sha1", key).update(buf).digest();
  const o = h[h.length - 1] & 0xf;
  const code =
    (((h[o] & 0x7f) << 24) | ((h[o + 1] & 0xff) << 16) | ((h[o + 2] & 0xff) << 8) | (h[o + 3] & 0xff)) %
    1000000;
  return code.toString().padStart(6, "0");
}

const PAGES = [
  ["dashboard", "/admin/dashboard"],
  ["projects", "/admin/projects"],
  ["pipeline", "/admin/pipeline"],
  ["operations", "/admin/operations"],
  ["compliance", "/admin/compliance"],
  ["compliance-monitor", "/admin/compliance/monitor"],
  ["siem", "/admin/siem"],
  ["copilot", "/admin/copilot"],
  ["messages", "/admin/messages"],
  ["finance", "/admin/finance"],
  ["retainers", "/admin/retainers"],
  ["meetings", "/admin/meetings"],
  ["settings", "/admin/settings"],
  ["radar", "/radar"],
];

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill("#email", EMAIL);
  await page.fill("#password", PASSWORD);
  await page.getByRole("button", { name: "Acceder" }).click();
  await page.waitForSelector('input[placeholder="000000"]', { timeout: 20000 });
  for (let attempt = 0; attempt < 2; attempt++) {
    const code = totp(TOTP_SECRET);
    await page.fill('input[placeholder="000000"]', code);
    await page.getByRole("button", { name: "Validar código" }).click();
    try {
      await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 12000 });
      return true;
    } catch {
      // maybe code rolled over at boundary → clear + retry once
      await page.fill('input[placeholder="000000"]', "");
    }
  }
  return false;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  // Dismiss first-run admin tour so screenshots show real content (OnboardingTourAdmin)
  await ctx.addInitScript(() => {
    try {
      localStorage.setItem("fulkro_admin_tour_completed", "true");
    } catch {
      /* noop */
    }
  });
  const page = await ctx.newPage();

  const ok = await login(page);
  const results = [];
  if (!ok) {
    console.log(JSON.stringify({ loginFailed: true, url: page.url() }, null, 2));
    await page.screenshot({ path: path.join(OUT, "00-login-FAILED.png"), fullPage: true });
    await browser.close();
    return;
  }
  console.log("LOGIN OK →", page.url());

  for (const [name, route] of PAGES) {
    const errors = [];
    const onConsole = (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); };
    const onPageErr = (e) => errors.push("PAGEERROR: " + String(e).slice(0, 200));
    page.on("console", onConsole);
    page.on("pageerror", onPageErr);
    let status = "ok";
    try {
      await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded", timeout: 25000 });
      await page.waitForTimeout(2500); // settle async data (SSE pages never hit networkidle)
    } catch (e) {
      status = "nav-error: " + String(e).slice(0, 120);
    }
    const finalUrl = page.url();
    const gated = /\/login(\?|$)/.test(finalUrl);
    await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true }).catch(() => {});
    page.off("console", onConsole);
    page.off("pageerror", onPageErr);
    results.push({ name, route, finalUrl, gated, status, errors: errors.slice(0, 5) });
    console.log(`· ${name.padEnd(20)} ${gated ? "GATED→login" : "rendered"} ${errors.length ? "ERRS:" + errors.length : ""}`);
  }

  // intentar un proyecto detalle (primer link de la lista)
  try {
    await page.goto(`${BASE}/admin/projects`, { waitUntil: "networkidle" });
    const href = await page.locator('a[href^="/admin/projects/"]').first().getAttribute("href").catch(() => null);
    if (href && !href.endsWith("/projects")) {
      await page.goto(`${BASE}${href}`, { waitUntil: "networkidle", timeout: 25000 });
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(OUT, "project-detail.png"), fullPage: true });
      results.push({ name: "project-detail", route: href, finalUrl: page.url(), gated: false, status: "ok", errors: [] });
      console.log("· project-detail        rendered", href);
    } else {
      console.log("· project-detail        NO PROJECTS in list");
    }
  } catch (e) {
    console.log("· project-detail        error", String(e).slice(0, 80));
  }

  fs.writeFileSync(path.join(OUT, "_summary.json"), JSON.stringify(results, null, 2));
  console.log("\nSUMMARY written to out/ux_review/_summary.json");
  await browser.close();
})();
