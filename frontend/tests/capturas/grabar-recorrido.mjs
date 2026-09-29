// Recorrido de ~40 s por los tres portales, grabado sobre el demo (`make demo`).
//
// De aquí salen docs/assets/recorrido.gif (README) y landing/assets/video/
// recorrido.mp4 (web). Cada escena lleva un rótulo con la fase del ciclo ENS,
// para que se entienda sin sonido. Todo son datos del demo: NovaEdge S.L. es
// ficticia.
//
// Uso (con el demo levantado):
//   FULKRO_URL=http://localhost:3000 FULKRO_API=http://127.0.0.1:18000 \
//     node tests/capturas/grabar-recorrido.mjs
//   # y después, desde la raíz del repo:
//   scripts/recorrido_a_gif.sh out/recorrido/recorrido.webm
import fs from "node:fs";
import path from "node:path";

import { chromium, request } from "@playwright/test";

const BASE = process.env.FULKRO_URL ?? "http://localhost:3000";
const API = `${process.env.FULKRO_API ?? "http://127.0.0.1:18000"}/api/v1`;
const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");
const SALIDA = process.env.FULKRO_RECORRIDO_DIR ?? `${REPO}/out/recorrido`;
const TAM = { width: 1440, height: 960 };
fs.mkdirSync(SALIDA, { recursive: true });

// ── Sesiones por API: el vídeo no enseña formularios de acceso ─────────────
const admin = await request.newContext();
const r = await admin.post(`${API}/_dev/login-as-marcos`);
if (!r.ok()) throw new Error(`login-as-marcos: ${r.status()} (¿demo con APP_ENV != production?)`);
const cookiesAdmin = (await admin.storageState()).cookies;
const aud = await (await admin.post(`${API}/_dev/auditor-portal-token`)).json();
const PID = aud.project_id;
const cab = await (await admin.get(`${API}/projects/${PID}/header`)).json().catch(() => ({}));
await admin.dispose();

const cli = await request.newContext();
const lc = await cli.post(`${API}/client-auth/login`, {
  data: { email: "cliente@fulkro.es", password: process.env.FULKRO_DEMO_PASSWORD ?? "fulkro-demo-2026" },
});
if (!lc.ok()) throw new Error(`client-auth/login: ${lc.status()}`);
const cookiesCliente = (await cli.storageState()).cookies;
await cli.dispose();

const soloSesion = (cs) =>
  cs.filter((c) => c.name === "fulkro_session" || c.name === "fulkro_csrf")
    .map((c) => ({ ...c, domain: new URL(BASE).hostname }));

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: TAM, recordVideo: { dir: SALIDA, size: TAM }, colorScheme: "light",
});

const proyecto = {
  id: PID, name: "Sede electrónica de NovaEdge", clientId: cab?.cliente?.id ?? "",
  clientName: "NovaEdge S.L.", ensCategory: "MEDIA", status: "ACTIVE", lastAccessedAt: 0,
};
await context.addInitScript((p) => {
  try {
    localStorage.setItem("fulkro-active-project",
      JSON.stringify({ state: { activeProject: p, lastUsedProjectId: p.id }, version: 0 }));
    for (const k of ["fulkro_admin_tour_completed", "fulkro_tutorial_completed",
      "fulkro_client_onboarding_dismissed"]) localStorage.setItem(k, "1");
    // Las tarjetas de guia de cada fase ocupan media pantalla: el recorrido
    // enseña los datos, no la explicacion.
    for (const id of ["categorizacion-dimensiones", "magerit-analysis", "dda-applicability",
      "risks-register", "plan-adecuacion", "evidence-vault", "conformity-declaration",
      "dossier-enac", "roadmap-overview"]) localStorage.setItem(`fulkro_copilot_guided_dismissed_${id}`, "1");
  } catch { /* sin almacenamiento: el recorrido sigue */ }
  // Cortinilla: cubre la carga y el salto al contenido; se retira cuando la
  // pagina ya esta colocada, asi el recorrido no enseña pantallas a medias.
  const cortina = () => {
    if (document.getElementById("fk-cortina")) return;
    const c = document.createElement("div");
    c.id = "fk-cortina";
    c.style.cssText = "position:fixed;inset:0;z-index:2147483646;background:#0e0a22;" +
      "transition:opacity .35s ease;pointer-events:none";
    document.documentElement.appendChild(c);
  };
  if (document.documentElement) cortina();
  else document.addEventListener("readystatechange", cortina, { once: true });
  const s = document.createElement("style");
  s.textContent = `html{background:#0e0a22}
    nextjs-portal,[data-nextjs-toast],[data-next-badge-root],
    [data-testid="copiloto-dock-toggle"],[aria-label^="Abrir copiloto"],
    footer:has(a[href^="tel:"]){display:none!important}`;
  (document.head || document.documentElement).appendChild(s);
}, proyecto);

const page = await context.newPage();

// Rótulo de escena: fase + qué se ve. Se pinta tras cada navegación.
async function rotulo(n, titulo, sub) {
  await page.evaluate(({ n, titulo, sub }) => {
    document.getElementById("fk-rotulo")?.remove();
    const d = document.createElement("div");
    d.id = "fk-rotulo";
    d.innerHTML = `<b>${n}</b><span><strong>${titulo}</strong><em>${sub}</em></span>`;
    d.style.cssText = "position:fixed;left:28px;bottom:28px;z-index:2147483647;display:flex;" +
      "gap:14px;align-items:center;padding:14px 22px 14px 14px;border-radius:16px;" +
      "background:rgba(14,10,34,.92);color:#fff;font:15px/1.3 system-ui,sans-serif;" +
      "box-shadow:0 12px 40px rgba(14,10,34,.35);border:1px solid rgba(171,164,255,.35)";
    const b = d.querySelector("b");
    b.style.cssText = "display:grid;place-items:center;width:38px;height:38px;border-radius:11px;" +
      "background:linear-gradient(135deg,#6C63FF,#e879f9);font-size:16px";
    d.querySelector("span").style.cssText = "display:flex;flex-direction:column;gap:2px";
    d.querySelector("em").style.cssText = "font-style:normal;opacity:.72;font-size:13px";
    document.body.appendChild(d);
  }, { n, titulo, sub });
}

// Las paginas del proyecto abren con la cabecera y la rejilla de pestañas, que
// ocupan casi toda la pantalla. El contenido se desplaza dentro de un contenedor
// propio (la carcasa es de altura fija), asi que se baja ESE contenedor hasta
// donde empieza el contenido.
async function alContenido(extra = 0) {
  await page.evaluate((extra) => {
    const navs = [...document.querySelectorAll('nav[aria-label="Otras vistas del proyecto"],' +
      'nav[aria-label="Vistas específicas categoría/arquetipo"],nav[aria-label="Secciones del proyecto"]')];
    const ultimo = navs.sort((a, b) => b.getBoundingClientRect().bottom - a.getBoundingClientRect().bottom)[0];
    let el = ultimo?.parentElement;
    while (el && !(el.scrollHeight > el.clientHeight + 4 &&
      /(auto|scroll)/.test(getComputedStyle(el).overflowY))) el = el.parentElement;
    const cont = el || document.scrollingElement;
    const delta = ultimo ? ultimo.getBoundingClientRect().bottom - cont.getBoundingClientRect().top - 12 : 0;
    cont.scrollBy({ top: Math.max(0, delta) + extra, behavior: "instant" });
  }, extra);
}

// `networkidle` no llega nunca: las paginas mantienen abierta una conexion SSE.
async function escena(url, n, titulo, sub, { espera = 2600, bajar = 0 } = {}) {
  await page.goto(`${BASE}${url}`, { waitUntil: "load", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1800);
  await alContenido();
  await page.waitForTimeout(300);
  await rotulo(n, titulo, sub);
  await page.evaluate(() => {
    const c = document.getElementById("fk-cortina");
    if (c) { c.style.opacity = "0"; setTimeout(() => c.remove(), 400); }
  });
  await page.waitForTimeout(400);
  await page.waitForTimeout(bajar ? espera / 2 : espera);
  if (bajar) {
    await page.evaluate((px) => {
      const c = [...document.querySelectorAll("*")].find((e) => e.scrollTop > 0) || document.scrollingElement;
      c.scrollBy({ top: px, behavior: "smooth" });
    }, bajar);
    await page.waitForTimeout(espera / 2);
  }
}

// ── Administración: el consultor recorre el ciclo ENS ──────────────────────
await context.addCookies(soloSesion(cookiesAdmin));
const P = `/admin/projects/${PID}`;
await escena("/admin/projects", "1", "Un operador, varios clientes", "Selector de proyectos · administración");
await escena(`${P}/workflow`, "2", "El ciclo ENS, fase a fase", "Puertas entre fases en el código");
await escena(`${P}/dimensiones`, "3", "Categorización", "Cinco dimensiones · Anexo I del RD 311/2022");
await escena(`${P}/magerit`, "4", "Análisis de riesgos", "MAGERIT v3 · activos, amenazas y salvaguardas", { bajar: 500 });
await escena(`${P}/dda`, "5", "Declaración de aplicabilidad", "73 medidas del Anexo II · 68 aplicables en MEDIA", { bajar: 600 });
await escena(`${P}/plan`, "6", "Plan de adecuación", "Hitos, dependencias y responsables");
await escena(`${P}/evidence`, "7", "Evidencias con custodia", "SHA-256 · firma Ed25519 · almacén WORM", { bajar: 400 });

// ── Cliente: ve, autoriza y firma ──────────────────────────────────────────
await context.clearCookies();
await context.addCookies(soloSesion(cookiesCliente));
await escena("/client-portal/dashboard", "8", "Portal de cliente", "El cliente ve, autoriza y firma · sin jerga");
await escena("/client-portal/firmas-hub", "9", "Firma electrónica", "Lienzo · eIDAS art. 25.1 · sello Ed25519");

// ── Auditor: sólo lectura, por enlace firmado ──────────────────────────────
await context.clearCookies();
await page.goto(`${BASE}${aud.portal_path}`, { waitUntil: "load" }).catch(() => {});
await page.waitForTimeout(1500);
const otp = page.getByTestId("auditor-otp-input");
if (await otp.isVisible().catch(() => false)) {
  await otp.fill(aud.otp);
  await page.getByTestId("auditor-otp-submit").click();
  await page.waitForTimeout(2000);
}
// La sesion del auditor vive en la memoria de la pestaña (una recarga pide el
// codigo otra vez): se entra por el menu del portal, como lo haria el auditor.
await page.getByRole("link", { name: /Cobertura DdA/ }).first().click().catch(() => {});
await page.waitForTimeout(3000);
await rotulo("10", "Portal del auditor", "Cobertura medida contra evidencias · sólo lectura");
await page.evaluate(() => document.getElementById("fk-cortina")?.remove());
await page.waitForTimeout(3600);

const video = await page.video().path();
await context.close();
await browser.close();
const destino = path.join(SALIDA, "recorrido.webm");
fs.renameSync(video, destino);
console.log(destino);
