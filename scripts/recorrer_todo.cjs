/**
 * RECORRIDO COMPLETO · las 167 paginas de la aplicacion, una por una.
 *
 * Regla que manda sobre todas las demas en este arnes:
 *
 *     UNA PAGINA QUE CARGA NO ES UNA PAGINA QUE FUNCIONA.
 *
 * Un HTTP 200 lo devuelve igual una pantalla llena de datos que un cascaron que
 * dice "no hay nada" que un error de React capturado por un limite de error. Por
 * eso aqui no se mide "responde": se mide QUE SE VE, QUE FALLA POR DEBAJO y SI
 * ALGUIEN PUEDE LLEGAR pinchando.
 *
 * Entra SIEMPRE por el puerto del FRONTEND, con sesiones de verdad. Nunca contra
 * la API: esa puerta ya engano una vez a esta campanya (ver docs/INFORME_BLOQUE_D.md,
 * apartado "el criterio de cierre que acordamos era vacuo").
 *
 * Uso (con el demo en pie · `make demo`):
 *     make recorrer-todo
 *
 * Variables:
 *     DEMO_URL              (por defecto http://localhost:3000)
 *     BACKEND_URL           (solo para acunyar enlaces · http://127.0.0.1:18000)
 *     SECRETO_TOTP          segundo factor del operador (lo pasa el Makefile)
 *     RECORRIDO_ESPERA      ms de espera tras cargar cada pagina (por defecto 4000)
 *     RECORRIDO_SOLO        filtra rutas por subcadena (para depurar)
 *     RECORRIDO_SIN_BFS     "1" salta el recorrido de alcanzabilidad
 *     RECORRIDO_MAX_BFS     tope de paginas a abrir en el BFS (por defecto 220)
 *
 * Sale 0 si no hay fallos SIN EXPLICAR; 1 si los hay.
 */
// CommonJS a proposito: los modulos ESM NO respetan NODE_PATH, y playwright vive
// en frontend/node_modules, no en la raiz del repositorio.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const RAIZ = path.resolve(__dirname, '..');
const BASE = process.env.DEMO_URL || 'http://localhost:3000';
const API = process.env.BACKEND_URL || 'http://127.0.0.1:18000';
const CORREO = process.env.FULKRO_DEMO_OWNER_EMAIL || 'demo@fulkro.es';
const CLAVE = process.env.FULKRO_DEMO_OWNER_PASSWORD || 'fulkro-demo-2026';
const CORREO_CLIENTE = process.env.FULKRO_DEMO_CLIENT_EMAIL || 'cliente@fulkro.es';
const SECRETO = process.env.SECRETO_TOTP;
const ESPERA = Number(process.env.RECORRIDO_ESPERA || 4000);
const FILTRO = process.env.RECORRIDO_SOLO || '';
const MAX_BFS = Number(process.env.RECORRIDO_MAX_BFS || 220);

const DIR_SALIDA = path.join(RAIZ, 'var', 'recorrido');
const DIR_CAPTURAS = path.join(DIR_SALIDA, 'capturas');

// ════════════════════════════════════════════════════════════════════════════
// 1 · INVENTARIO · las rutas se DERIVAN del arbol, no se escriben a mano
// ════════════════════════════════════════════════════════════════════════════
//
// Escribir la lista a mano es como se llega a un informe que recorre 40 URL
// inventadas y declara "todo verde": lo que no esta en la lista no falla nunca.
// Aqui la lista ES el arbol de `frontend/app`, asi que una pagina nueva entra
// sola en el recorrido y una pagina borrada desaparece sola.

/** Recorre `frontend/app` y devuelve una entrada por cada `page.tsx`. */
function derivarRutas() {
  const raizApp = path.join(RAIZ, 'frontend', 'app');
  const salida = [];

  const bajar = (dir) => {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, ent.name);
      if (ent.isDirectory()) bajar(p);
      else if (ent.name === 'page.tsx') {
        const rel = path.relative(raizApp, path.dirname(p));
        const segmentos = rel === '' ? [] : rel.split(path.sep);
        // Los grupos de ruta `(nombre)` organizan ficheros pero NO aparecen en
        // la URL: es la regla del App Router de Next.js. Se guardan aparte
        // porque son la mejor etiqueta que existe para agrupar el informe.
        const grupos = segmentos.filter((s) => /^\(.+\)$/.test(s))
                                .map((s) => s.slice(1, -1));
        const url = '/' + segmentos.filter((s) => !/^\(.+\)$/.test(s)).join('/');
        salida.push({
          fichero: path.relative(RAIZ, p),
          patron: url === '/' ? '/' : url.replace(/\/$/, ''),
          grupo: grupos.length ? grupos.join('/') : 'sin-grupo',
          dinamica: /\[/.test(url),
        });
      }
    }
  };
  bajar(raizApp);
  salida.sort((a, b) => a.patron.localeCompare(b.patron));
  return salida;
}

// ════════════════════════════════════════════════════════════════════════════
// 2 · RESOLUCION DE PARAMETROS · con dato real o NO VERIFICADA, nunca "pasa"
// ════════════════════════════════════════════════════════════════════════════

/** Sustituye `[param]` por identificadores REALES del catalogo. */
function resolver(patron, cat) {
  const ids = cat.ids || {};
  const tokens = cat.tokens || {};

  // Que identificador toca depende del prefijo de la ruta, no del nombre del
  // parametro: los 63 `[id]` del arbol son de cinco entidades distintas.
  const reglas = [
    [/^\/admin\/clients\/\[id\]/, () => ids.client_id, 'client_id'],
    [/^\/admin\/meetings\/\[id\]/, () => ids.meeting_id, 'meeting_id'],
    [/^\/admin\/pipeline\/leads\/\[id\]/, () => ids.lead_id, 'lead_id'],
    [/^\/admin\/magerit-analyses\/\[id\]/, () => ids.magerit_analysis_id, 'magerit_analysis_id'],
    [/^\/admin\/compliance\/norma-reports\/\[norma_key\]/, () => ids.norma_key, 'norma_key'],
    [/^\/client-portal\/registros\/\[tipo\]/, () => ids.registro_tipo, 'registro_tipo'],
    [/\[id\]/, () => ids.project_id, 'project_id'],
  ];

  let url = patron;
  const usados = [];

  if (/\[token\]/.test(patron)) {
    const portal = patron.split('/')[1];
    const t = tokens[portal];
    if (!t) {
      return { url: null, motivo: `no hay enlace acunyado para el portal «${portal}»` };
    }
    url = url.replace('[token]', t.token);
    usados.push(`token:${portal}`);
  }

  for (const [re, valor, nombre] of reglas) {
    if (!/\[/.test(url)) break;
    if (!re.test(patron)) continue;
    const v = valor();
    if (!v) {
      const motivo = (cat.sin_dato || {})[nombre]
        || `no hay ningun ${nombre} en la base del demo`;
      return { url: null, motivo };
    }
    url = url.replace(/\[[^\]]+\]/, v);
    usados.push(`${nombre}=${v}`);
  }

  if (/\[/.test(url)) {
    return { url: null, motivo: `parametro sin regla de resolucion en ${patron}` };
  }
  return { url, usados };
}

// ════════════════════════════════════════════════════════════════════════════
// 3 · PERSONAS · quien es el duenyo de cada ruta
// ════════════════════════════════════════════════════════════════════════════
//
// "Duenyo" = la persona para la que esa pagina existe. Es lo que convierte un
// 403 en un RESULTADO CORRECTO en vez de en un fallo: solo se exige contenido a
// la persona duenya, y a las demas se les exige justo lo contrario.

function personaDe(patron) {
  if (patron === '/client-portal/login') return 'anonimo';
  if (patron.startsWith('/client-portal')) return 'cliente';
  if (patron.startsWith('/admin')) return 'operador';
  for (const portal of ['auditor-portal', 'pentester-portal', 'remediation',
                        'verify-auth', 'diagnostico', 'sign', 'download']) {
    if (patron.startsWith('/' + portal + '/')) return `portal:${portal}`;
  }
  return 'anonimo';
}

// ════════════════════════════════════════════════════════════════════════════
// 4 · CAPTURA · lo que se mira en cada pagina
// ════════════════════════════════════════════════════════════════════════════

/** Palabras que solo aparecen en una pantalla que NO trae datos. */
const FRASES_VACIO = [
  /no hay (ning|dat|element|result|registr|archiv|document|evidenci|tare|alert|mensaj)/i,
  /sin (datos|registros|resultados|elementos|actividad|contenido)\b/i,
  /(todav[ií]a|a[uú]n) no (hay|tienes|se han|existe)/i,
  /no se (han )?encontr(aron|ado)/i,
  /nada que mostrar/i,
  /^0 resultados/im,
  /lista vac[ií]a/i,
  /no existen /i,
  // "Proximamente" es un estado vacio con buenos modales. Una pagina que dice
  // que la funcion llegara en otra version no tiene contenido HOY, que es
  // cuando la esta mirando alguien. Medido: /admin/inbox dice «la vista
  // agregada cross-project se incorporara en MB-19+» y /client-portal/whatsapp
  // dice «todavia no estan activas en tu entorno».
  /pr[oó]ximamente/i,
  /se incorporar[aá]/i,
  /todav[ií]a no est[aá]n? (activ|disponible)/i,
  /no est[aá]n? disponible/i,
];

/**
 * Texto FABRICADO: lo que nunca deberia llegar a la pantalla de nadie.
 *
 * `[MOCK]` esta el primero por un motivo concreto: asi aparecio «[MOCK] Agent
 * 12» bajo el rotulo «Sugerencia IA» en la portada del cliente. La comprobacion
 * se queda aqui para siempre.
 *
 * `TODO` va en MAYUSCULAS y con limite de palabra a proposito: en castellano
 * "todo" es una palabra normal y en minusculas daria un falso positivo por
 * pagina. Aun asi cada hallazgo se publica con su contexto, porque un rotulo
 * en versalitas ("VER TODO") tambien casa y eso lo tiene que juzgar una persona.
 */
/**
 * Lo que dice una pagina que se ha ROTO y alguien lo ha capturado.
 *
 * Un limite de error de React no es un estado vacio: es un fallo. La diferencia
 * importa porque las dos cosas se arreglan de forma distinta —una pide sembrar
 * datos, la otra pide arreglar codigo— y porque un limite de error devuelve
 * HTTP 200 y no siempre escupe nada a la consola. Es, literalmente, una pagina
 * que carga y no funciona.
 *
 * Medido: /admin/clients/{id} ensenya «No pudimos cargar esta seccion · Hubo un
 * problema cargando esta pagina del panel admin», con un boton «Reintentar».
 * Sin esta lista salia clasificada como VACIA, y se habria discutido si merecia
 * lista blanca cuando lo que merece es un arreglo.
 */
const FRASES_ERROR = [
  /no pudimos cargar/i,
  /algo (ha )?(sali[oó]|fue) mal/i,
  /se ha producido un error/i,
  /ha ocurrido un error/i,
  /error inesperado/i,
  /p[aá]gina no encontrada/i,
  /no se pudo cargar (el|la|los|las)/i,
];

const PATRONES_FABRICADO = [
  { nombre: '[MOCK]', re: /\[MOCK\]/g },
  { nombre: 'undefined', re: /\bundefined\b/g },
  { nombre: 'NaN', re: /\bNaN\b/g },
  { nombre: 'null', re: /\bnull\b/g },
  { nombre: 'lorem', re: /\blorem\b/gi },
  { nombre: 'TODO', re: /\bTODO\b/g },
  { nombre: 'FIXME', re: /\bFIXME\b/g },
];

function buscarFabricado(texto) {
  const hallazgos = [];
  for (const { nombre, re } of PATRONES_FABRICADO) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(texto)) !== null) {
      const desde = Math.max(0, m.index - 45);
      hallazgos.push({
        patron: nombre,
        contexto: texto.slice(desde, m.index + m[0].length + 45)
                       .replace(/\s+/g, ' ').trim(),
      });
      if (hallazgos.filter((h) => h.patron === nombre).length >= 3) break;
    }
  }
  return hallazgos;
}

/** Abre una URL y devuelve TODO lo que se puede medir de ella. */
async function visitar(pg, url, nombreCaptura) {
  pg.__consola = [];
  pg.__errores = [];
  pg.__peticionesFallidas = [];

  let respuesta = null;
  let errorNavegacion = null;
  try {
    respuesta = await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) {
    errorNavegacion = e.message.slice(0, 200);
  }
  await pg.waitForTimeout(ESPERA);
  // Defensivo: hay tours que reaparecen al entrar en una seccion nueva.
  if (await cerrarTourSiEstaAbierto(pg)) await pg.waitForTimeout(800);
  return medir(pg, url, nombreCaptura, respuesta, errorNavegacion);
}

/**
 * Mide la pagina que YA esta abierta, sin volver a navegar.
 *
 * Existe por un motivo concreto y medido: en los portales por token la pantalla
 * del codigo de un solo uso NO deja cookie. Si tras teclear el codigo se vuelve
 * a pedir la misma URL, reaparece la puerta y se mide otra vez la puerta. Con
 * `visitar()` a secas las doce paginas del portal del auditor salian «vacias»
 * con 174 caracteres: los de la propia pantalla del codigo.
 */
async function medir(pg, url, nombreCaptura, respuesta = null, errorNavegacion = null) {

  let texto = '';
  let principal = '';
  let senyales = { filas: 0, tarjetas: 0, celdas: 0, botones: 0, campos: 0,
                   caracteres: 0, caracteresCuerpo: 0 };
  let rechazos = [];
  try {
    const medido = await pg.evaluate(() => {
      // DOS textos, y la distincion es el corazon del criterio anti vacuidad:
      //
      //   · `cuerpo` es todo lo visible (barra lateral, cabecera, pie). Sirve
      //     para buscar TEXTO FABRICADO: un «[MOCK]» en la barra lateral es tan
      //     grave como uno en el contenido.
      //   · `principal` es solo <main>, el contenido de LA PAGINA. Es lo unico
      //     que puede decidir si la pagina trae datos.
      //
      // El primer intento clasificaba sobre el cuerpo entero y por eso conto 33
      // paginas vacias donde no las habia: en /admin/compliance basta con que un
      // widget lateral diga «Sin datos» para condenar una pagina con tres
      // tarjetas de normativa y sus puntuaciones. Medir el marco y llamarlo
      // contenido es cometer, en pequenyo, el error que este bloque persigue.
      const raiz = document.querySelector('main') || document.body;
      const t = document.body ? document.body.innerText : '';
      const tp = raiz ? raiz.innerText : t;
      const n = (sel) => raiz.querySelectorAll(sel).length;
      return {
        texto: t,
        principal: tp,
        senyales: {
          filas: n('tbody tr'),
          tarjetas: n('[class*="card" i]'),
          celdas: n('tbody td'),
          botones: n('button'),
          // Los campos de formulario cuentan como contenido. Sin esto, una
          // pantalla de entrada —que es un formulario que funciona y poco
          // texto— salia clasificada como "vacia", y eso es un falso positivo
          // del medidor, no un defecto de la aplicacion. Meterla en la lista
          // blanca habria sido tapar el error de medida con una excusa
          // escrita, que es peor que el error.
          campos: n('input, select, textarea'),
          caracteres: tp.length,
          caracteresCuerpo: t.length,
        },
        rechazos: (window.__rechazos || []).slice(0, 5),
      };
    });
    texto = medido.texto;
    principal = medido.principal;
    senyales = medido.senyales;
    rechazos = medido.rechazos;
  } catch (e) {
    errorNavegacion = (errorNavegacion || '') + ' | evaluate: ' + e.message.slice(0, 120);
  }

  const capturaRel = path.join('capturas', nombreCaptura + '.png');
  try {
    await pg.screenshot({ path: path.join(DIR_SALIDA, capturaRel), fullPage: false });
  } catch { /* una captura fallida no invalida la medida */ }

  // No basta con saber QUE casa una frase de vacio: hay que guardar la frase
  // TAL COMO SALE EN PANTALLA, con su contexto. Publicar la expresion regular
  // en vez del texto seria informar de la herramienta en lugar del hallazgo.
  let fraseError = null;
  for (const re of FRASES_ERROR) {
    const me = principal.match(re);
    if (me) {
      const i = principal.indexOf(me[0]);
      fraseError = principal.slice(Math.max(0, i - 20), i + me[0].length + 90)
                            .replace(/\s+/g, ' ').trim();
      break;
    }
  }

  let fraseVacio = null;
  for (const re of FRASES_VACIO) {
    const m2 = principal.match(re);
    if (m2) {
      const i = principal.indexOf(m2[0]);
      fraseVacio = principal.slice(Math.max(0, i - 30), i + m2[0].length + 70)
                            .replace(/\s+/g, ' ').trim();
      break;
    }
  }

  return {
    url,
    urlFinal: pg.url(),
    http: respuesta ? respuesta.status() : null,
    errorNavegacion,
    // "Rebota" = la aplicacion te ha echado a una pantalla de entrada. Con HTTP
    // 200 y sin un solo error: es el caso que mas se parece a funcionar sin
    // funcionar.
    rebotaALogin: /\/login($|\?)/.test(pg.url()) && !/\/login($|\?)/.test(url),
    consola: pg.__consola.slice(0, 8),
    errores: pg.__errores.slice(0, 5),
    rechazos,
    peticionesFallidas: pg.__peticionesFallidas.slice(0, 10),
    senyales,
    fraseVacio,
    fraseError,
    fabricado: buscarFabricado(texto),
    captura: capturaRel,
    textoBreve: principal.replace(/\s+/g, ' ').trim().slice(0, 400),
  };
}

/** Engancha los oyentes UNA vez por pagina; los buffers se vacian por visita. */
function instrumentar(pg) {
  pg.__consola = []; pg.__errores = []; pg.__peticionesFallidas = [];
  pg.on('console', (msg) => {
    if (msg.type() === 'error') pg.__consola.push(msg.text().slice(0, 220));
  });
  pg.on('pageerror', (err) => pg.__errores.push(String(err.message).slice(0, 220)));
  pg.on('response', (res) => {
    const tipo = res.request().resourceType();
    if ((tipo === 'xhr' || tipo === 'fetch') && res.status() >= 400) {
      // La URL COMPLETA, que es lo unico que permite cazar un 404 que solo
      // ocurre para una persona concreta (el 404 por RLS del formulario de
      // evidencias se encontro exactamente asi).
      pg.__peticionesFallidas.push(`${res.status()} ${res.request().method()} ${res.url()}`);
    }
  });
}

module.exports = { derivarRutas, resolver, personaDe, visitar, instrumentar,
                   buscarFabricado, FRASES_VACIO, DIR_SALIDA, DIR_CAPTURAS,
                   BASE, API, CORREO, CLAVE, CORREO_CLIENTE, SECRETO, ESPERA,
                   FILTRO, MAX_BFS, RAIZ, chromium, crypto, fs, path };

// ════════════════════════════════════════════════════════════════════════════
// 5 · SESIONES · tres personas, por el puerto del FRONTEND
// ════════════════════════════════════════════════════════════════════════════
//
// Nunca contra la API. El BLOQUE D demostro que se puede tener la API perfecta y
// la aplicacion inservible desde el navegador, y que un humo que entra por el
// puerto del backend no lo ve.

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

const GUION_RECHAZOS = () => {
  window.__rechazos = [];
  window.addEventListener('unhandledrejection', (e) => {
    const r = e.reason;
    window.__rechazos.push(String((r && (r.message || r.toString())) || r).slice(0, 200));
  });
};

async function nuevoContexto(nav) {
  const ctx = await nav.newContext({ viewport: { width: 1600, height: 1000 },
                                     locale: 'es-ES' });
  await ctx.addInitScript(GUION_RECHAZOS);
  return ctx;
}

/** Operador: correo + contrasenya + segundo factor, como en la pantalla. */
async function sesionOperador(nav) {
  const ctx = await nuevoContexto(nav);
  const pg = await ctx.newPage();
  instrumentar(pg);
  await pg.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(1500);
  await pg.fill('input[type="email"]', CORREO);
  await pg.fill('input[type="password"]', CLAVE);
  await pg.click('button[type="submit"]');
  await pg.waitForTimeout(3000);
  if (!SECRETO) throw new Error('falta SECRETO_TOTP');
  await pg.locator('input:visible').first().fill(totp(SECRETO));
  await pg.locator('button:visible').first().click();
  await pg.waitForTimeout(5000);
  await cerrarTourSiEstaAbierto(pg);
  const dentro = /\/admin\//.test(pg.url());
  return { ctx, pg, dentro, aterrizaje: pg.url().replace(BASE, '') };
}

/** Cliente: correo + contrasenya en el portal, sin segundo factor. */
async function sesionCliente(nav) {
  const ctx = await nuevoContexto(nav);
  const pg = await ctx.newPage();
  instrumentar(pg);
  await pg.goto(`${BASE}/client-portal/login`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2000);
  await pg.fill('input[type="email"]', CORREO_CLIENTE);
  await pg.fill('input[type="password"]', CLAVE);
  await pg.locator('button[type="submit"]').first().click();
  await pg.waitForTimeout(6000);
  await cerrarTourSiEstaAbierto(pg);
  const dentro = !/\/client-portal\/login/.test(pg.url());
  return { ctx, pg, dentro, aterrizaje: pg.url().replace(BASE, '') };
}

/**
 * Portal por token: un contexto POR PORTAL.
 *
 * Los portales con codigo de un solo uso lo vuelven a pedir al cambiar de
 * seccion (el portal del auditor lo hace, y USAGE.md lo avisa). Por eso el
 * codigo se guarda y se reintroduce cada vez que reaparece la pantalla, en
 * lugar de dar por hecho que una vez basta.
 */
async function sesionPortal(nav, portal, cat) {
  const ctx = await nuevoContexto(nav);
  const pg = await ctx.newPage();
  instrumentar(pg);
  const t = (cat.tokens || {})[portal];
  return { ctx, pg, otp: t ? t.otp : null, portal };
}

/**
 * Cierra el tour de bienvenida si esta abierto.
 *
 * POR QUE HACE FALTA, y es el cuarto error que este arnes se ha encontrado a si
 * mismo: en un demo RECIEN levantado, la primera entrada abre un modal
 * («TOUR ADMIN · PASO 1 DE 6» en administracion, 10 pasos en el portal del
 * cliente). Ese modal deja <main> tapado, y `innerText` no devuelve texto
 * oculto: el arnes media el modal y declaraba VACIAS paginas que estaban
 * LLENAS. Se vio comparando la captura de /admin/dashboard —cuatro indicadores,
 * actividad reciente, acciones rapidas— con la medida, que decia 0 caracteres.
 *
 * En la primera pasada no salio porque el demo llevaba usado un rato y el tour
 * ya estaba descartado. O sea: la version LIMPIA del demo medía peor que la
 * sucia, que es la clase de trampa que este bloque existe para no repetir.
 *
 * El tour se cierra, no se ignora: es real y una persona lo ve, pero lo que hay
 * que medir es la pagina de debajo. Que el tour aparece se comprueba en
 * `scripts/verificar_recorrido_usage.cjs`, que es su sitio.
 */
async function cerrarTourSiEstaAbierto(pg) {
  try {
    // Atajo barato: si no hay ningun dialogo abierto, no hay nada que cerrar.
    // Sin esto se lanzaban cinco busquedas de selector POR PAGINA aunque no
    // hubiera tour, y el recorrido pasaba de ~15 s a ~40 s por pagina — dos
    // horas de reloj para las 167. Una comprobacion cara que casi siempre
    // devuelve "no" hay que hacerla barata.
    if (await pg.locator('[role="dialog"]:visible').count() === 0) return false;
    for (const nombre of [/^Saltar$/i, /^Cerrar$/i, /^Entendido$/i, /^Empezar$/i]) {
      const b = pg.getByRole('button', { name: nombre }).first();
      if (await b.count() > 0 && await b.isVisible().catch(() => false)) {
        await b.click({ timeout: 5000 });
        await pg.waitForTimeout(1200);
        return true;
      }
    }
    // Algunos modales solo traen una X sin nombre accesible.
    const x = pg.locator('[role="dialog"] button[aria-label*="errar" i]').first();
    if (await x.count() > 0) {
      await x.click({ timeout: 5000 });
      await pg.waitForTimeout(1200);
      return true;
    }
  } catch { /* si no se puede cerrar, se mide lo que haya y se vera */ }
  return false;
}

async function pasarOtpSiLoPide(pg, otp) {
  if (!otp) return false;
  try {
    const texto = await pg.evaluate(() => document.body ? document.body.innerText : '');
    if (!/c[oó]digo de acceso|c[oó]digo de un solo uso|introduzca el c[oó]digo/i.test(texto)) {
      return false;
    }
    await pg.locator('input:visible').first().fill(otp);
    const boton = pg.locator('button:visible').filter({ hasText: /entrar|acceder|validar|continuar/i }).first();
    if (await boton.count() > 0) await boton.click();
    else await pg.locator('button:visible').first().click();
    await pg.waitForTimeout(4000);
    return true;
  } catch { return false; }
}

// ════════════════════════════════════════════════════════════════════════════
// 6 · ALCANZABILIDAD · lo que se puede usar pinchando
// ════════════════════════════════════════════════════════════════════════════
//
// "Existe" y "se alcanza" son dos cosas distintas, y la diferencia entre ambas
// tiene nombre: paginas huerfanas. El alta de cliente era una de ellas —la
// pagina estaba entera y no habia UN SOLO enlace que llevara a ella— y se
// encontro a mano. Esto lo cuenta.

/** Devuelve el patron de ruta al que corresponde una URL concreta, o null. */
function aPatron(url, patrones) {
  let p = url.split('#')[0].split('?')[0].replace(/\/$/, '') || '/';
  // Los identificadores se normalizan de vuelta a su hueco para poder comparar
  // con el inventario derivado del arbol.
  p = p.replace(/\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, '/[id]');
  p = p.replace(/\/ey[A-Za-z0-9_.-]{40,}/g, '/[token]');
  if (patrones.has(p)) return p;
  // `/admin/clients/[id]` y `/admin/projects/[id]` comparten forma: se prueba
  // tambien la variante con [token] por si el hueco era ese.
  const alt = p.replace('/[id]', '/[token]');
  if (patrones.has(alt)) return alt;
  return patrones.has(p) ? p : null;
}

async function recorrerEnAnchura(pg, semillas, patrones, limite, prefijoPermitido) {
  const vistas = new Set();
  const alcanzados = new Set();
  const rotos = [];
  const cola = [...semillas];

  while (cola.length && vistas.size < limite) {
    const url = cola.shift();
    const clave = url.split('#')[0];
    if (vistas.has(clave)) continue;
    vistas.add(clave);

    let resp = null;
    try {
      resp = await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch { continue; }
    await pg.waitForTimeout(1800);

    const estado = resp ? resp.status() : 0;
    const pat = aPatron(pg.url().replace(BASE, ''), patrones);
    if (estado >= 400) {
      rotos.push({ url: url.replace(BASE, ''), http: estado });
      continue;
    }
    if (pat) alcanzados.add(pat);

    let enlaces = [];
    try {
      enlaces = await pg.evaluate(() => Array.from(document.querySelectorAll('a[href]'))
        .map((a) => a.getAttribute('href')).filter(Boolean));
    } catch { /* sin enlaces medibles */ }

    for (const href of enlaces) {
      if (/^(https?:)?\/\//.test(href) && !href.startsWith(BASE)) continue;
      if (/^(mailto:|tel:|javascript:|#)/.test(href)) continue;
      const abs = href.startsWith('http') ? href
                : BASE + (href.startsWith('/') ? href : '/' + href);
      const ruta = abs.replace(BASE, '').split('#')[0];
      if (prefijoPermitido && !prefijoPermitido.some((p) => ruta.startsWith(p))) continue;
      if (!vistas.has(abs.split('#')[0])) cola.push(abs);
    }
  }
  return { alcanzados, rotos, abiertas: vistas.size };
}

// ════════════════════════════════════════════════════════════════════════════
// 7 · VEREDICTO POR PAGINA
// ════════════════════════════════════════════════════════════════════════════
//
// Aqui vive la regla del bloque. Una pagina NO aprueba por cargar:
//
//   verificada  -> se abrio, con la persona duenya, y trae CONTENIDO REAL.
//   vacia       -> se abrio y no trae nada. NO aprueba (salvo lista blanca).
//   fallida     -> rebota, revienta, o algo por debajo devuelve 4xx/5xx.
//   no-verificada -> no habia dato sembrado con el que resolver la ruta.
//
// Esa cuarta categoria es la que impide la trampa mas comoda: dar por buena una
// ruta dinamica visitandola con un identificador inventado. La pagina de "no
// encontrado" devuelve HTTP 200 y quedaria en verde.

function veredicto(m, listaBlanca, rebotesEsperados = {}) {
  const razones = [];

  // FALLIDA = la pagina no se puede usar: no llega, te echa, o revienta.
  if (m.errorNavegacion) razones.push(`navegacion: ${m.errorNavegacion}`);
  if (m.http !== null && m.http >= 400) razones.push(`HTTP ${m.http}`);
  // El rebote a la entrada se puede DECLARAR esperado, con motivo escrito. Es
  // el unico veredicto que admite declaracion, y a proposito: hay paginas que
  // deben echarte (la portada sin sesion), pero NINGUNA que deba reventar. Si
  // esta puerta se abriera a los errores de pagina o a los HTTP 4xx, seria una
  // manera comoda de silenciar fallos de verdad.
  if (m.rebotaALogin && !rebotesEsperados[m.patron]) {
    razones.push(`rebota a la pantalla de entrada (${m.urlFinal.replace(BASE, '')})`);
  }
  if (m.errores.length) razones.push(`error de pagina: ${m.errores[0]}`);
  if (m.rechazos.length) razones.push(`promesa rechazada sin capturar: ${m.rechazos[0]}`);
  // Una pantalla de error capturada es un FALLO, no un estado vacio: devuelve
  // HTTP 200, a veces sin un solo error en consola, y es exactamente «una
  // pagina que carga y no funciona».
  if (m.fraseError) razones.push(`pantalla de error: «${m.fraseError}»`);

  if (razones.length) return { estado: 'fallida', razones, incidencias: [] };

  if (m.rebotaALogin && rebotesEsperados[m.patron]) {
    return { estado: 'rebote-esperado',
             razones: [rebotesEsperados[m.patron]], incidencias: [] };
  }

  // INCIDENCIA = la pagina se ve, pero algo por debajo devolvio 4xx/5xx o
  // escupio un error a la consola. Se separa de FALLIDA a proposito: meterlo
  // todo en el mismo saco haria imposible distinguir "esta pantalla no sirve"
  // de "esta pantalla sirve y ademas hay un 404 que cazar", y las dos cosas hay
  // que arreglarlas pero no son la misma. Ninguna de las dos se queda sin
  // explicar: el criterio de cierre exige CERO fallos sin explicacion, y una
  // incidencia sin explicar cuenta como fallo.
  const incidencias = [
    ...m.peticionesFallidas.map((x) => `peticion ${x}`),
    ...m.consola.map((x) => `consola: ${x}`),
  ];

  // Con datos = hay senyal de contenido DENTRO de <main> y <main> no anuncia
  // que esta vacio. Una frase de vacio solo condena si ademas no hay filas ni
  // celdas: hay pantallas que traen una tabla llena y, debajo, un panel
  // secundario que dice «sin actividad».
  const s2 = m.senyales;
  // CASI EN BLANCO: la red de seguridad para paginas que estan vacias SIN
  // decirlo. Es una red DELIBERADAMENTE estrecha (menos de 250 caracteres y
  // ninguna estructura), porque su version ancha —"menos de 900 caracteres"—
  // condenaba paginas con contenido de verdad: /admin/workflow-command-center
  // (728 caracteres, «4 clientes requieren accion inmediata») o
  // /client-portal/settings/mfa (415, explicacion + control). El trabajo de
  // decidir si una pagina esta vacia lo hace el ANUNCIO, no el recuento.
  const casiEnBlanco = s2.filas === 0 && s2.celdas === 0 && s2.campos === 0
                    && s2.tarjetas === 0 && s2.caracteres < 250;
  // El umbral de 1.200 caracteres esta escrito aqui, y no escondido, porque es
  // un JUICIO y no una medida. Dice: si <main> trae mas de ~1.200 caracteres,
  // la pagina esta ensenando algo, y la frase de vacio pertenece a UNA PARTE de
  // ella (un panel lateral, una tarjeta de estado), no a la pagina entera.
  // Ejemplo medido: /admin/compliance trae tres tarjetas de normativa con sus
  // puntuaciones (3.078 caracteres) y ademas un widget que dice «Sin datos».
  // Llamar vacia a esa pagina seria tan falso como llamar llena a
  // /admin/messages, que trae 216 caracteres y «No hay mensajes que mostrar».
  //
  // El informe publica las senyales de CADA pagina precisamente para que quien
  // lo lea pueda discutir este numero en vez de tener que creerselo.
  const UMBRAL_CONTENIDO = 1200;
  // `campos >= 3` distingue un FORMULARIO de un filtro. /client-portal/continuidad
  // es un cuestionario con seis campos y ademas una frase de vacio en un panel
  // lateral: es contenido. /admin/messages tiene UN campo (el buscador) y dice
  // «No hay mensajes que mostrar»: es vacio. Sin este matiz, o se condena al
  // cuestionario o se salva la bandeja vacia.
  const anunciaVacio = Boolean(m.fraseVacio) && s2.filas === 0 && s2.celdas === 0
                    && s2.campos < 3 && s2.caracteres < UMBRAL_CONTENIDO;
  const vacia = anunciaVacio || casiEnBlanco;

  if (vacia) {
    const motivo = listaBlanca[m.patron];
    if (motivo) return { estado: 'vacia-justificada', razones: [motivo], incidencias };
    return {
      estado: 'vacia', incidencias,
      razones: [m.fraseVacio
        ? `la pantalla dice: «${m.fraseVacio}»`
        : `practicamente en blanco (tarjetas=${m.senyales.tarjetas} campos=${m.senyales.campos} texto=${m.senyales.caracteres} car.)`],
    };
  }
  if (incidencias.length) {
    return { estado: 'verificada-con-incidencia', razones: [incidencias[0]], incidencias };
  }
  return { estado: 'verificada', razones: [], incidencias: [] };
}

// ════════════════════════════════════════════════════════════════════════════
// 8 · PRINCIPAL
// ════════════════════════════════════════════════════════════════════════════

async function main() {
  fs.mkdirSync(DIR_CAPTURAS, { recursive: true });

  const catRuta = path.join(DIR_SALIDA, 'identificadores.json');
  if (!fs.existsSync(catRuta)) {
    console.error(`Falta ${catRuta}. Lo genera 'make recorrer-todo'.`);
    process.exit(2);
  }
  const cat = JSON.parse(fs.readFileSync(catRuta, 'utf8'));

  const blancaRuta = path.join(RAIZ, 'docs', 'recorrido', 'lista_blanca_vacias.json');
  const listaBlanca = fs.existsSync(blancaRuta)
    ? JSON.parse(fs.readFileSync(blancaRuta, 'utf8')) : {};
  const rebotesRuta = path.join(RAIZ, 'docs', 'recorrido', 'rebotes_esperados.json');
  const rebotesEsperados = fs.existsSync(rebotesRuta)
    ? JSON.parse(fs.readFileSync(rebotesRuta, 'utf8')) : {};

  let rutas = derivarRutas();
  if (FILTRO) rutas = rutas.filter((r) => r.patron.includes(FILTRO));
  const patrones = new Set(rutas.map((r) => r.patron));

  console.log(`Inventario derivado de frontend/app: ${rutas.length} paginas ` +
              `(${rutas.filter((r) => r.dinamica).length} dinamicas)`);

  const nav = await chromium.launch();
  const t0 = Date.now();

  // ── sesiones ────────────────────────────────────────────────────────────
  console.log('\n== sesiones ==');
  const op = await sesionOperador(nav);
  console.log(`  operador  ${op.dentro ? 'dentro' : 'NO ENTRA'} · ${op.aterrizaje}`);
  const cli = await sesionCliente(nav);
  console.log(`  cliente   ${cli.dentro ? 'dentro' : 'NO ENTRA'} · ${cli.aterrizaje}`);
  const anon = await nuevoContexto(nav);
  const pgAnon = await anon.newPage();
  instrumentar(pgAnon);
  const portales = {};
  for (const p of ['auditor-portal', 'pentester-portal', 'remediation',
                   'verify-auth', 'diagnostico', 'sign', 'download']) {
    portales[p] = await sesionPortal(nav, p, cat);
  }
  console.log(`  portales  ${Object.keys(portales).length} contextos por token`);

  const paginaDe = (persona) => {
    if (persona === 'operador') return op.pg;
    if (persona === 'cliente') return cli.pg;
    if (persona === 'anonimo') return pgAnon;
    return portales[persona.split(':')[1]].pg;
  };

  // ── pasada principal: las 167 ───────────────────────────────────────────
  console.log('\n== recorrido de las paginas ==');
  const resultados = [];
  let n = 0;
  for (const r of rutas) {
    n++;
    const persona = personaDe(r.patron);
    const res = resolver(r.patron, cat);
    const nombreCaptura = r.patron.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '') || 'raiz';

    if (!res.url) {
      resultados.push({ ...r, persona, estado: 'no-verificada',
                        razones: [res.motivo], url: null });
      console.log(`  [${String(n).padStart(3)}/${rutas.length}] NO VERIF  ${r.patron}  · ${res.motivo}`);
      continue;
    }

    const pg = paginaDe(persona);
    let m = await visitar(pg, BASE + res.url, nombreCaptura);
    // Los portales por token piden el codigo de un solo uso; si aparece, se
    // introduce y se vuelve a medir la pagina de verdad.
    if (persona.startsWith('portal:')) {
      const puesto = await pasarOtpSiLoPide(pg, portales[persona.split(':')[1]].otp);
      // Se re-MIDE, no se re-VISITA: volver a pedir la URL haria reaparecer la
      // pantalla del codigo y mediriamos la puerta en vez del portal.
      if (puesto) m = await medir(pg, BASE + res.url, nombreCaptura);
    }
    m.patron = r.patron;
    const v = veredicto(m, listaBlanca, rebotesEsperados);
    resultados.push({ ...r, persona, url: res.url, usados: res.usados,
                      medida: m, estado: v.estado, razones: v.razones,
                      incidencias: v.incidencias || [] });

    const etiqueta = { verificada: 'OK      ', vacia: 'VACIA   ',
                       'vacia-justificada': 'VACIA-OK', fallida: 'FALLO   ',
                       'verificada-con-incidencia': 'OK+INCID',
                       'rebote-esperado': 'ECHA-OK ',
                       'no-verificada': 'NO VERIF' }[v.estado];
    console.log(`  [${String(n).padStart(3)}/${rutas.length}] ${etiqueta} ${r.patron}` +
                (v.razones.length ? `  · ${v.razones[0].slice(0, 110)}` : ''));
  }

  // ── tabla de expectativas · el 403 esperado NO es un fallo ──────────────
  //
  // Se comprueba lo contrario de lo de arriba: que la puerta de cada persona
  // este CERRADA para las demas. Una pagina de administrador que se abre con la
  // sesion del cliente no es un fallo de esta tabla: es un agujero.
  console.log('\n== expectativas cruzadas ==');
  const MUESTRA = [
    '/admin/projects', '/admin/clients', '/admin/settings',
    '/client-portal/dashboard', '/client-portal/evidencias', '/client-portal/plan',
  ].filter((p) => patrones.has(p));
  const expectativas = [];
  for (const patron of MUESTRA) {
    const duenyo = personaDe(patron);
    for (const persona of ['operador', 'cliente', 'anonimo']) {
      if (persona === duenyo) continue;
      const res = resolver(patron, cat);
      if (!res.url) continue;
      const pg = paginaDe(persona);
      const m = await visitar(pg, BASE + res.url, `exp_${persona}_${patron.replace(/[^a-z0-9]+/gi, '_')}`);
      const rutaFinal = m.urlFinal.replace(BASE, '').split('?')[0].replace(/\/$/, '');
      // La puerta esta cerrada si la persona NO acaba en la pagina que pidio.
      //
      // El primer intento exigia rebote a la entrada, 401, 403 o /forbidden, y
      // marcaba seis huecos que no existian: `frontend/middleware.ts` no
      // devuelve 403, MANDA A CADA UNO A SU PORTAL (el cliente que pide
      // /admin/* acaba en /client-portal/dashboard, y el operador que pide
      // /client-portal/* acaba en /admin/dashboard). Eso es una puerta cerrada,
      // y ademas mejor que un 403 a secas. El fallo era del criterio, no de la
      // aplicacion.
      const llego = rutaFinal === res.url.replace(/\/$/, '');
      const cerrado = !llego
                   || (m.http !== null && (m.http === 401 || m.http === 403));
      expectativas.push({
        ruta: patron, persona, duenyo,
        esperado: 'no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403',
        observado: llego
          ? `ENTRA (HTTP ${m.http} y se queda en ${rutaFinal})`
          : `le mandan a ${rutaFinal}`,
        correcto: cerrado,
      });
      console.log(`  ${cerrado ? 'OK   ' : 'HUECO'} ${persona.padEnd(9)} -> ${patron}`);
    }
  }

  // ── alcanzabilidad ──────────────────────────────────────────────────────
  let alcance = null;
  if (process.env.RECORRIDO_SIN_BFS !== '1') {
    console.log('\n== alcanzabilidad (recorrido en anchura desde cada portada) ==');
    const alcanzados = new Set();
    const rotos = [];
    let abiertas = 0;
    const tramos = [
      { persona: 'operador', pg: op.pg, semillas: [`${BASE}/admin/projects`], prefijos: ['/admin'] },
      { persona: 'cliente', pg: cli.pg, semillas: [`${BASE}/client-portal`], prefijos: ['/client-portal'] },
      { persona: 'anonimo', pg: pgAnon, semillas: [`${BASE}/`], prefijos: ['/'] },
    ];
    for (const t of tramos) {
      const r = await recorrerEnAnchura(t.pg, t.semillas, patrones,
                                        Math.floor(MAX_BFS / tramos.length), t.prefijos);
      r.alcanzados.forEach((p) => alcanzados.add(p));
      rotos.push(...r.rotos.map((x) => ({ ...x, persona: t.persona })));
      abiertas += r.abiertas;
      console.log(`  ${t.persona.padEnd(9)} abre ${r.abiertas} paginas · alcanza ${r.alcanzados.size} patrones · ${r.rotos.length} enlaces rotos`);
    }
    // Los portales por token no se recorren en anchura: se entra por un enlace
    // que llega por correo, no pinchando desde ningun sitio de la aplicacion.
    // Contarlos como huerfanos seria mentir; se declaran aparte.
    const porToken = rutas.filter((r) => personaDe(r.patron).startsWith('portal:'))
                          .map((r) => r.patron);
    const huerfanas = rutas.map((r) => r.patron)
      .filter((p) => !alcanzados.has(p) && !porToken.includes(p));
    alcance = { alcanzados: [...alcanzados].sort(), huerfanas, rotos, abiertas,
                porToken };
    console.log(`  ALCANZADAS ${alcanzados.size}/${rutas.length} · HUERFANAS ${huerfanas.length} · POR TOKEN ${porToken.length}`);
  }

  await nav.close();

  const informe = {
    generado: new Date().toISOString(),
    duracionSegundos: Math.round((Date.now() - t0) / 1000),
    base: BASE,
    inventario: {
      total: rutas.length,
      dinamicas: rutas.filter((r) => r.dinamica).length,
      porGrupo: rutas.reduce((a, r) => { a[r.grupo] = (a[r.grupo] || 0) + 1; return a; }, {}),
    },
    sesiones: { operador: op.dentro, cliente: cli.dentro },
    catalogo: { sembradoPorElArnes: cat.sembrado_por_el_arnes || {},
                sinDato: cat.sin_dato || {} },
    resultados, expectativas, alcance,
  };
  fs.writeFileSync(path.join(DIR_SALIDA, 'recorrido.json'),
                   JSON.stringify(informe, null, 2));

  const cuenta = (e) => resultados.filter((r) => r.estado === e).length;
  console.log('\n' + '─'.repeat(74));
  console.log(` VERIFICADAS ${cuenta('verificada')} (+${cuenta('verificada-con-incidencia')} con incidencia)` +
              ` · REBOTE ESPERADO ${cuenta('rebote-esperado')}`);
  console.log(` VACIAS JUSTIFICADAS ${cuenta('vacia-justificada')} · VACIAS SIN JUSTIFICAR ${cuenta('vacia')}`);
  console.log(` NO VERIFICADAS (sin dato) ${cuenta('no-verificada')} · FALLIDAS ${cuenta('fallida')}`);
  console.log('─'.repeat(74));
  console.log(`Detalle: var/recorrido/recorrido.json · capturas en var/recorrido/capturas/`);

  const malas = cuenta('fallida') + cuenta('vacia');
  process.exit(malas > 0 ? 1 : 0);
}

if (require.main === module) {
  main().catch((e) => { console.error('FALLO del arnes:', e.stack || e.message); process.exit(2); });
}
