#!/usr/bin/env node
/**
 * Comprueba que el proxy /api/* quedo horneado apuntando a un host alcanzable
 * desde DENTRO de un contenedor.
 *
 * Por que existe (medido 2026-09-10, bloque D · D3): `next build` SERIALIZA el
 * destino de los rewrites en `.next/routes-manifest.json`, y `next start` usa
 * ese manifiesto en vez de volver a evaluar `rewrites()` de next.config.mjs.
 * En el demo, `FULKRO_BACKEND_URL=http://backend:8000` estaba correctamente
 * puesta como variable de RUNTIME, pero el build se habia hecho sin ella, asi
 * que el manifiesto decia `http://localhost:8000` — que dentro del contenedor
 * del frontend es el propio Next.js. Resultado: TODA llamada del navegador a
 * la API devolvia 500 y no se podia ni entrar por la web. `make smoke` no lo
 * veia porque entra por el puerto del backend, no por el del frontend.
 *
 * Se ejecuta al final del `next build` en frontend/Dockerfile: que reviente al
 * construir, no en produccion.
 *
 * Uso:  node scripts/verificar-proxy-api.js [ruta-al-routes-manifest.json]
 */
const path = require('path');

const ruta = process.argv[2]
  || path.join(process.cwd(), '.next', 'routes-manifest.json');

let manifiesto;
try {
  manifiesto = require(ruta);
} catch (e) {
  console.error(`FALLO: no se pudo leer ${ruta} (${e.message}).`);
  process.exit(1);
}

// `rewrites` es un array cuando next.config devuelve una lista, o un objeto
// {beforeFiles, afterFiles, fallback} cuando devuelve las tres fases.
const r = manifiesto.rewrites;
const lista = Array.isArray(r)
  ? r
  : [].concat(r?.beforeFiles || [], r?.afterFiles || [], r?.fallback || []);

const api = lista.find((x) => x && String(x.source).startsWith('/api'));
if (!api) {
  console.error(
    'FALLO: no hay ningun rewrite para /api/* en routes-manifest.json. '
    + 'El navegador no tendria por donde llegar al backend.',
  );
  process.exit(1);
}

if (/localhost|127\.0\.0\.1/.test(api.destination)) {
  console.error(
    `FALLO: el proxy /api/* quedo horneado a ${api.destination}. `
    + 'Dentro de un contenedor eso es el propio Next.js, no el backend: '
    + 'toda llamada del navegador devolveria 500. '
    + 'Pasa FULKRO_BACKEND_URL como --build-arg (no basta como variable de '
    + 'entorno en tiempo de ejecucion).',
  );
  process.exit(1);
}

console.log(`proxy /api/* -> ${api.destination}`);
