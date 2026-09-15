# Bloque Q · informe de cierre

**Alcance:** los 30 defectos de [`docs/INVENTARIO_Q.md`](INVENTARIO_Q.md).
**Commits:** `3447b8e` (Q1) · `d64adca` (Q2) · `9c02ca9` (Q2+Q3+Q4) · `ec6ec3f` ·
`07efe5f` (Q5) · `e758ad4` (Q0).
**Estado final:** 20 ARREGLADO · 9 CERRADO CON MOTIVO · 1 dividido (§15: E-001
arreglado, E-702/703 cerrado con motivo). Ningún estado intermedio.

---

## 1 · La tabla que importa

Por cada defecto: cuándo entró, qué debería haberlo cazado y por qué no lo hizo,
y qué guardia lo impide ahora. Ordenada por lo que enseña, no por número.

| # | defecto | cuándo entró | qué debería haberlo cazado, y por qué no lo hizo | qué lo impide ahora |
|---|---|---|---|---|
| §1 | Las 12 de 13 justificaciones falsas de la DdA | snapshot (2026-06-09) | **Nada. No existía.** Había tests de que la DdA *se generaba*, ninguno de que lo que dice *sea verdad*. El eje de exclusión y el texto que lo explica salían de sitios distintos y nadie comparaba los dos | `m03_dda/test_justificacion_no_aplica_dice_la_verdad.py` · el motivo se deriva de la misma tabla que decide la exclusión, así que no pueden discrepar |
| §2 | El acta E-012 se contradice en su JSON | snapshot · reincidente en `de6e617` (2026-06-12) | **Existía y era ciego.** El generador de PDF/DOCX estaba corregido desde O2; el JSON tenía su propio camino de lectura y ningún test comparaba las dos mitades del mismo documento | `m01_categorization/test_acta_e012_json_no_se_contradice.py` · compara tabla contra agregado |
| §3 | «Tu próxima actualización es hoy» en la ficha del cliente | `07efe5f` — **nació en este bloque** | **Nada, y es lo grave**: el arreglo de §15 se escribió y se dio por bueno sin ejecutarlo. Salió al *verificar* el arreglo, no al escribirlo | `_mes_siguiente()` con su docstring explicando el fallo; el valor ya no se calcula sobre `today()` |
| §4 | «25 variables y nueve» era falso (son 21 y 10) | `07efe5f` — **nació en este bloque** | **Nada.** Una cifra escrita de memoria dentro del arreglo que trata justamente de cifras escritas de memoria | `test_los_tres_entregables_que_no_salian.py` lee los marcadores **del `.docx`** y exige que el productor construya cada uno |
| §5 | El commit borra el contexto RLS · 500 con el dato guardado | snapshot · el mecanismo se tocó en `2d68f2f` (2026-06-14) | **Existía y era ciego, por construcción del arnés.** El fixture `db` ata la sesión a una transacción abierta a mano para revertirla al final: dentro de ese montaje `session.commit()` **no es un commit**, cierra una subtransacción y deja viva la de fuera, así que el GUC transaccional no se borra jamás. Escrito con el fixture, el test pasa igual antes y después del arreglo | `test_contexto_rls_sobrevive_al_commit.py`, con **sesión real y commit real**, fuera del arnés |
| §6 | El simulacro de auditoría no se guardaba | snapshot | **Existía y era ciego, por la misma razón que §5**: con el fixture, la ausencia de `commit()` es indistinguible de su presencia | `test_el_simulacro_se_guarda_de_verdad.py` · llama a la función del endpoint con sesión propia y comprueba la fila tras cerrarla |
| §7 | El «best-effort» del INES no revertía | `07efe5f` — **nació en este bloque** | **Nada.** Un `except` que promete en su docstring algo que el código no cumple; ningún test ejercía el camino de error | Guardia con una sesión de mentira que falla al leer y exige el `rollback()` |
| §8 | Tres pantallas sin quien arranque lo que exigen | snapshot | **Nada.** Los tests de backend probaban los endpoints —que funcionaban— y no existía ninguna comprobación de que alguien los llamara. El gate de cierre de BÁSICA exigía E-808 y su docstring afirmaba que el generador «ya existe»: era otro documento | `test_las_pantallas_arrancan_lo_que_exigen.py` · análisis estático de pantalla contra endpoint |
| §9 | Test contaminado por orden | snapshot | **Existía y era ciego.** El emisor de métricas captura el error y emite `fulkro_llm_lectura_fallida 1` en vez de caerse —decisión correcta—, así que el síntoma visible («faltan métricas») no se parecía a la causa (conexión heredada de un bucle de eventos muerto) | `NullPool` bajo `FULKRO_TESTING` + `test_la_bateria_no_hereda_conexiones.py`; y el emisor incluye ahora el **mensaje** del error, no sólo el tipo |
| §10 | 26 fallos por falta de clave de cifrado | snapshot | **Existía y mentía.** Se contaban como «dependencia de entorno», etiqueta que convierte un defecto en una propiedad del paisaje | `conftest.py` fija clave Fernet y `app_secret_key` de test, con `setdefault` |
| §11 | 11 fallos del corpus por PDF de terceros | snapshot | Igual que §10 | Marcador `requires_corpus_ccn` declarado, salto **con el motivo escrito**, y el README publica cuántos quedan fuera |
| §12 | Los 5 *errors* de pytest | snapshot | **Nadie los miraba.** Un *error* es colección o fixture rota —peor que un fallo— y no aparecían en ningún informe de la campaña hasta que este bloque los pidió uno a uno | Misma familia que §19: el módulo se abre su propia conexión y ahora queda marcado |
| §13 | Los 3 «sin agrupar» | snapshot | **Existía y era ciego** en dos: el `RESET ROLE` de salida fallaba encima y **tapaba la causa**; y `/no/such/path` daba por hecho que `mkdir` fallaría, cosa que como root no ocurre | Cada uno usa ahora el camino real de producción (`fn_refresh_drift_summary()`) o una imposibilidad estructural |
| §14 | `test_legal_audit_score_100` sólo pasa donde ya pasó | snapshot · **arreglado a medias en `9c02ca9`** | **Existía el arreglo y era parcial.** Q3 añadió el `mkdir` que faltaba —correcto para un clon limpio— y no tocó la causa: escribir dentro del árbol. El síntoma mutó de `FileNotFoundError` a `PermissionError` y siguió vivo | `FULKRO_LEGAL_AUDIT_OUT` y el test escribe en su `tmp_path`: deja de depender del árbol |
| §15 | E-001 sin productor de contexto | snapshot | **Nada.** La plantilla estaba en el catálogo y el gate la daba por disponible; nadie comprobaba que existiera quien rellenara sus variables | `test_los_tres_entregables_que_no_salian.py` |
| §16 | E-604 y E-005 fuera de la fábrica documental | snapshot | **Existía y estaba congelado en la posición equivocada.** El guardia de «un solo camino» **conocía los dos** y los llevaba en su lista de excepciones como línea base aceptada | El mismo guardia, con E-604 **fuera** de la lista; E-005 sigue dentro con su motivo escrito (no tiene plantilla) y su fila en `documents` resuelta |
| §17 | El informe INES no cabe en `documents` | snapshot | **Nada, y no podía haberlo.** No es un fallo de código sino del esquema: `documents` no sabía expresar un ámbito de organización. Un test sólo puede comprobar lo que el modelo permite representar | Migración `ines_cabe_documents_001` + CHECK `ck_documents_ambito` + guardia sobre `Document.__table__` |
| §19 | El marcador `requires_db` era ciego | `2fe3462` (2026-09-10) — **guardia de esta campaña** | **Existía y era ciego**, y sólo tenía cinco días. Deriva la marca de *pedir el fixture `db`*: cubre 2.717 tests y falla justo en los que se abren su propia conexión | El hook mira también si el **módulo** construye un engine · 3.369 → 3.371 |
| §20 | Un test que aseveraba el defecto | snapshot | **El guardia era el defecto.** Afirmaba con un `assert` que la ceguera tras el commit era el contrato | El brazo A dice ahora lo contrario y falla si la ceguera vuelve |
| §30 | Lo que queda de los 21 | `70342a1` (2026-06-14) | **Existía y arregló los casos, no la clase.** Cerró tres «no hacía commit» y dejó vivo el cuarto hermano | §5 no quita `refresh` uno a uno: va donde no se puede esquivar —el inquilino se recuerda y se reaplica en cada transacción—, así que la pareja número 31 nace arreglada |

### Los cerrados con motivo

| # | qué es | por qué se cierra sin arreglar |
|---|---|---|
| §11 | 11 PDF de guías CCN-STIC y AEPD | El repo **no puede** traerlos: obra de terceros con condiciones de reproducción propias. Marcador declarado + cifra publicada |
| §15b | E-702 / E-703 | Que **no** se generen sin una ejecución de verificación **es lo correcto**: un informe de verificación sin verificación detrás sería un documento inventado. Lo que sí era defecto —un 422 ilegible— está arreglado |
| §18 | 3.371 tests que el CI no ejecuta | Sembrar la base en CI es infraestructura, no corrección. Queda **medido y dicho**, que es lo que separa una limitación conocida de una mentira por omisión |
| §21 | 5 heads de Alembic | Converger toca el orden de aplicación en producción. Verificado que eran 5 **antes y después** del bloque: §17 consumió un head en vez de añadirlo |
| §22 | El `[MOCK]` de los agentes | Ya **no** es silencioso (`status="mock"`, coste 0, tokens NULL). Lo que queda —un solo consumidor comprueba la bandera— es una decisión de producto, no una corrección |
| §23 | `sign_facturae_xades` | Stub **declarado**: excepción tipada que nombra el certificado FNMT que falta. Falla en cerrado y lo dice |
| §24 | `npm audit` en `critical` | Bajar a HIGH es política de riesgo con efecto inmediato sobre mergear. Se declara la calibración real |
| §25 | Nueve cadenas de modelo sueltas | Centralizarlas es refactor transversal de la capa de IA. Ninguna produce una afirmación falsa en un documento |
| §27 | La evaluación de agentes sin tasa real | Ejecutarla exige `ANTHROPIC_API_KEY` y llamadas reales. Declarado en esos términos |
| §28 | Ningún cuestionario admite adjuntos | Carencia de **producto**, no incorrección normativa: ninguna pregunta afirma nada falso |

---

## 2 · Lo que la tabla dice, y que no estaba en la lista de arreglos

**Cuatro de las veinte filas de la tabla son defectos que nacieron dentro de
esta misma campaña de corrección.** §3, §4 y §7 nacieron en `07efe5f` —el commit que
arregla §15 y §17— y §19 es un guardia de `2fe3462` que tenía cinco días cuando
se descubrió que era ciego. Los tres primeros se encontraron **verificando el
arreglo, no escribiéndolo**: el arreglo se dio por bueno sin ejecutarlo. Es la
misma proporción que ya señalaba el cierre de la campaña anterior —nueve
autocorrecciones del arnés y no del sujeto— y apunta al mismo sitio.

**El arnés de test hacía inobservables dos de los tres defectos más caros.** §5 y
§6 no se podían ver desde el fixture `db`, y no por descuido: el fixture ata la
sesión a una transacción abierta a mano para revertirla al final, así que dentro
de él `session.commit()` **no es un commit**. Un test escrito con el arnés pasa
igual antes y después del arreglo. Se comprobó antes de escribir el definitivo.
La conclusión incómoda: **la capa de verificación decidía qué clase de defecto
era visible**, y la clase que ocultaba —todo lo que depende de que una
transacción termine de verdad— es precisamente donde vivían los 500 con el dato
ya guardado y los duplicados.

**Las etiquetas hacen de anestesia.** «Dependencia de entorno» (§10, §11, §12),
«línea base conocida» (§16) y «preexistente» son las tres formas que ha tomado el
mismo gesto: convertir un defecto en una propiedad del paisaje. §16 es el caso
puro — el guardia de «un solo camino» **conocía** los dos documentos que se
saltaban la fábrica y los llevaba en su lista de excepciones. El guardia no
estaba ciego: estaba congelando la posición equivocada.

**Arreglar el caso no arregla la clase.** §30 y §14 son la misma lección desde
dos sitios. El barrido de junio cerró tres «no hacía commit» y dejó vivo el
cuarto; Q3 añadió a §14 el `mkdir` que faltaba y dejó viva la causa —escribir
dentro del árbol—, así que el síntoma sólo mutó de `FileNotFoundError` a
`PermissionError`. Por eso §5 no quita `refresh` uno a uno: va al único sitio que
no se puede esquivar escribiendo otra consulta.

**No se puede fechar casi nada.** `git log -S` devuelve el commit raíz
—`72d98e5`, 2026-06-09, «snapshot inicial limpio»— para **15 de las 20** filas de
la tabla de arriba. El
historial se rehízo, así que la arqueología no alcanza más atrás: no es que los
defectos entraran ese día, es que ese día es el horizonte. Lo dice el propio
informe de O2 y conviene repetirlo aquí, porque una columna «cuándo entró» llena
de la misma fecha invita a leerla mal.

---

## 3 · Cierre · las cifras, y lo que no se pudo medir

### Lo medido, en esta máquina, contra `e758ad4`

```
$ pytest backend/tests --collect-only -q | tail -1
6709 tests collected in 2.94s                    ← 0 errores de colección

$ pytest backend/tests -q -m "not requires_db"
3315 passed, 23 skipped, 3371 deselected, 17 warnings in 46.11s
                                                 ← 0 fallos, 0 errores

$ PATH=…/.venv/bin:$PATH make lint
==> ruff local · All checks passed!
```

En el commit padre de Q5 esa misma orden daba `3312 passed, 3 failed`. Los tres
están atribuidos: dos eran §19 (tests con conexión propia que reventaban en vez
de saltar) y uno §14.

### La puerta de colección, en el CI

`pytest --collect-only -q backend/tests` **ya es un paso del CI** y es un gate
duro: `.github/workflows/ci.yml:341-348`, va **antes** de ejecutar nada y tumba
el job. Si la suite no colecciona, el resto estaría midiendo sobre una suite
incompleta —que es exactamente lo que pasó desde el bloque O1 sin que nadie lo
viera—.

### Lo que NO se pudo medir, y por qué

**La batería completa no se ha ejecutado.** De los 6.709 tests, **3.371 exigen
PostgreSQL** y en esta máquina no hay ninguno al alcance:

```bash
$ docker ps
docker: command not found          # WSL2 sin integración de Docker Desktop
$ pg_isready -h localhost -p 5432; pg_isready -h localhost -p 5433
no response                        # los dos puertos
$ make check-tools
ERROR: no hay 'docker compose' (plugin v2).
```

Así que **la cifra final de la batería completa de este bloque es la de los 3.338
que sí se pueden correr aquí: 3.315 pasan, 23 saltan, 0 fallan.** Los 3.371
restantes no están medidos, y decir otra cosa sería inventar el número. La última
medición de la batería entera es la del commit padre de Q3, con base de datos y
MinIO alcanzables: `44 failed, 6515 passed, 115 skipped, 0 errors` en 823 s — y
esos 44 están atribuidos uno a uno en §10-§14.

**`make clean && make demo && make smoke && make recorrer-todo` no se ha
ejecutado**, por lo mismo: los cuatro pasan por `docker compose`. El gate se
comporta bien —`check-tools` falla con el motivo escrito y no arranca a medias—
pero el resultado es que **esa comprobación queda sin hacer en este bloque**.

Las dos son limitaciones del entorno, no del árbol, y quedan como **N2** en
[Hallazgos nuevos](INVENTARIO_Q.md#hallazgos-nuevos). Lo que se puede afirmar con
lo medido: la suite colecciona entera, el subconjunto ejecutable pasa limpio, el
lint pasa, y ningún número de este informe procede de una ejecución que no se
haya hecho.
