/**
 * Comprueba, contra el demo levantado, cada cosa que USAGE.md dice que se vera.
 *
 * Por que existe: USAGE.md es un recorrido guiado y su criterio de aceptacion es
 * que alguien que no conoce el repositorio lo siga entero y termine sabiendo que
 * hace la plataforma. Un documento asi envejece mal en silencio: basta que una
 * pantalla cambie un rotulo o que el sembrado cambie un numero para que el
 * recorrido mande a la gente a sitios que ya no dicen eso. Este script lo mide.
 *
 * NO lee el codigo de la aplicacion: navega como lo haria una persona, con las
 * mismas URL, las mismas credenciales y los mismos rotulos que USAGE.md escribe.
 *
 * Uso (con el demo en pie · `make demo`):
 *
 *   SECRETO_TOTP="$(docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -tA \
 *      -c "SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u ON u.id=s.user_id \
 *          WHERE u.email='demo@fulkro.es' AND s.verified LIMIT 1;" | tr -d '[:space:]')" \
 *   NODE_PATH=frontend/node_modules node scripts/verificar_recorrido_usage.cjs
 *
 * Sale 0 si todo lo que USAGE.md promete esta ahi; 1 en cuanto algo no lo esta.
 */
// CommonJS a proposito: los modulos ESM NO respetan NODE_PATH, y playwright
// vive en frontend/node_modules, no en la raiz.
const { chromium } = require('playwright');
const crypto = require('node:crypto');

const BASE = process.env.DEMO_URL || 'http://localhost:3000';
const API = process.env.BACKEND_URL || 'http://127.0.0.1:18000';
const CORREO = process.env.FULKRO_DEMO_OWNER_EMAIL || 'demo@fulkro.es';
const CLAVE = process.env.FULKRO_DEMO_OWNER_PASSWORD || 'fulkro-demo-2026';
const SECRETO = process.env.SECRETO_TOTP;

let ok = 0;
let mal = 0;
const bien = (q, d = '') => { ok++; console.log(`  OK     ${q.padEnd(46)} ${d}`); };
const falla = (q, d = '') => { mal++; console.log(`  FALLO  ${q.padEnd(46)} ${d}`); };
const comprobar = (cond, q, d = '') => (cond ? bien(q, d) : falla(q, d));
const titulo = (t) => console.log(`\n${t}`);

function totp(secreto) {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const c of secreto.replace(/=+$/, '').toUpperCase()) {
    const i = A.indexOf(c);
    if (i >= 0) bits += i.toString(2).padStart(5, '0');
  }
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.substr(i, 8), 2));
  const contador = Buffer.alloc(8);
  contador.writeUInt32BE(Math.floor(Date.now() / 1000 / 30), 4);
  const h = crypto.createHmac('sha1', Buffer.from(bytes)).update(contador).digest();
  const o = h[h.length - 1] & 0xf;
  const v = ((h[o] & 0x7f) << 24 | (h[o + 1] & 0xff) << 16
             | (h[o + 2] & 0xff) << 8 | (h[o + 3] & 0xff)) % 1000000;
  return String(v).padStart(6, '0');
}

const texto = async (p) =>
  (await p.locator('body').innerText()).replace(/\s*\n\s*/g, ' / ').replace(/ {2,}/g, ' ');

async function main() {
  if (!SECRETO) {
    console.error('Falta SECRETO_TOTP (ver la cabecera de este fichero).');
    process.exit(2);
  }
  const nav = await chromium.launch();
  const ctx = await nav.newContext({ viewport: { width: 1600, height: 1000 } });
  const p = await ctx.newPage();

  // ── 1 · entrar como operador ──────────────────────────────────────────
  titulo('1 · entrar como operador');
  await p.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', CORREO);
  await p.fill('input[type="password"]', CLAVE);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(3000);
  const pideCodigo = (await texto(p)).includes('Código TOTP');
  comprobar(pideCodigo, 'la entrada pide un segundo factor', 'campo de 6 digitos');
  await p.locator('input:visible').first().fill(totp(SECRETO));
  await p.locator('button:visible').first().click();
  await p.waitForTimeout(5000);
  const selector = await texto(p);
  comprobar(p.url().includes('/admin/projects'),
    'entra y aterriza en el selector de proyectos', p.url().replace(BASE, ''));
  for (const cliente of ['NovaEdge S.L.', 'MicroServicios del Sur',
                         'DataForma Galicia', 'InfraCrítica Iberia']) {
    comprobar(selector.includes(cliente), `el selector lista «${cliente}»`);
  }
  comprobar(/TOUR ADMIN/i.test(selector), 'aparece el tour de 6 pasos');

  // ── 2 · alta de cliente ───────────────────────────────────────────────
  titulo('2 · dar de alta un cliente');
  // El tour tapa la pagina: USAGE.md dice que se puede saltar, asi que se salta.
  const saltar = p.getByRole('button', { name: /^Saltar$/i }).first();
  if (await saltar.count() > 0) { await saltar.click(); await p.waitForTimeout(1500); }
  // «Alta de cliente nuevo», NO «Nuevo proyecto»: son dos botones distintos y
  // hacen cosas distintas. USAGE.md lo avisa; aqui se comprueba que el enlace
  // existe de verdad (antes NO habia ninguno en toda la interfaz y el asistente
  // solo era alcanzable escribiendo la URL a mano).
  const alta6 = p.locator('a, button').filter({ hasText: /Alta de cliente nuevo/i }).first();
  comprobar(await alta6.count() > 0,
    'hay un enlace visible al alta de cliente nuevo');
  await alta6.click({ timeout: 30000 });
  await p.waitForTimeout(8000);
  const alta = await texto(p);
  comprobar(alta.includes('Datos cliente') && alta.includes('Contexto ENS')
            && alta.includes('Categoría preliminar') && alta.includes('Activos críticos')
            && alta.includes('Primer usuario') && alta.includes('Revisar y crear'),
    'el asistente tiene los 6 pasos que dice USAGE.md');
  comprobar(alta.includes('todo atómico'), 'el alta es una sola operación');

  // ── proyecto del demo ─────────────────────────────────────────────────
  // USAGE.md dice: "el único con datos es NovaEdge S.L.". Se entra por AHI, que
  // es lo que hara quien siga el recorrido. En el primer intento este arnes
  // pinchaba la primera fila del listado (DataForma Galicia, vacia) y daba 26
  // fallos que no eran del sujeto: eran mios.
  await p.goto(`${BASE}/admin/projects`, { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(4000);
  const saltar2 = p.getByRole('button', { name: /^Saltar$/i }).first();
  if (await saltar2.count() > 0) { await saltar2.click(); await p.waitForTimeout(1200); }
  // Se filtra por el buscador, que es lo que hace una persona, y asi queda una
  // sola tarjeta. Sin filtrar, el selector de tarjeta pinchaba la primera del
  // listado (DataForma Galicia, vacia) y todo lo demas salia en rojo por mi
  // culpa, no por la del sujeto.
  const buscadorProy = p.locator('input[placeholder*="uscar" i]').first();
  if (await buscadorProy.count() > 0) {
    await buscadorProy.fill('NovaEdge');
    await p.waitForTimeout(2500);
  }
  await p.locator('a,button').filter({ hasText: /Entrar al proyecto/i }).first()
         .click({ timeout: 30000 });
  await p.waitForTimeout(6000);
  const idProyecto = (p.url().match(/projects\/([0-9a-f-]{36})/) || [])[1];
  const cabecera = await texto(p);
  comprobar(Boolean(idProyecto) && /NovaEdge/i.test(cabecera),
    'se entra en el proyecto de NovaEdge S.L.', idProyecto || p.url());

  const ir = async (seccion) => {
    await p.goto(`${BASE}/admin/projects/${idProyecto}/${seccion}`,
                 { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(7000);
    return texto(p);
  };

  // ── 3 · DdA ───────────────────────────────────────────────────────────
  titulo('3 · la evaluación ENS · Declaración de Aplicabilidad');
  const dda = await ir('dda');
  const cifras = { 'TOTAL MEDIDAS': 73, APLICABLES: 68, 'NO APLICA': 5, IMPLANTADAS: 68 };
  for (const [rotulo, valor] of Object.entries(cifras)) {
    const re = new RegExp(`${rotulo}\\s*/\\s*${valor}\\b`);
    comprobar(re.test(dda), `DdA · ${rotulo} = ${valor}`,
      re.test(dda) ? '' : 'el numero de la pantalla no coincide con USAGE.md');
  }
  comprobar(dda.includes('Medidas') && dda.includes('Catálogo Anexo II'),
    'la DdA tiene la pestaña de medidas');

  // ── 4 · conformidad ───────────────────────────────────────────────────
  titulo('4 · la cobertura · camino a la conformidad');
  const conf = await ir('conformity');
  for (const paso of ['DdA final firmada', 'Plan adecuación implementado',
                      'Auditor externo ENAC asignado', 'Auditoría externa ejecutada',
                      'Distintivo', 'Reporte INES anual']) {
    comprobar(conf.includes(paso), `camino a conformidad · «${paso}»`);
  }
  for (const boton of ['Descargar Declaración (DOCX)', 'Descargar SVG',
                       'Copiar snippet HTML']) {
    comprobar(conf.includes(boton), `distintivo · botón «${boton}»`);
  }
  comprobar(/Verificación cloud/.test(conf) && /todas vía documental/.test(conf),
    'avisa de que no hay ninguna nube conectada');

  // ── 5 · entregable ────────────────────────────────────────────────────
  titulo('5 · generar un entregable');
  const plan = await ir('plan');
  comprobar(/16 semanas/.test(plan), 'el plan dice 16 semanas');
  comprobar(/35 tareas/.test(plan), 'el plan dice 35 tareas');
  comprobar(plan.includes('WBS-001') && plan.includes('WBS-081'),
    'las tareas van de WBS-001 a WBS-081');
  const boton = p.getByRole('button', { name: /Generar Plan Adecuación \(DOCX\)/i }).first();
  comprobar(await boton.count() > 0, 'existe el botón «Generar Plan Adecuación (DOCX)»');
  if (await boton.count() > 0) {
    try {
      const [descarga] = await Promise.all([
        p.waitForEvent('download', { timeout: 90000 }),
        boton.click(),
      ]);
      const nombre = descarga.suggestedFilename();
      comprobar(nombre.endsWith('.docx'), 'el botón descarga un .docx de verdad', nombre);
    } catch (e) {
      falla('el botón descarga un .docx de verdad', e.message.slice(0, 110));
    }
  }
  const docs = await ir('documents');
  comprobar(/DOCUMENTOS \/ 21\b/.test(docs), 'hay 21 documentos en el gestor documental');
  for (const cod of ['E-049', 'E-049-EXT', 'E-040']) {
    comprobar(docs.includes(cod), `documento ${cod} presente`);
  }

  // ── 6 · evidencia firmada ─────────────────────────────────────────────
  titulo('6 · la evidencia firmada');
  const ev = await ir('evidence');
  comprobar(/209\/209/.test(ev), 'el vault muestra 209/209');
  comprobar(ev.includes('Subir evidencia (admin)'),
    'el formulario de subida CARGA (no da «Project not found»)');
  comprobar(!ev.includes('No se pudo cargar el catálogo de subida'),
    'no hay error de catálogo en pantalla');
  const ficheros = ['politica-seguridad-novaedge-v1.pdf', 'acta-comite-seguridad-2026-03.pdf',
                    'mfa-obligatorio-entra-id.png', 'inventario-activos-2026Q1.csv',
                    'prueba-restauracion-backup-2026-02.pdf'];
  // Se buscan en la propia tabla del vault, filtrando por nombre, que es lo que
  // haria una persona. (Por API haria falta arrastrar la cookie de sesion al
  // contexto de peticiones; el primer intento devolvia 401 por eso.)
  for (const f of ficheros) {
    const fila = p.locator('tr,li,div').filter({ hasText: f }).first();
    let visto = await fila.count() > 0;
    if (!visto) {
      const buscador = p.locator('input[type="search"], input[placeholder*="ilt" i]').first();
      if (await buscador.count() > 0) {
        await buscador.fill(f);
        await p.waitForTimeout(2500);
        visto = (await texto(p)).includes(f);
      }
    }
    comprobar(visto, `evidencia firmada visible · ${f}`);
  }

  // ── 7 · portal de cliente ─────────────────────────────────────────────
  titulo('7 · portal de cliente');
  const cli = await (await nav.newContext({ viewport: { width: 1600, height: 1000 } })).newPage();
  await cli.goto(`${BASE}/client-portal/login`, { waitUntil: 'domcontentloaded' });
  await cli.waitForTimeout(2000);
  await cli.fill('input[type="email"]', 'cliente@fulkro.es');
  await cli.fill('input[type="password"]', CLAVE);
  await cli.locator('button[type="submit"]').first().click();
  await cli.waitForTimeout(7000);
  const inicio = await texto(cli);
  comprobar(/Hola NovaEdge S\.L\./.test(inicio), 'el cliente entra y se le saluda por su nombre');
  comprobar(/paso 1 de 10/.test(inicio), 'el cliente ve un recorrido de 10 pasos');
  comprobar(!inicio.includes('[MOCK]'),
    'NO se le ensena al cliente el texto del sustituto del modelo');
  for (const ruta of ['firmas-pendientes', 'certificacion', 'conformidad']) {
    const resp = await cli.goto(`${BASE}/client-portal/${ruta}`,
                                { waitUntil: 'domcontentloaded' });
    await cli.waitForTimeout(4000);
    const dentro = !cli.url().includes('/login');
    comprobar(resp.status() < 400 && dentro, `cliente · /${ruta}`,
      `HTTP ${resp.status()}${dentro ? '' : ' · rebota a la entrada'}`);
  }

  // ── 8 · portal de auditor ─────────────────────────────────────────────
  titulo('8 · portal de auditor');
  const tk = await ctx.request.post(
    `${API}/api/v1/_dev/auditor-portal-token?project_id=${idProyecto}`);
  if (!tk.ok()) {
    falla('emitir enlace de auditor', `HTTP ${tk.status()}`);
  } else {
    const { portal_path: ruta, otp } = await tk.json();
    const aud = await (await nav.newContext({ viewport: { width: 1600, height: 1000 } })).newPage();
    await aud.goto(BASE + ruta, { waitUntil: 'domcontentloaded' });
    await aud.waitForTimeout(3000);
    comprobar((await texto(aud)).includes('Introduzca el código de acceso'),
      'el enlace del auditor pide el código de un solo uso');
    await aud.locator('input:visible').first().fill(otp);
    await aud.locator('button:visible').filter({ hasText: /entrar/i }).first().click();
    await aud.waitForTimeout(7000);
    const res = await texto(aud);
    comprobar(/DDA · MEDIDAS \/ 73/.test(res), 'auditor · 73 medidas de DdA');
    comprobar(/EVIDENCIAS \/ 209/.test(res), 'auditor · 209 evidencias');
    comprobar(/solo lectura/i.test(res), 'auditor · avisa de que es sólo lectura');
    const secciones = ['Cobertura DdA', 'Audit log inmutable', 'Documentos canónicos'];
    for (const s of secciones) {
      comprobar(res.includes(s), `auditor · sección «${s}» en la navegación`);
    }
    // El codigo se repite en cada seccion: USAGE.md lo dice, se comprueba.
    await aud.getByRole('link', { name: /Audit log inmutable/i }).first().click();
    await aud.waitForTimeout(5000);
    const repide = (await texto(aud)).includes('Introduzca el código de acceso');
    comprobar(repide, 'auditor · vuelve a pedir el código al cambiar de sección',
      'USAGE.md avisa de ello');
    if (repide) {
      await aud.locator('input:visible').first().fill(otp);
      await aud.locator('button:visible').filter({ hasText: /entrar/i }).first().click();
      await aud.waitForTimeout(6000);
    }
    const log = await texto(aud);
    comprobar(/Registro de auditoría inmutable/.test(log),
      'auditor · el MISMO código vale otra vez');
    comprobar(/hash SHA-256 encadenado/.test(log), 'auditor · cadena de hash SHA-256');
    comprobar(/Exportar CSV/.test(log), 'auditor · el registro se puede exportar');
  }

  await nav.close();
  console.log('\n──────────────────────────────────────────────────────────────');
  console.log(` Recorrido de USAGE.md: ${ok} correctas, ${mal} fallidas`);
  console.log('──────────────────────────────────────────────────────────────');
  process.exit(mal > 0 ? 1 : 0);
}

main().catch((e) => { console.error('FALLO del arnes:', e.message); process.exit(2); });
