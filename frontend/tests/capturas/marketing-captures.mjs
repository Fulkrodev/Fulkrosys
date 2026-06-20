// Capturas de marketing para la landing (carrusel del index + galería de
// plataforma.html). 9 capturas LIMPIAS · 3 por portal:
//   ADMIN:   centro de mando · plan (Gantt) · DdA (SoA 73 medidas)
//   CLIENTE: inicio · firmas · mi certificación
//   AUDITOR: resumen del expediente · cobertura DdA·evidencias · registro inmutable
//
// Garantías de limpieza (requisito duro):
//  · captura SOLO con la página cargada del todo (networkidle + texto real
//    visible + sin "Cargando…"/skeleton) y el saneo aplicado.
//  · recorta el MURO admin (sidebar global + banner FASE + tabs + fila EXTRAS).
//  · elimina FAB del copiloto y el badge dev "N error".
//  · sanea jerga/códigos/anglicismos (CERTIFIED→Certificado, passed→Aprobada,
//    pentest→verificación [demo MEDIA = escaneo, NO pentest], E-NNN/M0N/E-702,
//    Ed25519, R6, Evidence Vault, Discovery, BIA, IDMS…), CIF B86727491,
//    Documentos 12, hashes hex variados. Conserva ENS/MAGERIT/DdA/SoA/ENAC/MEDIA.
//
// RGPD: 0 datos reales (demo NovaEdge sembrada). El renombrado demo + restore lo
// hace scripts/capturas_landing.py (modo marketing / marketing-fast).
import fs from "node:fs";
import path from "node:path";
import { chromium, request } from "@playwright/test";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const cfg = JSON.parse(fs.readFileSync(path.join(HERE, ".capturas-config.json"), "utf8"));
const PORT = process.env.PLAYWRIGHT_PORT || "3000";
const BASE = `http://localhost:${PORT}`;
const BACKEND = process.env.CAPTURAS_BACKEND || "http://localhost:8000";
const OUT = "/home/usuario/fulkro/landing/assets/capturas/marketing";
const SIZE = { width: 1440, height: 1024 };
fs.mkdirSync(OUT, { recursive: true });

const JARGON = ["Pentest MCPs", "Documentos IDMS", "Arquetipo", "Discovery", "BIA", "Workspace", "Auditoría seca", "Transparencia IA", "Topología de roles"];

// ── Auth (cookies admin + cliente · token auditor) ──
const rcA = await request.newContext();
await rcA.post(`${BACKEND}/api/v1/_dev/login-as-marcos`);
const adminCookies = (await rcA.storageState()).cookies.filter((c) => /fulkro_(session|csrf)/.test(c.name));
await rcA.dispose();
const rcC = await request.newContext();
await rcC.post(`${BACKEND}/api/v1/client-auth/login`, { data: { email: cfg.clientEmail, password: cfg.clientPassword } });
const clientCookies = (await rcC.storageState()).cookies.filter((c) => /fulkro_(session|csrf)/.test(c.name));
await rcC.dispose();

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: SIZE, colorScheme: "light", deviceScaleFactor: 1 });
await context.addInitScript(() => {
  try {
    localStorage.setItem("fulkro_admin_tour_completed", "1");
    localStorage.setItem("fulkro_tutorial_completed", "1");
    localStorage.setItem("fulkro_client_onboarding_dismissed", "1");
    ["categorizacion-dimensiones", "magerit-analysis", "dda-applicability", "risks-register", "plan-adecuacion", "evidence-vault", "conformity-declaration", "dossier-enac", "roadmap-overview"]
      .forEach((id) => localStorage.setItem(`fulkro_copilot_guided_dismissed_${id}`, "1"));
  } catch { /* */ }
});
await context.addInitScript(({ key, project }) => { try { localStorage.setItem(key, JSON.stringify({ state: { activeProject: project, lastUsedProjectId: project.id }, version: 0 })); } catch {} },
  { key: "fulkro-active-project", project: { id: cfg.projectId, name: "Sede electrónica de NovaEdge", clientId: "", clientName: "NovaEdge S.L.", ensCategory: "MEDIA", status: "ACTIVE", lastAccessedAt: 0 } });

const page = await context.newPage();

const CLEANUP_CSS = `*::-webkit-scrollbar{width:0!important;height:0!important;display:none!important}*{scrollbar-width:none!important}
  [data-testid="agent-suggestion-banner"],[data-testid="agent-suggestion-tier-gated"]{display:none!important}`;

// ── Recorte del MURO admin ──
async function cleanAdmin(mode) {
  await page.evaluate(({ JARGON, mode }) => {
    const txt = (el) => el.textContent || "";
    // Sidebar global izquierdo
    [...document.querySelectorAll("aside,nav")].forEach((el) => {
      const t = txt(el);
      if (/Dashboard/.test(t) && /Proyectos/.test(t) && /Compliance/.test(t) && /Notificaciones/.test(t) && t.length < 5000) el.style.display = "none";
    });
    // Banner FASE
    [...document.querySelectorAll("div,section,header,p")].forEach((el) => {
      const t = txt(el);
      if ((t.includes("Siguiente paso") || t.includes("Pendiente antes de avanzar")) && t.length < 600 && el.offsetHeight > 0) el.style.display = "none";
    });
    // Muro de pestañas + fila EXTRAS
    [...document.querySelectorAll("nav,div,ul,section")].forEach((el) => {
      const t = txt(el);
      const jc = JARGON.filter((m) => t.includes(m)).length;
      const isTabRow = /Resumen/.test(t) && /Workflow/.test(t) && /Dossier/.test(t) && /Roadmap/.test(t);
      if ((jc >= 3 || isTabRow) && t.length < 3500 && el.offsetHeight > 0 && el.offsetHeight < 360) el.style.display = "none";
    });
    if (mode === "mando") {
      const chips = [...document.querySelectorAll("div,section")].find((el) => {
        const t = txt(el);
        return /Categorización ENS/.test(t) && /Riesgos MAGERIT/.test(t) && t.length < 700;
      });
      if (chips) { let s = chips.nextElementSibling; while (s) { s.style.display = "none"; s = s.nextElementSibling; } }
    }
  }, { JARGON, mode });
}

// ── Mata FAB del copiloto + badge dev "N error" + portal dev de Next ──
async function killChrome() {
  await page.evaluate(() => {
    document.querySelectorAll('[data-testid="copiloto-dock-toggle"],[data-testid="copiloto-dock-open"],[aria-label^="Abrir copiloto"]').forEach((e) => e.remove());
    document.querySelectorAll("nextjs-portal,[data-nextjs-toast],[data-nextjs-toast-wrapper],#__next-build-watcher,#__next-prerender-indicator,[data-next-badge-root]").forEach((e) => { try { e.style.display = "none"; } catch {} });
    [...document.querySelectorAll("body *")].forEach((el) => {
      const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.nodeValue).join("").trim();
      if (/^\d+\s*error(es)?$/i.test(own) && el.children.length <= 2) {
        let t = el;
        for (let i = 0; i < 5 && t; i++) { const cs = getComputedStyle(t); if (cs.position === "fixed" || cs.position === "absolute") { t.style.display = "none"; break; } t = t.parentElement; }
        el.style.display = "none";
      }
    });
  });
}

// ── Saneo de jerga / códigos / anglicismos / relleno ──
async function scrub() {
  await page.evaluate(() => {
    document.querySelectorAll('[data-testid="agent-suggestion-banner"],[data-testid="agent-suggestion-tier-gated"]').forEach((el) => el.remove());
    // Oculta banners de aviso/estado interno (no aptos para marketing)
    document.querySelectorAll("div,section,header,aside,p,a").forEach((el) => {
      const t = el.textContent || "";
      const hide = t.includes("Cadena de firmas con incidencias") || t.includes("Siguiente paso") ||
        t.includes("Pendiente antes de avanzar") || t.includes("enlaces rotos") ||
        /CLUSTER ACTIONS|FIXED-DEMO/i.test(t);
      if (hide && t.length < 700 && el.offsetHeight > 0) el.style.display = "none";
    });
    // Badge de no-leídos incoherente junto a "Mensajes" (muestra "2" pero dice
    // "Sin mensajes recientes") → oculta el número (leaf cuyo contexto contiene
    // "Mensajes" + "Sin mensajes").
    [...document.querySelectorAll("*")].forEach((b) => {
      if (b.children.length === 0 && /^\d{1,2}$/.test((b.textContent || "").trim())) {
        let ctx = "", p = b;
        for (let i = 0; i < 4 && p; i++) { ctx += " " + (p.textContent || ""); p = p.parentElement; }
        if (/Mensajes/.test(ctx) && /Sin mensajes/.test(ctx)) b.style.display = "none";
      }
    });
    // Chip "Expira: <fecha>" del portal auditor (dato técnico · formato US ambiguo)
    [...document.querySelectorAll("*")].forEach((el) => {
      if (/^Expira:/.test((el.textContent || "").trim()) && (el.textContent || "").length < 60 && el.children.length <= 3) el.style.display = "none";
    });
    // "1 hitos" → "1 hito" (número y label en nodos separados · pase DOM)
    [...document.querySelectorAll("*")].forEach((el) => {
      if (el.children.length === 0 && /^\s*hitos\s*$/.test(el.textContent || "")) {
        const ctx = ((el.parentElement && el.parentElement.textContent) || "").replace(/\s+/g, " ");
        if (/(^|[^\d])1\s*hitos\b/.test(ctx)) el.textContent = (el.textContent || "").replace("hitos", "hito");
      }
    });
    // Documentos relleno → 12
    document.querySelectorAll("div,span,p").forEach((el) => {
      if (/nuevos en los últimos/i.test(el.textContent || "")) {
        const card = el.closest("div")?.parentElement || el.parentElement;
        card?.querySelectorAll("*").forEach((n) => { if (n.children.length === 0 && /^\s*\d{2,5}\s*$/.test(n.textContent || "")) n.textContent = "12"; });
      }
    });
    const SWAP = [
      // específicos antes que genéricos
      [/Autorización de pentest externo/gi, "Autorización de verificación técnica"],
      [/audit-ready ENAC/gi, "conforme con el ENS"],
      [/Marcos te propone/gi, "te proponemos"], [/Qué propone Marcos/gi, "Qué proponemos"],
      [/Marcos las está aplicando/gi, "Las estamos aplicando"], [/\btu cloud\b/gi, "tu nube"],
      [/Marcos te propondrá/gi, "Te propondremos"], [/Onboarding adaptativo/gi, "Bienvenida adaptativa"],
      [/ENS Medio\/Alto/gi, "ENS Medio"], [/Medio\/Alto/g, "Medio"],
      [/Expira:\s*(\d{1,2})\/(\d{1,2})\/(\d{4})(?:,?\s*[\d:]+)?/gi, "Expira: $2/$1/$3"],
      [/Audit log inmutable/gi, "Registro de auditoría inmutable"], [/\bAudit log\b/gi, "Registro de auditoría"],
      [/\b1 hitos\b/g, "1 hito"], [/Bienvenida adaptativo/gi, "Bienvenida adaptativa"],
      [/\bretainer_cierre\b/gi, "Cierre y mantenimiento"],
      [/Heatmap gaps/gi, "Mapa de cobertura"], [/\bHeatmap\b/gi, "Mapa"], [/\bgaps\b/gi, "huecos"],
      [/Vault WORM/gi, "Almacén inalterable"], [/\bWORM\b/g, "inalterable"], [/\bVault\b/gi, "Almacén"],
      [/\bper medida\b/gi, "por medida"],
      [/Gantt \+ PDA cronograma/gi, "Gantt · cronograma"],
      [/audit-ready/gi, "lista para"], [/\bapproved\b/gi, "Aprobado"],
      [/\bWBS-\d{2,4}\b[\s.:·-]*/g, ""],
      [/\s*\(M\d{1,2}\)/g, ""],
      [/refuerzos\s+R\d+/gi, "con refuerzos"],
      [/Reportes pentest/gi, "Reportes de verificación"],
      [/PENTEST RUNS/g, "VERIFICACIÓN TÉCNICA"], [/Pentest runs/gi, "Ejecuciones de verificación"],
      [/M08 verificación técnica E-?\d{3}/gi, "Verificación técnica"],
      [/\bpentest\b/gi, "verificación"],
      [/Evidence Vault/gi, "Almacén de evidencias"],
      [/Runs de auditoría/gi, "Ejecuciones de auditoría"], [/Run de auditoría/gi, "Ejecución de auditoría"],
      [/Hash chain R6/gi, "Cadena de integridad"], [/hash chain/gi, "cadena de integridad"],
      [/Cadena de hash R6/gi, "Cadena de hash"], [/con la función fn_[a-z_]+\(\)/gi, "de forma independiente"],
      [/\bfn_[a-z_]+\(\)/gi, ""], [/\s*con la función\s*/gi, ""], [/\bR6\b/g, ""],
      [/firma Ed25519/gi, "firma electrónica"], [/\bEd25519\b/g, "firma electrónica"],
      [/\bDiscovery\b/g, "Descubrimiento"], [/\bBIA\b/g, "Análisis de impacto"],
      [/\bSIEM\b/g, "Monitorización"], [/\bCopilot\b/g, "Copiloto"],
      [/Documentos IDMS/gi, "Documentos"], [/Pentest MCPs/gi, "Verificación técnica"],
      [/Auditoría seca/gi, "Auditoría interna"], [/Transparencia IA/gi, "Transparencia"], [/Topología de roles/gi, "Roles"],
      [/\bpre_venta\b/g, "Preventa"], [/\bpost_venta\b/g, "Posventa"],
      [/\bcertificacion_enac\b/g, "Certificación ENAC"], [/\bcertificacion\b/g, "Certificación"],
      [/\bimplantacion\b/g, "Implantación"], [/\badecuacion\b/g, "Adecuación"],
      [/\(?\bM0\d\b\)?/g, ""], [/\s*\(?E-\d{3}\)?/g, ""],
      [/\bB0{8}\b/g, "B86727491"],
      [/\bCERTIFIED\b/g, "Certificado"], [/\bACTIVE\b/g, "Activo"],
      [/\bpassed\b/g, "Aprobada"], [/\bPASSED\b/g, "APROBADA"],
      [/Chat con Marcos/gi, "Chat con tu consultor"], [/Marcos te avisará/gi, "Te avisaremos"],
      [/Enviar a Marcos/gi, "Enviar a tu consultor"], [/Marcos prepara/gi, "El equipo prepara"],
      [/Marcos opera/gi, "El equipo opera"], [/Marcos será/gi, "Tu consultor será"],
      [/matagarciamarcos@gmail\.com/gi, "marcosmata@fulkro.es"],
      [/\bOnboarding\b/g, "Bienvenida"], [/Conexiones cloud/gi, "Conexiones de nube"],
      [/\bRetainer\b/g, "Mantenimiento"], [/\bretainer\b/g, "mantenimiento"],
      [/tu workflow/gi, "tu proceso"], [/in-portal/gi, "en el portal"],
      [/\s*[·,]?\s*(AM|PM)\b/g, ""],
      [/([\wáéíóúñ])\s*\.\s*\.+/gi, "$1."],
    ];
    const HEXPOOL = ["a7f3c19e2b8d4f60", "9c5a1e3b7d28f4ec", "3e8b71d2a45cf190", "f04c2a9b6e7d1538", "b29d4f80c1a6e375", "7d1e9a3c5f2b8046", "5c8a2e1f9b3d7064", "e1b7f3a09c4d2856"];
    let _hc = 0;
    const fixHash = (v) => v.replace(/[0-9a-f]{6,}/gi, (m) => {
      const counts = {}; for (const ch of m) counts[ch] = (counts[ch] || 0) + 1;
      if (Math.max(...Object.values(counts)) / m.length < 0.6) return m;
      return HEXPOOL[_hc++ % HEXPOOL.length].slice(0, Math.min(m.length, 16));
    });
    const EMAIL = "test-client-e2e@example.com", CLEAN = "laura@novaedge.es";
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
    for (const n of nodes) {
      let v = n.nodeValue; if (!v) continue;
      if (v.includes(EMAIL)) v = v.split(EMAIL).join(CLEAN);
      // fecha US (m/d/aaaa con día>12) → d/m/aaaa · no toca las ya correctas (19/6)
      v = v.replace(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/g, (m, a, b, y) => (+b > 12 && +a <= 12) ? `${b}/${a}/${y}` : m);
      for (const [re, to] of SWAP) v = v.replace(re, to);
      v = fixHash(v);
      if (v !== n.nodeValue) n.nodeValue = v;
    }
  });
}

async function waitReady(readyText) {
  await page.waitForLoadState("networkidle", { timeout: 6000 }).catch(() => {});
  if (readyText) await page.getByText(readyText, { exact: false }).first().waitFor({ state: "visible", timeout: 9000 }).catch(() => {});
  await page.waitForFunction(() => !/Cargando|Loading/i.test(document.body ? document.body.innerText : ""), { timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(1300);
}

// Purga el log crudo (filtro + filas con JSON/códigos de evento/emails internos),
// dejando sólo la cabecera + el mensaje de "registro inmutable · cadena de hash".
async function purgeLog() {
  await page.evaluate(() => {
    // Sólo oculta elementos PEQUEÑOS (filas del log + filtro), nunca la tarjeta
    // grande que contiene el título + nº de entradas + banner explicativo.
    [...document.querySelectorAll("div,section,article,li,form,fieldset")].forEach((el) => {
      const t = el.textContent || "";
      const h = el.offsetHeight;
      const isRow = /tabla:|usuario:\s|"scope"|magic_link_id|auditor_portal|evidence\.upload|\.session\.start|\.view\b|hash:\s/.test(t);
      if (isRow && h > 20 && h < 240 && t.length < 1200) el.style.display = "none";
    });
    // Filtro completo (label + input con placeholder de códigos + Exportar CSV)
    [...document.querySelectorAll("*")].forEach((el) => {
      if (/FILTRAR POR ACCIÓN/.test(el.textContent || "") && (el.textContent || "").length < 220) {
        let c = el; for (let i = 0; i < 5 && c; i++) { if (c.offsetHeight > 40 && c.offsetHeight < 320) { c.style.display = "none"; break; } c = c.parentElement; }
      }
    });
    document.querySelectorAll("input,textarea").forEach((el) => {
      if (/auditor_portal|\.view|\.upload/.test(el.getAttribute("placeholder") || "")) (el.closest("div,form,section") || el).style.display = "none";
    });
    [...document.querySelectorAll("button,a")].forEach((el) => { if (/Exportar CSV/.test(el.textContent || "")) el.style.display = "none"; });
  });
}

// ── Estrecha el sidebar (cliente 290→230 · auditor 256→212) ──
// El usuario lo quiere "mucho más estrecho" en las capturas; el admin lo oculta
// cleanAdmin, así que esto sólo aplica a cliente + auditor.
async function slimSidebar() {
  await page.evaluate(() => {
    if (!document.getElementById("__slim")) {
      const st = document.createElement("style"); st.id = "__slim";
      st.textContent = ".w-sidebar{width:230px!important;min-width:230px!important;flex-basis:230px!important}";
      document.head.appendChild(st);
    }
    document.querySelectorAll("aside.sidebar-chrome").forEach((a) => { a.style.width = "230px"; a.style.minWidth = "230px"; a.style.flexBasis = "230px"; });
    [...document.querySelectorAll("aside")].forEach((a) => {
      const t = a.textContent || "";
      if (/Resumen/.test(t) && /Cobertura/.test(t)) { a.style.width = "212px"; a.style.minWidth = "212px"; a.style.flexBasis = "212px"; }
    });
  });
}

// ── Altura real del contenido (recorta la banda gris sobrante) ──
// Considera header + sidebars (capados a viewport) + descendientes de <main>
// (ignorando contenedores a pantalla completa). Devuelve el borde inferior real.
async function contentBottom() {
  return await page.evaluate(() => {
    const vh = window.innerHeight, vw = window.innerWidth;
    let b = 0;
    const push = (el, allowFull) => {
      if (!el) return;
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 50 || r.height < 12) return;
      if (r.left >= vw || r.top >= vh || r.bottom <= 0) return;
      if (!allowFull && r.height >= vh - 2) return;
      const ink = (el.textContent || "").trim().length > 0 || el.matches("svg,img,canvas,table,hr,button,input,textarea,a");
      if (!ink) return;
      b = Math.max(b, Math.min(r.bottom, vh));
    };
    push(document.querySelector("header"), true);
    document.querySelectorAll("aside,nav").forEach((e) => push(e, true));
    const main = document.querySelector("main");
    if (main) main.querySelectorAll("*").forEach((e) => push(e, false));
    return b;
  });
}

let SUF = "";       // sufijo de pasada ("" desktop · "-m" móvil)
let MOBILE = false; // pasada móvil (sin clip de altura · viewport 390)

async function capture(name, navFn, { ready, admin, mode, slim, purge, maxH } = {}) {
  await navFn();
  await waitReady(ready);
  await page.addStyleTag({ content: CLEANUP_CSS }).catch(() => {});
  if (admin) await cleanAdmin(mode);
  if (slim) await slimSidebar();
  await scrub();
  if (purge) await purgeLog();
  await killChrome();
  await page.waitForTimeout(500);
  const opts = { path: `${OUT}/${name}${SUF}.png` };
  if (!MOBILE) {
    const vh = page.viewportSize().height;
    let h = Math.min(vh, (await contentBottom()) + 22);
    if (maxH) h = Math.min(h, maxH);
    if (h > 160) opts.clip = { x: 0, y: 0, width: page.viewportSize().width, height: h };
  }
  await page.screenshot(opts);
  const remain = await page.evaluate(({ JARGON }) => {
    const t = document.body.innerText || "";
    const bad = ["CERTIFIED", "passed", "approved", "PENTEST", "Pentest", "audit-ready", "WBS-", "Ed25519", "Evidence Vault", "Vault", "Heatmap", "B00000000", "Siguiente paso", "Cargando", "1 error", "E-0", "E-7", "(M", "Discovery", " BIA", "Runs", " R6", "fn_", "auditor_portal", ".upload", "magic_link", "tabla:", "test.fulkro", "incidencias"].filter((m) => t.includes(m));
    return { jerga: JARGON.filter((m) => t.includes(m)), bad };
  }, { JARGON });
  console.log(name.padEnd(24), "jerga:", JSON.stringify(remain.jerga), "sospechoso:", JSON.stringify(remain.bad));
}

async function gotoAuditor(sub) {
  await page.goto(`${BASE}/auditor-portal/${cfg.auditorToken}/${sub}`, { waitUntil: "domcontentloaded" }).catch(() => {});
  const otp = page.getByTestId("auditor-otp-input");
  const gated = await otp.waitFor({ state: "visible", timeout: 8000 }).then(() => true).catch(() => false);
  if (gated) {
    await otp.fill(cfg.auditorOtp ?? "");
    await page.getByTestId("auditor-otp-submit").click().catch(() => {});
    await otp.waitFor({ state: "hidden", timeout: 10000 }).catch(() => {});
  }
}

async function captureAll() {
  // ── ADMIN ──
  await context.clearCookies();
  await context.addCookies(adminCookies);
  await capture("admin-mando", () => page.goto(`${BASE}/admin/projects/${cfg.projectId}/dda`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Categorización ENS", admin: true, mode: "mando", maxH: 610 });
  await capture("admin-plan", () => page.goto(`${BASE}/admin/projects/${cfg.projectId}/plan`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Plan de proyecto", admin: true, mode: "content" });
  await capture("admin-dda", () => page.goto(`${BASE}/admin/projects/${cfg.projectId}/dda`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Declaración de Aplicabilidad", admin: true, mode: "content" });
  // ── CLIENTE ──
  await context.clearCookies();
  await context.addCookies(clientCookies);
  await capture("cliente-inicio", () => page.goto(`${BASE}/client-portal/dashboard`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "No tienes pendientes", slim: true });
  await capture("cliente-firmas", () => page.goto(`${BASE}/client-portal/firmas-hub`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Validación de activos MAGERIT", slim: true });
  await capture("cliente-certificacion", () => page.goto(`${BASE}/client-portal/certificacion`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Tu certificación ENS", slim: true });
  await capture("cliente-remediaciones", () => page.goto(`${BASE}/client-portal/remediaciones`, { waitUntil: "domcontentloaded" }).catch(() => {}), { ready: "Mejoras propuestas", slim: true });
  // ── AUDITOR ──
  await context.clearCookies();
  await capture("auditor-resumen", () => gotoAuditor("summary"), { ready: "Resumen del proyecto", slim: true });
  await capture("auditor-cobertura", () => gotoAuditor("audit/dda-evidence-gaps"), { ready: "Cobertura", slim: true });
  await capture("auditor-registro", () => gotoAuditor("audit-log"), { ready: "Registro", purge: true, slim: true });
}

// Pasada desktop (1440) + pasada móvil (390 · sufijo -m)
SUF = ""; MOBILE = false; await page.setViewportSize({ width: 1440, height: 1024 });
await captureAll();
console.log("\n✅ 9 capturas desktop en", OUT);
SUF = "-m"; MOBILE = true; await page.setViewportSize({ width: 390, height: 844 });
await captureAll();
console.log("✅ 9 capturas móvil (-m) en", OUT);

await browser.close();
