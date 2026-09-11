# FULKRO

Plataforma que implantaba el **Esquema Nacional de Seguridad** (RD 311/2022) de punta a punta
—categorización, análisis de riesgos MAGERIT, declaración de aplicabilidad, plan de adecuación,
generación documental, recogida de evidencias y portal de auditor— construida y operada por una
sola persona. El proyecto cerró en septiembre de 2026 y el código se publica bajo Apache-2.0.

---

## Qué se ve

| | |
|---|---|
| ![Centro de mando](landing/assets/capturas/marketing/admin-mando.png) | ![Declaración de aplicabilidad](landing/assets/capturas/marketing/admin-dda.png) |
| **Centro de mando** · estado de todos los proyectos | **Declaración de aplicabilidad** · 73 medidas del Anexo II |
| ![Plan de adecuación](landing/assets/capturas/marketing/admin-plan.png) | ![Cobertura del auditor](landing/assets/capturas/marketing/auditor-cobertura.png) |
| **Plan de adecuación** · hitos y dependencias | **Portal de auditor** · cobertura medida contra evidencias |
| ![Registro de auditoría](landing/assets/capturas/marketing/auditor-registro.png) | ![Portal de cliente](landing/assets/capturas/marketing/cliente-inicio.png) |
| **Registro inmutable** · cadena de hashes verificable | **Portal de cliente** · lo que el cliente ve y firma |

Quedan cuatro más en [`landing/assets/capturas/marketing/`](landing/assets/capturas/marketing/):
`auditor-resumen`, `cliente-certificacion`, `cliente-firmas` y `cliente-remediaciones`.

---

## Para quién está construido, y para quién no

**Está construido para un operador único que lleva varios clientes en paralelo.** No para que una
empresa se registre y lo use.

No hay autorregistro. No existe un endpoint de alta:

```bash
$ git grep -nE '"/(signup|register|sign-up)"' -- backend/app
# sin salida
```

Solo hay dos poblaciones de sujeto, y están cableadas por nombre:

```bash
$ git grep -n "role_pool !=" -- backend/app/auth/dependencies.py
backend/app/auth/dependencies.py:71:    if subject.role_pool != "marcos":
backend/app/auth/dependencies.py:113:    if subject.role_pool != "cliente":
```

Y el reparto de las puertas de autorización enseña para quién se diseñó:

```bash
$ git grep -o 'Depends(require_owner)' -- backend/app | wc -l              # 249
$ git grep -o 'Depends(require_client_user)' -- backend/app | wc -l        #  31
$ git grep -o 'Depends(require_marcos_or_client)' -- backend/app | wc -l   #  24
```

**Esos tres comandos cuentan ocurrencias de un literal, no endpoints**, y una versión anterior de
este README saltó de lo uno a lo otro. El error no es el que parece: 132 de las 249 de
`require_owner` están a nivel de `APIRouter`, y **cada una protege todos los endpoints que cuelgan
de ese router**, que pueden ser uno o dieciséis. Es decir, el `grep` se queda **corto**, no largo.

Medido contra la aplicación en ejecución, recorriendo el árbol de dependencias de cada ruta de
forma recursiva (las puertas anidadas no salen en el primer nivel):

```bash
$ PYTHONPATH=. python3 scripts/medir_autorizacion.py
rutas resueltas          1201
operaciones (camino x metodo) 1201
contraste con el esquema OpenAPI: 1099 caminos, 1201 operaciones

puerta                         rutas   % rutas
require_owner                    845     70.4%
require_client_user               25      2.1%
require_marcos_or_client          81      6.7%

Corte por poblacion de sujeto (categorias EXCLUYENTES, suman el total):
solo administrador               849     70.7%
solo cliente                     176     14.7%
cualquiera de los dos             81      6.7%
ninguna de esas                   95      7.9%

De las 1106 rutas con puerta de poblacion, 849 exigen ser el administrador: 76.8%.
Rutas que pasan por `authenticate_request` (dependencia global): 1201/1201.
```

**Población contada: rutas.** En esta aplicación coinciden con las operaciones (camino × método),
porque cada ruta declara un solo método: 1.201 y 1.201, contrastado contra el esquema OpenAPI.

Las 845 reales frente a las 249 del `grep` dan la medida del desfase: contar el literal deja fuera
casi setecientos endpoints. Y hay un matiz que el conteo de tres puertas también se dejaba: hay
rutas que resuelven el sujeto con `get_current_user` o `get_current_client_user` sin pasar por
ninguna de las tres, así que «sin puerta» no significa «sin autenticación» — las 1.201 pasan por
`authenticate_request`.

**Con la población bien contada, la conclusión se sostiene: 76,8 % de las rutas con puerta de
población exigen ser el administrador**, casi ocho de cada diez. La frase era correcta; el comando
que la acompañaba, no. El script queda en el repositorio para que se pueda volver a medir.

**Consecuencia, dicha sin adornos:** un despacho de tres consultores no puede usar esto tal cual.
No hay bandeja de administración por usuario, ni roles intermedios, ni forma de repartir clientes
entre personas. Añadirlo no es configurar nada: es introducir un modelo de identidad que ahora
mismo no existe.

Es una decisión, no un descuido. Un solo operador significa que no hay que resolver permisos
entre iguales, ni conflictos de edición, ni jerarquías de visibilidad, y eso permitió llegar mucho
más lejos en la parte normativa. El coste es que el producto no escala a equipos sin rehacer la
capa de identidad. Se eligió a sabiendas.

---

---

## Cómo está construido

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    NAVEGADOR                         │
                    │                                                      │
   Marcos ─────────▶│  (admin)         167 páginas · Next.js 14 App Router │
   consultor        │  (client-portal) lo que el cliente ve y firma        │
                    │  (portal)        auditor ENAC · acceso por enlace    │
   Cliente ────────▶│  (public)        landing + verificación de firmas    │
                    │  (legal)         avisos RGPD art. 13                 │
   Auditor ────────▶│                                                      │
                    └────────────────────────┬─────────────────────────────┘
                                             │  cookie httpOnly + CSRF
                                             │  o enlace mágico Ed25519
                    ┌────────────────────────▼─────────────────────────────┐
                    │              FastAPI · 1.100 rutas                   │
                    │                                                      │
                    │  authenticate_request  ← una sola puerta, global     │
                    │    · pool marcos / pool cliente (ADR-013)            │
                    │    · lista blanca explícita para lo público          │
                    └────────────────────────┬─────────────────────────────┘
                                             │
     ┌───────────────────────────────────────┼───────────────────────────────┐
     │                    44 MOTORES · ciclo ENS                             │
     │                                                                       │
     │   m01 categorización ──▶ m02 MAGERIT ──▶ m03 DdA ──▶ m17 plan         │
     │        │                     │              │            │            │
     │        └─────────────────────┴──────────────┴────────────┘            │
     │                              │                                        │
     │                    m06 fábrica documental                             │
     │             render → SHA-256 → Ed25519 → fila → MinIO                 │
     │                              │                                        │
     │   m07 evidencias ──▶ m09 expediente ENAC ──▶ m27 conformidad          │
     │                                                                       │
     │   transversales: m05 firma · m12 enlaces · m11 copiloto (RAG)         │
     │                  m_observability · m_workflow_engine                  │
     └───────────────────────────────┬───────────────────────────────────────┘
                                     │
     ┌───────────────────────────────▼───────────────────────────────────────┐
     │  PostgreSQL 16 · 253 tablas · RLS en todo lo que lleva cliente        │
     │     pgvector (corpus)  ·  registro con cadena de hashes               │
     │  MinIO · documentos + evidencias WORM        Redis · colas            │
     └───────────────────────────────────────────────────────────────────────┘
```

**La forma tiene una razón.** Un motor es un paquete con su API, su servicio y sus
modelos, y una regla normativa vive en **un solo motor**. Cuando la misma regla
aparecía en dos, divergía — pasó con la regla del máximo del Anexo I (tres copias),
con el bienio del artículo 31 (cinco, ya divergentes en 720 vs 730 días) y con
«¿cuál es el análisis de riesgos vigente?» (ocho). Hay guardas que lo impiden en
`backend/tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py`.

---

## Cómo funciona: el ciclo, fase por fase

El ENS no es una checklist: es un ciclo con dependencias. Cada fase consume lo que
produjo la anterior, y las puertas entre fases están en el código, no en la cabeza
del consultor.

| # | fase | motor | produce | puerta hacia la siguiente |
|---|---|---|---|---|
| 1 | **Categorización** | m01 | acta **E-012** firmada | sin categoría aprobada no hay DdA |
| 2 | **Análisis de riesgos** | m02 | informe **E-028** (MAGERIT v3) | el análisis vigente es uno, y lo fija la base |
| 3 | **Declaración de aplicabilidad** | m03 | 73 entradas del Anexo II | congelarla exige ≥80 % valorado y firma del RSEG |
| 4 | **Plan de adecuación** | m17 | **E-150** con hitos y dependencias | — |
| 5 | **Implantación** | m07 | evidencias en almacén WORM | — |
| 6 | **Verificación** | m10 · m09 | simulacro pre-ENAC firmado | — |
| 7 | **Salida** | m09 · m27 | expediente ENAC · declaración **E-041** | la declaración dice lo verificado, no lo declarado |

### 1 · Categorización

Cinco dimensiones —confidencialidad, integridad, disponibilidad, autenticidad,
trazabilidad— valoradas sobre los servicios y los tipos de información del sistema.
La categoría es el **máximo** de las dimensiones afectadas.

Una dimensión que nadie valora **no se adscribe a ningún nivel**; es lo que dice el
Anexo I punto 3, y tiene consecuencias: un sistema sin ninguna dimensión valorada no
es BÁSICA, es un sistema sin categorizar. El acta E-012 lo imprime como «No afectada»
y el sistema no la rellena con un nivel inventado.

### 2 · Análisis de riesgos

MAGERIT v3 sobre el inventario de activos: dependencias, amenazas, salvaguardas,
riesgo intrínseco → efectivo → residual, y plan de tratamiento. La matriz 5×5 es la
del Libro III.

Un proyecto tiene **un** análisis vigente, y lo garantiza un índice único parcial en
la base con dos disparadores — no el orden de una consulta. El orden empataba: dos
análisis creados en la misma transacción comparten `created_at` al microsegundo,
porque `now()` devuelve el sello de inicio de transacción.

### 3 · Declaración de aplicabilidad

Las 73 medidas del Anexo II, extraídas del PDF del BOE y verificadas contra él
(`backend/tests/fixtures/anexo2_boe_verificado.json`). Una medida aplica por la
**categoría** del sistema **o** por el **nivel de una dimensión** — los dos ejes del
Anexo II punto 5. Son 45 medidas por el eje de categoría, 28 por el de dimensión y
47 pares (medida, dimensión).

Aplicables por categoría: **BÁSICA 52 · MEDIA 68 · ALTA 73**.

### 4 al 7

El plan de adecuación deriva del análisis de brechas; la implantación deja evidencia
fechada; la verificación ensaya la auditoría antes de pedirla; y la salida arma el
expediente que recibe el auditor de la entidad certificadora.

---

## Los cuatro portales

### Admin · el consultor

Es la superficie grande: 167 páginas, casi todas bajo `/admin/projects/{id}/…`.
La navegación es cronológica — sigue el ciclo, no el organigrama de motores — y cada
página lleva un copiloto que explica qué se está haciendo y por qué, asumiendo cero
conocimiento previo de ENS.

Lo que no es: un panel de administración genérico. No hay alta de usuarios, ni
gestión de permisos, ni configuración por cliente. Un solo operador, varios clientes.

### Cliente · lo mínimo

El cliente **ve, autoriza, firma y recibe**. No opera el ENS: no toca la DdA, no
edita el plan, no gestiona medidas. Firma con el dedo o el ratón sobre un lienzo
—firma electrónica simple, eIDAS art. 25.1— y el PDF lleva la firma embebida en su
última página con el sello Ed25519 al lado.

El tono está sujeto por tests: hay un filtro que rechaza jerga de administración y
lenguaje coercitivo en las respuestas al cliente.

### Auditor · sólo lectura, con anotaciones

Acceso por enlace mágico, sin cuenta. Ve la DdA, el análisis, las evidencias, el
registro de auditoría y el mapa de calor de cobertura — qué medidas están declaradas
implantadas y cuáles tienen evidencia vigente detrás. Puede anotar sobre cualquier
elemento y pedir aclaraciones, que llegan al consultor por SSE en tiempo real.

### Público · verificar sin entrar

La landing, los avisos legales del art. 13 del RGPD, y el distintivo de conformidad
con su verificación de firma contra la clave pública del sistema.


## Cómo probarlo

Un solo comando, sin ninguna clave de API:

```bash
git clone https://github.com/Fulkrodev/Fulkrosys.git
cd Fulkrosys
make demo
```

Deja la aplicación en `http://localhost:3000` con datos dentro —73 medidas del Anexo II, 73
entradas de Declaración de Aplicabilidad, 204 evidencias, 35 tareas de plan, 21 documentos y 1.031
fragmentos de corpus normativo— e imprime las credenciales de los tres portales, incluido el
código del segundo factor y el enlace firmado del auditor.

```bash
make smoke     # comprueba que hay datos REALES en los tres portales
make down      # para, conservando la base
make clean     # borra también los volúmenes
```

`make smoke` no consulta `/api/v1/health`, que devuelve un diccionario sin tocar la base y por
tanto daría verde con el esquema vacío. Contrasta poblaciones contra umbrales y entra de verdad en
administración, cliente y auditor. **Con la base vacía falla**: es su criterio de aceptación.

Los detalles —requisitos con versiones probadas, RAM y disco medidos, cómo pararlo, y los
problemas frecuentes con sus trazas reales— están en [`INSTALL.md`](INSTALL.md). La línea base de
lo que había antes, con los siete fallos que encontraba quien seguía el README anterior en una
máquina limpia, está en [`docs/INSTALL_TRACE.md`](docs/INSTALL_TRACE.md).

### Levantarlo a mano, sin el perfil demo

Se puede, pero necesita un entorno de compilación de C que el proyecto no declaraba: `pip install
-e "backend[dev]"` arrastra `pycairo` vía `mjml-python` y se construye desde fuente. Los paquetes
de sistema que hacen falta están en `INSTALL.md`. `docker-compose.yml` declara 22 servicios, pero
**16 son de pentesting** y no hacen falta para levantar la plataforma:

```bash
$ python3 -c "import yaml; print(len(yaml.safe_load(open('docker-compose.yml'))['services']))"
22
```

---

## Métricas

Todas llevan el comando que las reproduce. Las que no se pueden reproducir hoy
están marcadas como tales.

### Superficie

| | | comando |
|---|---:|---|
| Operaciones de API | **1.201** en 1.100 caminos | `app.openapi()` · abajo |
| Motores de dominio | **44** | `ls -d backend/app/motors/m*/ \| wc -l` |
| Tablas en PostgreSQL | **253** | `psql -c "\\dt" \| wc -l` |
| Migraciones Alembic | **271** | `ls backend/migrations/versions/*.py \| wc -l` |
| Páginas del frontend | **167** | `find frontend/app -name page.tsx \| wc -l` |
| Componentes React | **427** | `find frontend/components -name '*.tsx' \| wc -l` |
| Líneas de Python | **242.267** | `find backend/app -name '*.py' \| xargs wc -l` |

### Suite

```bash
$ pytest backend/tests -q
44 failed, 6510 passed, 115 skipped, 5 errors in 821.19s (0:13:41)
```

| | | |
|---|---:|---|
| Pasan | **6.510** | |
| Fallan | 44 | ninguno atribuible al código · ver *Dependencias de entorno* |
| Errores | 5 | los cinco, un puerto codificado en el fichero de test |
| Ficheros de test | **616** | `find backend/tests -name 'test_*.py' \| wc -l` |
| Specs de Playwright | **300** | `find frontend/tests -name '*.spec.ts' \| wc -l` |

### Recuperación del corpus · evaluación

49 consultas etiquetadas a mano sobre 1.031 fragmentos del corpus normativo
(RD 311/2022 y guías CCN-STIC). Intervalos por *bootstrap*, 10.000 remuestreos.

| rama | acierto@5 | recall@5 | MRR |
|---|---:|---:|---:|
| **vectorial sola** | **0,959** | **0,824** | **0,752** |
| fusión RRF (vectorial + léxica) | 0,878 | 0,667 | 0,690 |

```bash
make eval-recuperacion     # escribe out/eval_recuperacion.json
```

El resultado mandó: **la fusión se quitó**. La diferencia vectorial − fusión en
recall@5 es +0,157 con intervalo [+0,065, +0,255] — no cruza el cero. El informe
completo, con la metodología y los tres errores que tuvo su primera versión, está
en [`docs/EVAL_RECUPERACION.md`](docs/EVAL_RECUPERACION.md).

### Carga

Rampa de 1 a 80 peticiones simultáneas sobre los seis endpoints más llamados,
elegidos contando el tráfico real del recorrido completo. Umbral de rotura
declarado **antes** de medir: p95 > 1.000 ms.

| endpoint | techo | p95 a c=80 | dónde rompe |
|---|---:|---:|---|
| lecturas de proyecto | no rompe | < 300 ms | — |
| `/corpus/search` | **17 pet./s** | — | **c=10 · p95 1.385 ms** |

El cuello es el modelo de *embeddings*: se lleva el 89–93 % del tiempo de una
búsqueda. Detalle en [`docs/PRUEBA_DE_CARGA.md`](docs/PRUEBA_DE_CARGA.md).

### Recorrido de la interfaz

Las 167 páginas visitadas por navegador con identificadores reales, no inventados
—la pantalla de «no encontrado» devuelve HTTP 200 y dejaría pasar en verde una
ruta que no se ha comprobado—. Informe en
[`docs/RECORRIDO_COMPLETO.md`](docs/RECORRIDO_COMPLETO.md).

```bash
make recorrer-todo
```

---

## Las cifras, cada una con su comando

```bash
$ git ls-files backend/app | grep '\.py$' | xargs wc -l | tail -1
 237617 total

$ ls -d backend/app/motors/m*/ | wc -l
44

$ ls backend/migrations/versions/*.py | wc -l
268

# este necesita el venv activado y el .env cargado: importa la aplicacion
$ python3 -c "from backend.app.main import app; from fastapi.routing import APIRoute; print(len([r for r in app.routes if isinstance(r, APIRoute)]))"
1201
```

**Ese comando ya no reproduce, y merece explicación porque es un caso de manual.** Desde FastAPI
0.141, `include_router` deja de aplanar las rutas en `app.routes`: coloca objetos
`_IncludedRouter` con resolución perezosa. El mismo comando, con `fastapi 0.141.1` y
`starlette 1.6.0`, devuelve **0**, y no porque falte ningún endpoint. La etiqueta seguía diciendo
«rutas», pero lo que contaba había pasado a ser «objetos `APIRoute` que están en el primer nivel
de `app.routes`», que ya no es lo mismo.

La forma robusta a la versión es preguntar por el esquema, que además es la definición correcta de
«superficie de la API»: es lo que ve quien la consume.

```bash
$ python3 -c "from backend.app.main import app; e=app.openapi(); \
M={'get','post','put','patch','delete','head','options','trace'}; \
print(len(e['paths']),'caminos ·', sum(1 for v in e['paths'].values() for m in v if m in M),'operaciones')"
1099 caminos · 1201 operaciones
```

El 1.201 era correcto como valor —son operaciones, camino por método— y el conteo estático de
decoradores difiere porque hay routers incluidos varias veces bajo prefijos distintos. Lo que
había caducado era el comando.

Esto se llevó por delante dos tests que comprobaban registro de endpoints recorriendo `app.routes`
y contaban 0. **Nadie lo había visto porque el job de tests del CI no se ejecutaba nunca.**

### Tests: lo que se puede afirmar y lo que no

Esta tabla es deliberadamente incómoda, y es la cifra honesta.

| | | cómo se mide |
|---|---:|---|
| Recolectables | **6.674** | `pytest backend/tests/ --collect-only -q \| tail -1` |
| Que requieren base de datos | **3.294** | `pytest backend/tests/ -m requires_db --collect-only -q \| tail -1` |
| **Que el CI ejecuta de verdad** | **3.153** · el 48,7 % | el propio job lo cuenta y lo publica en su resumen |
| Última cifra local publicada | 5.978 | `ci.yml:56`, de una ejecución del 9 de junio de 2026 |

Los 6.674 recolectables son de ahora, y la cifra tiene su propia historia: entre el bloque O1 y el
cierre, `pytest backend/tests` **no coleccionaba en absoluto**. Un módulo importaba una constante
retirada, y un `ImportError` en la recolección aborta la suite entera sin ejecutar un solo test. Lo
cazó la primera vez que se corrió la batería completa en lugar de por directorios, y de ahí salió el
paso `La suite entera colecciona` del CI, que tumba el job antes de ejecutar nada. Antes de eso, la
recolección **abortaba con código 2** en
cualquier entorno limpio, porque `bs4`, `respx` y `pypdf` se importaban sin estar declaradas. En
máquina limpia daba `6383 tests collected, 7 errors`, sin llegar a ejecutar ni uno.

Los 3.153 que corren en CI son los que no necesitan una base sembrada. Los marcados
`requires_db` quedan fuera y el propio workflow dice por qué y con qué marca se delimitan. Un CI que
corre el 48,7 % y lo publica es honesto; uno que corre el 0 % mientras se presume de miles, no.

**Esa cifra de 5.978 no reproduce hoy y no aparece en ninguna otra parte del repositorio.** Está
escrita en un comentario del CI sin el comando que la produzca. Se conserva aquí como lo que es:
una afirmación de sus autores, no una medición.

No se escribe *"5.978 tests en verde"* porque nadie puede comprobarlo.

> **Aviso para quien reproduzca cualquier cifra de este README.** Si su intérprete tiene `grep`
> definido como función o alias que envuelve a `ugrep` con `--ignore-files`, respetará `.gitignore`
> y **omitirá en silencio ficheros versionados**, devolviendo un límite inferior con cara de
> medición. Medido aquí: 27 ficheros con `grep` a secas frente a 28 con `command grep`; el que
> faltaba está versionado pero bajo un patrón ignorado. Use `command grep`, o `git grep`, y
> compruebe con `type grep` qué está ejecutando en realidad.

---

## Lo que encontré auditando mi propio código

Cuatro hallazgos sobre este mismo repositorio: tres de una auditoría en ocho dimensiones y uno
anterior. Se cuentan con su medición, y los que siguen abiertos se dicen abiertos.

El informe completo de la auditoría, con los 68 bloques de hallazgo y el dictamen del verificador
adversarial de cada uno, está en [`docs/audit/AUDITORIA_2026-09.md`](docs/audit/AUDITORIA_2026-09.md).

### 1. Los agentes fabricaban respuestas en silencio · ABIERTO

Cuando falta `ANTHROPIC_API_KEY` o falla cualquier llamada, `AgentBase._call_llm` no propaga el
error: devuelve texto inventado.

```python
# backend/app/agents/base.py:206-216
except Exception as exc:
    logger.warning("LLM call failed for agent %s (%s): %s", ...)
    return self._mock_response(model, system_prompt, user_message, note=str(exc)[:160])
```

El diccionario que devuelve trae `"tokens_output": 50` —una constante— y un `tokens_input`
calculado contando palabras. Y aguas abajo, en `base.py:301`, eso se asienta en el libro mayor
con `status="success"` y un `cost_usd` calculado sobre esos tokens inventados.

Ningún consumidor comprueba el prefijo `[MOCK]`:

```bash
$ git grep -n '\[MOCK\]' -- backend/app
backend/app/agents/base.py:216:        tag = "[MOCK]" if not note else "[MOCK-FALLBACK]"
```

Una sola línea en todo el árbol, y es la que lo escribe. En una plataforma de cumplimiento
normativo esto significa entregables falsos indistinguibles de los reales, y un registro de coste
que miente. **Sigue abierto.** El arreglo correcto es propagar el fallo y marcar la entrada del
ledger, no tapar el síntoma.

### 2. El CI estaba en verde sin comprobar casi nada · RESUELTO en su mayor parte

Lo que había, medido paginando el historial entero de GitHub Actions —362 ejecuciones, no la
primera página—:

```bash
$ curl -s "https://api.github.com/repos/Fulkrodev/Fulkrosys/actions/runs?per_page=100&page=N"
CI                       121 ejecuciones · 121 de evento push · 0 de workflow_dispatch
```

Los jobs `test` y `playwright` estaban condicionados a `workflow_dispatch`, así que **no se habían
ejecutado nunca**: ni una sola vez en 121 ejecuciones. `mypy` no fallaba por errores de tipo,
*crasheaba* con código 2 por el doble convenio de import `app.*` frente a `backend.app.*` —no
comprobaba ni un fichero— y `continue-on-error: true` lo pintaba verde. El job `safety` llevaba
`|| true` y un parser que devolvía éxito ante fichero ausente, JSON corrupto o cambio de esquema.

Qué se ha hecho:

- El job `test` corre en cada `push` y `pull_request`, con la base provisionada de verdad
  (extensiones, funciones, roles, `alembic upgrade head` y GRANTs), reutilizando la receta que ya
  llevaba 41 ejecuciones verdes en `admin-polish-empirical.yml`.
- **Corre 3.153 de 6.674 tests**, y el propio job lo publica en su resumen contándolo en
  cada ejecución. Los 3.294 que necesitan base sembrada quedan fuera y está dicho por qué, con la
  marca de pytest que los delimita.
- `mypy` se invoca desde `backend/`, sin `continue-on-error`, acotado a una lista de módulos que ya
  pasan limpios (160 de 1.056 ficheros). De golpe eran 515 errores en 212 ficheros. La lista solo
  puede crecer.
- El gate de `safety` se reescribió y se probó provocando los cuatro fallos a propósito: el parser
  viejo devolvía éxito en los cuatro, el nuevo devuelve fallo en los cuatro.
- `deploy.yml` desplegaba por SSH a un servidor borrado el 9 de septiembre. Se retiró a
  `docs/historia/` en vez de parchearlo.

**Lo que sigue abierto:** no hay branch protection —`protected: false`, comprobado contra la API—,
así que los gates anteriores pueden saltarse. Es configuración de GitHub y hay que hacerla a mano;
los pasos exactos están en [`docs/CI.md`](docs/CI.md). Y 896 de los 1.056 ficheros siguen sin
pasar por `mypy`.

### 3. El detector de verdad vacua · RESUELTO en la parte medida

Un test es *vacuamente verdadero* cuando pasa porque no hay datos que puedan contradecirlo.
«No hay huérfanos» sobre una tabla vacía se cumple solo: ese test da verde para siempre, no vuelve
a comprobar nada, y encima cuenta como cobertura.

Empecé con una señal ingenua —ejecutar la suite contra una base vacía y marcar lo que pasara— y
**el primer resultado no valía**:

```
3.294  ejecutados con -m requires_db
2.930  pasaron contra la base vacía          (89 %)
```

Un 89 % no es un hallazgo, es un filtro mal calibrado: la mayoría de esos tests **crean sus
propios datos dentro del test**, que es el patrón correcto. Así que instrumenté la sesión de
pruebas con eventos de SQLAlchemy ([`scripts/vacuity_plugin.py`](scripts/vacuity_plugin.py)) para
medir, por test y en ejecución, dos cosas más: cuántas filas escribe y cuántas lee.

```
  357  + escribieron 0 filas
  299  + leyeron 0 filas REALES               <- sospechosos
```

Ese «reales» es el núcleo del método, y salió de una validación fallida. Con `filas_leidas == 0`
a secas, el filtro **se comía 4 de los 5 vacuos que ya estaban confirmados a mano**: `SELECT
COUNT(*)` devuelve siempre una fila, también sobre una tabla vacía, y esa fila contiene el cero.
El test no examinó nada, pero el contador marcaba 1. `filas_leidas_reales` excluye las consultas
de solo agregados, y los cinco vuelven a cero.

Sospechoso no es vacuo: hay tests que pasan legítimamente sin datos. Así que muestreo y triaje a
mano, uno por uno:

```
muestra   80 de 299 (26,8 %), semilla 20260910
método    random.Random(semilla).sample(poblacion, 80), Python 3.12
vacuos    5 de 80 = 6,25 %
IC 95 %   Wilson [2,70 % – 13,81 %] · con corrección por población finita [3,49 % – 13,02 %]
estimado  ~19 de 299 (IC 10 a 39)
```

Los 5 confirmados están arreglados: ahora afirman primero que hay población que examinar, así que
sobre una base vacía **fallan** en vez de pasar. Tres de los cinco se verificaron además en
positivo contra una base con datos; los otros dos no, porque sus tablas no están en el fixture, y
así queda dicho.

El detector se ejecuta así:

```bash
python scripts/vacuity_check.py \
  --database-url postgresql+asyncpg://... \
  --counters /tmp/counters.jsonl \
  --baseline out/vacuity_baseline.txt
```

Con `--baseline` sale con código 1 **solo ante sospechosos nuevos**. Los 294 heredados están
congelados en [`out/vacuity_baseline.txt`](out/vacuity_baseline.txt). Una puerta que tumba el
build con 299 heredados no la activa nadie, y una puerta que nadie activa no protege de nada.
**No está cableado en CI.**

### 4. Un tercio de la capa de agentes duplicaba lógica que ya existía · RESUELTO

Este es anterior a la auditoría de ocho dimensiones —es de abril de 2026— y se cuenta porque
explica una cifra que, mal contada, parece un agujero.

El registro de agentes declara **31** identificadores, de los cuales **12** están activos. Y aquí
hay que confesar un error propio, porque una versión anterior de este README dijo 32 y 13, y remató
con un «cuadra» que era falso por partida doble.

El fallo estaba en el método: contar con `grep` *literales de cadena* del fichero, que aparecen
también en comentarios y docstrings, y no *entradas del registro*. Parseando el módulo con AST:

```bash
$ python3 -c "«recorrer AGENT_REGISTRY con ast y contar por status»"
entradas del registro: 31
   deprecated                       14
   activo                           12
   reservado                         2
   externalized_to_motor             2
   scaffolding_covered_by_engine     1
```

El segundo error iba en dirección contraria y por eso el resultado parecía cuadrar: el glob
`backend/app/agents/*.py` **no es recursivo** y se dejaba fuera a `CopilotoAgent`, que vive en
`agent_14_copiloto/__init__.py`. Buscando recursivamente son **13** clases, no 12.

Así que la cifra honesta es **12 identificadores activos y 13 clases implementadas**, y no cuadran:
hay una clase más que identificadores en activo. Dos errores que se compensaban producían un
«cuadra» tranquilizador. Es exactamente el fallo que este README dice combatir, cometido en este
README.

Los 14 deprecados están así a propósito, y el motivo está escrito en el propio módulo:

> Sesión 9 (2026-04-23): auditoría sistemática detectó 10 agentes scaffolding redundantes con
> motores deterministas o stubs muertos sin invocación. Se eliminaron código + prompts +
> endpoints específicos; los IDs quedan registrados aquí con `status=deprecated` para mantener
> compatibilidad histórica (no reusar).
>
> — `backend/app/agents/registry.py`

Otros dos salieron después por la misma vía: A15 y A26 eran stubs cuya funcionalidad real vive en
`m23_retainer`, y su endpoint `/invoke` devuelve 410 apuntando al motor.

La regla que lo motivó es de las primeras del proyecto: **motores deterministas antes que LLM
para decisiones normativas**, porque ante un auditor de ENAC hay que poder trazar por qué salió
un resultado. Un agente que envuelve en lenguaje natural una decisión que ya toma un motor no
añade valor y sí añade superficie de fallo. Al medirlo, un tercio de la capa de agentes estaba en
ese caso.

Los identificadores no se reciclan: quedan quemados con su estado y su nota, para que nadie
reutilice un número y herede la confusión.

---

## Limitaciones conocidas

**Las rutas absolutas a la máquina del autor: resueltas, y lo que enseñaban.** Había 62
ocurrencias de `/home/usuario` en 28 ficheros versionados, 13 de ellas código que se evaluaba al
importar. Quedan 29 en 3 ficheros, todas documentación o registro fechado:

```bash
$ grep -rIo "/home/usuario" --exclude-dir=.git . | wc -l    # 29
$ grep -rIl "/home/usuario" --exclude-dir=.git .            # 3 ficheros
docs/audit/AUDITORIA_2026-09.md          <- informe fechado · citas textuales
README.md                                <- este texto
out/audit_codigo_2026-06-14/FIX_TRACKER.md
```

Lo interesante no era la cifra sino a dónde apuntaban. Los tres
`load_dotenv(Path("/home/usuario/fulkro/.env"))` de los ingestores no señalaban a este repositorio:
señalaban a un **segundo checkout** que existe en la máquina del autor y que tiene su propio `.env`
con `DATABASE_URL`, `MINIO_SECRET_KEY` y `ANTHROPIC_API_KEY`. El pipeline funcionaba ahí, y solo
ahí, tomando configuración de otro repositorio. Y como `load_dotenv` devuelve `False` sin lanzar
nada, fuera de esa máquina el fallo era silencioso: no un error, un pipeline corriendo sin
configuración.

Un efecto colateral que merece figurar aquí: `backend/tests/corpus/test_rd311_parser.py` era
**vacuamente verdadero** fuera de esa máquina —14 saltos silenciosos, porque la ruta absoluta nunca
existía—. La misma clase de bug que el hallazgo 3, escondida detrás de una ruta.

**La evaluación de agentes cubre 3 de las 13 clases de agente** —`agent_27_clasificador`,
`agent_18_reunion` y `agent_06_contratos`— con 10 entradas curadas cada una. Hay un cuarto golden
dataset, `deliverable_text_auditor`, que no es una clase de agente sino una capability: en total,
**4 objetivos evaluados y 40 entradas**.

```bash
$ ls -d docs/catalogs/golden_datasets/*/ | xargs -n1 basename
agent_06_contratos
agent_18_reunion
agent_27_clasificador
deliverable_text_auditor
$ command grep -rn "(AgentBase)" --include=*.py backend/app | wc -l
13
```

Antes de septiembre de 2026 esto decía «uno de trece», y era **generoso con la verdad**: el único
dataset que había medía una capability, no un agente. La cobertura de clases de agente era **0**.

Los tres nuevos se eligieron porque su salida es **estructura verificable sin juicio** —códigos de
un catálogo cerrado, enumerados, intervalos, recuentos—; los que producen prosa siguen sin dataset
a propósito, porque evaluarlos exige un criterio subjetivo que un gate no puede aplicar.

**Lo que este número NO dice**: ninguno de los cuatro tiene todavía una tasa de aciertos real,
porque el gate contra el modelo necesita `ANTHROPIC_API_KEY` y no se ha ejecutado. Lo verde hoy
mide el arnés y el cableado, no al modelo. Los umbrales de 0,80 son los que declara cada dataset,
**no una medición calibrada**.

**Nueve cadenas de modelo sueltas por el código**, sin registro central:

```bash
$ git grep -ohE "claude-[a-z0-9.-]+" -- backend/app backend/scripts scripts | sort -u
claude-haiku-4-5              claude-opus-4-6        claude-sonnet-4-5
claude-haiku-4-5-20251001     claude-opus-4-7        claude-sonnet-4-5-20250929
claude-sonnet                 claude-opus-4-8        claude-sonnet-4-6
```

Unas fijadas con fecha y otras no, y `claude-sonnet` a secas **no es un identificador válido**:
una llamada con esa cadena falla en tiempo de ejecución.

**Lo que el detector de vacuidad no cubre.** `-m requires_db` selecciona 3.294 de 6.464 tests, el
51 %. Los otros 3.170 quedan fuera del método, y ahí también puede haber vacuidad —por ejemplo un
test que asevera sobre una lista vacía devuelta por un mock—. No se ha medido.

**`requires_db` está sobre-marcado.** En la muestra de 80, 45 tests piden el fixture `db` y no
lanzan ni una sentencia SQL; extrapolado, unos 168 de los 299. No es un defecto —esos tests son
legítimos— pero significa que `-m requires_db` arrastra a la base tests que no la necesitan.
Optimización pendiente, no corregida.

**Ningún cuestionario admite adjuntar un fichero.** Un cliente al que se le pregunta «¿tenéis
inventario de activos?» sólo puede contestar con texto: no puede adjuntar el inventario. El
sistema sí sabe guardar ficheros —hay adjuntos en evidencias (`evidence.fichero_path`), en el
chat (`workspace_chat_messages.adjunto_file_id`), en mensajería (`client_message_attachments`) y
en los artefactos de acompañamiento a auditoría—, pero la tabla de respuestas no tiene dónde
ponerlos:

```bash
# las columnas de una respuesta de cuestionario: no hay ninguna de fichero
$ psql -d fulkro -tAc "SELECT column_name FROM information_schema.columns \
    WHERE table_name='onboarding_responses';"
answered_at updated_at session_id id answer_value section question_id

# quién SÍ tiene adjuntos, para contrastar
$ psql -d fulkro -tAc "SELECT table_name||'.'||column_name FROM information_schema.columns \
    WHERE table_schema='public' AND (column_name LIKE '%adjunt%' OR column_name LIKE '%fichero%' \
    OR column_name LIKE '%attach%');"
```

**Cuántas preguntas son, medido.** 135 definiciones en los catálogos de código: 73 de simulacro
de auditoría (`m10_audit_sim`, una por medida del Anexo II), 18 de coaching (`m09_audit_prep`),
14 de los cuestionarios LMS (`docs/catalogs/lms_courses_v1.json`), 10 de materialidad de cambios
(`m28`), 10 de materialidad de conformidad (`m27`) y 10 de captura de dimensiones (`m16`). Ese es
el número que puedo reproducir con un comando sobre **este** repositorio:

```bash
$ python3 -c "
from backend.app.motors.m10_audit_sim.audit_questions import AUDIT_QUESTIONS
from backend.app.motors.m09_audit_prep.coaching import COACHING_QUESTIONS
from backend.app.motors.m28_change_governance.materiality_engine import IMPACT_QUESTIONS
from backend.app.motors.m27_conformity.conformity_service_paso5 import MATERIALITY_QUESTIONS
from backend.app.motors.m16_onboarding.dimensions_capture import CANONICAL_DIM_QUESTIONS_DEFINITIONS as D
import json; lms = json.load(open('docs/catalogs/lms_courses_v1.json'))
print(len(AUDIT_QUESTIONS), len(sum(COACHING_QUESTIONS.values(), [])), len(IMPACT_QUESTIONS),
      len(MATERIALITY_QUESTIONS), len(D))"
73 18 10 10 10
```

Las 73 del simulacro no son una lista escrita a mano: se derivan de la tabla autoritativa del
Anexo II y un `assert` en el import falla si sobra o falta alguna
(`audit_questions.py:762`), así que ese sumando no puede desalinearse en silencio.

Hubo una cifra de **1.077** circulando en una revisión. **Era de otro repositorio** —el zip
OSS—, no de éste. No es que no supiera reconstruirla: es que no se puede, porque mide otro
sujeto. Queda dicha y descartada para que nadie la vuelva a arrastrar.

Es una carencia real de producto, no una incorrección normativa: ninguna de esas preguntas
afirma nada falso. Por eso queda como frente abierto y no se arregló en la corrección normativa.

---

## Frentes abiertos

Inventario de lo que queda por hacer, cada uno con qué es y cómo se reproduce.
Está aquí porque un README que sólo cuenta lo que funciona no sirve para decidir
si merece la pena retomar el proyecto.

El origen es un recorrido del ciclo ENS completo por navegador, dos veces —BÁSICA
y MEDIA—, con verificación adversarial independiente de cada hallazgo: 50
incidencias, 44 confirmadas y 6 mal diagnosticadas. Las 11 bloqueantes se
cerraron; esto es el resto.

### Dependencias de entorno · los 44 fallos y los 5 errores, atribuidos

```bash
$ pytest backend/tests -q
44 failed, 6510 passed, 115 skipped, 5 errors      # árbol actual
45 failed, 6367 passed, 115 skipped, 5 errors      # 2c1e40f, antes de esta campaña
```

Ninguno de los 44 responde a un defecto del código. Los tres grupos se midieron
corriendo los mismos ficheros en los dos árboles, contra la misma base de datos:
salen **idénticos**, `22 failed · 195 passed · 5 errors` a los dos lados.

| grupo | cuántos | qué falta | señal |
|---|---:|---|---|
| Clave de cifrado | **25** | `FULKRO_MASTER_ENCRYPTION_KEY` | `RuntimeError: Encryption master key unavailable` |
| Puerto codificado | **16** | un PostgreSQL en `localhost:5433` | `connection to server at "localhost", port 5433 failed` |
| Sin agrupar | 3 | ver abajo | — |

**Clave de cifrado (25).** `core/encryption` (6), `m08_verification` (5),
`m16_onboarding` (9), `m20_workspace` (4) y `admin_settings` (1). Todo lo que
escribe una columna `EncryptedText` — mensajes del espacio de trabajo, credenciales
SSH, tokens OAuth, contraseña SMTP — necesita la clave maestra, y el entorno de
test no la trae.

**Puerto codificado (16).** `corpus/test_pdf_ingest.py` (11) y los 5 errores de
`m21_diagnosis/test_iso27001_coverage.py`, que abre su propia conexión:

```python
# backend/tests/motors/m21_diagnosis/test_iso27001_coverage.py:19
"postgresql://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro"
```

Es la misma clase de dependencia no declarada que tenían los dos tests de MinIO,
resuelta en su día parametrizando el destino y saltando con el motivo escrito
cuando no se alcanza. Aquí sigue abierta.

**Sin agrupar (3).** `test_legal_audit_score_100` (puntuación de auditoría legal),
`test_drift_summary_aggregates_events` (m28) y
`test_persist_report_falls_back_to_inline_when_desktop_unavailable`
(m_compliance_monitor). Fallan igual en los dos árboles.

Reproducción de la atribución:

```bash
git worktree add /tmp/base 2c1e40f
# los mismos ficheros, los dos árboles, la misma base de datos
pytest backend/tests/motors/m20_workspace backend/tests/corpus \
       backend/tests/motors/m21_diagnosis -q
```

### Un test que sólo falla cuando corre la batería entera

`backend/tests/auth/test_global_dep_whitelist.py::test_bloque_g_metrics_publico_sin_auth`
pasa en solitario y pasa con todo `backend/tests/auth`. Sólo falla dentro de la
batería completa, así que arrastra estado de algún test anterior. No he
conseguido atribuírselo a ningún cambio: pasa igual en la línea base y en el
árbol actual cuando se corre acotado.

```bash
pytest backend/tests/auth -q                    # 90 passed
pytest backend/tests -q | grep metrics_publico  # FAILED
```

Un test que depende del orden no mide lo que dice medir, y esta campaña ha ido
justo de eso.

### El commit borra el contexto RLS y el `refresh` posterior revienta · 3 endpoints

El contexto de inquilino se fija con variables de ámbito **transacción**
(`set_config(..., true)`). El `commit()` las borra. El `db.refresh()` que viene
después corre ya sin contexto, no ve su propia fila, y el endpoint responde 500
**con la operación ya guardada**. El usuario reintenta y duplica.

La huella está en la base del demo: un proyecto llamado `DUPLICADO-CLAUDE`,
creado dos veces por esta vía.

```bash
# reproducir · crear proyecto desde el diálogo "Nuevo proyecto" del admin
#   -> HTTP 500, y el proyecto existe:
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro \
  -c "SELECT nombre, count(*) FROM projects GROUP BY nombre HAVING count(*) > 1;"

# los tres sitios
grep -rn "await db.commit()" -A3 backend/app/api/v1/projects.py | grep -B2 refresh
```

### El resultado del simulacro de auditoría no se guarda · falta un `commit`

`backend/app/agents/dry_run_api.py:36-39` devuelve el resultado del servicio y
nunca llama a `db.commit()`. La ejecución se ve en pantalla y desaparece: el
histórico está siempre vacío, así que no se puede comparar una ejecución con la
anterior ni demostrar progreso a un auditor.

```bash
# ejecutar el dry-run desde /admin/projects/{id}/audit-dry-run y después:
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro \
  -c "SELECT count(*) FROM audit_dry_run_results;"   # no sube
```

### Las justificaciones de "no aplica" de la DdA son falsas · 12 de 13

La plantilla de justificación nunca menciona la dimensión que motiva la
exclusión, y en varios casos afirma que la medida no aplica **porque aplica**.
Son el texto que lee el auditor para aceptar una exclusión del Anexo II.

```bash
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -c \
  "SELECT justificacion_no_aplica FROM dda_entries
   WHERE aplicabilidad='no_aplica' AND justificacion_no_aplica IS NOT NULL LIMIT 5;"
```

### El acta E-012 en JSON se contradice consigo misma

`m01_categorization/api.py:1081-1098`: la tabla de tipos de información dice
`D=BAJO` y el resultado agregado del mismo documento dice otra cosa. El PDF y el
DOCX salen del generador corregido; el JSON tiene su propio camino de lectura,
que es el defecto que llevamos toda la auditoría persiguiendo.

```bash
curl -s -b cookies.txt \
  "$API/api/v1/categorization/systems/$SID/acta-e012.json" | jq '.result.dimensiones'
```

### Tres pantallas que no pueden arrancar lo que ellas mismas exigen

Hueco de interfaz, no de backend: el endpoint existe y funciona en los tres
casos, simplemente no hay nada que lo llame.

- **`/plan`** muestra un Gantt vacío y ninguna acción para generar el plan.
- **`/dossier`** es de sólo lectura y no ofrece crear el `AuditPreparationRun`
  que la propia página necesita para mostrar algo.
- **E-808, la Autoevaluación CCN-STIC 808**, obligatoria para cerrar BÁSICA, no
  tiene productor: nadie llama a `generate_document(template_codigo="E-808")` y
  el endpoint genérico no la rellena.

```bash
grep -rn "pda/generate\|runs\b.*categoria\|E-808" frontend/ | grep -v node_modules
```

### El mensaje de error de los contactos manda al sitio equivocado

Los contactos de cliente y los de proyecto son dos ámbitos distintos. Cuando
falta uno, el error no dice en cuál de las dos pestañas hay que crearlo, así que
el operador lo busca donde no está.

### Dos documentos firmables que se emiten fuera de la fábrica documental

La fábrica (`m06`) renderiza, calcula la huella, firma con Ed25519, registra la
fila en `documents` y sube copia durable. Quien renderiza por su cuenta se salta
las cinco cosas — y `documents` es exactamente lo que lee el generador del
expediente del auditor.

- **Adenda E-604** (`m14_contracts/adenda_generator.py`) · es firmable y **tiene
  plantilla en el catálogo**, así que es enchufable a la fábrica tal cual.
- **Acta de reunión E-005** (`m18_communication/minutes_service.py`) · también
  firmable (`POST /api/v1/minutes-signing/approve`), pero **no tiene plantilla**:
  "E-005 sin plantilla" consta en tres sitios de `m09`. Enchufarla exige crearla
  primero.

El guard congela esta línea base: un tercer camino rompe el build.

```bash
pytest backend/tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py
```

### Los 3 entregables de 28 que siguen sin salir

Con el generador cableado (P2), una pulsación lleva el proyecto BÁSICA de **6 de
28 a 25 de 28**. Los tres que quedan, y por qué:

**E-001 · fallo de la plantilla, no del motor.**

```
HTTP 500 · Failed to render DOCX /app/var/templates_docx/E-001.docx:
           None is undefined
```

Una variable que la plantilla usa sin guarda y que el contexto no trae. El panel
lo anota y sigue con los demás, así que no tumba la tanda.

**E-702 y E-703 · les falta una ejecución, no un dato.**

```
HTTP 422 · Missing required placeholders: score.score, run.categoria_ens,
           run.fecha_emision
```

Son los informes técnicos de verificación: piden el resultado de una ejecución
de auditoría (`run.*`, `score.*`), no datos del proyecto. Que no se generen sin
ella es lo correcto — un informe de verificación sin verificación detrás sería
un documento inventado. Lo que falta es engancharlos al auditor interno, que ya
existe (`POST /audit-prep/projects/{id}/internal-audit/run`).

```bash
curl -s -b cookies.txt -X POST -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' -d '{"template_codigo":"E-001","context":{}}' \
  "$API/api/v1/projects/$PID/documents/generate"
```

### El informe INES no cabe en `documents` · y es estructural

El informe anual del art. 32 es **por organización y por año**
(`organization_id`), no por proyecto. La tabla `documents` exige
`project_id NOT NULL`. Registrarlo obliga antes a decidir a qué proyecto
pertenece el informe de una organización que tiene varios — que es una decisión
de modelo, no un arreglo.

```bash
grep -n "ines_annual_docx" backend/app/motors/m27_conformity/api.py
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro \
  -c "\d documents" | grep project_id
```

## Cierre del proyecto

El proyecto cerró en septiembre de 2026 tras una campaña de corrección de 33
commits sobre el propio repositorio, con una regla única: un punto se cierra
cuando el código cambia y existe un test que falla en el commit anterior y pasa
en el nuevo, con las dos salidas pegadas al commit.

| | antes | después |
|---|---:|---:|
| Tests que pasan | 6.367 | **6.510** |
| Fallos atribuibles al código | — | **0** |
| Incidencias bloqueantes del ciclo ENS | 11 | **0** |
| Entregables del expediente · BÁSICA | 1 de 28 | **25 de 28** |

El informe de cierre —con el patrón dominante que se encontró, las nueve
autocorrecciones y la lección sobre la capa de verificación— está en
[`docs/INFORME_CIERRE_CAMPANA.md`](docs/INFORME_CIERRE_CAMPANA.md).

---

## Datos y licencias

El **código** está bajo [Apache-2.0](LICENSE).

El **contenido normativo de terceros incluido en el repositorio no está cubierto por esa licencia**
y conserva el régimen de su fuente.

El fixture de tests (`backend/tests/fixtures/corpus_seed.sql.gz`) incluye **solo fuentes de libre
redistribución**: el RD 311/2022 —texto del BOE, y el artículo 13 de la Ley de Propiedad
Intelectual excluye las disposiciones legales y sus textos oficiales de la propiedad intelectual—
más legislación de la Unión Europea (RGPD, DORA, NIS2, eIDAS). Son 1.031 chunks de 1.977.

Los chunks de las guías **CCN-STIC** y de la **AEPD** no se versionan: los genera el pipeline de
ingesta en local. Las guías CCN-STIC no son disposiciones legales, y la guía de la AEPD está
publicada bajo CC BY-NC-SA 4.0, cuya cláusula NonCommercial es incompatible con Apache-2.0.

Es una decisión de ingeniería antes que un trámite: el fixture pesa la mitad, cualquiera puede
clonarlo y ejecutarlo sin heredar material que no es suyo para redistribuir, y el corpus completo
sigue siendo reproducible en local para quien tenga las fuentes.

**Cerrado el 2026-09-10:** `docs/catalogs/ens_measures_catalog_v1.yaml` contenía párrafos copiados
literalmente de la CCN-STIC 804. Las descripciones están **reescritas con lenguaje propio**; la
cabecera ya no atribuye las descripciones a la guía, y `fuente_oficial` sigue apuntando a la
sección concreta para no perder la trazabilidad. Lo vigila un umbral medible:

```bash
$ python3 scripts/verificar_catalogo_sin_copia_literal.py --ref 72d98e5
Referencia: 72d98e5  (79 medidas)
Trabajo:    árbol actual (73 medidas)
Medidas comparadas:        73
Coincidencia máxima:       7 palabras consecutivas (en mp.if.2)
  texto de esa racha:      "relacion de personas autorizadas y un sistema"
Medidas en el umbral o por encima (8+): 0
```

Dos cosas de ese bloque, porque hasta el 2026-09-11 decía otra cosa. **Eran 79 medidas y hoy son
73**: el commit `2276d99` eliminó seis códigos que no existen en el RD 311/2022 (venían de la
CCN-STIC 804 v2017, basada en el RD 3/2010 derogado). Y **el comando lleva `--ref`**: sin él el
script se niega a medir y avisa de que comparar HEAD consigo mismo da copia total. La versión
anterior de este README pegaba una salida que ya no se producía — exactamente el defecto que este
documento dice perseguir.

Ese script compara contra la versión anterior en git y falla si alguna descripción vuelve a
compartir 8 palabras seguidas con el original. `backend/tests/scripts/test_catalogo_sin_copia_literal.py`
lo cubre en CI sin necesitar git. **Lo que ninguno de los dos verifica** es que la descripción sea
normativamente exacta: eso lo revisa una persona.

### Procedencia del corpus: qué es norma y qué es resumen nuestro

El corpus mezcla dos cosas y **tiene que decir cuál es cuál**, porque el copiloto cita sus fuentes
y una cita normativa vale lo que valga su procedencia.

| fuente | qué es | editor declarado | de dónde sale el texto |
|---|---|---|---|
| `RD_311_2022` | **norma oficial** (BOE-A-2022-7191) | BOE · Ministerio | HTML consolidado del BOE, descargado a `var/corpus/` |
| `UE-DORA`, `UE-NIS2`, `UE-RGPD`, `UE-EIDAS` | **norma oficial** | Parlamento Europeo y Consejo | textos oficiales, descargados |
| Guías `CCN-STIC-800…814` | **guías del CCN** | CCN | los PDF que el operador descarga a `var/corpus/` (`git ls-files \| grep stic_serie_800` → 0) |
| `FULKRO_RESUMEN_CONFORMIDAD_ENS` | **resumen propio** | FULKRO | `backend/app/corpus/data/`, escrito aquí |

**Corregido el 2026-09-10.** Ese último era `CCN_STIC_809.md`: 103 líneas y 14,7 KB escritas en
este repositorio, tituladas como la guía CCN-STIC-809 y subtituladas como si las publicase el
Centro Criptológico Nacional, e ingeridas con `publisher="Centro Criptológico Nacional (CCN)"` y
la URL oficial como origen del texto. La guía real son decenas de páginas.

**No era una copia: era un resumen que se presentaba como el original.** El problema no es de
derechos de copia, es de **procedencia**: el buscador del copiloto podía devolver un fragmento de
ese resumen citando al CCN, con un texto que puede no estar en su guía. Es el mismo defecto que
[ADR-059](docs/adr/ADR-059-llamada-llm-fallida-no-es-exito.md) —fabricar algo y sellarlo como
auténtico— una capa más abajo. Ahora el título dice lo que es, el editor es FULKRO, la URL oficial
figura como **referencia** y no como origen, y los fragmentos van etiquetados
`seccion="resumen_secundario"` para que la recuperación distinga norma de resumen.

Lo que impide que vuelva a pasar con la guía siguiente es un test, no la limpieza:
`backend/tests/corpus/test_procedencia_corpus.py` falla si un módulo del corpus ingiere un texto
versionado bajo `backend/app/corpus/data/` **y** declara como editor a un tercero, o pone una URL
ajena como origen, o si el propio fichero se firma como obra de otro. Lleva lista blanca explícita,
hoy **vacía**, y comentada con lo que entraría en ella legítimamente y lo que no. Verificado en
rojo contra el estado anterior: **3 de las reglas saltan**; contra el actual, las 5 pasan.

No necesita base de datos, así que corre en el job `test` de CI.

### Terceros que requieren atribución

- **shadcn/ui** (MIT © 2023 shadcn) — 28 componentes en `frontend/components/ui/`
- **MITRE ATT&CK** — `backend/app/motors/m08_verification/mitre_mapper.py`
- **MAGERIT v3.0 Libro II** (MINHAP, reutilizable citando fuente) — `docs/catalogs/magerit_libro2_catalog_v1.yaml`

---

## Estructura

**Para el mapa de piezas y los límites entre ellas, con el diagrama del sistema y
los enlaces a las decisiones que lo justifican: [`ARCHITECTURE.md`](ARCHITECTURE.md)
— una página.** El índice completo de decisiones está en
[`docs/adr/README.md`](docs/adr/README.md).

```
backend/          FastAPI · 46 directorios de motor en app/motors/ · 269 migraciones
frontend/         Next.js 14 · App Router · 5 grupos de ruta:
                  (admin) (client-portal) (legal) (portal) (public)
docs/             catálogos que lee el arranque (MAGERIT, precios, ENS) y especificaciones
infra/docker/     init SQL de extensiones, funciones RLS y roles · Dockerfile de producción
scripts/          utilidades de operación y el detector de verdad vacua
landing/          sitio estático del proyecto, archivado
```
