# Medición · los dos RCE de Next.js y qué cuesta salir de ellos

**Fecha de la medición**: 2026-09-10 · **commit**: `c8ece1c` · **rama**: `main`
**Máquina**: Linux 6.6.87.2 (WSL2), Node v20.20.2, npm v10.8.2

Este documento existe para sustituir una corazonada por dos números. La pregunta era:

> ¿Usa esta aplicación las funcionalidades que los dos RCE atacan? ¿Y qué rompe el salto a Next
> 15.5.24, contado en errores?

Todo lo que sigue lleva el comando que lo produce y su salida. Donde no se pudo medir, lo dice con
esas palabras y explica por qué. **Nada de este documento es una estimación presentada como
medición.**

Convención: los comandos se ejecutan desde la raíz del repositorio salvo que se indique otra cosa.
Se usa `command grep` para saltarse el envoltorio de `ugrep` que hay en esta máquina, que respeta
`.gitignore` y omite ficheros en silencio. `$SCRATCH` abrevia el directorio temporal de la sesión
donde vive la copia; en las salidas reales aparece la ruta completa.

---

## 0. Punto de partida

```
$ cd frontend && node -e "console.log(require('next/package.json').version)"
14.2.33
```

Los dos avisos críticos están acotados por escrito, con fecha de caducidad, en
`.github/npm-audit-allowlist.json`, y `.github/scripts/npm_audit_gate.py` los deja pasar hasta el
**2026-12-31**. Acotados no es arreglados: pasada esa fecha el gate los trata como fallo.

---

## 1. Cuáles son exactamente los dos CVE

```
$ cd frontend && npm audit --json
```

Recuento por severidad que devuelve el informe:

```json
{"info": 0, "low": 1, "moderate": 0, "high": 7, "critical": 1, "total": 9}
```

El único paquete con severidad `critical` es `next`, que arrastra **25 avisos propios** (más uno
transitivo por `postcss`). Dos de los 25 son críticos:

| GHSA | CVE | CWE | Título del aviso | Rango vulnerable |
|---|---|---|---|---|
| `GHSA-p293-qw3h-jr36` | CVE-2026-75604 | CWE-22 | Unauthenticated Remote Code Execution on windows-hosted servers | `>=13.4.0 <15.5.24` |
| `GHSA-2xp9-vwfh-vxw4` | (sin CVE asignado) | CWE-1395 | Unauthenticated Remote Code Execution in Image Optimization API when AVIF files are used | `>=10.0.0 <15.5.24` |

Descripción literal de cada aviso, tomada de la base de avisos de GitHub:

- **GHSA-p293-qw3h-jr36** — «A vulnerability in applications using Pages and App router without
  Cache Component can lead to remote code execution when the server is hosted on machines using a
  Windows filesystem.» Versiones parcheadas: 15.5.24 y 16.3.3. CVSS 9.0. El aviso dice
  explícitamente que **no hay solución alternativa** («No known workaround available»).
- **GHSA-2xp9-vwfh-vxw4** — «A vulnerability in the underlying `libheif` library used by `sharp`
  which Next.js uses for image optimization can lead to remote code execution when AVIF files are
  optimized.» Versiones parcheadas: 15.5.24 y 16.3.3. El aviso añade: «Until a fix has propagated,
  optimization of AVIF files is disabled.»

Así que las dos superficies son:

1. La resolución de rutas del App/Pages Router **sobre un sistema de ficheros Windows**.
2. La **API de optimización de imágenes**, cuando decodifica un AVIF con `libheif` (que llega a
   través del paquete `sharp`).

**Un detalle que conviene no pasar por alto**: la corrección que propone el propio npm no es
15.5.24, sino **16.3.4**.

```
$ cd frontend && npm audit --json | python3 -c "import sys,json; print(json.load(sys.stdin)['vulnerabilities']['next']['fixAvailable'])"
{'name': 'next', 'version': '16.3.4', 'isSemVerMajor': True}
```

npm calcula 16.3.4 porque el rango vulnerable agregado de `next` llega hasta
`16.3.0-preview.10`: hay avisos (no críticos) que 15.5.24 no cierra. Volveremos a esto en §3.5.

---

## 2. ¿Usa esta aplicación las superficies afectadas?

### 2.1 GHSA-p293-qw3h-jr36 · el de Windows

El aviso condiciona la explotación a que el servidor corra **sobre un sistema de ficheros Windows**.
Lo demás lo cumple esta aplicación de sobra, así que la pregunta se reduce al sistema operativo.

Lo que sí se cumple (y por tanto no salva a nadie):

```
$ cd frontend && for d in app pages src/app src/pages; do printf "  %-12s " "$d/"; [ -d "$d" ] && echo "EXISTE ($(command find $d -name 'page.tsx' | wc -l) page.tsx)" || echo "no existe"; done
  app/         EXISTE (167 page.tsx)
  pages/       no existe
  src/app/     no existe
  src/pages/   no existe

$ cd frontend && command grep -rl --include=*.ts --include=*.tsx "use cache" . --exclude-dir=node_modules | wc -l
0
```

App Router con 167 páginas y **cero** uso de Cache Component (que además es una función de Next 15+,
no disponible en 14). Es decir: la aplicación encaja en la descripción «Pages and App router without
Cache Component».

El sistema operativo del despliegue, medido sobre el contenedor que está corriendo:

```
$ docker exec fulkro-demo-frontend-1 sh -c 'uname -s -m; cat /etc/os-release | head -2'
Linux x86_64
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"

$ command grep -nE "^FROM" frontend/Dockerfile
42:FROM node:20-bookworm-slim AS deps
48:FROM node:20-bookworm-slim AS builder
70:FROM node:20-bookworm-slim AS runner
```

Y el servicio `frontend` no monta ningún directorio del anfitrión, así que ni siquiera por un
`bind mount` entraría un sistema de ficheros Windows en juego:

```
$ sed -n '395,415p' docker-compose.demo.yml | command grep -nE "volumes|:/app"
(el bloque frontend no declara volumes)
```

**Veredicto: NO ALCANZABLE en el despliegue de referencia.** El único camino que lo haría alcanzable
es ejecutar el frontend **nativamente sobre Windows** (`next start` fuera de Docker). Con Docker
Desktop en Windows el contenedor sigue viendo un sistema de ficheros Linux dentro de la máquina
virtual, así que ese caso tampoco entra. **No medido**: no se ha probado a ejecutar la aplicación
sobre un Windows nativo — no hay ninguna máquina Windows disponible en este entorno, y el
`INSTALL.md` no propone esa vía.

### 2.2 GHSA-2xp9-vwfh-vxw4 · el del optimizador de imágenes y AVIF

Aquí hay cuatro preguntas encadenadas, y las cuatro tienen medición.

**(a) ¿Usa la aplicación `next/image`?** Sí, seis ficheros lo importan:

```
$ cd frontend && command grep -rl --include=*.tsx --include=*.ts -E "from ['\"]next/image['\"]" . --exclude-dir=node_modules
./app/(client-portal)/client-portal/login/page.tsx
./app/login/page.tsx
./app/not-found.tsx
./components/brand/Logo.tsx
./components/layout/ClientSidebar.tsx
./components/layout/Sidebar.tsx
```

La etiqueta correcta es *«seis ficheros importan `next/image`»*. Que se importe no significa que la
API de optimización llegue a servir nada, y de hecho aquí no sirve nada — lo que viene ahora.

**(b) ¿Llega alguna imagen de esta aplicación a la API de optimización?** No. Todos los `<Image>`
apuntan a SVG locales bajo `/public/brand/`, y Next **no enruta los SVG por el optimizador**: emite
la ruta estática directamente. Medido sobre la página renderizada:

```
$ curl -s http://127.0.0.1:3000/login | command grep -oE 'src="[^"]*"' | sort -u | command grep -v _next/static
src="/brand/fulkro-logo-light.svg"

$ curl -s http://127.0.0.1:3000/login | command grep -c "_next/image"
0
```

Descontados los `chunks` de JavaScript, la única imagen de la página de acceso es el SVG servido
como ruta estática, y **no aparece ni una sola vez `/_next/image` en el HTML**. Si se pide a mano,
el optimizador lo rechaza, porque `dangerouslyAllowSVG` no está activado (no hay bloque `images:` en
`next.config.mjs`), mientras que la ruta estática sí responde:

```
$ curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:3000/_next/image?url=%2Fbrand%2Ffulkro-logo-light.svg&w=256&q=75"
400
$ curl -s -o /dev/null -w "%{http_code} %{content_type}\n" "http://127.0.0.1:3000/brand/fulkro-logo-light.svg"
200 image/svg+xml
```

**(c) Entonces, ¿es inalcanzable el endpoint?** No tan rápido. El endpoint `/_next/image` **está
activo**. No acepta URLs remotas, porque `next.config.mjs` no tiene bloque `images:` y por tanto
`remotePatterns` está vacío:

```
$ command grep -nE "images|remotePatterns|formats|dangerouslyAllowSVG" frontend/next.config.mjs
(sin coincidencias · codigo de salida 1)

$ curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:3999/_next/image?url=https%3A%2F%2Fexample.com%2Fa.png&w=256&q=75"
400
```

Pero sí acepta rutas locales, y `next.config.mjs` reescribe `/api/:path*` al backend FastAPI.
Consecuencia: una petición a `/_next/image?url=/api/loquesea` hace que el propio Next **vaya a
buscar los bytes al backend** y los meta en el optimizador.

Se comprobó levantando un origen que sirve un AVIF real en el puerto 8000 y pidiendo la
optimización. El destino del rewrite lo fija `FULKRO_BACKEND_URL`, que por defecto es
`http://localhost:8000` (`next.config.mjs:2`); en la imagen del demo el build-arg lo cambia a
`http://backend:8000` (`docker-compose.demo.yml:395`). Cambia el host, no el mecanismo: en los dos
casos el optimizador de Next va a buscar los bytes al backend.

```
$ convert -size 64x64 xc:red prueba.avif && file prueba.avif
prueba.avif: ISO Media, AVIF Image

$ curl -s -D- -o /dev/null "http://127.0.0.1:3999/_next/image?url=%2Fapi%2Fprueba.avif&w=256&q=75" \
       -H "Accept: image/avif,image/webp,*/*" | command grep -iE "^HTTP/|^content-type"
HTTP/1.1 200 OK
Content-Type: image/avif

# y en el log del origen:
ORIGEN: /api/prueba.avif
```

El optimizador fue a buscar el fichero. **La superficie es alcanzable.** Un control con PNG confirma
que el pipeline de decodificación está vivo (166 bytes de PNG salen como 88 bytes de WebP):

```
$ curl -s "http://127.0.0.1:3999/_next/image?url=%2Fapi%2Fprueba.png&w=256&q=75" -o salida.bin
$ ls -l prueba.png salida.bin | awk '{print $5, $9}'
166 prueba.png
88 salida.bin
$ file salida.bin
salida.bin: RIFF (little-endian) data, Web/P image, VP8 encoding, 64x64
```

**(d) ¿Y el AVIF llega a `libheif`?** No, y esta es la parte decisiva. El AVIF vuelve **byte a byte
idéntico** al original:

```
$ sha256sum prueba.avif salida_avif.bin
366378b7fdc4b7d3ee777f187560cf56f67544990a4d0c825e4287135a0894fd  prueba.avif
366378b7fdc4b7d3ee777f187560cf56f67544990a4d0c825e4287135a0894fd  salida_avif.bin
```

El motivo está en el código de Next 14.2.33 y es verificable. El optimizador intenta usar `sharp` y,
si no está, cae a `squoosh`:

```
$ cd frontend && sed -n '155,158p;709p' node_modules/next/dist/server/image-optimizer.js
let sharp;
try {
    sharp = require(process.env.NEXT_SHARP_PATH || "sharp");
    if (sharp && sharp.concurrency() > 1) {
        const { processBuffer } = require("./lib/squoosh/main");
```

`sharp` **no está instalado**, ni en el árbol de desarrollo ni en la imagen que se despliega:

```
$ ls -d frontend/node_modules/sharp
ls: cannot access 'frontend/node_modules/sharp': No such file or directory

$ command grep -c '"sharp"' frontend/package-lock.json
0

$ command grep -rniE "sharp" frontend/Dockerfile* docker-compose*.yml
(sin salida)

$ docker exec fulkro-demo-frontend-1 sh -c 'ls -d /app/node_modules/sharp; find / -name "*libheif*" -not -path "/proc/*" 2>/dev/null'
ls: cannot access '/app/node_modules/sharp': No such file or directory
(ninguna coincidencia de libheif)
```

Y el propio Next lo confirma por consola al arrancar:

```
⚠ For production Image Optimization with Next.js, the optional 'sharp' package is strongly
  recommended. Run 'npm i sharp', and Next.js will use it automatically for Image Optimization.
```

Sin `sharp`, la decodificación la intenta `squoosh`, que no sabe leer AVIF; la excepción cae en el
`catch` del optimizador (`image-optimizer.js:830-838`: «If we fail to optimize, fallback to the
original image»), que devuelve el buffer de origen sin tocar.
Eso explica exactamente el SHA-256 idéntico. **`libheif` no existe en el despliegue, así que el
código vulnerable no llega a ejecutarse.**

**Veredicto: NO ALCANZABLE en el despliegue de referencia**, por ausencia de la biblioteca
vulnerable — no por configuración ni por validación de entradas.

**Y aquí está la letra pequeña, que importa**: la protección es que `sharp` no esté instalado, y
Next.js **pide instalarlo en cada arranque de producción**. Basta que alguien haga caso a ese aviso
—un `npm i sharp` bienintencionado para que las imágenes carguen más rápido— para que la superficie
pase de inalcanzable a viva, sin que ningún gate del repositorio se entere. El `npm audit` seguiría
diciendo lo mismo, porque el aviso ya está acotado.

### 2.3 Resumen de la primera pregunta

| Aviso | Superficie | ¿Alcanzable aquí? | Con qué medición |
|---|---|---|---|
| `GHSA-p293-qw3h-jr36` | Rutas sobre sistema de ficheros Windows | **No alcanzable** | El despliegue es Debian 12 en contenedor Linux (`uname`, `FROM node:20-bookworm-slim`) y el servicio no monta volúmenes del anfitrión |
| `GHSA-2xp9-vwfh-vxw4` | Optimizador de imágenes decodificando AVIF | **No alcanzable**, pero por los pelos | El endpoint SÍ es alcanzable vía `/_next/image?url=/api/...`; lo que falta es `libheif`, ausente porque `sharp` no está instalado (`find /` dentro del contenedor, SHA-256 idéntico de ida y vuelta) |

Ninguno de los dos veredictos es «el código es seguro». Son «en esta configuración, el camino de
explotación está cortado». La diferencia importa para decidir.

---

## 3. Qué rompe el salto a 15.5.24, contado en errores

### 3.1 Método

La actualización se probó **sobre una copia**, nunca sobre el árbol de trabajo:

```
$ cp -a /home/usuario/dev/Fulkrosys/frontend "$SCRATCH/frontend-next15"
$ sha256sum frontend/package.json "$SCRATCH/frontend-next15/package.json"
2e4aced6a8e9fa1d4308c6ae7b162006c6adaed74c7f92bf3ce0ff95a55b7cda  frontend/package.json
2e4aced6a8e9fa1d4308c6ae7b162006c6adaed74c7f92bf3ce0ff95a55b7cda  .../frontend-next15/package.json
```

`frontend/package.json` y `frontend/package-lock.json` del repositorio **no se han modificado**.

### 3.2 Línea base, en el árbol real

El job `frontend-typecheck` de `.github/workflows/ci.yml` ejecuta `npm run typecheck`, que es
`tsc --noEmit`. Antes de tocar nada:

```
$ cd frontend && npm ci
$ cd frontend && /usr/bin/time -f "elapsed=%es" npm run typecheck; echo "EXIT=$?"
> frontend@0.1.0 typecheck
> tsc --noEmit
elapsed=12.97s
EXIT=0

$ command grep -cE "error TS[0-9]+" typecheck_baseline.log
0

$ cd frontend && /usr/bin/time -f "elapsed=%es" npm run build; echo "EXIT=$?"
▲ Next.js 14.2.33
   ...
elapsed=57.93s
EXIT=0
```

(`tsc --noEmit` no imprime nada cuando no hay errores: el `0` de arriba es el recuento de líneas
`error TS` sobre su salida guardada.)

**Hoy: 0 errores de `tsc`, `npm run build` pasa** (con 8 avisos de ESLint y dos avisos de
`jose`/Edge Runtime, todos preexistentes), y produce **168 rutas** (83 estáticas + 85 dinámicas).

### 3.3 Qué arrastra la actualización

```
$ npm view next@15.5.24 peerDependencies --json
{
  "sass": "^1.3.0",
  "react": "^18.2.0 || 19.0.0-rc-de68d2f4-20241204 || ^19.0.0",
  "react-dom": "^18.2.0 || 19.0.0-rc-de68d2f4-20241204 || ^19.0.0",
  "@playwright/test": "^1.51.1",
  "@opentelemetry/api": "^1.1.0",
  "babel-plugin-react-compiler": "*"
}
```

**React 19 no es obligatorio**: `next@15.5.24` acepta React 18. Eso reduce mucho el alcance del
salto. La actualización aplicada en la copia fue, por tanto, mínima:

```
$ npm install next@15.5.24 eslint-config-next@15.5.24 --package-lock-only
$ npm ci
added 601 packages in 12s
next instalado: 15.5.24
react instalado: 18.3.1
```

El lock pasa de 654 a 652 paquetes. `react` y `react-dom` se quedan en 18.3.1.

Efecto colateral que conviene saber: **`next build` reescribe `tsconfig.json`** por su cuenta. Lo
anuncia por consola («We detected TypeScript in your project and reconfigured your tsconfig.json
file for you»), añade `"target": "ES2017"` y, de paso, reformatea el fichero entero expandiendo los
arrays:

```
$ diff frontend/tsconfig.json "$SCRATCH/frontend-next15/tsconfig.json"
3c3,7
<     "lib": ["dom", "dom.iterable", "esnext"],
---
>     "lib": [
>       "dom",
>       "dom.iterable",
>       "esnext"
>     ],
21,22c25,29
<       "@/*": ["./*"]
<     }
---
>       "@/*": [
>         "./*"
>       ]
>     },
>     "target": "ES2017"
24,25c31,39
<   "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
<   "exclude": ["node_modules"]
---
>   "include": [
>     "next-env.d.ts",
>     "**/*.ts",
>     "**/*.tsx",
>     ".next/types/**/*.ts"
>   ],
>   "exclude": [
>     "node_modules"
>   ]
```

Es un cambio automático y sin consecuencias funcionales, pero ensucia el diff de la actualización si
nadie lo espera.

### 3.4 Los números

Hay que separar dos comprobaciones que suelen confundirse: `tsc --noEmit` **no** valida las props de
las páginas contra los tipos de ruta que Next genera. Eso lo hace `next build`. De ahí que el primer
número no se mueva y el segundo sí.

| Comprobación | Next 14.2.33 | Next 15.5.24 (sin codemod) | Next 15.5.24 (tras codemod + 1 línea) |
|---|---|---|---|
| `npm run typecheck` (`tsc --noEmit`) | **0 errores** | **0 errores** | **0 errores** |
| `next build --no-lint` (sólo tipos) | pasa | **falla** · 1 error de tipos | **pasa** |
| `npm run build` (completo) | **pasa** · 0 errores, 8 avisos | **falla** · 1 error de ESLint, 8 avisos | **pasa** · 0 errores, 8 avisos |
| `npm audit` · críticos | **1 paquete, 2 GHSA críticos** | **0 críticos** | **0 críticos** |
| `npm audit` · avisos totales | 9 | 6 | 6 |
| Rutas generadas | 168 | — | **168** |

**`tsc --noEmit`: 0 errores hoy → 0 errores con Next 15.5.24.** El número no se mueve, y la razón es
medible: la aplicación casi no usa las APIs que Next 15 volvió asíncronas.

```
$ cd frontend && command grep -rl --include=*.ts --include=*.tsx -E "from ['\"]next/headers['\"]" . --exclude-dir=node_modules | wc -l
0
```

Cero ficheros importan `next/headers`, así que `cookies()`, `headers()` y `draftMode()` —las tres
funciones que pasaron a ser asíncronas— no se usan en ninguna parte. (Un `grep` de `cookies()` da 8
ficheros, pero los ocho son `context.cookies()` de Playwright en `tests/e2e/`: no tienen nada que ver.)

### 3.5 Los errores del build, agrupados por causa

**Grupo 1 — `params` de página, ahora una `Promise` · 77 ficheros.**

El primer `next build` con Next 15 falla en el lint antes de llegar a los tipos. Desactivando el lint
aparece la causa real, literal:

```
$ npx next build --no-lint
✓ Compiled successfully in 11.7s
  Checking validity of types ...
Failed to compile.

app/(admin)/admin/magerit-analyses/[id]/import/page.tsx
Type error: Type '{ params: { id: string; }; }' does not satisfy the constraint 'PageProps'.
  Types of property 'params' are incompatible.
    Type '{ id: string; }' is missing the following properties from type 'Promise<any>': then, catch, finally, [Symbol.toStringTag]
```

`next build` aborta en el **primer** fichero con error de tipos, así que ese «1» no es el tamaño del
problema: es lo primero que se encontró. Para contar el grupo entero se usó el codemod oficial:

```
$ npx @next/codemod@canary next-async-request-api . --force
All done.
Results:
0 errors
1156 unmodified
0 skipped
77 ok
Time elapsed: 1.559seconds
```

**77 ficheros modificados** (76 `page.tsx` + 1 `layout.tsx`), 0 errores, 0 saltados, en 1,6 segundos.
El cambio es mecánico:

```diff
-export default function MageritImportPage({
-  params,
-}: {
-  params: { id: string };
-}) {
+export default async function MageritImportPage(
+  props: {
+    params: Promise<{ id: string }>;
+  }
+) {
+  const params = await props.params;
   return <MageritImportPanel analysisId={params.id} />;
 }
```

**Grupo 2 — regla nueva de `eslint-config-next` 15 · 1 fichero, 1 línea.**

```
./app/global-error.tsx
106:13  Error: Do not use an `<a>` element to navigate to `/`. Use `<Link />` from `next/link`
        instead. See: https://nextjs.org/docs/messages/no-html-link-for-pages  @next/next/no-html-link-for-pages
```

Es un `Error`, no un aviso, y `next build` corta con él. Con Next 14 ese mismo fichero no se marcaba:
el build base da 8 avisos y **cero** errores, los mismos 8 avisos que el build con Next 15. Es decir,
la regla es nueva, no es deuda que estuviera oculta.

**Grupos que NO aparecieron.** Ninguno de los sospechosos habituales de Next 15 dio un solo error:

- `cookies()` / `headers()` / `draftMode()` asíncronos — 0 ficheros los usan (medido en §3.4).
- Cambio de caché por defecto (`fetch` ya no se cachea, rutas ya no son estáticas por defecto) — 0
  errores de compilación. **No medido**: un cambio de caché no rompe el build, cambia el
  comportamiento en ejecución. Verificarlo exigiría ejercitar las 168 rutas con la aplicación
  completa detrás, y eso no se ha hecho aquí (ver §5).
- El resto de roturas conocidas de Next 15, contadas sobre el código fuente (excluyendo
  `node_modules/` y `.next/`, que es donde un `grep` descuidado encuentra falsos positivos):

```
$ cd frontend && for pat in '@next/font' 'from "next/font' 'experimental-edge' '\.geo\b' \
      '\brequest\.ip\b|\breq\.ip\b' 'unstable_'; do
    printf "  %-34s %s ficheros\n" "$pat" \
      "$(command grep -rlE --include=*.ts --include=*.tsx "$pat" app components lib hooks middleware.ts | wc -l)"
  done
  @next/font                         0 ficheros
  from "next/font                    1 ficheros
  experimental-edge                  0 ficheros
  \.geo\b                            0 ficheros
  \brequest\.ip\b|\breq\.ip\b        0 ficheros
  unstable_                          0 ficheros
```

  El único `next/font` es `app/layout.tsx:2`, que ya importa de `next/font/google` (la forma nueva;
  la que rompió fue `@next/font`, que aquí no aparece). Tampoco hay Route Handlers —
  `find app -name route.ts` da 0— ni `generateMetadata`, que son los otros dos sitios donde `params`
  se volvió asíncrono.

**Resultado tras aplicar los dos arreglos** (codemod automático + una línea de
`eslint-disable-next-line`):

```
$ npm run build
elapsed=43.63s
EXIT=0
  Errores: 0 · Warnings: 8
```

Build en verde, **168 rutas**, las mismas que con Next 14.

### 3.6 Qué pasa con los avisos de seguridad después del salto

```
$ cd "$SCRATCH/frontend-next15" && npm audit --json > audit_next15.json
$ python3 -c "import json;print(json.load(open('audit_next15.json'))['metadata']['vulnerabilities'])"
{'info': 0, 'low': 1, 'moderate': 1, 'high': 4, 'critical': 0, 'total': 6}
```

Los dos RCE desaparecen. Quedan 6 avisos (4 `high`), todos en dependencias de herramientas —
`brace-expansion`, `js-yaml`, `nanoid`, `postcss`, `postcss-selector-parser` — y ninguno crítico.
`next` deja de tener avisos propios: su severidad `moderate` le llega por `postcss`.

Conviene entender **cómo** se arregla el aviso del AVIF, porque no es lo que uno supondría. Next
15.5.24 **añade AVIF a la lista de tipos que no se optimizan**:

```
# Next 14.2.33 (arbol real)
$ command grep -A8 "const BYPASS_TYPES = " frontend/node_modules/next/dist/server/image-optimizer.js
const BYPASS_TYPES = [
    SVG,
    ICO,
    ICNS,
    BMP,
    JXL,
    HEIC
];

# Next 15.5.24 (copia)
$ command grep -A9 "const BYPASS_TYPES = " node_modules/next/dist/server/image-optimizer.js
const BYPASS_TYPES = [
    SVG,
    ICO,
    ICNS,
    BMP,
    JXL,
    HEIC,
    AVIF
];
```

Es exactamente lo que anuncia el aviso: «optimization of AVIF files is disabled». No es un
`libheif` arreglado; es un AVIF que ya no se decodifica. Comprobado en ejecución contra la copia con
Next 15.5.24, con el mismo AVIF de antes:

```
$ curl -s -D- -o salida_avif_n15.bin "http://127.0.0.1:3998/_next/image?url=%2Fapi%2Fprueba.avif&w=256&q=75"
HTTP/1.1 200 OK
Content-Type: image/avif

$ cmp -s prueba.avif salida_avif_n15.bin && echo IDENTICO || echo DISTINTO
IDENTICO

# control con PNG: el optimizador sigue funcionando
$ curl -s -D- -o salida_png_n15.bin "http://127.0.0.1:3998/_next/image?url=%2Fapi%2Fprueba.png&w=256&q=75"
HTTP/1.1 200 OK
Content-Type: image/webp
$ ls -l prueba.png salida_png_n15.bin | awk '{print $5, $9}'
166 prueba.png
88 salida_png_n15.bin
```

Y un efecto secundario del salto que hay que saber: **Next 15 sí instala `sharp`**, y con él entra
`libheif` en el árbol de dependencias, aunque el optimizador ya no lo llame para AVIF.

```
$ ls -d node_modules/sharp
node_modules/sharp
$ ls node_modules/next/dist/server/lib/squoosh
ls: cannot access 'node_modules/next/dist/server/lib/squoosh': No such file or directory
$ node -e "const v=require('sharp').versions; console.log(v.heif, v.vips, v.sharp)"
1.23.2 8.18.6 0.35.4
$ strings node_modules/@img/sharp-libvips-linux-x64/lib/libvips-cpp.so.8.18.6 | command grep -ci "libheif\|heif_"
25
```

O sea: hoy la aplicación está protegida **porque le falta la biblioteca**; con Next 15.5.24 estaría
protegida **porque el código ya no la llama para AVIF**. La segunda es una garantía mejor, pero la
biblioteca pasa a estar presente.

---

## 4. La decisión

**Recomendación: subir a Next 15.5.24, y hacerlo pronto — pero no hoy a ciegas.** El trabajo medido
es un codemod automático sobre 77 ficheros (1,6 segundos, 0 errores) más una línea. No es «un
proyecto», que es lo que dice hoy la justificación escrita en `.github/npm-audit-allowlist.json`.
Esa justificación se escribió sin este número y ahora se puede corregir.

**Su contrapartida, y no es menor.** Lo que está medido es que **compila**: `tsc` en 0, `next build`
en verde y las mismas 168 rutas. Lo que **no** está medido es que **funcione**. Next 15 cambia el
comportamiento de caché por defecto (`fetch` deja de cachearse, las rutas dejan de ser estáticas por
omisión) y eso no produce ni un error de compilación: se manifiesta en ejecución, en 168 rutas, tres
portales y un middleware que decide autorización. Subir apoyándose sólo en «el build pasa» es
cambiar un riesgo conocido y acotado por uno desconocido y sin acotar. Entre el build en verde y el
despliegue hay que meter la suite de Playwright y un recorrido de los tres portales.

Segundo aviso, de otro tipo: **15.5.24 no deja el `npm audit` en cero.** Quedan 6 avisos, 4 de ellos
`high`, y la corrección que propone npm es 16.3.4, no 15.5.24 (§1). Subir a 15.5.24 cierra lo crítico
y deja lo demás donde está; ir a 16.x es otro salto mayor que no se ha medido aquí.

**Si aun así se decide esperar** —por ejemplo, porque el calendario del primer cliente manda— esto es
lo que hay que vigilar, y no es «esperar tranquilo»:

1. **Que nadie instale `sharp`.** Es la única cosa que hoy separa el aviso del AVIF de ser
   explotable, y Next.js recomienda instalarlo por consola en cada arranque de producción. Merece un
   test que falle si `sharp` aparece en `package-lock.json` mientras `next` siga por debajo de
   15.5.24. Hoy no existe tal test: se ha comprobado que `sharp` no aparece en el lock, no que algo
   impida que aparezca.
2. **Que nadie despliegue el frontend sobre Windows nativo.** Dentro de contenedores Linux el aviso
   de Windows no aplica; fuera de ellos, sí.
3. **Que no se añada `images.remotePatterns` ni `dangerouslyAllowSVG`** a `next.config.mjs`. Hoy no
   hay bloque `images:`, y eso es lo que impide que el optimizador acepte orígenes remotos.
4. **La fecha real de caducidad es el 2026-12-31**, escrita en `.github/npm-audit-allowlist.json`.
   No es una formalidad: `npm_audit_gate.py` trata una entrada caducada como fallo del build, así que
   ese día el CI se pone rojo por sí solo. Con el codemod medido, no hay razón para llegar a esa
   fecha con esto abierto.

---

## 5. Lo que NO se pudo medir, y por qué

- **Que la aplicación funcione con Next 15**, no sólo que compile. No se ejecutó la suite de
  Playwright ni un recorrido manual de los tres portales sobre la copia actualizada: eso exige la
  pila completa (backend, PostgreSQL, MinIO, sembrado) apuntando a la copia, y la copia sólo tiene el
  frontend. Es el trabajo que queda antes de subir de verdad.
- **El comportamiento de caché por defecto de Next 15** en las 168 rutas. Por lo mismo que el punto
  anterior: no se manifiesta en el build.
- **La explotabilidad real de ninguno de los dos avisos.** No se ha escrito ni ejecutado ninguna
  prueba de concepto. Lo medido es la *alcanzabilidad del camino* (qué componente responde, con qué
  bytes y con qué biblioteca), no que un atacante logre ejecución.
- **El comportamiento sobre un sistema de ficheros Windows.** No hay máquina Windows en este entorno.
- **Next 16.3.4**, que es lo que npm propone como corrección. Sólo se midió 15.5.24, que es lo que
  cierra los dos críticos y lo que dice la lista de avisos acotados.
- **El primer intento de actualización se abandonó por un cuelgue de npm**, no por un problema del
  código: `npm install next@15.5.24` se quedó parado dos veces (22 minutos sin E/S ni actividad de
  red, proceso en estado `S`). Se rodeó resolviendo primero el lock (`--package-lock-only`, 2 s) y
  luego instalando con `npm ci` (12 s). El resultado medido es el mismo árbol; queda anotado porque
  quien repita estos comandos puede toparse con el mismo cuelgue.

---

## Apéndice · reproducir esto de cero

```bash
# 1. Los avisos
cd frontend && npm ci && npm audit --json > /tmp/audit.json
python3 -c "import json;d=json.load(open('/tmp/audit.json'));print(d['metadata']['vulnerabilities'])"

# 2. La superficie
command grep -rl --include=*.tsx -E "from ['\"]next/image['\"]" . --exclude-dir=node_modules | wc -l
command grep -rl --include=*.ts --include=*.tsx -E "from ['\"]next/headers['\"]" . --exclude-dir=node_modules | wc -l
docker exec fulkro-demo-frontend-1 sh -c 'ls -d /app/node_modules/sharp; find / -name "*libheif*" -not -path "/proc/*" 2>/dev/null'

# 3. La linea base
npm run typecheck && npm run build

# 4. El salto, sobre una COPIA
cp -a frontend /tmp/next15 && cd /tmp/next15
npm install next@15.5.24 eslint-config-next@15.5.24 --package-lock-only && npm ci
npx next build --no-lint                          # -> error de params sincronos
npx @next/codemod@canary next-async-request-api . --force   # -> 77 ok
npm run build                                      # -> 1 error de ESLint en global-error.tsx
npm audit --json | python3 -c "import sys,json;print(json.load(sys.stdin)['metadata']['vulnerabilities'])"
```
