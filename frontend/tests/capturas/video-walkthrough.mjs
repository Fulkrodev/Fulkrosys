// Vídeo walkthrough v3 · simbiosis admin↔cliente para la landing.
// Producto real (NovaEdge demo), 1080p, intro/outro de marca con logo, fuentes
// de marca, cursor animado recorriendo features. SIN rótulos incrustados (el
// texto explicativo va como HTML SOBRE el vídeo en el index). RGPD: 0 datos
// reales; saneo de jerga/códigos internos y de datos de relleno, conservando los
// términos ENS reales (ENS, MAGERIT, declaración de aplicabilidad, ENAC, SoA…).
//
// Correcciones v3 (feedback Marcos):
//  · Oculta el badge "1 error" / indicador dev de Next.js (nextjs-portal, toast,
//    build-watcher) — en el vídeo Y en las capturas (spec aparte).
//  · Sin fondo lila pegado: el cliente se autentica por COOKIES vía API
//    (POST /api/v1/client-auth/login) → ya no se procesa el login bajo la portada.
//  · Sin frames en blanco entre escenas: fondo oscuro en <html> desde
//    document_start → la navegación nunca destella blanco.
//  · Sin captions incrustadas: el vídeo es producto puro + intro/outro de marca.
import fs from "node:fs";
import path from "node:path";

import { chromium, request } from "@playwright/test";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const cfg = JSON.parse(fs.readFileSync(path.join(HERE, ".capturas-config.json"), "utf8"));
const PORT = process.env.PLAYWRIGHT_PORT || "3000";
const BASE = `http://localhost:${PORT}`;
const BACKEND = process.env.CAPTURAS_BACKEND || "http://localhost:8000";
const REPO = "/home/usuario/fulkro";
const VIDEO_DIR = `${REPO}/landing/assets/video`;
const FRAMES_DIR = `${REPO}/out/video_frames`;
const SIZE = { width: 1920, height: 1080 };
const DARK = "#0e0a22";
fs.mkdirSync(VIDEO_DIR, { recursive: true });
fs.mkdirSync(FRAMES_DIR, { recursive: true });

const LOGO = `<svg viewBox="0 0 96 96" style="width:100%;height:100%" aria-hidden="true"><polygon points="48,76 16,76 48,28" fill="#8B83FF"/><polygon points="48,76 80,76 48,28" fill="#c8c1ff"/><rect x="19" y="22.5" width="58" height="8.5" rx="4.25" fill="#fff"/><circle cx="48" cy="28" r="4.6" fill="#8B83FF"/></svg>`;

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: SIZE,
  recordVideo: { dir: VIDEO_DIR, size: SIZE },
  colorScheme: "light",
  deviceScaleFactor: 1,
});

// ── Init script en CADA documento (document_start) ──────────────────────────
//  1) Fondo <html> oscuro: durante la navegación (commit→primer paint) ya no
//     destella blanco bajo la portada.
//  2) Oculta el indicador dev de Next.js (badge "N error", toasts, build-watcher,
//     dev-tools button). El host vive en el DOM ligero → display:none lo elimina.
//  3) Flags de onboarding/tour/copiloto para arrancar sin overlays.
await context.addInitScript(() => {
  try {
    const s = document.createElement("style");
    s.id = "fk-nodev";
    s.textContent = `html{background:#0e0a22!important}
      nextjs-portal,[data-nextjs-toast],[data-nextjs-toast-wrapper],
      #__next-build-watcher,#__next-prerender-indicator,
      [data-next-badge-root],[data-next-badge],
      [data-nextjs-dev-tools-button],[data-nextjs-dev-tools],
      [data-nextjs-dialog-overlay]{display:none!important;visibility:hidden!important}
      [data-testid="copiloto-dock-toggle"],[data-testid="copiloto-dock-open"],
      [aria-label^="Abrir copiloto"]{display:none!important;visibility:hidden!important}`;
    (document.head || document.documentElement).appendChild(s);
  } catch { /* ignore */ }
  try {
    localStorage.setItem("fulkro_admin_tour_completed", "1");
    localStorage.setItem("fulkro_tutorial_completed", "1");
    localStorage.setItem("fulkro_client_onboarding_dismissed", "1");
    ["categorizacion-dimensiones", "magerit-analysis", "dda-applicability", "risks-register",
     "plan-adecuacion", "evidence-vault", "conformity-declaration", "dossier-enac", "roadmap-overview"]
      .forEach((id) => localStorage.setItem(`fulkro_copilot_guided_dismissed_${id}`, "1"));
  } catch { /* ignore */ }
});

// ── Auth admin (cookies) + proyecto activo rico sembrado ────────────────────
const rcAdmin = await request.newContext();
try { await rcAdmin.post(`${BACKEND}/api/v1/_dev/login-as-marcos`); } catch { /* ignore */ }
const stAdmin = await rcAdmin.storageState();
const adminCookies = stAdmin.cookies.filter((c) => c.name === "fulkro_session" || c.name === "fulkro_csrf");
const proj = { id: cfg.projectId, name: "Sede electrónica de NovaEdge", clientId: "", clientName: "NovaEdge S.L.", ensCategory: "MEDIA", status: "ACTIVE", lastAccessedAt: 0 };
try {
  const hr = await rcAdmin.get(`${BACKEND}/api/v1/projects/${cfg.projectId}/header`);
  if (hr.ok()) { const h = await hr.json(); if (h.cliente?.id) proj.clientId = h.cliente.id; }
} catch { /* ignore */ }
await rcAdmin.dispose();

// ── Auth cliente (cookies) vía API · sin mostrar el formulario de login ─────
let clientCookies = [];
try {
  const rcClient = await request.newContext();
  const lr = await rcClient.post(`${BACKEND}/api/v1/client-auth/login`, {
    data: { email: cfg.clientEmail, password: cfg.clientPassword },
  });
  if (lr.ok()) {
    const stClient = await rcClient.storageState();
    clientCookies = stClient.cookies.filter((c) => c.name === "fulkro_session" || c.name === "fulkro_csrf");
  } else {
    console.log("client-auth/login no-ok:", lr.status());
  }
  await rcClient.dispose();
} catch (e) { console.log("client login:", e.message); }

// Siembra del active-project-store (igual que loginAsMarcos · ADR-054).
await context.addInitScript(({ key, project }) => {
  try { localStorage.setItem(key, JSON.stringify({ state: { activeProject: project, lastUsedProjectId: project.id }, version: 0 })); } catch { /* ignore */ }
}, { key: "fulkro-active-project", project: proj });

// Pre-warm de rutas (Next dev compila on-demand): evita primeros frames vacíos.
try {
  const rcWarm = await request.newContext();
  await Promise.all([
    rcWarm.get(`${BASE}/admin/projects/${cfg.projectId}/dda`).catch(() => {}),
    rcWarm.get(`${BASE}/client-portal/dashboard`).catch(() => {}),
    rcWarm.get(`${BASE}/client-portal/firmas-hub`).catch(() => {}),
    rcWarm.get(`${BASE}/client-portal/conformidad`).catch(() => {}),
  ]);
  await rcWarm.dispose();
} catch { /* ignore */ }

const page = await context.newPage();

// ── Chrome de marca (post-hidratación, persiste): portada + cursor ──────────
const injectChrome = () => page.evaluate(() => {
  if (!document.getElementById("fk-fonts")) {
    const l = document.createElement("link");
    l.id = "fk-fonts"; l.rel = "stylesheet";
    l.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Bricolage+Grotesque:wght@600;700;800&display=swap";
    document.head.appendChild(l);
  }
  if (!document.getElementById("fk-style")) {
    const s = document.createElement("style");
    s.id = "fk-style";
    s.textContent = `
      #fk-cover{position:fixed;inset:0;z-index:2147483645;opacity:1;transition:opacity .26s ease,transform .4s cubic-bezier(.6,0,.32,1);pointer-events:none;overflow:hidden;background:#0e0a22}
      #fk-cover .bg{position:absolute;inset:-30%;background:radial-gradient(40% 40% at 30% 30%,#3a2d7a,transparent 70%),radial-gradient(45% 45% at 75% 65%,#2a1f63,transparent 70%),#0e0a22;animation:fkbg 9s ease-in-out infinite alternate}
      @keyframes fkbg{0%{transform:translate(0,0) scale(1)}100%{transform:translate(5%,-4%) scale(1.1)}}
      #fk-cursor{position:fixed;left:50%;top:50%;width:26px;height:26px;z-index:2147483647;pointer-events:none;transition:left .72s cubic-bezier(.4,0,.2,1),top .72s cubic-bezier(.4,0,.2,1);filter:drop-shadow(0 4px 7px rgba(0,0,0,.45))}
      #fk-cursor.click{animation:fkclick .4s ease}
      @keyframes fkclick{0%{transform:scale(1)}45%{transform:scale(.78)}100%{transform:scale(1)}}
      *::-webkit-scrollbar{width:0!important;height:0!important;display:none!important}*{scrollbar-width:none!important}
      [data-testid="agent-suggestion-banner"],[data-testid="agent-suggestion-tier-gated"]{display:none!important}
      [data-testid="copiloto-dock-toggle"],[data-testid="copiloto-dock-open"],[aria-label^="Abrir copiloto"]{display:none!important;visibility:hidden!important}
      nextjs-portal,[data-nextjs-toast],[data-nextjs-toast-wrapper],#__next-build-watcher,#__next-prerender-indicator,[data-next-badge-root],[data-next-badge],[data-nextjs-dev-tools-button],[data-nextjs-dev-tools]{display:none!important;visibility:hidden!important}
    `;
    document.head.appendChild(s);
  }
  if (!document.getElementById("fk-cover")) {
    const c = document.createElement("div"); c.id = "fk-cover";
    c.innerHTML = '<div class="bg"></div>';
    document.body.appendChild(c);
  } else if (!document.getElementById("fk-cover").querySelector(".bg")) {
    document.getElementById("fk-cover").innerHTML = '<div class="bg"></div>';
  }
  if (!document.getElementById("fk-cursor")) {
    const cur = document.createElement("div"); cur.id = "fk-cursor";
    cur.innerHTML = '<svg viewBox="0 0 24 24" style="width:100%;height:100%"><path d="M5 3l4.4 15.6 2.7-6.1 6.2-2.8z" fill="#fff" stroke="#1a1438" stroke-width="1.3" stroke-linejoin="round"/></svg>';
    document.body.appendChild(cur);
  }
});

const fontsReady = () => page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true).catch(() => true) : true)).catch(() => {});
const coverOn = () => page.evaluate((dark) => {
  let c = document.getElementById("fk-cover");
  if (!c) {
    c = document.createElement("div"); c.id = "fk-cover";
    c.style.cssText = `position:fixed;inset:0;z-index:2147483645;background:${dark};transition:opacity .26s ease;pointer-events:none;overflow:hidden`;
    c.innerHTML = `<div class="bg" style="position:absolute;inset:-30%;background:radial-gradient(40% 40% at 30% 30%,#3a2d7a,transparent 70%),radial-gradient(45% 45% at 75% 65%,#2a1f63,transparent 70%),${dark}"></div>`;
    (document.body || document.documentElement).appendChild(c);
  }
  c.style.opacity = "1"; c.style.transform = "scale(1)";
}, DARK);
const coverOff = () => page.evaluate(() => { const c = document.getElementById("fk-cover"); if (c) { c.style.opacity = "0"; c.style.transform = "scale(1.06)"; } });

// ── Saneo de jerga/relleno · conserva términos ENS reales ───────────────────
const scrub = () => page.evaluate(() => {
  document.querySelectorAll('[data-testid="agent-suggestion-banner"],[data-testid="agent-suggestion-tier-gated"],[data-testid="copiloto-dock-toggle"],[data-testid="copiloto-dock-open"]').forEach((el) => el.remove());
  document.querySelectorAll("div,section,header,aside,p").forEach((el) => {
    const t = el.textContent || "";
    const hide = t.includes("Siguiente paso:") || t.includes("Pendiente antes de avanzar") ||
      t.includes("enlaces rotos") || t.includes("Cadena de firmas con incidencias") || t.includes("CLUSTER ACTIONS") ||
      t.includes("Autorización de pentest externo"); // pentest es de ALTA, no MEDIA
    if (hide && t.length < 460 && el.offsetHeight > 0) el.style.display = "none";
  });
  // Documentos: número de relleno → 12
  document.querySelectorAll("div,span,p").forEach((el) => {
    if (/nuevos en los últimos/i.test(el.textContent || "")) {
      const card = el.closest("div")?.parentElement || el.parentElement;
      card?.querySelectorAll("*").forEach((n) => { if (n.children.length === 0 && /^\s*\d{2,5}\s*$/.test(n.textContent || "")) n.textContent = "12"; });
    }
  });
  // Panel interno de scaffolding de test (CLUSTER ACTIONS / FIXED-DEMO).
  document.querySelectorAll("div,section,aside,nav,ul").forEach((el) => {
    const t = el.textContent || "";
    if (/FIXED-DEMO|cluster actions/i.test(t) && t.length < 1600 && el.offsetHeight > 0) el.style.display = "none";
  });
  // Oculta SOLO la fila EXTRAS (jerga interna: Pentest MCPs, Documentos IDMS,
  // Topología de roles, Auditoría seca, Arquetipo…). El muro de pestañas se
  // recorta aparte (sólo cabecera + chips ENS).
  document.querySelectorAll("div,section,nav,ul").forEach((el) => {
    const t = el.textContent || "";
    if ((/Pentest MCPs/.test(t) || /Documentos IDMS/.test(t) || /Topología de roles/.test(t)) && t.length < 900 && el.offsetHeight > 0 && el.offsetHeight < 120) el.style.display = "none";
  });

  const SWAP = [
    [/\bpre_venta\b/g, "Preventa"], [/\bpost_venta\b/g, "Posventa"],
    [/\bcertificacion_enac\b/g, "Certificación ENAC"], [/\bcertificacion\b/g, "Certificación"],
    [/\bimplantacion\b/g, "Implantación"], [/\badecuacion\b/g, "Adecuación"],
    [/\s*\(?E-\d{3}\)?/g, ""], [/\bB0{8}\b/g, "B86727491"],
    [/tu workflow/gi, "tu proceso"], [/in-portal/gi, "en el portal"],
    [/Marcos te avisará/gi, "Te avisaremos"],
    [/Chat con Marcos/gi, "Chat con tu consultor"],
    [/\bOnboarding\b/g, "Bienvenida"], [/Conexiones cloud/gi, "Conexiones de nube"],
    [/\bRetainer\b/g, "Mantenimiento"], [/\bretainer\b/g, "mantenimiento"],
    [/Pentest MCPs/gi, "Verificación técnica"], [/Documentos IDMS/gi, "Documentos"],
    [/Auditoría seca/gi, "Auditoría interna"], [/Transparencia IA/gi, "Transparencia"],
    [/Topología de roles/gi, "Roles"],
    [/matagarciamarcos@gmail\.com/gi, "marcosmata@fulkro.es"],
    [/\bCERTIFIED\b/g, "Certificado"], [/\bACTIVE\b/g, "Activo"],
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
    for (const [re, to] of SWAP) v = v.replace(re, to);
    v = fixHash(v);
    if (v !== n.nodeValue) n.nodeValue = v;
  }
});

async function settle(short = false) {
  await page.locator("h1,h2,[role='heading']").first().waitFor({ state: "visible", timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(short ? 80 : 130);
}

// ESTABILIDAD antes de destapar/actuar: espera a que desaparezcan los esqueletos
// ("Cargando…") y da margen a que el indicador dev transitorio de hidratación
// ("N error") se borre solo. Así NUNCA grabamos la ventana inestable (el esqueleto
// que "pega un salto" al rellenarse + el badge transitorio). Es la cura de raíz
// del "parón brusco": no tapamos el error, esperamos a que la página esté estable.
async function waitStable(timeout = 5000) {
  await page.waitForFunction(() => {
    const b = document.body; if (!b) return false;
    return !/Cargando|Cargando…|Loading/i.test(b.innerText || "");
  }, { timeout }).catch(() => {});
  await page.waitForTimeout(620);
}

async function cursorTo(textOrLoc, wait = 800, click = false) {
  let box = null;
  try {
    const loc = typeof textOrLoc === "string" ? page.getByText(textOrLoc, { exact: false }).first() : textOrLoc;
    box = await loc.boundingBox({ timeout: 1500 });
  } catch { /* ignore */ }
  if (box) {
    const x = Math.round(box.x + Math.min(box.width / 2, 120));
    const y = Math.round(box.y + box.height / 2);
    await page.evaluate(({ x, y, click }) => {
      const c = document.getElementById("fk-cursor");
      if (c) { c.style.left = x + "px"; c.style.top = y + "px"; if (click) { c.classList.remove("click"); void c.offsetWidth; c.classList.add("click"); } }
    }, { x, y, click });
  }
  await page.waitForTimeout(wait);
}

// ── Navegación tapada (sin flash): cover → commit → cover → settle → chrome ──
async function go(url, short = false) {
  await coverOn();
  await page.waitForTimeout(140);
  await page.goto(`${BASE}${url}`, { waitUntil: "commit", timeout: 30000 }).catch(() => {});
  await coverOn();
  await settle(short);
  await waitStable();        // espera carga REAL bajo la portada (mata badge + esqueleto)
  await injectChrome();
  await coverOn();
  await fontsReady();
  await scrub();             // sanea el DOM ya ESTABLE (el saneo aguanta · no hay re-render)
}

// Escena por CARGA COMPLETA (con portada): navega tapada → ya estable → destapa →
// recorre con el cursor. `beats` = [[texto|locator, ms, click?], …].
async function scene(url, beats, shot, lead = 360, tail = 320) {
  await go(url, true);
  await coverOff();
  await page.waitForTimeout(lead);
  for (const b of beats) await cursorTo(b[0], b[1] ?? 700, b[2] ?? false);
  if (shot) await page.screenshot({ path: `${FRAMES_DIR}/${shot}.png` }).catch(() => {});
  await page.waitForTimeout(tail);
}

// Escena por NAVEGACIÓN SPA (clic en el menú · SIN recarga completa → sin badge
// transitorio, sin flash blanco, sin parón). El cursor va al menú, hace clic, la
// app transiciona, esperamos estable y saneamos el contenido nuevo. NO usa portada.
async function spaNav(linkName, beats, shot, tail = 320) {
  const link = page.getByRole("link", { name: linkName }).first();
  await cursorTo(link, 540, true);                       // cursor al menú + clic visual
  await link.click({ timeout: 4000 }).catch(() => {});
  // Espera a que aparezca el contenido DESTINO (primer beat) antes de seguir:
  // evita capturar la sección a mitad de transición.
  if (beats[0]) await page.getByText(beats[0][0], { exact: false }).first().waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  await waitStable();                                    // sin esqueletos + asentado
  await scrub();
  await page.waitForTimeout(240);
  for (const b of beats) await cursorTo(b[0], b[1] ?? 680, b[2] ?? false);
  if (shot) await page.screenshot({ path: `${FRAMES_DIR}/${shot}.png` }).catch(() => {});
  await page.waitForTimeout(tail);
}

// ── INTRO de marca (~1.5s) ──────────────────────────────────────────────────
await page.goto("about:blank");
await page.evaluate(({ logo, dark }) => {
  document.documentElement.style.background = dark;
  document.body.style.margin = "0";
  const l = document.createElement("link"); l.rel = "stylesheet";
  l.href = "https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Bricolage+Grotesque:wght@600;700;800&display=swap";
  document.head.appendChild(l);
  const c = document.createElement("div"); c.id = "fk-cover";
  c.style.cssText = `position:fixed;inset:0;overflow:hidden;background:${dark};transition:opacity .4s ease`;
  c.innerHTML = `<div style="position:absolute;inset:-30%;background:radial-gradient(40% 40% at 30% 30%,#3a2d7a,transparent 70%),radial-gradient(45% 45% at 75% 65%,#2a1f63,transparent 70%),${dark};animation:fkbg 9s ease-in-out infinite alternate"></div>
    <div id="fk-introcard" style="position:absolute;inset:0;display:grid;place-items:center;text-align:center;opacity:0;transform:translateY(8px);transition:opacity .5s ease,transform .5s ease">
      <div>
        <div style="display:flex;align-items:center;justify-content:center;gap:18px;margin-bottom:26px">
          <span style="width:64px;height:64px;display:inline-block">${logo}</span>
          <span style="font-family:'Bricolage Grotesque','Sora',system-ui;font-weight:800;font-size:54px;color:#fff;letter-spacing:-.02em">fulkro</span>
        </div>
        <div style="font-family:'Sora',system-ui;font-size:24px;color:#E4E1F6;font-weight:600">Plataforma de implantación y certificación del ENS</div>
        <div style="font-family:'Sora',system-ui;font-size:14px;color:#aba4ff;margin-top:14px;letter-spacing:.04em">Recorrido por el producto · datos de demostración</div>
      </div>
    </div>
    <style>@keyframes fkbg{0%{transform:translate(0,0) scale(1)}100%{transform:translate(5%,-4%) scale(1.1)}}</style>`;
  document.body.appendChild(c);
  requestAnimationFrame(() => { const k = document.getElementById("fk-introcard"); if (k) { k.style.opacity = "1"; k.style.transform = "none"; } });
}, { logo: LOGO, dark: DARK });
await page.waitForTimeout(1300);
await page.screenshot({ path: `${FRAMES_DIR}/00-intro.png` }).catch(() => {});

// ── ADMIN: la plataforma construye el ENS (sólo cabecera + chips ENS reales) ─
await context.addCookies(adminCookies);
await go(`/admin/projects/${cfg.projectId}/dda`, true);
// Recorta el MURO: oculta TODO lo posterior a la fila de chips (pestañas + fila
// EXTRAS con jerga interna + contenido). Sólo hermanos posteriores; jamás
// cabecera ni chips.
await page.evaluate(() => {
  window.scrollTo(0, 0);
  const chips = [...document.querySelectorAll("div,section")].find((el) => {
    const t = el.textContent || "";
    return /Categorización ENS/.test(t) && /Riesgos MAGERIT/.test(t) && t.length < 600;
  });
  if (chips) { let s = chips.nextElementSibling; while (s) { s.style.display = "none"; s = s.nextElementSibling; } }
});
await page.waitForTimeout(60);
await coverOff();
await page.waitForTimeout(300);
await cursorTo("Categorización ENS", 560, true);
await page.screenshot({ path: `${FRAMES_DIR}/01-admin-a.png` }).catch(() => {});
await cursorTo("Evidencias", 480, true);
await cursorTo("Riesgos MAGERIT", 620, true);
await page.screenshot({ path: `${FRAMES_DIR}/02-admin-b.png` }).catch(() => {});
await page.waitForTimeout(160);

// ── CLIENTE (cookies inyectadas · login nunca a la vista) ───────────────────
// UNA sola carga completa (dashboard, tapada + estable). El resto: navegación
// SPA real por el menú (sin recarga · sin badge transitorio · sin parón).
await context.clearCookies();
await context.addCookies(clientCookies);

// Dashboard: el cliente apenas trabaja · ve el avance de su certificación.
await scene(`/client-portal/dashboard`,
  [["No tienes pendientes", 720, false]], "03-cliente-dashboard", 380, 340);

// Cumplimiento: resumen sin tecnicismos · todo al día (SPA).
await spaNav(/Cumplimiento/,
  [["Todo al día", 660, false]], "04-cliente-cumplimiento", 320);

// Firmas: el trabajo ya hecho (DdA · 73 medidas del Anexo II + MAGERIT) · sólo
// aprobar y firmar, con validez legal (SPA).
await spaNav(/Firmas pendientes/,
  [["Declaración de Aplicabilidad", 700, false], ["Validación de activos MAGERIT", 600, true]], "05-cliente-firmas", 340);

// Mi certificación: el camino hasta la certificación ENAC (SPA).
await spaNav(/Mi certificación/,
  [["certificación ENS", 700, false]], "06-cliente-certificacion", 380);

// ── OUTRO de marca (~2.2s) ──────────────────────────────────────────────────
await coverOn();
await page.evaluate(() => { const c = document.getElementById("fk-cursor"); if (c) c.style.display = "none"; });
await page.waitForTimeout(210);
await page.evaluate((logo) => {
  const c = document.getElementById("fk-cover");
  if (!c) return;
  c.innerHTML = `<div class="bg" style="position:absolute;inset:-30%;background:radial-gradient(40% 40% at 30% 30%,#3a2d7a,transparent 70%),radial-gradient(45% 45% at 75% 65%,#2a1f63,transparent 70%),#0e0a22;animation:fkbg 9s ease-in-out infinite alternate"></div>
    <div id="fk-outro" style="position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:24px;opacity:0;transform:translateY(8px);transition:opacity .55s ease,transform .55s ease">
      <div>
        <div style="width:56px;height:56px;margin:0 auto 22px">${logo}</div>
        <div style="font-family:'Bricolage Grotesque','Sora',system-ui;font-size:42px;font-weight:800;line-height:1.2;color:#FCFCFF;max-width:820px;margin:0 auto">Hecho por una plataforma.<br>Revisado por expertos.</div>
        <div style="font-family:'Sora',system-ui;margin-top:22px;font-size:21px;color:#E4E1F6">La tercera vía del Esquema Nacional de Seguridad.</div>
      </div>
    </div>`;
  requestAnimationFrame(() => { const o = document.getElementById("fk-outro"); if (o) { o.style.opacity = "1"; o.style.transform = "none"; } });
}, LOGO);
await page.waitForTimeout(480);
await page.screenshot({ path: `${FRAMES_DIR}/06-outro.png` }).catch(() => {});
await page.waitForTimeout(1050);

// ── Cierre ──────────────────────────────────────────────────────────────────
const video = page.video();
await context.close();
try {
  const raw = video ? await video.path() : null;
  if (raw && fs.existsSync(raw)) { fs.renameSync(raw, `${VIDEO_DIR}/walkthrough.webm`); console.log("webm:", `${VIDEO_DIR}/walkthrough.webm`); }
} catch (e) { console.log("rename webm:", e.message); }
await browser.close();
console.log("frames en", FRAMES_DIR);
