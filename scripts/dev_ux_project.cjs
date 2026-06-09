/**
 * Dev UX review — IN-PROJECT ENS workflow. Logs in, enters a project (sets the
 * active-project context via the selector), then screenshots the core ENS
 * lifecycle pages. Captures console errors + final URL per page.
 *
 * Run: NODE_PATH=frontend/node_modules node scripts/dev_ux_project.cjs
 */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = "http://localhost:3000";
const EMAIL = process.env.MARCOS_EMAIL || "marcosmata@fulkro.es";
const PASSWORD = process.env.MARCOS_PASSWORD || "";
const TOTP_SECRET = process.env.MARCOS_TOTP_SECRET || "";
const OUT = path.resolve(__dirname, "..", "out", "ux_project");

function base32Decode(s) {
  const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of s.replace(/=+$/, "").toUpperCase().replace(/\s/g, "")) {
    const i = a.indexOf(c);
    if (i >= 0) bits += i.toString(2).padStart(5, "0");
  }
  const b = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) b.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(b);
}
function totp(secret) {
  const key = base32Decode(secret);
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 1000 / 30)));
  const h = crypto.createHmac("sha1", key).update(buf).digest();
  const o = h[h.length - 1] & 0xf;
  const code =
    (((h[o] & 0x7f) << 24) | ((h[o + 1] & 0xff) << 16) | ((h[o + 2] & 0xff) << 8) | (h[o + 3] & 0xff)) %
    1000000;
  return code.toString().padStart(6, "0");
}

const SUBPAGES = [
  "summary", "archetype", "dimensiones", "dda", "magerit", "risks",
  "plan", "evidence", "obligations", "conformity", "audit-dry-run",
  "dossier", "contratos", "equipo", "cloud-connectors", "chat",
];

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.waitForSelector("#email", { timeout: 15000 });
  await page.fill("#email", EMAIL);
  await page.fill("#password", PASSWORD);
  await page.getByRole("button", { name: "Acceder" }).click();
  await page.waitForSelector('input[placeholder="000000"]', { timeout: 20000 });
  for (let i = 0; i < 2; i++) {
    await page.fill('input[placeholder="000000"]', totp(TOTP_SECRET));
    await page.getByRole("button", { name: "Validar código" }).click();
    try {
      await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 12000 });
      return true;
    } catch {
      await page.fill('input[placeholder="000000"]', "");
    }
  }
  return false;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => {
    try { localStorage.setItem("fulkro_admin_tour_completed", "true"); } catch {}
  });
  const page = await ctx.newPage();
  if (!(await login(page))) { console.log("LOGIN FAILED"); await browser.close(); return; }

  // Enter a project via the selector (sets active-project context)
  // Seed ONE MEDIA project via the atomic wizard endpoint (dev DB has 0 projects).
  await page.goto(`${BASE}/admin/projects`, { waitUntil: "networkidle" });
  const PAYLOAD = {
    step1_datos_cliente: { razon_social: "Proyecto Demo Review VI SL", cif: "B00000026" },
    step2_contexto_ens: {
      sector_ens: "privado_licita_aapp",
      tipo_organizacion: "pyme",
      tamano_empleados: "pequeno",
    },
    step3_categoria: {
      categoria_preliminar: "MEDIA",
      dims_anexo_i: {
        confidencialidad: "MEDIO", integridad: "MEDIO", disponibilidad: "MEDIO",
        autenticidad: "MEDIO", trazabilidad: "BAJO",
      },
    },
    step4_activos: {
      activos: [
        { nombre: "ERP corporativo", tipo: "software" },
        { nombre: "Datos de clientes", tipo: "datos" },
        { nombre: "Servidor de ficheros", tipo: "infraestructura" },
      ],
      dependencias_cloud: ["AWS", "Microsoft 365"],
    },
    step5_first_user: {
      email: "cockpit-demo-vi@example.com",
      full_name: "Cockpit Demo Review",
      cargo: "Responsable de Seguridad",
      send_magic_link: false,
    },
  };
  const created = await page.evaluate(async (payload) => {
    const cm = document.cookie.match(/(?:^|;\s*)fulkro_csrf=([^;]+)/);
    const csrf = cm ? decodeURIComponent(cm[1]) : null;
    const res = await fetch("/api/v1/admin/diagnostico-wizard/create-project", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json", "X-CSRF-Token": csrf },
      credentials: "include",
      body: JSON.stringify(payload),
    });
    return { status: res.status, body: await res.text() };
  }, PAYLOAD);
  console.log("CREATE status =", created.status, "·", created.body.slice(0, 200));
  let pid = null;
  try { pid = JSON.parse(created.body).project_id; } catch {}
  if (!pid) { console.log("could not create project"); await browser.close(); return; }
  console.log("CREATED PROJECT pid =", pid);
  // Land on summary to set active-project context (header endpoint now returns 200)
  await page.goto(`${BASE}/admin/projects/${pid}/summary`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);

  const results = [];
  for (const sub of SUBPAGES) {
    const errors = [];
    const onC = (msg) => { if (msg.type() === "error") errors.push(msg.text().slice(0, 160)); };
    const onP = (e) => errors.push("PAGEERR: " + String(e).slice(0, 160));
    page.on("console", onC);
    page.on("pageerror", onP);
    let status = "ok";
    try {
      await page.goto(`${BASE}/admin/projects/${pid}/${sub}`, { waitUntil: "domcontentloaded", timeout: 25000 });
      await page.waitForTimeout(2200);
    } catch (e) { status = "nav-error:" + String(e).slice(0, 80); }
    const finalUrl = page.url();
    const redirected = !finalUrl.includes(`/${sub}`);
    await page.screenshot({ path: path.join(OUT, `${sub}.png`), fullPage: true }).catch(() => {});
    page.off("console", onC);
    page.off("pageerror", onP);
    results.push({ sub, finalUrl, redirected, status, errors: errors.slice(0, 4) });
    console.log(`· ${sub.padEnd(16)} ${redirected ? "REDIRECT→" + finalUrl.split(pid)[1] : "ok"} ${errors.length ? "ERRS:" + errors.length : ""}`);
  }
  fs.writeFileSync(path.join(OUT, "_summary.json"), JSON.stringify({ pid, results }, null, 2));
  console.log("\nSUMMARY → out/ux_project/_summary.json");
  await browser.close();
})();
