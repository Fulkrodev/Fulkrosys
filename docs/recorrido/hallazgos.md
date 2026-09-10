## Lo que ha encontrado, empezando por lo que peor se lee

Este apartado lo escribe una persona; todo lo que viene después de la línea son
tablas generadas por la medida. La separación es deliberada: el juicio sobre lo
que significan los números no lo puede firmar un script.

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

### 2 · Un código de ticket interno, en la pantalla de un cliente

El escáner de texto fabricado encontró **una** aparición en las 167 páginas, y
es de verdad. El portal de descarga le enseña a quien recibe el enlace:

> Descarga aún no disponible · descarga_dossier_final pendiente de integracion
> M09 dossier_generator (**TODO-FASE-9-MAGIC-LINK-DOSSIER-DOWNLOAD-001**).

Es la misma familia que el «[MOCK] Agent 12» del bloque D: un artefacto interno
que se escapa a la interfaz de alguien de fuera. La otra mitad de la noticia es
buena y también hace falta decirla: **cero apariciones de `[MOCK]`** en las 167
páginas, así que el arreglo de D1 aguanta.

### 3 · Siete de las ocho páginas legales no las enlaza nadie

Las páginas legales se enlazan entre sí, pero **desde fuera del grupo legal sólo
hay un enlace en todo el código**: el del banner de cookies, que apunta a
`/cookies`.

```
$ grep -rn 'href="/\(privacy\|terms\|trust\|imprint\|dpa-template\|sub-processors\|derechos-rgpd\)"' \
    frontend/components frontend/app frontend/lib | grep -v "app/(legal)/"
   (sin resultados)
```

A la política de privacidad, a los términos, al centro de confianza, al aviso
legal y al listado de subencargados **sólo se llega escribiendo la URL**. Para
un producto que vende cumplimiento, y cuya política de privacidad tiene que ser
accesible, es un defecto con más consecuencias que las de navegación.

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

### 6 · Tres veces que el arnés se equivocó, y por qué se cuentan

Un medidor también puede ser vacuo, y éste lo fue tres veces antes de dar una
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
