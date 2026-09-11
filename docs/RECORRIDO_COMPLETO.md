# Recorrido completo de la aplicación

**Generado**: 2026-09-10T23:04:37.306Z · **Duración**: 969 s · **Contra**: http://localhost:3000

Reproducirlo entero:

```
make demo && make recorrer-todo
```

> La regla que manda sobre todas las demás en este documento: **una página que carga no es una página que funciona.** Un HTTP 200 lo devuelve igual una pantalla llena de datos que un cascarón que dice «no hay nada». Aquí no se mide *responde*: se mide **qué se ve**, **qué falla por debajo** y **si alguien puede llegar pinchando**.

## Lo que ha encontrado, empezando por lo que peor se lee

Este apartado lo escribe una persona; todo lo que viene después de la línea son
tablas generadas por la medida. La separación es deliberada: el juicio sobre lo
que significan los números no lo puede firmar un script.

### 0 · Lo primero: ¿estas cifras son de antes o de después de arreglar?

Un titular que caduca dentro del mismo commit que lo publica ya nos pasó una
vez. Así que va delante y con la comprobación al lado.

**Son de DESPUÉS**, y se puede verificar por dos vías independientes:

- **Por el reloj.** El último arreglo de producto se comprometió a las 21:05 y
  la primera pasada buena se generó a las 21:47. `git log --date=format:'%H:%M'`
  lo enseña.
- **Por la medida, que es la que vale.** Las tres páginas que estaban rotas por
  usar una API de Next.js 15 sobre Next.js 14 salen `verificada` en el JSON en
  bruto, y ni un solo 404 a `/admin/projects/{id}/dashboard` aparece ya entre
  las incidencias:

  ```
  $ python3 -c "import json;d=json.load(open('var/recorrido/recorrido.json'));\
  print([x['estado'] for x in d['resultados'] if 'cliente-info' in x['patron']])"
  ['verificada']
  ```

Las cifras de este documento se han vuelto a medir el **2026-09-11** sobre una
pila reconstruida con los arreglos del bloque I dentro.

### 0.b · Qué NO se arregló, y por qué

Se arreglaron cuatro defectos de producto. Los que quedan, uno a uno, para que
nadie tenga que deducirlos de una tabla:

**1. `ProjectSwitcherDropdown` sigue enlazando a una ruta que no existe, a
propósito.** Es el cuarto de los cuatro componentes que apuntaban a
`/admin/projects/{id}/dashboard`. Los otros tres se arreglaron. Éste no, y el
motivo está escrito en el propio fichero: además del `/dashboard` inexistente,
mete un id de **cliente** donde va uno de **proyecto**. Quitarle sólo el
`/dashboard` cambiaría un 404 visible por una pantalla de «proyecto no
encontrado» servida con **HTTP 200** — sustituir un fallo que se ve por uno que
no se ve, que es exactamente lo contrario de lo que busca esta campaña. Se
arregla cuando se arreglen las dos cosas a la vez.

**2. Las dos páginas FALLIDAS siguen fallando.**
`/admin/projects/[id]/workflow` y `/admin/workflow-command-center/projects/[id]`
enseñan una pantalla de error con «No se pudo cargar la vista del proyecto ·
Project not found». Están contadas como fallo, no como vacío, precisamente para
que no se puedan confundir con una pantalla legítimamente sin datos. No se han
arreglado porque el diagnóstico no está hecho: hay que averiguar si el
identificador que llega es el equivocado o si la consulta filtra de más, y eso
es trabajo con su propia medida.

**3. Las once páginas con incidencia por debajo siguen pidiendo endpoints que
devuelven 404 o 403.** Nueve de ellas son `/admin/projects/[id]/*` llamando a
rutas de API que no existen (`/archetype`, `/assets`, `/invoices`,
`/workspace`…). La página se ve, así que un recorrido que sólo mirara el HTTP
200 diría que todo va bien. No se arreglan aquí porque son nueve piezas de
backend distintas, no un defecto.

**4. Las ocho páginas vacías sin justificar siguen vacías.** Cinco porque el
demo no siembra el dato y tres porque la función no existe todavía; el detalle,
en el apartado 7. Sembrar cinco cosas es trabajo de sembrado, no de este bloque,
y las tres que dicen «próximamente» no se arreglan sembrando nada.

**Y uno que sí se arregló en este bloque**: el código de ticket interno
`TODO-FASE-9-MAGIC-LINK-DOSSIER-DOWNLOAD-001` que el portal de descarga le
enseñaba a un cliente. **Estaba anotado, ahora está arreglado**: el motivo
interno va al registro y el cliente recibe un mensaje que le dice lo único que
le sirve. De paso, el frontend detectaba ese caso buscando una subcadena del
mensaje del backend —`"pendiente de integracion"`—, de forma que este mismo
arreglo lo habría roto en silencio y el aviso amable se habría vuelto un error
rojo. Ahora mira el código HTTP 501.

### 1 · Crear un proyecto te dejaba en un 404

Cuatro componentes enlazaban a `/admin/projects/{id}/dashboard`. **Esa ruta no
existe**: no hay ninguna carpeta `dashboard` bajo
`frontend/app/(admin)/admin/projects/[id]/`. El recorrido lo vio como una
petición 404 por debajo en casi todas las páginas de proyecto (Next.js precarga
el destino del enlace del encabezado, así que el 404 ocurre sin que nadie
pinche).

El peor de los cuatro es `CreateProjectModal`: después de crear un proyecto, la
aplicación te llevaba ahí. Los otros dos arreglados son el chip de proyecto del
encabezado y la miga de pan, presentes en **todas** las páginas de proyecto.

El cuarto sigue roto **a propósito**, con el motivo escrito en el propio
fichero: `ProjectSwitcherDropdown` además mete un id de **cliente** donde va uno
de **proyecto**. Quitarle sólo el `/dashboard` cambiaría un 404 visible por una
página de «proyecto no encontrado» servida con HTTP 200 — sustituir un fallo que
se ve por uno que no se ve, que es exactamente lo contrario de lo que busca esta
campaña.

### 2 · Un código de ticket interno, en la pantalla de un cliente · ARREGLADO

El escáner de texto fabricado encontró **una** aparición en las 167 páginas, y
era de verdad. El portal de descarga le enseñaba a quien recibe el enlace:

> Descarga aún no disponible · descarga_dossier_final pendiente de integracion
> M09 dossier_generator (**TODO-FASE-9-MAGIC-LINK-DOSSIER-DOWNLOAD-001**).

Era la misma familia que el «[MOCK] Agent 12» del bloque D: un artefacto interno
que se escapa a la interfaz de alguien de fuera. Y no sólo feo: es información
de arquitectura interna regalada a cualquiera que tenga un enlace.

**Arreglado el 2026-09-11.** El motivo interno va al registro, con el `purpose`
al lado para poder buscarlo, y quien recibe el enlace lee lo único que le sirve:
que no es culpa suya y que no tiene que hacer nada. Los dos 501 de ese
despachador —el del dossier y el del certificado— pasan por el mismo sitio.

Un detalle que sale de arreglarlo, y que es el hallazgo de segundo orden: el
frontend distinguía «todavía no disponible» de «ha fallado algo» **buscando la
subcadena `"pendiente de integracion"` en el mensaje del backend**. O sea, este
mismo arreglo lo habría roto en silencio: el aviso amable en azul se habría
convertido en un error rojo sin que nada avisara. Ahora mira el código HTTP 501,
que es lo que ese código significa.

La otra mitad de la noticia es buena y también hace falta decirla: **cero
apariciones de `[MOCK]`** en las 167 páginas, así que el arreglo de D1 aguanta.

### 3 · Siete de las ocho páginas legales no las enlazaba nadie · ARREGLADO (y debajo había otro defecto)

Las páginas legales se enlazaban entre sí, pero **desde fuera del grupo legal
sólo había un enlace en todo el código**: el del banner de cookies, que apunta a
`/cookies`.

```
$ grep -rn 'href="/\(privacy\|terms\|trust\|imprint\|dpa-template\|sub-processors\|derechos-rgpd\)"' \
    frontend/components frontend/app frontend/lib | grep -v "app/(legal)/"
   (sin resultados)
```

A la política de privacidad, a los términos, al centro de confianza, al aviso
legal y al listado de subencargados **sólo se llegaba escribiendo la URL**.

En un producto que vende cumplimiento eso pesa más que en otro. El RGPD (art.
13) no pide que la información al interesado *exista*: pide que se le
**facilite**, y el considerando 58 exige que sea «fácilmente accesible». Y
`/derechos-rgpd` es peor todavía: es la página para **ejercer** un derecho, y un
derecho que no tiene por dónde pincharse no se puede ejercer.

**Arreglado el 2026-09-11.** Las ocho van en `FulkroFooter`, que vive en el
layout raíz, así que salen en todas las páginas menos en los cuatro portales por
token —que tienen identidad neutra por diseño y su propio pie— y en el propio
grupo legal, que ya traía los suyos y habría enseñado la lista dos veces.

**Y aquí lo interesante, que es lo que este bloque persigue: arreglarlo destapó
un defecto que llevaba escondido justo debajo.** En la primera pasada con el pie
puesto, el recorrido encontró un enlace roto que antes no existía:

```
$ python3 -c "import json;print(json.load(open('var/recorrido/recorrido.json'))['alcance']['rotos'])"
[{'url': '/api/v1/legal/dpa-template/download', 'http': 401, 'persona': 'anonimo'}]
```

El botón de descarga del contrato de encargo del tratamiento devolvía **401**. Y
el endpoint **se declara público en su propio docstring** («`dpa_public_router`
(no auth)»): lo paraba la dependencia global de autenticación de ADR-030 antes
de llegar a él. Llevaba así desde siempre, y nadie lo había notado **porque a esa
página no llegaba nadie**.

Es exactamente la misma familia que el 401 de `/metrics` del bloque G, y la
misma lección en una frase: **un endpoint que nadie puede alcanzar no es un
endpoint que funciona, es uno que nadie ha probado.** Arreglado por el proceso
que el propio ADR-030 exige —entrada en la lista blanca con su criterio
justificado, test de regresión y enmienda al ADR—, y comprobado sobre HTTP: de
401 a 200 con un DOCX de 41.577 bytes.

### 3.b · Las huérfanas, separadas: 15 del producto, no 67

La cifra de 67 huérfanas del primer informe era cierta y poco útil, porque metía
en el mismo saco tres cosas que se arreglan de forma distinta. Ahora el reparto
es parte del arnés, no de este texto, y da esto:

| | páginas |
|---|---|
| Declaradas · destino de una reescritura, **no debe** llegarse pinchando | 3 |
| **Del producto · ninguna referencia en todo el código** | **15** |
| Del sembrado · el enlace existe, falta la fila desde la que pinchar | 41 |
| Del arnés · sólo enlazada desde un control que el rastreador no acciona | 0 |

De 67 a 59 primero, por los enlaces legales del pie; y de 59 al reparto de
arriba. **El número que hay que mirar es 15.**

Y aquí hay dos correcciones de mi propio medidor que valen más que la cifra:

- **La primera versión de este reparto daba «0 del producto».** Leía
  `tsconfig.tsbuildinfo` —un artefacto de compilación que contiene *todas* las
  rutas del proyecto— y contaba los specs de Playwright como enlaces. Un spec
  que hace `page.goto('/admin/x')` no es un enlace: nadie puede pincharlo.
  Salía la cifra perfecta, y era falsa.
- **La segunda daba 31, y también era falsa, por lo contrario.** Buscaba la ruta
  literal, y las pestañas de proyecto no se escriben así: `ProjectTabs.tsx`
  tiene una tabla de fragmentos (`{ href: "/exit" }`) que se componen en tiempo
  de render con `basePath = \`/admin/projects/${projectId}\``. Veintisiete
  páginas que están enlazadas salían como «sin ninguna referencia».

Las quince que quedan sí lo son, comprobadas a mano. Cuatro llaman la atención
por ser el gemelo administrativo del portal del auditor —`audit/annotations`,
`audit/clarifications`, `audit/dda-evidence-gaps`, `audit/draft-report`—:
páginas enteras, con su API detrás, a las que no lleva ningún enlace. Y
`/client-portal/firmas-pendientes` es la lista de documentos que un cliente
tiene que firmar, sin un solo sitio desde el que llegar a ella.

**No se han arreglado en este bloque.** Añadir quince entradas de menú sin
pensar dónde va cada una es cómo se llega a un menú que nadie entiende; y cuatro
de ellas piden decidir antes si el gemelo administrativo del portal del auditor
es una sección o son pestañas de `/audit`. Queda contado, que era lo pedido.

### 3.c · Arreglar una página rota puso ROJA una puerta que llevaba meses verde

Esto salió al empujar los 29 commits y mirar Actions, y es la mejor ilustración
de para qué sirve este bloque entero.

`/admin/projects/[id]/cliente-info` era una de las tres páginas que usaban la
API de `params` de Next.js 15 sobre Next.js 14: `use(params)` lanzaba el error
de React #438, el límite de error lo capturaba y la pantalla se quedaba en «No
pudimos cargar esta sección», **sirviendo HTTP 200**.

Esa página tiene su propia puerta de accesibilidad en CI
(`tests/polish/p1/14_admin_project_cliente_info.spec.ts`, que exige **cero**
violaciones de axe de severidad crítica o seria). Y **estaba en verde**.

Estaba en verde porque un límite de error no tiene nada que analizar: ni el
desplegable de filtro de contactos, ni el campo de búsqueda. axe barría una caja
de error, no encontraba nada, y la puerta pasaba. Al arreglar la página, CI se
puso rojo con dos violaciones **críticas** que llevaban ahí desde siempre:

```
Error: WCAG AA · 2 violations: [critical] label, [critical] select-name
```

- El `<select>` de categoría no tenía nombre accesible. Quien lo ve se orienta
  con la primera opción («Todas las categorías»); quien lo recorre con un lector
  de pantalla llega al control sin ese contexto.
- El buscador usaba `placeholder` como si fuera etiqueta. No lo es: desaparece
  en cuanto escribes, y no se anuncia como nombre del campo.

Los dos arreglados con `aria-label`. Pero lo que hay que llevarse no es el
arreglo, son **dos** lecciones:

1. **Una puerta de calidad sobre una página rota no mide nada, y encima da un
   verde tranquilizador.** No falló: pasó, durante meses, sobre una pantalla de
   error. Es exactamente «una página que carga no es una página que funciona»,
   pero aplicado al medidor en vez de a la página.
2. **Arreglar algo puede destapar deuda que estaba tapada por el fallo.** Que CI
   se ponga rojo después de un arreglo no significa que el arreglo esté mal:
   aquí significa que hasta ahora no se estaba midiendo nada.

### 4 · El sembrado del demo deja tres familias de rutas sin nada que enseñar

`make demo` no crea ninguna reunión, ningún lead y ningún informe de norma. Sus
páginas (`/admin/meetings/[id]`, `/admin/pipeline/leads/[id]`,
`/admin/compliance/norma-reports/[norma_key]`) no se podían recorrer: no había
ni un identificador con el que resolverlas.

El arnés las siembra por la vía de servicio de la propia aplicación para poder
verificarlas, y queda dicho aquí porque **es un hallazgo, no fontanería**: el
demo es el escaparate, y esas tres páginas no tienen nada que enseñar en él.

### 5 · Dos defectos del propio demo, encontrados por accidente

Al construir el catálogo de identificadores aparecieron dos cosas que ningún
comando en verde detectaba:

- **`/api/v1/_dev/seed-commercial-lead` rebautizaba al cliente estrella del
  demo.** El cliente del demo y el del arnés E2E son *la misma fila* (los dos
  con CIF `B00000000`), porque `demo_bootstrap.py` renombra el de test a
  «NovaEdge S.L.» para que las capturas de `USAGE.md` cuadren con la pantalla.
  Una sola llamada a ese endpoint dejaba mintiendo a `USAGE.md`, a `make smoke`
  y a `make recorrido`, sin un solo error por ninguna parte.

- **`make demo` dos veces seguidas duplicaba el proyecto entero.**
  `seed_full_implantation` buscaba el proyecto sólo por su nombre de test, y
  `demo_bootstrap` lo renombra al terminar; la segunda llamada no lo encontraba
  y creaba uno nuevo, sembrándolo completo. Dos «Sede electrónica de NovaEdge»
  con 209 evidencias cada una — pese a que la función se documenta a sí misma
  como idempotente.

Los dos están arreglados y verificados sobre un demo reconstruido de cero.

### 6 · Las veces que el arnés se equivocó, y por qué se cuentan

Un medidor también puede ser vacuo, y éste lo fue varias veces antes de dar una
cifra fiable. Se deja escrito porque las cifras de abajo sólo valen si se sabe
cómo se corrigieron:

1. **Contaba como «vacías» las pantallas de formulario.** Una pantalla de
   entrada es un formulario que funciona y poco texto. Se arregló contando los
   campos como señal de contenido — no metiéndolas en la lista blanca, que
   habría sido tapar un error de medida con una excusa escrita.

2. **Marcaba seis huecos de autorización que no existían.** El criterio exigía
   rebote a la entrada, 401, 403 o `/forbidden`; pero `frontend/middleware.ts`
   no devuelve 403: **manda a cada persona a su propio portal**. Eso es una
   puerta cerrada, y además mejor que un 403 a secas. El fallo era del criterio.

3. **Clasificaba sobre el `body` entero**, marco incluido. Bastaba con que un
   widget lateral dijera «Sin datos» para condenar una página con tres tarjetas
   de normativa y sus puntuaciones. La primera pasada dio 33 vacías y muchas no
   lo eran. Ahora se mide dentro de `<main>`.

4. **Medía el modal del tour de bienvenida en vez de la página de debajo.** En
   un demo recién levantado, la primera entrada abre un tour («TOUR ADMIN · PASO
   1 DE 6»). Ese modal tapa `<main>`, e `innerText` no devuelve texto oculto: el
   arnés declaraba vacías páginas que estaban llenas. Se vio comparando la
   captura de `/admin/dashboard` —cuatro indicadores, actividad reciente,
   acciones rápidas— con una medida que decía cero caracteres. Y lo peor: en la
   pasada anterior no salió **porque el demo llevaba usado un rato y el tour ya
   estaba descartado**. O sea, la versión limpia del demo medía peor que la
   sucia, que es exactamente la clase de trampa que este bloque existe para no
   repetir. Ahora el tour se cierra antes de medir; que el tour aparece se
   comprueba en `scripts/verificar_recorrido_usage.cjs`, que es su sitio.

   Un quinto ajuste del mismo tipo: se contaban filas de tabla y campos de
   formulario como señal de contenido, pero no **tarjetas**, y media aplicación
   moderna enseña sus datos en rejillas de tarjetas y no en tablas.

6. **Y uno nuevo, del 2026-09-11, que me lo hice yo con el arreglo del pie.**
   Cuando una página no tiene `<main>`, el arnés cae al `<body>`. Al añadir los
   ocho enlaces legales al pie global, esos ~200 caracteres empezaron a contar
   como contenido de la página, y `/forbidden` —una pantalla de «403 · Acceso
   restringido», vacía por naturaleza y en la lista blanca por eso— pasó de 8 a
   12 páginas vacías totales... contando una de menos, es decir, **dejó de
   medirse como vacía sin que su contenido hubiera cambiado en nada**.

   Es exactamente el error 3 volviendo por la puerta de atrás: medir el marco y
   llamarlo contenido. Y la tentación era no decir nada, porque el número salía
   mejor. Arreglado: cuando no hay `<main>`, el respaldo **resta** el texto del
   pie y de la navegación, y la medida anota `tieneMain` para que nadie lea esa
   cifra creyendo que mide lo mismo en las dos clases de página.

   La regla, por si sirve para la próxima: **un cambio de chrome no puede mover
   una cifra de vacuidad.** Si la mueve, el criterio está midiendo el marco.

La primera pasada se hizo además contra un demo que mis propias pruebas habían
ensuciado (el proyecto duplicado, el lead sembrado a mano). **Las cifras de este
documento son de una pasada contra un demo reconstruido con `make clean && make
demo`**, que es lo que se encuentra quien clona el repositorio.

### 7 · Las ocho páginas vacías que NO he justificado, y por qué

La lista blanca tiene cinco entradas y ninguna de relleno: son páginas vacías
**porque el estado del proyecto es ése** (un proyecto MEDIA sin pentest, una
certificación sin terminar) o por naturaleza (un «403 · Acceso restringido»).
Las otras ocho no entran, y se dividen en dos familias que se arreglan de forma
distinta:

**a) El demo no siembra el dato (cinco).** La aplicación funciona; el escaparate
está vacío. Y el escaparate importa: es lo que ve quien clona el repositorio.

| Ruta | Lo que dice | Qué falta |
|---|---|---|
| `/admin/system-health` | «Sin checks registrados todavía · ejecuta sync-registry» | La propia pantalla nombra el remedio, y `make demo` no lo ejecuta nunca |
| `/admin/compliance/monitor` | «ESTADO GLOBAL · Sin datos» sobre 17 comprobaciones | Mismo origen: el registro de comprobaciones no se siembra |
| `/admin/messages` | «No hay mensajes que mostrar» con los 4 clientes en el filtro | Ni un mensaje sembrado |
| `/client-portal/inbox` | «Todo al día · sin notificaciones» + «No hay mensajes» | El otro lado del mismo hueco |
| `/client-portal/billing` | «Aún no hay facturas emitidas para este proyecto» | El demo tiene contrato de 10.700 € y ninguna factura |

**b) La función no existe todavía (tres).** Aquí no falta dato: falta producto.
Son páginas que están en el menú y que, al pincharlas, dicen que vuelvas luego.

| Ruta | Lo que dice |
|---|---|
| `/admin/inbox` | «La vista agregada cross-project **se incorporará en MB-19+**. Por ahora, abre el proyecto específico desde el sidebar» |
| `/client-portal/whatsapp` | «WhatsApp · **próximamente** · Las notificaciones por WhatsApp todavía no están activas en tu entorno» |
| `/client-portal/dpc-anual` | Anuncia «revisa las 4 secciones de contexto» y no llega a enseñarlas |

Que las tres lo digan con buenos modales no las hace menos vacías: **«próximamente»
es un estado vacío con educación**, y una entrada de menú que lleva a un cartel
de «vuelve luego» es de las cosas que peor sientan a quien está evaluando un
producto. Se dejan fuera de la lista blanca a propósito.

---

## Los tres números

|  | Páginas | Qué significa |
|---|---|---|
| **Verificadas** | 154 | se abrieron con la persona dueña y traen contenido real (incluye las vacías justificadas una a una) |
| **No verificadas por falta de dato** | 3 | no había dato sembrado con el que resolver la ruta · **jamás cuentan como aprobadas** |
| **Fallidas** | 10 | no se abren, rebotan, revientan, o renderizan un estado vacío sin justificar |

Total del inventario: **167** páginas, de las que **83** llevan parámetro en la ruta.

## 1 · El inventario es el árbol, no una lista

Las rutas no están escritas a mano en ningún sitio: se **derivan** de `frontend/app` recorriendo cada `page.tsx` y quitando los grupos de ruta `(nombre)`, que organizan ficheros pero no aparecen en la URL. Escribir la lista a mano es exactamente como se llega a un informe que recorre 40 URL inventadas y declara «todo verde»: lo que no está en la lista no falla nunca. Con la lista derivada, una página nueva entra sola en el recorrido y una borrada desaparece sola.

| Grupo de ruta | Páginas |
|---|---|
| admin | 95 |
| client-portal | 41 |
| portal | 15 |
| legal | 8 |
| sin-grupo | 4 |
| public | 4 |

### Los identificadores de las 83 rutas dinámicas

Una ruta con `[id]` no se puede recorrer sin un identificador que **exista** en la base. Inventarse un UUID no vale: la pantalla de «no encontrado» devuelve HTTP 200 y la ruta entraría en verde sin haberse comprobado. Por eso hay un catálogo (`scripts/recorrido_identificadores.py`) que lee la base y, para los portales por token, **acuña enlaces de verdad** con el mismo servicio que usa la aplicación: el token y su código de un solo uso son los que recibiría una persona real.

**Tres familias de rutas no tenían ni un dato con el que recorrerlas.** El arnés las siembra por la vía de servicio de la propia aplicación, y queda dicho aquí porque es un hallazgo sobre el sembrado del demo, no un detalle de fontanería: `make demo` deja estas páginas sin nada que enseñar.

| Identificador | Cómo se obtiene y por qué hizo falta |
|---|---|
| `meeting_id` | MeetingService.create_meeting · el sembrado del demo no crea ninguna reunion |

Y estas no se pudieron resolver ni sembrando — sus páginas van a **NO VERIFICADA**:

| Identificador | Motivo |
|---|---|
| `token:diagnostico` | el enlace se puede acunyar, pero la tabla `diagnosis_runs` esta vacia: el demo no crea ninguna sesion de diagnostico previo |
| `token:pentester-portal` | el enlace se puede acunyar, pero la tabla `external_pentester_handoffs` esta vacia: el demo no crea ningun encargo a pentester externo |
| `token:verify-auth` | el enlace se puede acunyar, pero la tabla `verification_runs` esta vacia: el demo no crea ninguna verificacion tecnica que autorizar |

## 2 · Resultado página a página

`ok` = contenido real · `ok·inc` = se ve, pero algo falló por debajo · `vacía·ok` = vacía y justificada abajo · `VACÍA` = dice «no hay datos» y **no aprueba** · `FALLO` = no se puede usar · `NO VERIF` = sin dato para resolver la ruta.

### `admin` · 89/95

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/admin/alerts` | operador | ok |  |
| `/admin/clients` | operador | ok |  |
| `/admin/clients/[id]` | operador | ok |  |
| `/admin/clients/[id]/branding` | operador | ok |  |
| `/admin/clients/[id]/meetings` | operador | ok |  |
| `/admin/clients/new` | operador | ok |  |
| `/admin/compliance` | operador | ok |  |
| `/admin/compliance/monitor` | operador | VACÍA | la pantalla dice: «Sync registry ESTADO GLOBAL Sin datos Sin datos OK 0 OK ATENCIÓN 0 Atención CRÍTICO 0 Crítico SIN DATOS 0 S» |
| `/admin/compliance/norma-reports` | operador | ok |  |
| `/admin/compliance/norma-reports/[norma_key]` | operador | ok |  |
| `/admin/compliance/projects` | operador | ok |  |
| `/admin/copilot` | operador | ok |  |
| `/admin/cross-project-compliance` | operador | ok |  |
| `/admin/dashboard` | operador | ok |  |
| `/admin/finance` | operador | ok |  |
| `/admin/inbox` | operador | VACÍA | la pantalla dice: «vista agregada cross-project se incorporará en MB-19+. Por ahora, abre el proyecto específico desde el sidebar pa» |
| `/admin/llm-observability` | operador | vacía·ok | Todos los contadores a cero (llamadas 0 · coste 0,00 $ · latencia 0 ms) porque el demo se levanta SIN clave de Anthropic — `make demo` deja `ANTHROPIC |
| `/admin/llm-observability/golden-eval` | operador | ok |  |
| `/admin/magerit-analyses/[id]/import` | operador | ok |  |
| `/admin/magic-links` | operador | ok |  |
| `/admin/meetings` | operador | ok |  |
| `/admin/meetings/[id]` | operador | ok |  |
| `/admin/meetings/new` | operador | ok |  |
| `/admin/messages` | operador | VACÍA | la pantalla dice: «tica Iberia SA Solo no leídos No hay mensajes que mostrar.» |
| `/admin/notifications` | operador | ok |  |
| `/admin/operations` | operador | ok |  |
| `/admin/pipeline` | operador | ok |  |
| `/admin/pipeline/leads/[id]` | operador | ok |  |
| `/admin/projects` | operador | ok |  |
| `/admin/projects/[id]` | operador | ok |  |
| `/admin/projects/[id]/aepd` | operador | ok |  |
| `/admin/projects/[id]/archetype` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/archetype |
| `/admin/projects/[id]/audit` | operador | ok |  |
| `/admin/projects/[id]/audit-dry-run` | operador | ok |  |
| `/admin/projects/[id]/audit/annotations` | operador | ok |  |
| `/admin/projects/[id]/audit/clarifications` | operador | ok |  |
| `/admin/projects/[id]/audit/dda-evidence-gaps` | operador | ok |  |
| `/admin/projects/[id]/audit/draft-report` | operador | ok |  |
| `/admin/projects/[id]/auditor-handoff` | operador | ok |  |
| `/admin/projects/[id]/awareness` | operador | ok |  |
| `/admin/projects/[id]/backup-policy` | operador | ok |  |
| `/admin/projects/[id]/bia` | operador | ok |  |
| `/admin/projects/[id]/billing/aapp` | operador | ok |  |
| `/admin/projects/[id]/changes` | operador | ok |  |
| `/admin/projects/[id]/chat` | operador | ok |  |
| `/admin/projects/[id]/cliente-info` | operador | ok |  |
| `/admin/projects/[id]/cloud-connectors` | operador | ok |  |
| `/admin/projects/[id]/communication` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/communication/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/communication/plan |
| `/admin/projects/[id]/conformity` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/conformity/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/renewal |
| `/admin/projects/[id]/contratos` | operador | ok |  |
| `/admin/projects/[id]/dda` | operador | ok |  |
| `/admin/projects/[id]/diagnosis` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/diagnosis/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/latest |
| `/admin/projects/[id]/dimensiones` | operador | ok·inc | peticion 403 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/dimensions |
| `/admin/projects/[id]/discovery` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/assets |
| `/admin/projects/[id]/discrepancies` | operador | ok |  |
| `/admin/projects/[id]/documents` | operador | ok |  |
| `/admin/projects/[id]/dossier` | operador | ok |  |
| `/admin/projects/[id]/equipo` | operador | ok |  |
| `/admin/projects/[id]/equipo/areas` | operador | ok |  |
| `/admin/projects/[id]/evidence` | operador | ok |  |
| `/admin/projects/[id]/exit` | operador | ok |  |
| `/admin/projects/[id]/feature-flags` | operador | ok |  |
| `/admin/projects/[id]/financial` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/invoices |
| `/admin/projects/[id]/implementation` | operador | ok |  |
| `/admin/projects/[id]/magerit` | operador | ok |  |
| `/admin/projects/[id]/mcps` | operador | ok |  |
| `/admin/projects/[id]/obligations` | operador | ok |  |
| `/admin/projects/[id]/onboarding` | operador | ok |  |
| `/admin/projects/[id]/personalizacion` | operador | ok |  |
| `/admin/projects/[id]/plan` | operador | ok |  |
| `/admin/projects/[id]/planes-accion` | operador | ok |  |
| `/admin/projects/[id]/providers` | operador | ok |  |
| `/admin/projects/[id]/remediation` | operador | ok |  |
| `/admin/projects/[id]/renewal` | operador | ok |  |
| `/admin/projects/[id]/retainer` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/retainer/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/retainer |
| `/admin/projects/[id]/risks` | operador | ok |  |
| `/admin/projects/[id]/roadmap` | operador | ok |  |
| `/admin/projects/[id]/roles` | operador | ok |  |
| `/admin/projects/[id]/settings` | operador | ok |  |
| `/admin/projects/[id]/summary` | operador | ok |  |
| `/admin/projects/[id]/transparency` | operador | ok |  |
| `/admin/projects/[id]/users` | operador | ok |  |
| `/admin/projects/[id]/verification` | operador | ok |  |
| `/admin/projects/[id]/workflow` | operador | FALLO | pantalla de error: «Renovación Cierre No se pudo cargar la vista del proyecto Project not found» |
| `/admin/projects/[id]/workspace` | operador | ok·inc | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/workspace/chat?limit=100 |
| `/admin/projects/new` | operador | ok |  |
| `/admin/retainers` | operador | ok |  |
| `/admin/retainers/churn-risk` | operador | ok |  |
| `/admin/settings` | operador | ok |  |
| `/admin/siem` | operador | ok |  |
| `/admin/system-health` | operador | VACÍA | la pantalla dice: «nly (cliente NO ve). OVERALL Sin datos 0checks CRÍTICOS 0 LLM ANOMALÍAS 0 DB Conectado Compliance checks (m_» |
| `/admin/timesheet` | operador | ok |  |
| `/admin/whatsapp` | operador | ok |  |
| `/admin/workflow-command-center` | operador | ok |  |
| `/admin/workflow-command-center/projects/[id]` | operador | FALLO | pantalla de error: «No se pudo cargar la vista del proyecto Project not found» |

### `client-portal` · 37/41

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/client-portal` | cliente | ok |  |
| `/client-portal/account` | cliente | ok |  |
| `/client-portal/account/notifications` | cliente | ok |  |
| `/client-portal/actas` | cliente | ok |  |
| `/client-portal/billing` | cliente | VACÍA | la pantalla dice: «por transferencia bancaria. Aún no hay facturas emitidas para este proyecto. Portal asistido por FULKRO · c» |
| `/client-portal/categorizacion` | cliente | ok |  |
| `/client-portal/certificacion` | cliente | ok |  |
| `/client-portal/chat` | cliente | ok |  |
| `/client-portal/cloud-connections` | cliente | ok |  |
| `/client-portal/conformidad` | cliente | ok |  |
| `/client-portal/continuidad` | cliente | ok |  |
| `/client-portal/cumplimiento` | cliente | ok |  |
| `/client-portal/dashboard` | cliente | ok |  |
| `/client-portal/dda` | cliente | ok |  |
| `/client-portal/dpc-anual` | cliente | VACÍA | la pantalla dice: «mbién aparece en /firmas-hub. Todavía no hay DPC anual programada. Se generará automáticamente 30 días antes del a» |
| `/client-portal/evidencias` | cliente | ok |  |
| `/client-portal/files` | cliente | ok |  |
| `/client-portal/firma` | cliente | ok |  |
| `/client-portal/firmas-hub` | cliente | ok |  |
| `/client-portal/firmas-pendientes` | cliente | ok |  |
| `/client-portal/inbox` | cliente | VACÍA | la pantalla dice: «Todos No leídos Con archivos No hay mensajes que mostrar. Portal asistido por FULKRO · consultoría ENS · fulkro» |
| `/client-portal/incidents` | cliente | ok |  |
| `/client-portal/login` | anonimo | ok |  |
| `/client-portal/magerit` | cliente | ok |  |
| `/client-portal/onboarding` | cliente | ok |  |
| `/client-portal/onboarding/oauth-callback` | cliente | ok |  |
| `/client-portal/pentest-authorization` | cliente | vacía·ok | «No hay ninguna autorización pentest pendiente todavía». Coherente con la entrada anterior: proyecto MEDIA sin pentest en curso, luego no hay nada que |
| `/client-portal/plan` | cliente | ok |  |
| `/client-portal/policies` | cliente | ok |  |
| `/client-portal/registros` | cliente | ok |  |
| `/client-portal/registros/[tipo]` | cliente | ok |  |
| `/client-portal/remediaciones` | cliente | ok |  |
| `/client-portal/retainer` | cliente | vacía·ok | «Aún no hay oferta de mantenimiento · Cuando tu certificación ENS esté completa, aquí verás la propuesta». El proyecto del demo está en implantación,  |
| `/client-portal/retainer-checkin` | cliente | ok |  |
| `/client-portal/settings` | cliente | ok |  |
| `/client-portal/settings/mfa` | cliente | ok |  |
| `/client-portal/settings/notifications` | cliente | ok |  |
| `/client-portal/tasks` | cliente | ok |  |
| `/client-portal/transparency` | cliente | ok |  |
| `/client-portal/whatsapp` | cliente | VACÍA | la pantalla dice: «cos vía WhatsApp. WhatsApp · próximamente Las notificaciones por WhatsApp todavía no están activas en tu entor» |
| `/client-portal/workflow` | cliente | ok |  |

### `portal` · 13/15

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/auditor-portal/[token]` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/audit-log` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/audit/dda-evidence-gaps` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/dda` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/documents` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/draft-report` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/e041` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/evidence` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/magerit` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/pentest` | portal:auditor-portal | vacía·ok | «Sin pentest registrado · El pentest técnico es obligatorio en la categoría ALTA. Para BÁSICA y MEDIA puede aplicar opcionalmente». El proyecto del de |
| `/auditor-portal/[token]/plan` | portal:auditor-portal | ok |  |
| `/auditor-portal/[token]/summary` | portal:auditor-portal | ok |  |
| `/pentester-portal/[token]` | portal:pentester-portal | NO VERIF | no hay enlace acunyado para el portal «pentester-portal» |
| `/remediation/[token]` | portal:remediation | ok |  |
| `/verify-auth/[token]` | portal:verify-auth | NO VERIF | no hay enlace acunyado para el portal «verify-auth» |

### `legal` · 8/8

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/cookies` | anonimo | ok |  |
| `/derechos-rgpd` | anonimo | ok |  |
| `/dpa-template` | anonimo | ok |  |
| `/imprint` | anonimo | ok |  |
| `/privacy` | anonimo | ok |  |
| `/sub-processors` | anonimo | ok |  |
| `/terms` | anonimo | ok |  |
| `/trust` | anonimo | ok |  |

### `sin-grupo` · 4/4

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/` | anonimo | echa·ok | La aplicación no tiene portada pública: `frontend/app/page.tsx` es un `redirect(ROUTES.dashboard)`, así que sin sesión la cadena acaba en la pantalla  |
| `/docs/verify-signature` | anonimo | ok |  |
| `/forbidden` | anonimo | vacía·ok | Es la pantalla de «403 · Acceso restringido». Su contenido ES el aviso: una página de acceso denegado con datos sería una contradicción. Vacía por nat |
| `/login` | anonimo | ok |  |

### `public` · 3/4

| Ruta | Persona |  | Nota |
|---|---|---|---|
| `/diagnostico/[token]` | portal:diagnostico | NO VERIF | no hay enlace acunyado para el portal «diagnostico» |
| `/download/[token]` | portal:download | ok·inc | peticion 501 GET http://localhost:3000/api/v1/public/download/eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI3Y2IxMjA2My1kYTAyLTQwOGUtODI4My0wZGIzYTA |
| `/ml/consume` | anonimo | echa·ok | Es el punto de canje de un enlace mágico, no una página: espera `?token=…` y redirige al portal que corresponda al propósito del enlace. Visitada a pe |
| `/sign/[token]` | portal:sign | ok |  |

## 3 · El criterio anti vacuidad

Una página que renderiza «no hay datos» **no pasa**. Es la misma enfermedad de siempre: tiene forma de comprobación y no comprueba nada. Cada página clasificada como vacía tiene que estar en una lista blanca **con su motivo escrito una a una**, o cuenta como fallo.

### Lista blanca · 5 páginas legítimamente vacías

Fuente: `docs/recorrido/lista_blanca_vacias.json`.

| Ruta | Por qué está vacía a propósito |
|---|---|
| `/admin/llm-observability` | Todos los contadores a cero (llamadas 0 · coste 0,00 $ · latencia 0 ms) porque el demo se levanta SIN clave de Anthropic — `make demo` deja `ANTHROPIC_API_KEY=` vacía a propósito. No hay llamadas al modelo que observar, así que el cero es el número correcto. Es además el mismo dato que publica `/metrics` tras el BLOQUE G: si algún día no fuera cero sin haber configurado la clave, ESO sería el hallazgo. |
| `/auditor-portal/[token]/pentest` | «Sin pentest registrado · El pentest técnico es obligatorio en la categoría ALTA. Para BÁSICA y MEDIA puede aplicar opcionalmente». El proyecto del demo es MEDIA, así que la ausencia de pentest es el estado CORRECTO y la pantalla lo explica. Que salga con datos exigiría un proyecto ALTA. |
| `/client-portal/pentest-authorization` | «No hay ninguna autorización pentest pendiente todavía». Coherente con la entrada anterior: proyecto MEDIA sin pentest en curso, luego no hay nada que autorizar. La pantalla además dice qué pasará cuando lo haya. |
| `/client-portal/retainer` | «Aún no hay oferta de mantenimiento · Cuando tu certificación ENS esté completa, aquí verás la propuesta». El proyecto del demo está en implantación, no certificado: la oferta de retainer todavía NO debe existir. Enseñar una aquí sería el defecto. |
| `/forbidden` | Es la pantalla de «403 · Acceso restringido». Su contenido ES el aviso: una página de acceso denegado con datos sería una contradicción. Vacía por naturaleza, no por falta de sembrado. |

**Cómo se decide, y dónde está el juicio.** Se mide dentro de `<main>` —no del `body`— porque la barra lateral y la cabecera son marco, no contenido: en la primera pasada, clasificar sobre el `body` entero contó 33 páginas vacías donde no las había (basta un widget lateral que diga «Sin datos» para condenar una página con tres tarjetas de normativa). Una página se declara vacía si `<main>` no tiene filas de tabla, ni celdas, ni campos de formulario y baja de 900 caracteres; o si anuncia que está vacía y además `<main>` no llega a 1.200 caracteres. **Ese 1.200 es un juicio, no una medida**, y por eso la tabla de abajo publica las señales de cada página: para que se pueda discutir el número en vez de tener que creérselo.

### 8 páginas vacías SIN justificar

Cada una de éstas es un defecto: o falta sembrado, o la pantalla no sabe pedir sus datos.

| Ruta | Persona | Filas | Car. en `<main>` | Lo que se ve |
|---|---|---|---|---|
| `/admin/compliance/monitor` | operador | 0 | 632 | la pantalla dice: «Sync registry ESTADO GLOBAL Sin datos Sin datos OK 0 OK ATENCIÓN 0 Atención CRÍTICO 0 Crítico SIN DATOS 0 S» |
| `/admin/inbox` | operador | 0 | 348 | la pantalla dice: «vista agregada cross-project se incorporará en MB-19+. Por ahora, abre el proyecto específico desde el sidebar pa» |
| `/admin/messages` | operador | 0 | 216 | la pantalla dice: «tica Iberia SA Solo no leídos No hay mensajes que mostrar.» |
| `/admin/system-health` | operador | 0 | 345 | la pantalla dice: «nly (cliente NO ve). OVERALL Sin datos 0checks CRÍTICOS 0 LLM ANOMALÍAS 0 DB Conectado Compliance checks (m_» |
| `/client-portal/billing` | cliente | 0 | 215 | la pantalla dice: «por transferencia bancaria. Aún no hay facturas emitidas para este proyecto. Portal asistido por FULKRO · c» |
| `/client-portal/dpc-anual` | cliente | 0 | 843 | la pantalla dice: «mbién aparece en /firmas-hub. Todavía no hay DPC anual programada. Se generará automáticamente 30 días antes del a» |
| `/client-portal/inbox` | cliente | 0 | 252 | la pantalla dice: «Todos No leídos Con archivos No hay mensajes que mostrar. Portal asistido por FULKRO · consultoría ENS · fulkro» |
| `/client-portal/whatsapp` | cliente | 0 | 351 | la pantalla dice: «cos vía WhatsApp. WhatsApp · próximamente Las notificaciones por WhatsApp todavía no están activas en tu entor» |

### 2 páginas que te echan a la entrada, y deben echarte

Declaradas en `docs/recorrido/rebotes_esperados.json`. Es el **único** veredicto que admite declaración, y a propósito: hay páginas que deben echarte, pero ninguna que deba reventar. Un error de página o un HTTP 4xx no se pueden declarar esperados por esta vía.

| Ruta | Por qué echa, y por qué está bien |
|---|---|
| `/` | La aplicación no tiene portada pública: `frontend/app/page.tsx` es un `redirect(ROUTES.dashboard)`, así que sin sesión la cadena acaba en la pantalla de entrada. Echar a quien no ha entrado es el comportamiento correcto; lo que sería un fallo es que dejara pasar. |
| `/ml/consume` | Es el punto de canje de un enlace mágico, no una página: espera `?token=…` y redirige al portal que corresponda al propósito del enlace. Visitada a pelo, sin token, no tiene nada que canjear y manda a la entrada. Un enlace real sí la atraviesa — es el camino por el que el arnés entra a los siete portales por token de este mismo informe. |

### Texto fabricado en el DOM visible

Se busca en cada página: `[MOCK]`, `undefined`, `NaN`, `null`, `lorem`, `TODO`, `FIXME`. `[MOCK]` está el primero por un motivo concreto: así apareció «[MOCK] Agent 12» bajo el rótulo «Sugerencia IA» en la portada del cliente. La comprobación se queda aquí para siempre.

**Cero apariciones.** Ninguna de las 167 páginas enseña texto fabricado.

## 4 · Tabla de expectativas · un 403 esperado es un resultado correcto

Lo de arriba comprueba que la puerta de cada persona **se abre** para ella. Esto comprueba lo contrario: que está **cerrada** para las demás. Que el cliente reboto a su pantalla de entrada al pedir una página de administrador no es un fallo del recorrido; es el resultado que se esperaba. Lo que sería un fallo es que se abriera.

| Persona | Ruta (dueño: otra persona) | Esperado | Observado |  |
|---|---|---|---|---|
| cliente | `/admin/projects` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/dashboard | correcto |
| anonimo | `/admin/projects` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /login | correcto |
| cliente | `/admin/clients` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/dashboard | correcto |
| anonimo | `/admin/clients` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /login | correcto |
| cliente | `/admin/settings` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/dashboard | correcto |
| anonimo | `/admin/settings` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /login | correcto |
| operador | `/client-portal/dashboard` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /admin/dashboard | correcto |
| anonimo | `/client-portal/dashboard` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/login | correcto |
| operador | `/client-portal/evidencias` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /admin/dashboard | correcto |
| anonimo | `/client-portal/evidencias` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/login | correcto |
| operador | `/client-portal/plan` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /admin/dashboard | correcto |
| anonimo | `/client-portal/plan` | no llega: o le echan a la entrada, o le mandan a su propio portal, o 401/403 | le mandan a /client-portal/login | correcto |

Sin huecos: todas las puertas cerradas se comportan como debían.

## 5 · Alcanzabilidad · «¿lo puede usar alguien de fuera?», medido

Recorriendo en anchura los enlaces desde la portada de cada persona se abrieron **114** páginas.

|  | Número |  |
|---|---|---|
| Se alcanzan pinchando | 90 | de 167 páginas del inventario |
| **Huérfanas** | 59 | no se alcanzan pinchando · el reparto de abajo dice de quién es el defecto en cada caso, porque no es el mismo |
| Sólo por enlace de correo | 18 | portales por token · no se llega pinchando **por diseño**, no se cuentan como huérfanas |
| Enlaces rotos | 0 | apuntan a un 404 |

Las huérfanas son el defecto que apareció a mano con el alta de cliente —la página estaba entera y no había **un solo enlace** que llevara a ella—, ahora contado. Y al revés: los enlaces rotos son los que sí están y no llevan a ninguna parte.

### Las 59 huérfanas, repartidas

«Huérfana» a secas mete en el mismo saco cosas muy distintas, y esa mezcla hace que la cifra no sirva para decidir nada. El reparto es mecánico y se puede rehacer a mano: se busca la ruta literal en `frontend/{app,components,lib,hooks}`, excluyendo el `page.tsx` y el `layout.tsx` de la propia página (que se citan a sí mismos en la cabecera, y eso no es un enlace entrante).

Qué queda **fuera** de la búsqueda, y por qué importa: los `tests/`, porque un spec que hace `page.goto('/admin/x')` **no es un enlace** —nadie puede pincharlo—; y `tsconfig.tsbuildinfo`, que es un artefacto de compilación con **todas** las rutas del proyecto dentro. La primera versión de este reparto los leía y daba «0 huérfanas del producto» de 59: la cifra perfecta, y falsa.

|  | Número | Qué significa |
|---|---|---|
| Declaradas · no son huérfanas | 3 | destino de una reescritura o redirección · no se llega pinchando **y no debe llegarse** |
| **Del producto** | 15 | **ninguna referencia** a la ruta en todo el código · no se llega salvo tecleando la URL |
| Del sembrado | 41 | el enlace **existe**, pero vive en una fila o tarjeta que el demo no crea · el defecto es del sembrado, no de la aplicación |
| Del arnés | 0 | enlazada sólo desde la paleta de comandos, un menú o un desplegable · el rastreador no sabe accionarlos · **no es defecto de nadie**, es un límite de la medida |

El número que duele es el del producto: **15**. Otras 41 tienen su enlace escrito en alguna parte, y 3 no son huérfanas en absoluto: están declaradas en `docs/recorrido/rebotes_esperados.json` como destinos de reescritura a los que **no debe** llegarse pinchando.

#### 15 sin ninguna referencia en el código

- `/admin/clients/[id]/branding`
- `/admin/clients/[id]/meetings`
- `/admin/inbox`
- `/admin/llm-observability`
- `/admin/magerit-analyses/[id]/import`
- `/admin/projects/[id]/audit/annotations`
- `/admin/projects/[id]/audit/clarifications`
- `/admin/projects/[id]/audit/dda-evidence-gaps`
- `/admin/projects/[id]/audit/draft-report`
- `/admin/projects/[id]/billing/aapp`
- `/admin/projects/[id]/equipo/areas`
- `/admin/projects/[id]/feature-flags`
- `/admin/timesheet`
- `/client-portal/firmas-pendientes`
- `/client-portal/registros/[tipo]`

#### 41 con enlace, pero sin dato con el que pincharlo

| Ruta | Dónde está su enlace |
|---|---|
| `/admin/clients/[id]` | `frontend/app/(admin)/admin/messages/_components/AdminInboxList.tsx`, `frontend/app/(admin)/admin/projects/[id]/cliente-info/page.tsx`, `frontend/app/(admin)/admin/clients/[id]/branding/page.tsx` |
| `/admin/clients/new` | `frontend/app/(admin)/admin/projects/page.tsx` |
| `/admin/compliance/norma-reports/[norma_key]` | `frontend/app/(admin)/admin/compliance/norma-reports/page.tsx` |
| `/admin/cross-project-compliance` | `frontend/app/(admin)/admin/compliance/projects/page.tsx`, `frontend/lib/api/admin-cross-project-compliance.ts` |
| `/admin/llm-observability/golden-eval` | `frontend/app/(admin)/admin/llm-observability/page.tsx` |
| `/admin/magic-links` | `frontend/app/(admin)/admin/projects/[id]/auditor-handoff/page.tsx`, `frontend/components/project/ProjectTabs.tsx` |
| `/admin/pipeline` | `frontend/components/admin/LeadDetailView.tsx`, `frontend/components/admin/copilot/OnboardingTourAdmin.tsx`, `frontend/lib/constants.ts` |
| `/admin/pipeline/leads/[id]` | `frontend/components/admin/LeadDetailView.tsx` |
| `/admin/projects/[id]/aepd` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/audit-dry-run` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/awareness` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/backup-policy` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/bia` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/cloud-connectors` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/discovery` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/exit` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/mcps` | `frontend/components/project/ProjectTabs.tsx`, `frontend/components/layout/Sidebar.tsx`, `frontend/lib/constants.ts` |
| `/admin/projects/[id]/onboarding` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/planes-accion` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/providers` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/remediation` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/renewal` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/retainer` | `frontend/app/(admin)/admin/retainers/page.tsx`, `frontend/components/project/ProjectTabs.tsx`, `frontend/components/layout/Sidebar.tsx` |
| `/admin/projects/[id]/transparency` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/projects/[id]/workspace` | `frontend/components/project/ProjectTabs.tsx` |
| `/admin/retainers` | `frontend/app/(admin)/admin/dashboard/page.tsx`, `frontend/app/(admin)/admin/retainers/churn-risk/page.tsx`, `frontend/components/project/ProjectTabs.tsx` |
| `/admin/retainers/churn-risk` | `frontend/app/(admin)/admin/dashboard/page.tsx`, `frontend/components/dashboard/ChurnRiskWidget.tsx`, `frontend/lib/constants.ts` |
| `/admin/whatsapp` | `frontend/lib/api/admin-whatsapp.ts`, `frontend/hooks/useInboundWhatsAppSSE.ts` |
| `/admin/workflow-command-center` | `frontend/app/(admin)/admin/workflow-command-center/projects/[id]/page.tsx`, `frontend/components/workflow-command-center/ForecastTimeline30d.tsx`, `frontend/components/workflow-command-center/ProjectCardUrgent.tsx` |
| `/admin/workflow-command-center/projects/[id]` | `frontend/components/workflow-command-center/ForecastTimeline30d.tsx`, `frontend/components/workflow-command-center/ProjectCardUrgent.tsx`, `frontend/components/workflow-command-center/ProjectRowCompact.tsx` |
| `/client-portal` | `frontend/app/(client-portal)/client-portal/billing/page.tsx`, `frontend/app/(client-portal)/client-portal/cloud-connections/page.tsx`, `frontend/app/(client-portal)/client-portal/account/page.tsx` |
| `/client-portal/account/notifications` | `frontend/app/(client-portal)/client-portal/account/page.tsx` |
| `/client-portal/categorizacion` | `frontend/lib/api/client-categorizacion.ts` |
| `/client-portal/evidencias` | `frontend/components/client-portal/EvidenciasUploadPage.tsx` |
| `/client-portal/firma` | `frontend/app/(client-portal)/client-portal/retainer-checkin/page.tsx`, `frontend/app/(client-portal)/client-portal/firmas-hub/page.tsx`, `frontend/app/(client-portal)/client-portal/firmas-pendientes/page.tsx` |
| `/client-portal/login` | `frontend/app/(client-portal)/client-portal/page.tsx`, `frontend/components/auth/AuthGuard.tsx`, `frontend/components/layout/ClientHeader.tsx` |
| `/client-portal/onboarding/oauth-callback` | `frontend/components/client-portal/ConnectorsClientView.tsx`, `frontend/components/client-portal/CloudConnectFirstStep.tsx` |
| `/client-portal/registros` | `frontend/app/(client-portal)/client-portal/registros/[tipo]/page.tsx` |
| `/client-portal/retainer` | `frontend/app/(client-portal)/client-portal/retainer-checkin/page.tsx`, `frontend/components/client-portal/retainer-checkin/CheckinDetail.tsx`, `frontend/lib/api/retainer-offer.ts` |
| `/client-portal/retainer-checkin` | `frontend/app/(client-portal)/client-portal/retainer/page.tsx`, `frontend/components/client-portal/retainer-checkin/CheckinDetail.tsx` |
| `/docs/verify-signature` | `frontend/components/auth/PublicKeyVerifier.tsx` |

## 6 · Fallos e incidencias, uno a uno

El criterio de cierre exige **cero fallos sin explicar**. No cero fallos: cero fallos *sin explicar*. Una incidencia que se deja sin explicación cuenta como fallo.

### 2 páginas fallidas

| Ruta | Persona | Por qué |
|---|---|---|
| `/admin/projects/[id]/workflow` | operador | pantalla de error: «Renovación Cierre No se pudo cargar la vista del proyecto Project not found» |
| `/admin/workflow-command-center/projects/[id]` | operador | pantalla de error: «No se pudo cargar la vista del proyecto Project not found» |

### 10 páginas que se ven pero tienen algo roto por debajo

| Ruta | Persona | Incidencia |
|---|---|---|
| `/admin/projects/[id]/archetype` | operador | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/archetype; consola: Failed to load resource: the server responded with a status of 404 (Not Found) |
| `/admin/projects/[id]/communication` | operador | peticion 404 GET http://localhost:3000/api/v1/communication/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/communication/plan; consola: Failed to load resource: the server responded with a status of 40 |
| `/admin/projects/[id]/conformity` | operador | peticion 404 GET http://localhost:3000/api/v1/conformity/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/renewal; peticion 404 GET http://localhost:3000/api/v1/conformity/projects/0d549370-326d-4cf3-abc |
| `/admin/projects/[id]/diagnosis` | operador | peticion 404 GET http://localhost:3000/api/v1/diagnosis/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/latest; consola: Failed to load resource: the server responded with a status of 404 (Not Found) |
| `/admin/projects/[id]/dimensiones` | operador | peticion 403 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/dimensions; consola: Failed to load resource: the server responded with a status of 403 (Forbidden) |
| `/admin/projects/[id]/discovery` | operador | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/assets; peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/identiti |
| `/admin/projects/[id]/financial` | operador | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/invoices; peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/invoic |
| `/admin/projects/[id]/retainer` | operador | peticion 404 GET http://localhost:3000/api/v1/retainer/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/retainer; consola: Failed to load resource: the server responded with a status of 404 (Not Found) |
| `/admin/projects/[id]/workspace` | operador | peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a8e0372907/workspace/chat?limit=100; peticion 404 GET http://localhost:3000/api/v1/projects/0d549370-326d-4cf3-abcb-c1a |
| `/download/[token]` | portal:download | peticion 501 GET http://localhost:3000/api/v1/public/download/eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI3Y2IxMjA2My1kYTAyLTQwOGUtODI4My0wZGIzYTAzNWJlNjIiLCJzdWIiOiIwZDU0OTM3MC0zMjZkLTRjZjMtYWJjY |

---

**Capturas de pantalla**: `var/recorrido/capturas/` (una por página). **Medida en bruto**: `var/recorrido/recorrido.json`. **El arnés**: `scripts/recorrer_todo.cjs`.
