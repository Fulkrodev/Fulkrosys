# Bloque R · qué se resolvió, qué no, y con qué comando se comprueba

Una sección por punto. En cada una: el comando que midió el defecto con su
salida, el arreglo, el comando que prueba que pasa, y el diferencial de
artefacto donde toca. Los puntos que se quedan fuera dicen **qué falta y por
qué**, con esas palabras.

Todo lo medido aquí es sobre `origin/main` en `e74f581` (el padre) y sobre la
rama de este bloque (el hijo). El intérprete es el del checkout de
`/home/usuario/fulkro`, porque este clon no trae entorno de Python propio.

## Resumen

| # | Frente | Estado | Commit |
|---|---|---|---|
| R11 | README sin limitaciones declaradas | **Cerrado** | `53cd13a` |
| R5a | La justificación que se desmentía a sí misma | **Cerrado** | `eb8085c` |
| R3 | Ejecutar las evaluaciones | **NO se hace** · falta la clave | — |
| R1 | El catálogo de modelos | **Cerrado** | `b328cbe` |
| R8 | Una sola cabeza de Alembic | **Cerrado**, con el defecto ya resuelto de antes | `69e09b1` |
| R10 | Los dos detalles | **Cerrado** | `da799b3` |
| R2 | La puerta del modo degradado | **Parcial**, y se explica exactamente qué mitad | `863f234` |
| R9 | El umbral del audit | **Cerrado** | `5fb5fb5` |
| R7 | Los 3.371 | **Parcial**: hay dónde ejecutarlos, no el número | `519e3ae` |
| R5b | El salto a Next 15 | **NO se hace** · falta poder ejecutar Playwright | — |

**Tres mediciones del enunciado no reproducen.** Están en R7, R8 y R9, cada una
en su sección. La de R8 cambia el trabajo entero de ese punto.

---

## Las tres discrepancias, juntas

### 1 · Los tests `requires_db` son 3.371, no 3.294

```
$ pytest backend/tests/ --collect-only -q -m "requires_db"
3371/6709 tests collected (3338 deselected)
$ pytest backend/tests/ --collect-only -q -m "not requires_db"
3338/6709 tests collected (3371 deselected)
```

Medido sobre el padre `e74f581`, donde los 6.709 totales sí coinciden. La
diferencia tiene explicación y no es un error: `ci.yml:155-159` fecha esas
cifras el **2026-09-10**, sobre **6.470** tests recogidos. Desde entonces el
repositorio ganó 239 tests. La cifra no era falsa, era vieja.

Al cerrar el bloque la suite tiene **85 tests más**, todos de este bloque y
todos sin base de datos, así que los `requires_db` siguen siendo 3.371 y lo
que crece es la otra mitad:

```
$ pytest backend/tests/ --collect-only -q -m "requires_db"      # en bb221a9
3371/6794 tests collected (3423 deselected)
```

En el README va la medida del final, con su comando.

### 2 · No hay cuatro cabezas de Alembic. Hay una

```
$ cd backend && alembic heads
ines_cabe_documents_001 (head)
```

Las tres que se nombraban ya estaban convergidas antes de este bloque:

```
$ sed -n '41,48p' backend/migrations/versions/sub_atom_5b_magerit_child_rls_001.py
revision: str = "sub_atom_5b_magerit_child_rls_001"
# Multi-parent merge · consolida 3 heads existing en single revision
down_revision: Union[str, Sequence[str], None] = (
    "cluster6_client_mfa_001",
    "radar_v9_perfect_f_001",
    "remediation_enhancement_b35_e_001",
)
```

Y todo el repositorio usa ya `alembic upgrade head` en singular — CI,
`provision-entrypoint.sh` (cuyo comentario dice literalmente «árbol con 1
head»), `README_SETUP.md`. `INSTALL.md` no menciona `alembic` en absoluto, así
que tampoco había nada que corregir ahí.

Consecuencia: **el `alembic merge` no se ejecuta**, porque mergear una sola
cabeza no es una operación. Lo que sí se hace es lo que el propio punto llamaba
«el noventa por ciento del valor» y no existía: la guardia.

### 3 · Los siete `high` del `npm audit` se miden sin `--production`

```
$ cd frontend && npm audit --production --json | ... metadata.vulnerabilities
{'info': 0, 'low': 1, 'moderate': 0, 'high': 2, 'critical': 1, 'total': 4}
$ npm audit --json | ... metadata.vulnerabilities
{'info': 0, 'low': 1, 'moderate': 0, 'high': 7, 'critical': 1, 'total': 9}
```

El informe que alimenta la puerta se genera **con** `--production`. Cinco de
los siete son dependencias de desarrollo y nunca han pasado por ella. Esa mitad
del punto era exacta: no se miraban en absoluto.

---

## R11 · El README y lo que no hace · CERRADO

**Medido.**

```
$ grep -n "INFORME_CIERRE\|INVENTARIO_Q\|MEDICION_NEXTJS" README.md
(sin salida · exit 1)
$ wc -l README.md
539 README.md
```

539 líneas y ni una limitación declarada del estado actual, con cinco
perfectamente documentadas en su propio `docs/`.

**El arreglo.** Sección `## Lo que hoy no está cerrado` tras `## Métricas`, con
los cinco puntos y su enlace. Se actualizó al cerrar R7, R9 y R2 para que diga
lo que es verdad al final del bloque, no al principio.

**Prueba.** No lleva test propio: lo que lleva test es que las cifras del README
reproduzcan su comando (ver R8).

---

## R5a · La justificación mentirosa · CERRADO

**Medido.** Dos ficheros del mismo repositorio decían lo contrario sobre el
mismo aviso. `.github/npm-audit-allowlist.json`:

> "No es un parche: es un proyecto."

`docs/MEDICION_NEXTJS_15.md:628`:

> "El trabajo medido es un codemod automático sobre 77 ficheros (1,6 segundos,
> 0 errores) más una línea. No es «un proyecto», que es lo que dice hoy la
> justificación escrita en `.github/npm-audit-allowlist.json`."

**El arreglo.** Las dos justificaciones dicen ahora lo medido: el salto son 77
ficheros de codemod más una línea; lo que falta no es el salto sino verificar en
ejecución que Next 15 no rompe las 168 rutas, porque el cambio de caché por
omisión no produce errores de compilación. Se añade el campo `medicion`
apuntando al documento. El defecto no era aceptar el aviso —los dos críticos son
no alcanzables, y eso también está medido— sino **exagerar el coste del arreglo
para no hacerlo**.

**Prueba.**

```
$ python3 .github/scripts/npm_audit_gate.py <informe> <lista>
[GATE npm audit] PASA · ningun CRITICAL sin acotar · exit=0
```

Y desde R9, `test_la_puerta_de_npm_audit_corta_en_high.py` exige que toda
entrada acotada lleve motivo de más de 80 caracteres, versión que lo arregla y
fecha de revisión.

---

## R3 · Ejecutar las evaluaciones · NO SE HACE

**Qué falta: la clave de API.** No está en el repositorio ni en este entorno.

```
$ gh secret list
HETZNER_HOST          2026-06-10T11:53:46Z
HETZNER_SSH_KEY       2026-06-10T11:53:25Z
HETZNER_USER          2026-06-10T11:54:04Z
$ env | grep -c ANTHROPIC_API_KEY
0
```

**Por qué no se rodea.** Las 40 entradas se evalúan llamando al modelo: es lo
que se está midiendo. Sin clave no hay tasa de acierto, y fabricar una sería
justo lo contrario de lo que este punto persigue. El job está bien construido
—`evals-llm` queda SALTADO en gris, no en verde— así que el repositorio no
miente sobre ello; simplemente no tiene el dato.

**Lo que hay que hacer, y son tres pasos de nadie más que el dueño del
repositorio:** poner `ANTHROPIC_API_KEY` como secreto (Settings → Secrets and
variables → Actions), lanzar `evals.yml` a mano, y escribir
`EVALUACION_AGENTES.md` (retirado del repositorio) con fecha, commit, modelo por agente, tasa por
conjunto, umbral y los fallos uno a uno. **Si algún conjunto baja del umbral, no
se baja el umbral: se documenta el fallo.**

Mientras tanto, el README dice en «Lo que hoy no está cerrado» que la evaluación
nunca se ha ejecutado, que es la verdad.

---

## R1 · El catálogo de modelos · CERRADO

**Medido.**

```
$ grep -rhoE 'claude-(sonnet|opus|haiku)-[0-9][a-z0-9-]*' backend/app \
    --include="*.py" | sort | uniq -c | sort -rn
      8 claude-opus-4-7          5 claude-opus-4-6
      7 claude-haiku-4-5         3 claude-opus-4-8
      6 claude-sonnet-4-5        2 claude-haiku-4-5-20251001
      5 claude-sonnet-4-6        1 claude-sonnet-4-5-20250929
$ grep -rn "MODEL_CATALOG" .
(sin salida)
```

37 literales, 8 identificadores, 18 ficheros, ningún sitio que los declare. Y
los cinco defectos del enunciado se confirmaron todos:

- **(a)** `base.py:62` tenía 6 alias; `copilot_admin_service.py:361` y
  `copilot_cliente_service.py:305`, 4 — sin `opus-4` ni `opus-4.6`. Había una
  **cuarta** copia sin detectar: la lista blanca de `test_framework.py:124`.
- **(b)** `.get(alias, alias)`, con un test consagrándolo:
  `test_unknown_alias_passthrough`.
- **(c)** `grep -rn "use_fallback" backend/ --include="*.py"` → 5 líneas: firma,
  docstring, uso interno y las dos del test. Cero desde producción.
- **(d)** `_MODELS_WITHOUT_TEMPERATURE` con un solo miembro, y `opus-4-8`
  llamado con `temperature` desde `triage_agent.py:183`.
- **(e)** `orchestrator.py:480`, `model_version="claude-opus-4-8"` escrito a
  mano en el manifiesto de la ejecución de verificación.

**El arreglo.** `backend/app/core/ai/model_catalog.py`: una estructura congelada
que es la única fuente. `resolver` **levanta** `ModeloDesconocido` con el alias,
los válidos y el fichero. Las copias del copiloto se borran. La lista de
`temperature` pasa a ser un campo del modelo. El arranque aborta si un agente o
una persona declaran un alias inexistente. `FULKRO_MODEL_OVERRIDE__<alias>` se
valida contra el catálogo. La cadena de reserva se reintenta de verdad en 429
agotado y 5xx —no en 400 ni 401— recalculando la temperatura para el modelo de
reserva, que si no R3 se violaba justo en el camino de error.

**Honestidad sobre (d).** `claude-opus-4-8` queda con
`temperatura_verificada=False`. Comprobar si heredó la deprecación de 4.7 exige
una llamada real con clave de API, que no hay. El campo dice que no se sabe en
vez de fingirlo.

**Prueba.** Sobre el padre `eb8085c`, con el catálogo copiado encima para que el
fallo no sea un `ImportError` vacío:

```
$ pytest backend/tests/core/ai/test_model_catalog.py -q
PADRE: 7 failed, 17 passed · exit=1
   test_solo_hay_un_mapa_de_alias
   test_el_copiloto_resuelve_todos_los_alias[admin-opus-4]
   test_el_copiloto_resuelve_todos_los_alias[admin-opus-4.6]
   test_el_copiloto_resuelve_todos_los_alias[admin-opus-4.8]
   ...y los tres mismos en cliente
HIJO:  24 passed · exit=0

$ pytest backend/tests/core/ai/test_llm_router.py -q
PADRE: 2 failed, 9 passed · exit=1   (la reserva no existe: LLMBackendError)
HIJO:  11 passed · exit=0
```

Falla exactamente en `opus-4` y `opus-4.6`, como predecía el enunciado — y
además en `opus-4.8`, que no estaba en **ninguna** de las tres copias pese a que
`m08` lo usa.

La guardia AST no falla en el padre por una razón que conviene decir: el
catálogo se construyó a partir de los literales que ya existían, así que no hay
ninguno huérfano que denunciar. Es una guardia contra lo que **entre**, y se
comprobó que funciona introduciendo uno:

```
$ sed -i 's/claude-sonnet-4-6/claude-sonnet-5-0/' .../llm_prioritizer.py
$ pytest ...::test_todo_identificador_de_modelo_esta_en_el_catalogo -q
1 failed · exit=1
```

**Diferencial de artefacto.** Se cambia `TRIAGE_MODEL` y se regenera el
manifiesto de una ejecución de verificación:

```
PADRE                                   HIJO
{                                       {
  "model_version": "claude-opus-4-8",     "model_version": "claude-opus-4-8",
  "manifest_hash": "5bc5e0f34..."         "manifest_hash": "5bc5e0f34..."
}                                       }
   ── tras TRIAGE_MODEL = "opus-4.7" ──
{                                       {
  "model_version": "claude-opus-4-8",     "model_version": "claude-opus-4-7",
  "manifest_hash": "5bc5e0f34..."         "manifest_hash": "3c015aee..."
}                                       }
   el manifiesto NO se mueve:              el manifiesto sigue al modelo
   la procedencia miente
```

En el manifiesto va el modelo **configurado**, no el que respondió, y a
propósito: se construye antes de ejecutar nada y su hash es la base de la
comparación de determinismo contra el golden. El modelo que respondió de verdad
se graba por hallazgo en `Verdict.model_version`, que ahora lo toma de la
respuesta (`triage_agent.py`).

---

## R8 · Las cabezas de Alembic · CERRADO (el defecto ya no existía)

Ver la discrepancia 2 arriba: **una** cabeza, no cuatro, y el repositorio ya usa
`upgrade head` en singular en todas partes.

**Lo que sí se hace.** `backend/tests/test_una_sola_cabeza_alembic.py`: una sola
hoja; ninguna revisión huérfana fuera de la cadena; tantos ficheros como
revisiones; y `upgrade heads` en plural prohibido en el aprovisionamiento,
porque escribir el plural es rendirse ante el árbol abierto en vez de converger.
El árbol **ya se abrió** en tres cabezas antes —por eso existe esa migración de
merge— y se convergió a mano sin que nada detectara la apertura.

Un test que pasa desde el primer día no demuestra que mire donde dice, así que
lleva uno que monta una copia del árbol con una revisión huérfana y comprueba
que la detección salta.

**Lo que NO se verifica, y por qué.** `alembic upgrade head` contra una base
limpia. Esta máquina no tiene servidor PostgreSQL ni Docker (ver R7). Lo que sí
se verifica es el árbol, que es donde vive el defecto.

**Segundo hallazgo del mismo punto: cuatro cifras del README no reproducían su
propio comando.**

```
migraciones      decía 271    → 273
líneas (tabla)   decía 242267 → 243999
ficheros de test decía 616    → 632
líneas (bloque)  decía 237617 → 243999
```

Una cifra con su comando al lado que ya no reproduce es peor que no tener cifra:
invita a comprobarla y falla la comprobación. Se corrigen y se añade
`test_las_cifras_del_readme_reproducen.py`, que ejecuta cada comando y compara.
El propio test se cuenta a sí mismo, y eso es lo correcto: añadir un test obliga
a mover la cifra.

```
$ pytest backend/tests/test_las_cifras_del_readme_reproducen.py -q
PADRE: 4 failed, 4 passed · exit=1
HIJO:  8 passed · exit=0
```

**Queda fuera a propósito** el resultado de la suite (`44 failed, 6510 passed`):
no es un comando de segundos sino una ejecución de catorce minutos contra una
base sembrada, y esa base no existe en esta máquina. Sigue sin verificar.

---

## R10 · Los dos detalles · CERRADO

### (a) Sin base de datos la batería reventaba

**Medido.**

```
$ pytest backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py
ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5433)
1 failed in 4.13s
```

**El arreglo.** El patrón correcto ya estaba en el mismo `conftest.py`, aplicado
a MinIO (línea 590): sonda de socket y, si no responde, `pytest.skip` con el
motivo, el destino y el comando. Se copia para postgres dentro del hook de
colección que ya existe, una vez por sesión, y arregla los 3.371 de golpe.

```
$ pytest backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py
1 skipped in 0.01s · exit=0
```

**Prueba.** `test_sin_base_de_datos_los_requires_db_se_saltan.py` lanza pytest
en un **subproceso** con `DATABASE_URL` a un puerto muerto —la sonda se cachea
por sesión, así que dentro de la misma ejecución ya está resuelta— y exige
salida 0 con `skipped`, sin `ConnectionRefusedError`, y con un motivo que diga
qué destino se intentó y cómo levantarlo.

### (b) «La pestaña siguiente»

`AssignContactModal.tsx:227` mandaba al usuario a una pestaña por su posición, y
la pestaña tiene nombre. Dos problemas: un lector de pantalla no transmite la
posición, y era una instrucción para que el usuario hiciera clic en algo que el
código podía hacer por él (`setTab` estaba doce líneas más arriba). Ahora es un
botón.

**Barrido del resto**, como pedía el punto. Siete más, y **dos de ellas las
encontró la propia guardia** después de que el barrido a mano las pasara por
alto:

| fichero | decía | dice |
|---|---|---|
| `whatsapp/page.tsx` | «un thread a la izquierda» | «de la lista» |
| `cloud-connections/page.tsx` | «en la sección de abajo» | «uno de los disponibles» |
| `categorizacion/page.tsx` | «Revísala más abajo» | «Ya puedes revisarla» |
| `magerit/page.tsx` | «los detalles más abajo» | «Ya puedes revisar» |
| `files/page.tsx` (×2) | «el botón de arriba», «arriba a la derecha» | «Compartir documento» |
| `EntregablesGeneratorPanel.tsx` | «el botón de arriba» | «Generar los que faltan» |

Se deja **una**, con su motivo escrito en las excepciones del test:
`OnboardingTutorial.tsx`, donde el tutorial *enseña* dónde está el icono
flotante. Ahí la posición es la información, no un atajo para no programar la
acción.

```
$ pytest backend/tests/test_sin_referencias_posicionales_en_la_interfaz.py -q
9 passed · exit=0
$ npx tsc --noEmit · exit=0
```

---

## R2 · El modo degradado · PARCIAL, y aquí está exactamente qué mitad

**Medido, y reproduce la medición del enunciado al carácter.**

```
$ for f in backend/app/agents/agent_*.py; do \
    printf "%s %s\n" "$(basename $f)" "$(grep -c 'fallback' $f)"; done
agent_04_redactor 9 · agent_06_contratos 16 · agent_11_auditor_virtual 9 ·
agent_12_coach_cliente 8 · agent_17_cualificador 10 · agent_18_reunion 9 ·
agent_19_propuestas 11 · agent_20_negociacion 11 · agent_27_clasificador 9 ·
agent_31_enriquecedor_dda 10
```

Son **diez**, no nueve (el enunciado dice «nueve de los doce» y lista diez).

```
$ grep -rn '"mock"' backend/app | grep -v test
un solo consumidor en el producto: m11_copiloto/inline_agents_api.py:298
```

Peor de lo dicho: los endpoints específicos **ni siquiera recibían** la bandera.
Cada agente construye su propio diccionario de resultado y ninguno copiaba
`mock` dentro.

**Y el sitio donde de verdad se veía**, que no estaba en el enunciado:
`LeadDrawer.tsx` y `ActionChip.tsx` invocaban al agente, **tiraban el
resultado** y hacían `toast.success("... ejecutado")`. Un visto bueno verde a
algo que no había pasado por ningún modelo.

**Lo que se hace.** `agents/procedencia.py` declara tres valores —`modelo`,
`plantilla_por_fallo_de_esquema`, `sin_clave_de_api`— que viajan como
`generado_por` en los diez agentes, en cada paso de `workflows_simple` y en su
respuesta global, y llegan a los dos sitios de la interfaz, que ahora avisan.
`es_del_modelo` trata la **ausencia** de la marca como «no vino del modelo»,
para que un camino nuevo que se olvide de declararla falle del lado seguro.
`workflows_simple` llevaba un defecto propio: encadena la salida del paso N como
contexto del N+1, así que una plantilla en medio contamina lo que venga detrás;
la respuesta global sólo se declara «modelo» si **todos** los pasos lo son.

### Lo que NO se hace, y por qué

El criterio de cierre pedía `test_no_se_firma_un_documento_con_texto_que_no_vino
_del_modelo`: enriquecer una medida sin clave, intentar firmar la DdA y exigir
el rechazo. **No se puede construir, porque la premisa no se sostiene.** A31 no
escribe en `dda_entries`:

```
$ grep -rn "justificacion_no_aplica=" --include="*.py" backend/app
m03_dda/service.py:166  justificacion_no_aplica=None
m03_dda/service.py:190  justificacion_no_aplica=justificacion
$ grep -rn "enrich_no_aplica_justification" --include="*.py" backend/app
solo agents/api.py — ni un consumidor interno
$ grep -rn "31/enrich" --include="*.ts" --include="*.tsx" frontend
(sin salida) — tampoco lo llama la interfaz
```

La justificación que acaba en la DdA firmable la escribe
`render_no_aplica_justification` (`m03_dda/templates.py`), una plantilla
**determinista** del motor, a partir del motivo real de exclusión. Eso no es el
camino de reserva del LLM: es **R1** (motores deterministas > LLM para
decisiones normativas) funcionando como debe.

Es decir: hoy no hay ningún fragmento de texto de LLM dentro del documento
firmable que rechazar. Añadir una columna de procedencia a `dda_entries` y una
puerta de firma sería inventar un acoplamiento que el código no tiene, y dejar
el repositorio afirmando un control sobre un riesgo que no corre. **El día que
la salida de un agente entre en un entregable firmable, esa puerta hará falta**,
y el vocabulario para construirla ya está puesto.

**Diferencial de artefacto.** El mismo agente sin `ANTHROPIC_API_KEY`:

```
PADRE                                   HIJO
fallback_used: true                     fallback_used: true
schema_valid:  false                    schema_valid:  false
generado_por:  (la clave NO existe)     generado_por:  "sin_clave_de_api"
texto: "La medida mp.s.2 ... no         texto: (el mismo)
        resulta de aplicacion..."
```

El texto servido es el mismo en los dos. Lo que cambia es que ahora se sabe que
no lo escribió nadie.

---

## R9 · El umbral del `npm audit` · CERRADO

**Medido.** `npm_audit_gate.py:71` cortaba sólo en `critical`. Al subir el
umbral aparecieron **doce** avisos que pasaban enteros: diez de `next` (DoS con
Server Components ×5, SSRF en WebSocket upgrades, en Server Actions y en
rewrites, bypass de middleware con i18n) y dos de `postcss`. Ninguno se veía en
el recuento por severidad, porque ese recuento agrupa por **paquete** y `next`
ya figuraba como `critical`: doce avisos escondidos detrás de una línea que ya
estaba en rojo conocido.

**Lo que se arregla, no se acota.** `npm audit fix --package-lock-only`, sin
cambio mayor: `nanoid` 3.3.11 → 3.3.19, `postcss` 8.5.10 → 8.5.28,
`postcss-selector-parser` 6.1.2 → 6.1.4. Verificado que el árbol sigue en pie:

```
$ npm ci              exit=0
$ npx tsc --noEmit    exit=0
$ npm run build       exit=0 · las mismas rutas
$ npm audit --production --json
{'info':0,'low':0,'moderate':0,'high':1,'critical':1,'total':2}
```

**Lo que se acota, y con qué honestidad.** Los diez de `next` son el mismo
paquete y el mismo arreglo que los dos críticos: el salto a 15.5.24, ya medido.
Lo que **no** se afirma es que no sean alcanzables: de los dos críticos sí se
midió, de estos diez no, y decir que no lo son sin comprobarlo sería repetir el
defecto que R5a corrigió en este mismo fichero. Caducan el 2026-12-31 con el
resto, así que el CI se pondrá rojo solo si el salto no se ha hecho. Los dos de
`postcss` son la copia **anidada** dentro de `next` y ahí sí hay atenuante
comprobable: procesan el CSS del propio repositorio en tiempo de construcción.
Pero **no comparten arreglo** con los otros: el `npm audit fix` de arriba sólo
alcanza la copia de primer nivel, y la anidada no la cierra el salto a 15.5.24
sino `next@16.3.5` (campo `arreglado_en` de la lista).

**Las dependencias de desarrollo** se cuentan e informan aparte, sin tumbar el
build: un segundo informe sin `--production` que el gate recibe por
`--informe-dev` y del que nombra los 5 paquetes exclusivos de desarrollo.

**Prueba.**

```
$ pytest backend/tests/test_la_puerta_de_npm_audit_corta_en_high.py -q
PADRE: 5 failed, 11 passed · exit=1
HIJO:  16 passed · exit=0
```

---

## R7 · Los 3.371 · PARCIAL · hay dónde ejecutarlos, no el número

**Lo que faltaba no era infraestructura**, y el enunciado tenía razón: estaba
casi todo hecho y medido en los comentarios de `ci.yml:160-200`. El job ya
levanta `pgvector/pgvector:pg16`, el sembrado ya funciona ahí (1,37 s · ok 25 ·
skip 2 · fail 0), el corpus ya carga (1.031 fragmentos) y una muestra acotada ya
sale limpia (289 en 108 s). Sólo faltaba un sitio donde ejecutarlo.

**Lo que se hace.** `.github/workflows/pytest-completo.yml`: postgres,
provisión, migraciones, GRANTs, los **dos** pasos de sembrado y `-m requires_db`
repartido en cuatro trozos con `pytest-split` — cuatro runners en paralelo, no
cuatro horas. Nace **fuera** de la puerta de PR a propósito (`workflow_dispatch`
+ cron nocturno). Los cuatro pasos para promoverlo quedan escritos en la
cabecera del YAML y en `docs/CI.md` §2.7.

### Lo que falta, y por qué

**El número.** El punto decía «ejecútalo y dime el número: ése es el trabajo de
este punto», y no se puede obtener aquí:

```
$ docker ps
The command 'docker' could not be found in this WSL 2 distro.
$ which psql pg_ctl postgres
/usr/bin/psql          (ni pg_ctl ni postgres)
$ ls /var/lib/postgresql/
No such file or directory
```

Sólo está el cliente de PostgreSQL, no el servidor, y no hay Docker. Sin base no
hay ejecución, y la respuesta a «¿dos horas o dos días?» **sigue sin conocerse**.
El workflow está escrito y su YAML valida, pero **no se ha ejecutado ni una
vez**: hay que lanzarlo desde Actions.

---

## R5b · El salto a Next 15 · NO SE HACE

**Qué falta: poder ejecutar Playwright.** El punto es explícito en que el
eslabón que falta es la suite de Playwright, y que no hay que construirla porque
ya está en `ci.yml:439`. Pero ejecutarla exige la pila completa —backend,
PostgreSQL, MinIO, sembrado— apuntando a la copia actualizada, y esta máquina no
tiene ni Docker ni servidor de base de datos (mismos comandos que en R7).

**Por qué no se sube igualmente.** Porque lo que está medido es que **compila**,
no que **funcione**, y el propio `docs/MEDICION_NEXTJS_15.md` dice que Next 15
cambia el comportamiento de caché por omisión en 168 rutas, tres portales y un
middleware que decide autorización, sin producir un solo error de compilación.
Subir apoyándose en «el build pasa» es cambiar un riesgo conocido y acotado por
uno desconocido y sin acotar.

**Lo que sí queda hecho de este frente:** la justificación ya no miente (R5a), y
los doce avisos `high` están ahora a la vista y acotados con fecha (R9), de modo
que el CI se pondrá rojo por sí solo el 2026-12-31 si nadie lo ha hecho. El
salto a 15.5.24 cierra diez de esos doce; los dos de `postcss` anidado piden
`next@16.3.5`, y siguen rojos en esa fecha aunque el salto a 15 se haga.

---

## Comprobación final

Sobre `bb221a9`, el último commit del bloque:

```
$ python -m pytest backend/tests/ --collect-only -q   → 6794 tests · exit=0
$ python -m pytest backend/tests/ -m "not requires_db" -q
                                                      → 3400 passed · exit=0
$ make lint                                           → All checks passed · exit=0
```

Los 6.794 son los 6.709 del padre más los 85 tests que añade el bloque (ver la
primera discrepancia). De los 3.423 que recoge la segunda orden pasan 3.400 y
se saltan 23 (vuelto a medir el 2026-09-23: `3400 passed, 23 skipped`).
