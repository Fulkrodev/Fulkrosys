import { chromium, request as pwRequest } from "@playwright/test";
import fs from "node:fs";

const FRONT = "http://localhost:3000";
const BACK = "http://localhost:8000";
const OUT = "/home/usuario/fulkro/out/visual/auditor";
const WIDTHS = [375, 768, 1280, 1920];
fs.mkdirSync(OUT, { recursive: true });

const api = await pwRequest.newContext();
await api.post(`${BACK}/api/v1/_dev/create-test-client`).catch(() => {});
const tr = await api.post(`${BACK}/api/v1/_dev/auditor-portal-token`);
console.log("auditor-portal-token:", tr.status());
const tok = await tr.json();
const token = tok.token;
const otp = tok.otp;
console.log("portal_path:", tok.portal_path, "otp?", Boolean(otp));

const SECTIONS = [
  "summary", "audit/dda-evidence-gaps", "dda", "magerit", "plan", "evidence",
  "e041", "audit-log", "pentest", "documents", "draft-report",
];
const report = [];
const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();

async function ensureOtp() {
  const inp = page.getByTestId("auditor-otp-input");
  if (otp && (await inp.isVisible().catch(() => false))) {
    await inp.fill(otp);
    await page.getByTestId("auditor-otp-submit").click();
    await inp.waitFor({ state: "hidden", timeout: 8000 }).catch(() => {});
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  }
}

for (const s of SECTIONS) {
  for (const w of WIDTHS) {
    await page.setViewportSize({ width: w, height: 900 });
    const url = `/auditor-portal/${token}/${s}`;
    try { await page.goto(FRONT + url, { waitUntil: "networkidle", timeout: 25000 }); } catch {}
    await ensureOtp();
    await page.waitForTimeout(500);
    let m = { sw: 0, iw: w, p: url };
    try { m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth, p: location.pathname })); } catch {}
    const fname = `${s.replace(/[^\w]+/g, "_")}__${w}.png`;
    try { await page.screenshot({ path: `${OUT}/${fname}`, fullPage: true }); } catch {}
    const onPortal = (m.p || "").includes("/auditor-portal/");
    report.push({ s, w, overflowPx: m.sw - m.iw, scrollWidth: m.sw, onPortal });
  }
}

await browser.close();
await api.dispose();
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
const over = report.filter((x) => x.overflowPx > 2 && x.onPortal);
const off = report.filter((x) => !x.onPortal);
console.log(`\nAUDITOR DONE ${report.length} shots · overflow=${over.length} · off-portal=${off.length}`);
for (const o of over) console.log(`  OVERFLOW ${o.s} @${o.w} +${o.overflowPx}px (sw=${o.scrollWidth})`);
if (off.length) console.log(`  off-portal (no entró/redirect): ${[...new Set(off.map((o) => o.s))].join(", ")}`);
