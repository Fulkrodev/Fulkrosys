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

Ocho de cada diez endpoints protegidos exigen ser **el** administrador, en singular.

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

**Estado: no hay un arranque de un solo comando.** No existe `Makefile` en el repositorio:

```bash
$ ls Makefile
ls: cannot access 'Makefile': No such file or directory
```

Lo que sí funciona hoy, medido:

```bash
# 1. Entorno e instalación
python3 -m venv .venv && source .venv/bin/activate
cd backend && pip install -e ".[dev]" && cd ..

# 2. Infraestructura. Para arrancar la API bastan estos tres; clamav,
#    celery-worker y celery-beat son los otros tres de núcleo y hacen
#    falta para antivirus y tareas en segundo plano, no para servir.
docker compose up -d postgres redis minio

# 3. Base de datos: el orden importa y es inviolable.
#    postgres se expone en el 5433 (docker-compose.yml:13), no en el 5432.
export PGPASSWORD=changeme
PSQL="psql -h localhost -p 5433 -U fulkro -d fulkro"
$PSQL -f infra/docker/init-extensions.sql   # pgvector
$PSQL -f infra/docker/init-functions.sql    # current_project_id() y current_client_id(), que usan las políticas RLS
$PSQL -f infra/docker/init-roles.sql        # fulkro_app, fulkro_app_bypassrls, fulkro_migrate
cd backend && alembic upgrade head && cd ..

# 4. Claves de firma Ed25519 (el arranque las exige)
python scripts/generate_dev_signing_keys.py   # dentro del venv activado

# 5. Arrancar
uvicorn backend.app.main:app --env-file .env --port 8000
# OpenAPI en http://localhost:8000/docs
```

`docker-compose.yml` declara 22 servicios, pero **16 son de pentesting** y no hacen falta para
levantar la plataforma:

```bash
$ python3 -c "import yaml; print(len(yaml.safe_load(open('docker-compose.yml'))['services']))"
22
```

Los seis de núcleo son `postgres`, `redis`, `minio`, `clamav`, `celery-worker` y `celery-beat`.
Los tres del paso 2 son los que la API necesita para responder; los otros tres cubren el antivirus
de las evidencias y las tareas en segundo plano.

**Frentes abiertos de arranque**, verificados: hay rutas absolutas a la máquina de su autor que
rompen el pipeline de corpus en cualquier otro sitio (ver *Limitaciones*), y `.env.example` no
trae las cuatro variables que `backend/app/startup_checks.py` exige, así que copiarlo no basta.

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

Ese 1.201 sale de **introspeccionar el objeto `app` en ejecución**, no de contar decoradores en el
fuente. El conteo estático difiere porque hay routers incluidos varias veces bajo prefijos
distintos.

### Tests: lo que se puede afirmar y lo que no

Esta tabla es deliberadamente incómoda, y es la cifra honesta.

| | | cómo se mide |
|---|---:|---|
| Recolectables | **6.464** | `pytest backend/tests/ --collect-only -q \| tail -1` |
| Que requieren base de datos | **3.294** | `pytest backend/tests/ -m requires_db --collect-only -q \| tail -1` |
| Verificados por el CI | **0** | el job `test` de `ci.yml:60` está condicionado a `workflow_dispatch` y nunca se ha disparado |
| Última cifra local publicada | 5.978 | `ci.yml:56`, de una ejecución del 9 de junio de 2026 |

**Esa cifra de 5.978 no reproduce hoy y no aparece en ninguna otra parte del repositorio.** Está
escrita en un comentario del CI sin el comando que la produzca. Se conserva aquí como lo que es:
una afirmación de sus autores, no una medición.

No se escribe *"5.978 tests en verde"* porque nadie puede comprobarlo.

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

### 2. El CI estaba en verde sin comprobar casi nada · ABIERTO

- El job `test` está colgado de `workflow_dispatch` (`ci.yml:60`) y **nunca se ha ejecutado**.
- `mypy` lleva `continue-on-error: true` (`ci.yml:35`), así que no bloquea nada.
- El job `safety` revienta, no escribe informe, y su parser «tolerante» convierte eso en éxito.
- **No hay branch protection ni rulesets**, así que los comentarios «block merge» de tres YAML son
  ficción: no hay nada que bloquear.

Un CI en verde que no comprueba nada es peor que no tener CI, porque miente con autoridad.
**Sigue abierto.**

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

El registro de agentes declara 32 identificadores, pero solo 13 están activos:

```bash
$ grep -oE '"(activo|scaffolding|scaffolding_covered_by_engine|deprecated|externalized_to_motor)"' \
    backend/app/agents/registry.py | sort | uniq -c
     13 "activo"
     14 "deprecated"
      2 "externalized_to_motor"
      1 "scaffolding"
      2 "scaffolding_covered_by_engine"
```

**13 activos frente a 12 clases implementadas: cuadra.** No falta ningún agente.

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

**El pipeline de corpus no arranca fuera de la máquina de su autor.** Hay 34 rutas absolutas
`/home/usuario` en 26 ficheros versionados, 6 de ellas en `backend/app/`:

```bash
$ git grep -o "/home/usuario" -- . ':!README.md' | wc -l
34
$ git grep -l "/home/usuario" -- . ':!README.md' | wc -l
26
```

(Se excluye este README, que menciona la ruta cuatro veces para documentar el problema.
Sin excluirlo salen 38 en 27 ficheros, y esa cifra mediría el texto que estás leyendo.)

Un caso típico: `backend/app/corpus/ccn_stic_ingest.py:26` hace
`load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))`.

**La evaluación de agentes cubre uno de doce.** Hay un arnés completo de 2.428 líneas en
`backend/app/motors/m_observability/`, y un solo dataset, con 10 ejemplos:

```bash
$ ls -d docs/catalogs/golden_datasets/*/ | xargs -n1 basename
deliverable_text_auditor
$ python3 -c "import json; print(len(json.load(open('docs/catalogs/golden_datasets/deliverable_text_auditor/v1.json'))['entries']))"
10
```

Frente a doce clases de agente implementadas:

```bash
$ grep -rhoE "^class [A-Za-z0-9_]*Agent[A-Za-z0-9_]*" backend/app/agents/*.py \
    | grep -vE "Error$|^class AgentBase$" | sort -u | wc -l
12
```

La infraestructura de evaluación está construida; los datos para usarla, no. Es el hueco más
grande del proyecto: sin datasets, no hay forma de saber si un cambio de prompt mejora o empeora.

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

**Frente abierto, y se dice:** `docs/catalogs/ens_measures_catalog_v1.yaml` declara en su cabecera
«descripciones: CCN-STIC 804 v2017» y contiene párrafos copiados de esa guía en 79 medidas. Sigue
en el repositorio y hay que reescribirlo.

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
