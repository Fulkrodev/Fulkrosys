// Replica el checkFocusVisibleIndicator del polish gate y reporta el elemento.
import { chromium } from "@playwright/test";

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL || "http://localhost:8000";
const BASE = `http://localhost:${process.env.PLAYWRIGHT_PORT || 3100}`;
const PAGES = process.argv.slice(2);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const api = await ctx.request.post(`${BACKEND}/api/v1/_dev/login-as-marcos`);
const cookies = api.headersArray().filter(h => h.name.toLowerCase() === "set-cookie").map(h => {
  const [pair] = h.value.split(";"); const i = pair.indexOf("=");
  return { name: pair.slice(0, i), value: pair.slice(i + 1), url: BASE };
});
await ctx.addCookies(cookies);

for (const path of PAGES) {
  const page = await ctx.newPage();
  await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(500);
  await page.evaluate(() => { document.activeElement?.blur?.(); document.body.focus(); });
  await page.keyboard.press("Tab");
  await page.waitForTimeout(100);
  const info = await page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { el: "(body)" };
    const s = window.getComputedStyle(el);
    return {
      el: el.tagName + (el.className ? "." + String(el.className).slice(0, 80) : ""),
      text: (el.textContent || "").slice(0, 40),
      outline: s.outline, boxShadow: s.boxShadow.slice(0, 60),
    };
  });
  console.log(`${path} ::`, JSON.stringify(info));
  await page.close();
}
await browser.close();
