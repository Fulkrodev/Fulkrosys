# Informe del BLOQUE D

**Fecha**: 2026-09-10 · **Commits**: 9 sobre `03aed23` · **Rama**: `main`

Todo lo que sigue lleva el comando que lo reproduce. Donde no hay comando, está
escrito «no medido» y por qué.

---

## Dos cosas antes que el resumen

Las dos hablan de lo mismo, que es de lo que va la campaña entera: **una verdad
vacía no es una mentira, es peor, porque tiene forma de comprobación**.

### 1 · El criterio de cierre que acordamos era vacuo para lo que importaba

`make demo && make smoke` se dio por bueno el 2026-09-10, se escribió en el
informe de C0/C1 como cierre de C0.10, y con ese mismo criterio en verde **la
aplicación no se podía usar desde el navegador**. No es que estuviera lenta o
fea: el POST de entrada devolvía 500 y **toda** llamada del navegador a la API
fallaba. Cualquiera que hubiera clonado el repositorio y seguido `INSTALL.md`
habría visto una pantalla de acceso que no deja acceder.

La causa, medida: `next build` **serializa** el destino de los *rewrites* en
`.next/routes-manifest.json`, y `next start` usa ese manifiesto en vez de volver
a evaluar `rewrites()` de `next.config.mjs`. `FULKRO_BACKEND_URL` estaba
correctamente puesta como variable de tiempo de ejecución —el comentario del
`Dockerfile` afirmaba explícitamente que ahí bastaba— pero la imagen se había
construido sin ella, así que el manifiesto decía `http://localhost:8000`, que
dentro del contenedor del frontend es el propio Next.js:

```
$ docker exec fulkro-demo-frontend-1 sh -lc 'echo $FULKRO_BACKEND_URL'
http://backend:8000                                  <- la variable SÍ estaba
$ docker exec fulkro-demo-frontend-1 node -e \
    "console.log(require('/app/.next/routes-manifest.json').rewrites)"
[{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }]
$ docker logs fulkro-demo-frontend-1 | tail
Failed to proxy http://localhost:8000/api/v1/auth/login ECONNREFUSED
```

**Y por qué el humo no lo veía**: sus apartados 1 a 4 entran por
`127.0.0.1:18000`, el puerto del **backend**. Comprueban que la API responde,
que hay datos, que se puede entrar en los tres portales. Todo eso era cierto.
Lo que no comprueban es que el **navegador** llegue a esa API, que es lo único
que le pasa a una persona. La etiqueta decía «el demo sirve datos reales en los
tres portales» y lo que el comando medía era la API. El apartado 5, el único que
tocaba el frontend, se limitaba a pedir la portada y contar bytes, con un
comentario que enunciaba la falacia y a la vez la daba por buena
(`git show aff2dcd~1:scripts/demo_smoke.sh`, línea 345):

> *«Lo que hay detrás de la pantalla de entrada ya lo han comprobado los
> apartados 1 a 4 contra la API»*

Esa frase es la falacia entera en una línea: da por comprobado *lo que hay
detrás* midiendo *por otra puerta*.

El arreglo del criterio importa más que el arreglo del fallo: `make smoke` tiene
ahora un apartado **5.b** que repite el POST de entrada por el puerto del
**frontend**. Verificado que no es vacuo: contra la imagen anterior da **21
correctas / 1 fallida**; tras reconstruir, **22 / 0**. Y el `Dockerfile` falla
al construir si el destino queda horneado a `localhost`
(`frontend/scripts/verificar-proxy-api.js`), para que reviente construyendo y no
en producción.

Lección, escrita para no repetirla: **un criterio de cierre que no atraviesa el
mismo camino que el usuario no es un criterio de cierre.** Y la manera de
detectarlo es la de siempre: preguntarle a cada comprobación *qué mide
exactamente*, no *qué tranquiliza*.

### 2 · La respuesta fabricada no se quedaba en un registro: llegaba a la pantalla del cliente

D1 se ocupaba de que una llamada al modelo que falla dejara de contabilizarse
como éxito. Visto así parece un asunto de contabilidad interna: una fila del
registro con un estado equivocado y unos tokens inventados. Lo era, y ya habría
bastado. Pero al recorrer el portal como lo haría un cliente, esto es lo primero
que se leía en su portada:

```
Sugerencia IA
[MOCK] Agent 12 (Coach Cliente Evaluador). Model: sonnet-4.6.
Message length: 232. Sin ANTHROPIC_API_KEY: no se ha llamado al modelo.
```

Bajo un rótulo que dice **«Sugerencia IA»**. Es decir: el texto de relleno del
sustituto del modelo se estaba sirviendo al usuario **como si fuera producto**.
No se quedaba en `llm_interaction_log` para que lo viera un administrador: salía
por la interfaz, en la primera pantalla, en el portal del cliente que paga.

Eso es lo que justifica que D1 fuera lo primero y no un apunte de limpieza. El
mismo defecto —fabricar algo y presentarlo como auténtico— aparece en tres capas
distintas de este repositorio, y las tres se han cerrado en este bloque:

| capa | qué se fabricaba | qué lo sellaba como auténtico |
|---|---|---|
| **agente** (D1) | respuesta y tokens | `status="success"` y un coste calculado sobre 50 tokens constantes |
| **interfaz** (D3) | la misma respuesta | el rótulo «Sugerencia IA» en el portal del cliente |
| **corpus** (extra) | un resumen propio de 103 líneas | `publisher="Centro Criptológico Nacional (CCN)"` y la URL oficial como origen |

La tercera la encontró la segunda, y la segunda la encontró recorrer la
aplicación en vez de leerla. Ninguna de las tres la habría encontrado un test.

---

## Resumen por sub-bloque

| | qué se pedía | resultado medido |
|---|---|---|
| **D1** | que una llamada fallida deje de contar como éxito | `ConnectionError` → antes `success`, 222 tokens, **$0,001266**; ahora `error`, tokens y coste `NULL`. **7/7** tests (4 sin BD, 3 contra PostgreSQL) |
| **D6** | que `evals-llm` se salte sin clave | job **saltado** (gris), no verde. Tres casos probados extrayendo el paso del YAML |
| **D3** | recorrido guiado de diez minutos | `USAGE.md` · `make recorrido` → **60 correctas, 0 fallidas** |
| **D2** | subir la cobertura de evaluaciones | de **0** clases de agente a **3 de 13** (4 datasets, 40 entradas). Gate del arnés 6/6 → **25/25** |
| **D4** | ¿escala? | dos réplicas tras nginx · **15 correctas, 0 fallidas**. El fallo que encontró (SSE): **1 de 2 → 2 de 2** |
| **D5** | Next.js y el catálogo | codemod de **77 ficheros** + 1 línea; catálogo con **79 descripciones** reescritas, coincidencia máxima **7 palabras** |

**Criterio de cierre, ejecutado sobre el árbol final:**

```
make clean && make demo                2m 22s
make smoke                             22 correctas, 0 fallidas
make recorrido                         60 correctas, 0 fallidas
bash scripts/probar_dos_replicas.sh    15 correctas, 0 fallidas
```

---

## Decisiones con su contrapartida

- [ADR-058](adr/ADR-058-escalabilidad-horizontal.md) · escalabilidad horizontal.
  Entrega «como mucho una vez», buffer de repetición aún por proceso, Redis como
  dependencia del tiempo real multi-réplica.
- [ADR-059](adr/ADR-059-llamada-llm-fallida-no-es-exito.md) · la llamada fallida.
  `NULL` a cambio de perder el `NOT NULL`, `estimado` sí suma, y por qué el
  diccionario en memoria devuelve 0 mientras la fila guarda `NULL`.

---

## Lo que queda abierto

1. **Ningún golden dataset tiene todavía una tasa de aciertos real.** El gate
   contra el modelo necesita `ANTHROPIC_API_KEY` y no se ha ejecutado nunca. Los
   umbrales de 0,80 son los que declara cada dataset, **no una medición
   calibrada**.
2. **Los dos RCE de Next.js siguen acotados, no arreglados.** Medido: ninguno es
   alcanzable en esta configuración, pero uno se salva sólo por la **ausencia de
   `sharp`**, y Next imprime en cada arranque «Run `npm i sharp`». El salto a
   15.5.24 cuesta un codemod automático y una línea; lo que no está medido es que
   **funcione**, sólo que compile.
3. **Tres límites de seguridad viven en la memoria del proceso**
   (`_failed_attempts` del portal de auditor, dos `_RATE_STATE`). Con N réplicas
   se multiplican por N.
4. **Tres de las seis claves Ed25519 se generan en disco si faltan.** Sólo
   coinciden entre réplicas porque comparten un volumen local.
5. **`var/evidences` no está en MinIO.** Dos réplicas en máquinas distintas no
   compartirían las evidencias subidas.
6. **La protección de rama sigue sin activar.** Los pasos, con los nombres
   literales de los checks, están en [CI.md](CI.md).
7. **Que las 79 descripciones del catálogo sean normativamente exactas no lo
   verifica ningún script.** Eso lo revisa una persona.
8. **`AgentBase` ya no fabrica, pero `copilot_admin_service` y
   `copilot_cliente_service` siguen escribiendo `status="success"` a mano.** Hoy
   es correcto (sus tokens vienen del proveedor); si adquieren modo degradado,
   tendrán que usar los mismos estados.

## Lo que NO se ha medido, y por tanto no se afirma

- Rendimiento y latencia, antes o después del puente SSE.
- Cuántas réplicas aguanta PostgreSQL. Esto escala la capa de aplicación, no la
  de datos.
- Comportamiento con réplicas en **máquinas distintas**: todo lo medido son dos
  contenedores en el mismo anfitrión compartiendo un volumen local.
- Que la aplicación **funcione** con Next 15, sólo que compile.
- El coste en euros de `evals-llm`, que pasa de 10 a 40 llamadas por ejecución.
