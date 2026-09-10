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
| Recolectables | **6.470** | `pytest backend/tests/ --collect-only -q \| tail -1` |
| Que requieren base de datos | **3.294** | `pytest backend/tests/ -m requires_db --collect-only -q \| tail -1` |
| **Que el CI ejecuta de verdad** | **3.153** · el 48,7 % | el propio job lo cuenta y lo publica en su resumen |
| Última cifra local publicada | 5.978 | `ci.yml:56`, de una ejecución del 9 de junio de 2026 |

Los 6.470 recolectables son de ahora: hasta este cambio la recolección **abortaba con código 2** en
cualquier entorno limpio, porque `bs4`, `respx` y `pypdf` se importaban sin estar declaradas. En
máquina limpia daba `6383 tests collected, 7 errors`, sin llegar a ejecutar ni uno.

Los 3.153 que corren en CI son los que no necesitan una base sembrada. Los 3.294 marcados
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
- **Corre 3.153 de 6.470 tests, el 48,7 %**, y el propio job lo publica en su resumen contándolo en
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
literalmente de la CCN-STIC 804 en las 79 medidas. Las 79 descripciones están **reescritas con
lenguaje propio**; la cabecera ya no atribuye las descripciones a la guía, y `fuente_oficial`
sigue apuntando a la sección concreta para no perder la trazabilidad. Lo vigila un umbral medible:

```bash
$ python3 scripts/verificar_catalogo_sin_copia_literal.py
Medidas comparadas:        79
Coincidencia máxima:       7 palabras consecutivas (en mp.if.2)
Medidas en el umbral o por encima (8+): 0
RESULTADO: VERDE
```

Ese script compara contra la versión anterior en git y falla si alguna descripción vuelve a
compartir 8 palabras seguidas con el original. `backend/tests/scripts/test_catalogo_sin_copia_literal.py`
lo cubre en CI sin necesitar git. **Lo que ninguno de los dos verifica** es que la descripción sea
normativamente exacta: eso lo revisa una persona.

**Frente abierto, y se dice:** `backend/app/corpus/data/CCN_STIC_809.md` es el mismo problema un
nivel peor. Son 103 líneas que **dicen ser la guía** («# CCN-STIC-809 — Declaración, Certificación
y Aprobación Provisional… Centro Criptológico Nacional»), con 17 párrafos de más de 400 caracteres,
y se ingestan declarando al CCN como editor. Sigue en el repositorio y hay que retirarlo o
reescribirlo.

### Terceros que requieren atribución

- **shadcn/ui** (MIT © 2023 shadcn) — 28 componentes en `frontend/components/ui/`
- **MITRE ATT&CK** — `backend/app/motors/m08_verification/mitre_mapper.py`
- **MAGERIT v3.0 Libro II** (MINHAP, reutilizable citando fuente) — `docs/catalogs/magerit_libro2_catalog_v1.yaml`

---

## Estructura

```
backend/          FastAPI · 44 motores en app/motors/ · 268 migraciones Alembic
frontend/         Next.js 14 · App Router · 5 grupos de ruta:
                  (admin) (client-portal) (legal) (portal) (public)
docs/             catálogos que lee el arranque (MAGERIT, precios, ENS) y especificaciones
infra/docker/     init SQL de extensiones, funciones RLS y roles · Dockerfile de producción
scripts/          utilidades de operación y el detector de verdad vacua
landing/          sitio estático del proyecto, archivado
```
