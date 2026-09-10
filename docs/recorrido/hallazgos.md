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
