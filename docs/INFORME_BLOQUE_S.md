# Bloque S · la plataforma, ejecutada entera, y lo que estaba roto por debajo

El bloque R cerró con tres frentes abiertos por falta de entorno: los 3.371 tests
con base de datos que nunca se habían ejecutado, el salto a Next 15 sin probar en
ejecución y las pruebas contra el modelo real. Este bloque consiguió el entorno
(PostgreSQL `pgvector/pgvector:pg16` y MinIO en Docker, la clave de API) y ejecutó
todo: suite de backend, E2E, polish de accesibilidad de los tres portales, las
llamadas reales al modelo, la imagen Docker de producción y tres pasadas
adversariales (todos los enlaces de navegación, todos los GET de la API y todos
los `fetch` que escriben).

Lo que salió no eran sobre todo tests desfasados: eran **defectos de la
aplicación** que los saltos, las esperas mal puestas y la falta de ejecución
tapaban. Todos están arreglados y cubiertos por un test que hoy pasa: los tests
nuevos de este bloque se comprobaron además en rojo contra el código anterior, y
el resto quedan cubiertos por specs E2E que antes fallaban o se saltaban.

## Resultado

| | antes del bloque | al cerrarlo |
|---|---:|---:|
| Tests con base de datos (`requires_db`) | nunca ejecutados | **3.321 pasan · 0 fallan** |
| Tests sin base de datos | 3.400 pasan | **3.556 pasan · 0 fallan** |
| Total recogidos | 6.794 | **6.952** (75 saltados, por los motivos de abajo) |
| E2E Playwright | 299 pasan · 54 fallan · 96 saltados | **413 pasan · 0 fallan · 0 saltados** |
| Polish WCAG (admin + cliente + auditor) | 96 de 97 | **97 de 97** |
| `npm audit` (producción y desarrollo) | 14 avisos, 2 críticos | **0** |
| Build de producción | 8 avisos | **0 avisos · 168 rutas** |
| Imagen Docker del frontend | — | **se construye y sirve** |
| Tests contra el modelo real | nunca | **22 de 22** (uno por agente y motor) |

Gasto en la API de Anthropic para probar la IA: unos 2,5 $ como máximo.

## Defectos de la aplicación, por gravedad

### Seguridad

- **Cerrar sesión no cerraba la sesión, en ningún portal.** El admin mandaba el
  `POST` sin `X-CSRF-Token` (403) y el cliente apuntaba a `/client-auth/logout`,
  sin `/api/v1`, que Next no reenvía (404). En los dos casos la interfaz decía
  «Sesión cerrada», la sesión seguía viva en el servidor, la cookie httpOnly seguía
  en el navegador y volver a la página protegida entraba sin pedir nada. En un
  equipo compartido, el siguiente usaba la sesión del anterior. El test que lo
  habría visto (`fase_10` «logout · sesión cleared») estaba saltado.
  → `hooks/useLogout.ts` · `tests/e2e/logout-cierra-la-sesion.spec.ts`
- **Sesiones recién creadas rechazadas al azar** (1 de cada 50 entradas acababa
  en el login). PyJWT rechaza un `iat` en el futuro sin tolerancia, y basta con
  que el reloj retroceda una fracción de segundo entre emitir y verificar. En
  producción con más de un proceso pasa lo mismo. Se verifica con 10 s de
  tolerancia, también en los enlaces mágicos.
  → `auth/crypto.py` · `test_jwt_tolera_desfase_de_reloj.py`
- **Next 14.2.33 con 14 avisos**, dos de ellos de ejecución remota de código. Se
  sube a **15.5.26** (el codemod de `params` asíncronos, 80 ficheros) y la copia
  de `postcss` anidada en `next` se fuerza a 8.5.28 con `overrides`. Se comprobó
  en ejecución, no solo compilando: Next 14 y Next 15 dan **exactamente** el
  mismo resultado sobre la suite E2E completa (299 / 54 / 96 los dos), y las
  diferencias de a uno eran tests inestables, repetidos hasta demostrarlo.
- El webhook de WhatsApp (360dialog) pasa a ser ruta pública, porque llega sin
  sesión y el auth global lo rechazaba con 401 (ningún mensaje entrante llegaba
  nunca). La credencial es la firma HMAC o el token compartido, comparada en
  tiempo constante, y en producción sin secreto se rechaza todo.

### Cosas que no funcionaban para el usuario

- **El copiloto del portal de cliente no respondió nunca a nadie**: `fetch` sin
  cabecera CSRF → 403. Además pintaba el Markdown del modelo como texto (`##`,
  `**` literales). Probado con una llamada real: responde con el estado del
  proyecto, cita el RD 311/2022 y respeta el tono R29.
- **Los avisos en tiempo real al cliente no llegaban** en el demo y en todo
  despliegue detrás del proxy de Next: la respuesta SSE no declaraba
  `no-transform`, y el proxy la retenía para comprimirla.
- **El triaje de hallazgos de m08 fallaba en cada llamada**: Opus 4.8 rechaza
  `temperature` («deprecated for this model») y el catálogo decía que la
  admitía. Medido con una llamada real.
- **El borrador de informe de auditoría** (`draft-report.ts`) también iba sin
  CSRF.
- **Anotaciones y aclaraciones del auditor**: el `refresh` iba después del
  `commit`, cuando RLS ya oculta la fila. Respondía 500 con la fila ya guardada,
  y el auditor, al reintentar, la duplicaba.
- **Gestión de usuarios de cliente (cockpit)**: las rutas corrían sin contexto de
  cliente. El listado salía vacío, el alta daba 500 y el reseteo y la baja
  respondían «no encontrado».
- **El panel de workspace del admin** llamaba a una API que no existe
  (`/api/v1/projects/...` en vez de `/api/v1/workspace/projects/...`): el panel
  entero daba 404.
- **El checklist de cierre** no guardaba la siembra (sin `commit`): cada visita
  generaba ids nuevos y «marcar completado» respondía 404. Además, dos primeras
  visitas simultáneas chocaban con la restricción única (ahora `ON CONFLICT DO
  NOTHING`).
- El histórico de enlaces mágicos tumbaba la página (`<SelectItem value="">`), la
  pestaña LMS no recibía `por_estado`, el resultado de un escaneo MCP no
  aparecía hasta elegirlo en el histórico, el distintivo «Último usado» del
  selector no salía nunca, y el portal de auditor pedía el OTP en cada vista
  (gastando un uso del enlace cada vez).
- **Cinco 500** encontrados barriendo los 632 GET de la API con datos reales:
  la observabilidad LLM (`int(None)` en cuanto había una llamada fallida), el
  acta E-012 de un sistema que perdió sus valoraciones (ahora 409 que explica
  qué falta), el informe INES de una organización inexistente (ahora 404, JSON y
  DOCX) y, el más grave, **la descarga de documentos del portal de cliente**: la
  fila de auditoría iba con `created_at` nulo a una columna NOT NULL, así que
  toda descarga fallaba después de leer el fichero. Con esos arreglos, el
  barrido da 0 respuestas 5xx como admin y como cliente.

### Enlaces que llevaban a «no encontrado»

**40 enlaces que emite el backend** apuntaban a páginas que no existen: las
acciones siguientes del flujo de trabajo (`/admin/proposals/new`,
`/admin/dda/entries`, `/admin/onboarding/sessions/new`…), los enlaces de las
notificaciones (`/client-portal/tasks/{id}`…), 20 plantillas de tarea que
guardaban `{project_id}` literal en el enlace y un correo con un `href` relativo.
Cada uno lleva ahora a la pestaña del proyecto donde se hace la acción (R23). La
barra lateral enlazaba clientes por *slug* en vez de por id, y la miga de pan de
cada proyecto llevaba a la lista global de clientes, retirada con R23. El dashboard, la
paleta Cmd+K y el mapa de rutas del copiloto ofrecían secciones que solo
redirigen al selector: el pipeline comercial, dormido a propósito desde el
Batch 2 y que se deja así, y la consola global de retainers.

`test_enlaces_de_interfaz_existen.py` lo impide: contrasta cada enlace de interfaz
del backend con el árbol real de páginas, y no cuenta como destino una
redirección heredada a una portada.

### Contenido normativo y comercial

- **Tarifa**: las propuestas de m13 calculaban con fórmulas propias (recargos por
  empleado, CPDs, bonus de éxito…), y una MEDIA salía a 14.650 € en m13 y a
  16.300 € en la tarifa canónica. Por decisión del dueño, m13 delega en la
  calculadora canónica y no tiene fórmula propia.
  `test_pricing_media_coincide_con_la_calculadora_canonica` impide que se vuelvan
  a separar. Una plantilla de tarea citaba además la tarifa vieja (3.900 / 9.500 /
  25.000 €).
- **CCN-STIC 808 frente a 809**: la autoevaluación de BÁSICA es la verificación
  CCN-STIC 808, y la 809 regula la Declaración de Conformidad. Se corrigen el
  glosario, las tareas del cliente y, en los dos documentos firmables (E-180 y el
  distintivo de m27), la cita exacta: la autoevaluación la prevé el **artículo
  38.1** y el Anexo III del RD 311/2022, contrastado con el corpus.

### Accesibilidad

Botones dentro de botones (MAGERIT, que tenía en rojo el workflow de polish del
CI en cada push; firmas del cliente; facturación AAPP; y la `DataTable` genérica,
que convertía en `<button disabled>` las cabeceras no ordenables), una etiqueta
que se asociaba al botón de ayuda en vez de al campo, y un texto con contraste
4,11 en workspace.

## Lo que había detrás de los tests saltados

De 96 E2E saltados quedan **0**. Unos eran marcadores vacíos (`async () => {}`,
27 en un solo fichero). Otros probaban funciones retiradas, y se sustituyeron por
tests de que la redirección existe. Y muchos llevaban un motivo que ya no era
verdad: «router comercial dormido» con el router montado, «tabla eliminada»
cuando la migración que la eliminaba es un `pass`, el flujo de consumo de enlaces
mágicos que sigue vivo para el precliente… Reactivados, destaparon buena parte de
los defectos de arriba. Los tres specs que exigían variables de entorno se
preparan ahora solos por la API.

En la suite de backend quedan saltados, por motivos que se sostienen: 46 que
llaman al modelo real (opt-in; 22 se ejecutaron en este bloque), 11 que necesitan
PDFs de terceros que el repositorio no puede distribuir, 14 que necesitan el HTML
del BOE descargado (pasan los 14 con `FULKRO_CORPUS_DIR`), 2 condicionales y 2
marcadores de «activación futura» de M01 y M19.

## Guardas nuevas

- `test_fetch_que_escribe_lleva_csrf.py`: ningún `fetch` directo que escriba va
  sin `X-CSRF-Token`. Salta en los tres ficheros tal como estaban.
- `test_enlaces_de_interfaz_existen.py`: los enlaces de interfaz del backend
  llevan a páginas reales.
- `test_las_cifras_del_readme_reproducen.py`: ahora cubre también las cifras
  repetidas en otras secciones del README, que se habían quedado viejas (268 y 269
  migraciones cuando había 273, 46 motores cuando había 44).
- `pytest-completo.yml`: sembraba como `fulkro_app` (que desde el endurecimiento
  de roles no puede `SET ROLE fulkro`) y contaba filas de una tabla que no existe.
  Habría fallado en su primera ejecución. Corregido y reproducido en local.

## Lo que queda abierto

- **Las evaluaciones de agentes** (40 entradas) siguen sin ejecutarse contra el
  modelo. Se decidió no gastar en medir tasas: lo que se probó fue que cada agente
  funciona de punta a punta con el modelo real.
- **Los enlaces de notificaciones con `?task=`, `?evidence=`, `?audit=`…** llevan
  a la página correcta, pero esas páginas todavía no leen el parámetro para
  resaltar el elemento.
- **El DPA** menciona en prosa `/admin/compliance/breach`, que es una ruta de API,
  no una página. Es texto legal y no se ha tocado.
- **El pipeline comercial** sigue dormido, por decisión del dueño; su API
  funciona y sus tests pasan.
- **`pytest-completo.yml` no se ha visto correr en GitHub**: se reprodujo paso a
  paso en local con la misma imagen. Se lanza de noche o a mano.
