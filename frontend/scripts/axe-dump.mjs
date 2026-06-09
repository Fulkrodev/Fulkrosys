// Dump exact axe violation nodes for given admin pages (debug polish failures).
// Usage: node scripts/axe-dump.mjs /admin/projects /admin/projects/<id>/roadmap ...
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL || "http://localhost:8000";
const BASE = `http://localhost:${process.env.PLAYWRIGHT_PORT || 3100}`;
const PAGES = process.argv.slice(2);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });

// login-as-marcos → copy session cookies
const api = await ctx.request.post(`${BACKEND}/api/v1/_dev/login-as-marcos`);
if (!api.ok()) { console.error("login-as-marcos failed", api.status()); process.exit(1); }
const setCookies = api.headersArray().filter(h => h.name.toLowerCase() === "set-cookie");
const cookies = setCookies.map(h => {
  const [pair] = h.value.split(";");
  const idx = pair.indexOf("=");
  return { name: pair.slice(0, idx), value: pair.slice(idx + 1), url: BASE };
});
await ctx.addCookies(cookies);
const projectId = "00000000-0000-0000-0000-000000000001";
await ctx.addInitScript((pid) => {
  localStorage.setItem("fulkro_admin_tour_completed", "1");
  // mirror auth-real fixture: dismiss copilot guided flows + set active project
  for (const ph of ["onboarding","diagnostico","analisis_riesgos","adecuacion","implantacion","dda_final","verificacion","conformidad","retainer"]) {
    localStorage.setItem(`fulkro_copilot_guided_dismissed_${ph}`, "1");
  }
  localStorage.setItem("fulkro-active-project", JSON.stringify({
    state: {
      activeProject: {
        id: pid, name: "Proyecto ENS Test E2E", clientId: pid,
        clientName: "Test E2E Client", ensCategory: "ALTA",
        status: "ACTIVE", lastAccessedAt: Date.now(),
      },
      lastUsedProjectId: pid,
    },
    version: 0,
  }));
}, projectId);

const VIEWPORTS = [
  { width: 375, height: 812 }, { width: 414, height: 896 },
  { width: 768, height: 1024 }, { width: 1024, height: 768 },
  { width: 1280, height: 800 }, { width: 1920, height: 1080 },
];

for (const path of PAGES) {
  const page = await ctx.newPage();
  await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  // mirror polish fixture: pasea los 6 viewports y escanea en 1280x800 +300ms
  for (const vp of VIEWPORTS) {
    await page.setViewportSize(vp);
    await page.waitForTimeout(150);
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(300);
  const res = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const bad = res.violations.filter(v => ["critical", "serious"].includes(v.impact));
  console.log(`\n===== ${path} · ${bad.length} critical/serious =====`);
  for (const v of bad) {
    console.log(`--- [${v.impact}] ${v.id}: ${v.help}`);
    for (const n of v.nodes.slice(0, 6)) {
      console.log(`  target: ${JSON.stringify(n.target)}`);
      console.log(`  html  : ${n.html.slice(0, 220)}`);
      const cc = n.any?.find(a => a.id === "color-contrast");
      if (cc?.data) console.log(`  data  : fg=${cc.data.fgColor} bg=${cc.data.bgColor} ratio=${cc.data.contrastRatio} required=${cc.data.expectedContrastRatio}`);
    }
  }
  await page.close();
}
await browser.close();
