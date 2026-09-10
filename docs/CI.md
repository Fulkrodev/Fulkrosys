# Integración continua: qué corre, qué protege de verdad y qué es decorativo

Todas las cifras de este documento están medidas el **2026-09-10** sobre el
repositorio público `Fulkrodev/Fulkrosys`, rama `main`. Cada afirmación lleva
pegado el comando que la produce. Donde no se ha medido, pone **no medido** y por
qué.

**Aviso de simultaneidad.** Lo medido corresponde al commit `c8ece1c`. Mientras
se escribía este documento, otro trabajo en curso estaba reescribiendo `ci.yml` y
`security-scan.yml` y había **borrado `deploy.yml`** del árbol de trabajo
(`git status --porcelain` → ` D .github/workflows/deploy.yml`, más
`.github/scripts/safety_gate.py` y `.github/mypy-clean-modules.txt` sin seguimiento).
La sección 2 describe lo que hay en `c8ece1c`; cuando esos cambios se consoliden
hay que volver a medirla, y hay que reconfirmar los nombres literales de los
checks de la sección 6 antes de escribirlos en la protección de rama.

Aviso general: los comandos con `grep` de este documento usan `command grep`
a propósito. El `grep` del entorno de desarrollo es una función que llama a
`ugrep` con `--ignore-files` y respeta `.gitignore`, así que omite en silencio
ficheros versionados (medido: 27 resultados con `grep` frente a 28 con
`command grep` sobre la misma búsqueda).

---

## 1. Mapa rápido

| Workflow | Cuándo corre | ¿Puede tumbar algo? | Veredicto |
|---|---|---|---|
| `ci.yml` | push y PR a `main`, y a mano | Sí, `lint` y `frontend-typecheck` | Parcialmente decorativo: `typecheck` no comprueba nada y `test`/`playwright` no se han ejecutado nunca |
| `security-scan.yml` | push y PR a `main`, lunes 06:00 UTC, y a mano | Sí, `bandit` y `npm audit` | `safety` es decorativo |
| `deploy.yml` | push a `main` y a mano | Sí, `gate` y `migrations` | Despliega a un servidor que ya no existe; el gate de migraciones tiene un agujero. **Borrado del árbol de trabajo por otro trabajo en curso** |
| `admin-polish-empirical.yml` | push y PR a `main` tocando `frontend/**`, y a mano | Sí | Es el único sitio del repo con una receta de base de datos que funciona en CI |
| `evals.yml` | push y PR a `main`, lunes 07:00 UTC, y a mano | Sí, `evals-arnes` siempre; `evals-llm` sólo cuando hay clave (si no, queda SALTADO, no verde) | Ver sección 4 |
| `publish-image.yml` (nuevo) | push a `main` y a etiquetas `v*`, PR que toquen la imagen, y a mano | Sí, si el build falla no hay imagen | Ver sección 5 |

Medido:

```
$ ls .github/workflows/
admin-polish-empirical.yml
ci.yml
evals.yml
publish-image.yml
security-scan.yml
```

`deploy.yml` no aparece porque otro trabajo en curso lo ha borrado del árbol de
trabajo; sigue existiendo en el commit `c8ece1c`, que es lo que describe la
sección 2.3.

---

## 2. Estado real de los workflows que ya existían

### 2.1 `ci.yml`

Nombres literales de los checks, tal como aparecen en la interfaz (son los ids de
los jobs, porque ninguno declara `name:`): `lint`, `typecheck`,
`frontend-typecheck`, `test`, `playwright`.

**`test` y `playwright` no se han ejecutado nunca.** Ambos llevan
`if: github.event_name == 'workflow_dispatch'` (`ci.yml:60` y `ci.yml:99`) y las
121 ejecuciones registradas son de tipo `push`:

```
$ curl -s "https://api.github.com/repos/Fulkrodev/Fulkrosys/actions/workflows/ci.yml/runs?per_page=100" \
  | python3 -c "import json,sys,collections; d=json.load(sys.stdin); print('total:', d['total_count'], '| descargados:', len(d['workflow_runs']), dict(collections.Counter(r['event'] for r in d['workflow_runs'])))"
total: 121 | descargados: 100 {'push': 100}

$ curl -s "https://api.github.com/repos/Fulkrodev/Fulkrosys/actions/workflows/ci.yml/runs?per_page=100&page=2" \
  | python3 -c "import json,sys,collections; d=json.load(sys.stdin); print(len(d['workflow_runs']), dict(collections.Counter(r['event'] for r in d['workflow_runs'])))"
21 {'push': 21}
```

Y en la última ejecución se ven saltados:

```
$ curl -s "https://api.github.com/repos/Fulkrodev/Fulkrosys/actions/runs/34420800539/jobs" | ...
lint                   failure
frontend-typecheck     success
typecheck              success
test                   skipped
playwright             skipped
```

**Quitarle el `if` a `test` no lo arreglaría.** El job levanta un `pgvector`
pelado y no ejecuta ni roles, ni `alembic upgrade head`, ni el seed: la base de
datos está vacía. La receta que sí funciona lleva 41 ejecuciones verdes y vive en
`admin-polish-empirical.yml:106-136` (extensiones `uuid-ossp`, `pgcrypto` y
`vector` — sin AGE ni pgaudit —, `init-functions.sql`, `init-roles.sql`,
`alembic upgrade head` como `fulkro_migrate`, y los `GRANT`).

```
$ curl -s ".../workflows/admin-polish-empirical.yml/runs?per_page=100" | ...
total_count: 46 ... conclusiones: {'success': 41, 'failure': 5}
```

**`typecheck` no comprueba nada.** Lleva `continue-on-error: true`
(`ci.yml:35`), y por debajo mypy revienta con exit 2 (`Source file found twice
under different module names`) por el doble convenio `app.*` frente a
`backend.app.*`. El check sale verde igualmente: en la ejecución 34420800539
`typecheck -> success`. Ejecutado desde `backend/` para esquivar el crash, mypy
da **515 errores en 212 ficheros de 1056** (medición previa de la auditoría; no
re-ejecutada aquí porque `pip install -e backend[dev]` no completa en esta
máquina, ver sección 7).

**`main` está en rojo ahora mismo**, y no por algo cosmético: `lint` falla por un
`F811` real, el hook `pytest_collection_modifyitems` está definido dos veces en
`backend/tests/conftest.py` (líneas 121 y 436), y la segunda definición tapa a la
primera, matando el salto de los tests de LLM.

```
$ curl -s ".../workflows/ci.yml/runs?per_page=3" | ...
2fe34622 push completed failure 2026-09-10T00:19:28Z
0a73baf7 push completed success 2026-09-09T18:42:04Z
```

### 2.2 `security-scan.yml`

Nombres literales de los checks: `bandit · Python SAST`,
`safety · Python dep vulnerabilities`, `npm audit · Node dep vulnerabilities`.

`bandit` y `npm audit` fallan bien. **`safety` es decorativo**: la llamada acaba
en `|| true` (`security-scan.yml:105`) y el filtro que la sigue tiene
`except Exception: ... sys.exit(0)` (`security-scan.yml:111-115`), de modo que
devuelve éxito si el fichero no existe, si el JSON está corrupto o si `safety`
cambia el formato de salida. El propio comentario del workflow lo admite: «el
gate duro es bandit + npm».

### 2.3 `deploy.yml`

**Este fichero está borrado en el árbol de trabajo** por otro trabajo en curso
(`git status --porcelain` → ` D .github/workflows/deploy.yml`). Lo que sigue
describe lo que hay en el commit `c8ece1c` y queda aquí como constancia de por
qué merecía irse.

Nombres literales de los checks: `gate`, `migrations`, `deploy`.

Despliega por SSH a un Hetzner **que se borró el 9 de septiembre**. El job
`deploy` no falla cuando faltan los secretos porque hace `exit 0` explícito
(`deploy.yml:85-88`), y eso está bien señalizado con un `::notice::`.

El agujero real está en `migrations` (`deploy.yml:69-73`):

```bash
heads="$(python -m alembic heads 2>&1 || true)"
n="$(echo "$heads" | grep -c '(head)' || true)"
if [ "${n:-0}" -ge 2 ]; then ... exit 1; fi
```

Si `alembic heads` revienta, `|| true` se traga el error, `grep -c` cuenta 0 y el
gate pasa. Es decir: el gate detecta dos heads, pero no detecta que Alembic ni
siquiera arranque.

Dato relacionado, medido por AST en la auditoría previa: hay **268 revisiones y
un solo head** (`provider_c002_generado_status_001`). La expresión regular
ingenua da 4 heads y es falsa, porque hay `down_revision` en tupla multilínea. No
hay deuda de multi-head.

### 2.4 `admin-polish-empirical.yml`

Nombres literales de los checks:
`Admin Polish 75 specs (PROBE + P1 + P2 + P3)`,
`Cliente Polish 10 pages (dashboard + 9 core)`,
`Auditor Portal Polish 12 pages (sections + annotations + gaps + report)`.

Sólo se dispara si el PR toca `frontend/**` o el propio workflow. Por eso **no
puede marcarse como check obligatorio**: un check obligatorio que no se dispara
en todos los PR deja el merge bloqueado para siempre esperando un estado que
nunca llega.

---

## 3. Los comentarios «block merge» de los YAML son ficción

Hoy la rama `main` **no está protegida**:

```
$ curl -s https://api.github.com/repos/Fulkrodev/Fulkrosys/branches/main \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['protected']); print(d['protection'])"
False
{'enabled': False, 'required_status_checks': {'enforcement_level': 'off', 'contexts': [], 'checks': []}}
```

Ningún check bloquea ningún merge. Cualquiera con permiso de escritura puede
empujar directamente a `main` con todo en rojo, y de hecho el último commit de
`origin/main` tiene `ci.yml` en rojo. Los pasos para arreglarlo están en la
sección 6.

---

## 4. Evaluaciones de agentes como gate (`evals.yml`)

### 4.1 La cobertura real es 3 de 13 (bloque D · D2)

```
$ command grep -rn "(AgentBase)" backend/app --include=*.py | wc -l
13
$ find docs/catalogs/golden_datasets/ -name '*.json' | wc -l
4
```

**4 datasets, 3 clases de agente.** La diferencia no es un descuido: el cuarto,
`deliverable_text_auditor`, mide una *capability*, no una clase de agente. Cada
uno con 10 entradas curadas: **40 entradas en total**.

Hasta el 2026-09-10 esta sección decía «1 de 13», y era **generoso con la
verdad**: contaba esa capability como si fuera un agente. La cobertura de clases
de agente era **0**. Ahora son tres —`agent_27_clasificador`,
`agent_18_reunion` y `agent_06_contratos`—, elegidos porque su salida es
estructura verificable sin juicio (códigos de un catálogo cerrado, enumerados,
intervalos, recuentos). Los que producen prosa siguen sin dataset a propósito.

Las otras diez clases no tienen evaluación de ninguna clase. No hay número que
enseñar sobre ellas, ni bueno ni malo.

**Y lo que este 3 de 13 NO dice**: ninguno de los cuatro tiene todavía una tasa
de aciertos real. El gate contra el modelo necesita `ANTHROPIC_API_KEY` y no se
ha ejecutado nunca. Todo lo verde de `evals-arnes` mide el arnés y el cableado,
no al modelo; los umbrales de 0,80 son los que declara cada dataset, no una
medición calibrada. La primera ejecución real puede salir por debajo, y si sale,
lo primero que hay que revisar son las bandas de curación, no el modelo.

### 4.2 El CLI del arnés no sirve como gate

Este es el hallazgo central de la tarea, y está medido. El arnés
(`backend/app/motors/m_observability/`, 2.428 líneas según
`wc -l`) tiene un runner por línea de comandos, pero **ese runner no evalúa nada
ni con clave ni sin ella**, porque nunca cablea el `actual_provider`.

Sin `ANTHROPIC_API_KEY`, declara el 100% habiendo evaluado cero entradas:

```
$ python -m backend.app.motors.m_observability.eval_runner \
    --agent deliverable_text_auditor --version v1 --format json
{"total_entries": 0, "entries_in_dataset": 10, "passed": 0, "failed": 0,
 "pass_rate": 1.0, "severity": "ok", "entry_results": []}
$ echo $?
0
```

Una tasa de aciertos sobre un denominador vacío vale 1.0 por convenio. Un gate
que mirase ese `exit 0` sería **vacuamente verdadero**: pasaría con el dataset
entero saltado.

Con la clave presente (basta una falsa, no llega a llamar a la API) hace lo
contrario, y tampoco mide nada:

```
$ ANTHROPIC_API_KEY=dummy python -m backend.app.motors.m_observability.eval_runner \
    --agent deliverable_text_auditor --format json
... "diff_summary": "structure_check failed · actual type=NoneType" (x10)
$ echo $?
2
```

La causa está en `eval_runner.py`: el CLI llama a `run_eval()` sin
`actual_provider` y sin importar el paquete `evaluators`. El único sitio del
repositorio que sí conecta la capability real es
`golden_eval_runs_service.execute_eval_run_sync`, que exige una sesión de base de
datos y una fila en `golden_eval_runs`.

Por eso `evals.yml` **no usa ese CLI**: replica esa misma conexión
(`deliverable_text_auditor_capability.audit_deliverable_sync` como
`actual_provider`) sin base de datos. Es duplicación consciente, y el arreglo
correcto es que el CLI acepte cablear el proveedor; está anotado como petición al
propietario de `eval_runner.py`.

### 4.3 Los dos gates y qué significa cada verde

**`evals-arnes`** (determinista, sin red ni clave). Corre siempre y puede tumbar
el build. No evalúa ningún agente: comprueba que el arnés sigue siendo usable.
Seis comprobaciones, medidas en local:

El script vive embebido en el propio job (para no crear ficheros de los que este
trabajo no es propietario). Para ejecutarlo en local hay que extraerlo del YAML,
que es exactamente lo que se hizo para medir:

```
$ python - <<'EX'
import yaml, pathlib
d = yaml.safe_load(open('.github/workflows/evals.yml'))
for st in d['jobs']['evals-arnes']['steps']:
    r = st.get('run', '')
    if "python - <<'PY'" in r:
        cuerpo = r.split("python - <<'PY'\n", 1)[1].rsplit("PY\n", 1)[0]
        pathlib.Path('/tmp/evals_arnes.py').write_text(cuerpo, encoding='utf-8')
EX
$ PYTHONPATH="$PWD" python /tmp/evals_arnes.py
OK    · datasets descubiertos = 1 (mínimo 1): [('deliverable_text_auditor', 'v1')]
OK    · deliverable_text_auditor/v1: entradas curadas = 10 (esperadas >= 10)
OK    · deliverable_text_auditor/v1: pass_rate_warn_below del JSON = 0.8 == min_pass_rate de la política = 0.8
OK    · deliverable_text_auditor/v1: pass_rate_alert_below del JSON = 0.6 == pass_rate_alerta de la política = 0.6
OK    · deliverable_text_auditor/v1: evaluador registrado para 'deliverable_text_auditor' (registrados: ['deliverable_text_auditor'])
OK    · deliverable_text_auditor/v1: auto-consistencia dataset<->evaluador 10/10

resumen: 6/6 comprobaciones OK
$ echo $?
0
```

La sexta comprobación es la interesante: le devuelve al evaluador la salida que
el propio dataset declara como esperada. Si con eso no aprueba, es que dataset y
evaluador se han separado y el gate del LLM estaría midiendo contra un baremo
imposible.

Y no es un gate vacuo. Mutando el fichero de umbrales (25 entradas exigidas y
tasa mínima 0,90) falla, como debe:

```
FALLO · deliverable_text_auditor/v1: entradas curadas = 10 (esperadas >= 25)
FALLO · deliverable_text_auditor/v1: pass_rate_warn_below del JSON = 0.8 == min_pass_rate de la política = 0.9
resumen: 4/6 comprobaciones OK
$ echo $?
1
```

**`evals-llm`** (evaluación real). Necesita el secreto `ANTHROPIC_API_KEY`,
porque la capability bajo prueba llama al modelo: **el modelo es lo que se mide**.

- Si el secreto **no está**: el job queda **SALTADO** (icono gris), no verde.
  Quien decide es un tercer job de tres segundos, `hay-clave`, cuya única salida
  es un booleano; `evals-llm` lleva ese booleano en un `if:` **de nivel de job**.

  Hasta el 2026-09-10 este job terminaba en VERDE escribiendo
  `EVALUACIÓN NO EJECUTADA` en el resumen. El texto era honesto y el icono decía
  lo contrario, **y el icono es lo que se lee**: en la lista de checks de un PR
  se ven iconos, no resúmenes. Se cambió en el bloque D (D6).

  El `if` tiene que ser de nivel de job porque un `if` de paso deja el job en
  verde igualmente. Y hace falta el job intermedio porque el contexto `secrets`
  **no se puede leer** en `jobs.<id>.if` (sólo `github`, `needs`, `vars` e
  `inputs`); un paso normal sí lo lee, y por eso `hay-clave` lo traduce a una
  salida que el `if` sí puede consultar.

  Para convertir la ausencia de clave en **fallo** en vez de en salto, crear la
  variable de repositorio `FULKRO_EVALS_REQUIRED = true` (Settings → Secrets and
  variables → Actions → pestaña Variables). Con esa variable el job arranca y
  falla en su primer paso, con el motivo escrito en el resumen.

  Los tres casos están probados en local, extrayendo el paso del YAML y
  ejecutándolo con `bash`:

  ```
  $ docker run --rm -v "$PWD:/w" -w /w fulkro/backend:test python -c \
      "import yaml;print(yaml.safe_load(open('.github/workflows/evals.yml'))['jobs']['hay-clave']['steps'][0]['run'])" \
      > /tmp/paso.sh
  $ ANTHROPIC_API_KEY="" EXIGIDA=""     GITHUB_OUTPUT=/tmp/o bash /tmp/paso.sh; cat /tmp/o
  presente=false      # -> evals-llm SALTADO
  $ ANTHROPIC_API_KEY="" EXIGIDA=true   GITHUB_OUTPUT=/tmp/o bash /tmp/paso.sh; cat /tmp/o
  presente=false      # -> evals-llm arranca y falla (::warning:: emitido)
  $ ANTHROPIC_API_KEY="sk-x" EXIGIDA="" GITHUB_OUTPUT=/tmp/o bash /tmp/paso.sh; cat /tmp/o
  presente=true       # -> evals-llm evalua de verdad
  ```
- Si el secreto **está**: ejecuta las 10 entradas contra el modelo y aplica dos
  criterios, ambos definidos en `.github/evals-threshold.yml`:
  1. `min_entradas_evaluadas: 10` — el control anti-verde-vacuo. Si se evalúan
     menos de 10, falla aunque la tasa de aciertos salga 100%.
  2. `min_pass_rate: 0.80` — el mismo 0,8 que el dataset declara en
     `regression_thresholds.pass_rate_warn_below`. Con 10 entradas, tolera
     exactamente 2 fallos.

Los tres escenarios de la lógica de decisión están probados en local con un
proveedor sustituido, sin llamar a la API:

```
modo=perfecto       entradas evaluadas 10, aciertos 100%   -> exit 0
modo=cuatro_mal     entradas evaluadas 10, aciertos 60%    -> exit 1
modo=sin_respuesta  entradas evaluadas 0, saltadas 10      -> exit 1
```

Qué pasa cuando se roza el umbral: `pass_rate == 0.80` **pasa** (la comparación
es `>=`). Rozarlo no es una victoria. Con 10 entradas cada una vale 10 puntos, así
que un solo caso nuevo mal curado mueve el resultado un 10%: un verde por los
pelos hay que mirarlo a mano antes de fusionar. La justificación completa de cada
número, incluida la razón de que no haya reintentos (temperatura 0.0, R3), está
escrita dentro de `.github/evals-threshold.yml`.

**Coste**: 10 llamadas a Sonnet por ejecución, con `max_tokens=1200` y entradas de
unos 3.000 caracteres. **Coste en euros: no medido** — no se ha ejecutado con una
clave real desde aquí.

---

## 5. Imagen publicada (`publish-image.yml`)

Construye `infra/docker/Dockerfile` y publica en GHCR, que es gratuito en
repositorios públicos y se autentica con el `GITHUB_TOKEN` del propio workflow
(sin secretos nuevos).

Etiquetas: `sha-<sha completo del commit>` siempre, `latest` en la rama por
defecto, y `vX.Y.Z` en etiquetas `v*`.

Una vez publicada:

```
docker pull ghcr.io/fulkrodev/fulkrosys/backend:latest
docker pull ghcr.io/fulkrodev/fulkrosys/backend:sha-<sha completo del commit>
```

SBOM y procedencia van adjuntas como atestaciones OCI (`sbom: true`,
`provenance: mode=max`). Se leen sin herramientas de terceros:

```
docker buildx imagetools inspect ghcr.io/fulkrodev/fulkrosys/backend:latest \
  --format '{{ json .SBOM }}'
```

y además se guardan como artefacto `sbom-<sha>` del run, por si se quiere sin
descargar la imagen.

### 5.1 Paso manual obligatorio tras la primera publicación

Un paquete recién creado en GHCR nace **privado** aunque el repositorio sea
público, así que el primer `docker pull` anónimo fallará hasta que alguien lo
haga público a mano:

1. `https://github.com/orgs/Fulkrodev/packages` (o la pestaña **Packages** del
   perfil propietario) → paquete `backend`.
2. **Package settings** → **Danger Zone** → **Change package visibility** →
   **Public** → confirmar escribiendo el nombre del paquete.
3. En la misma pantalla, **Manage Actions access**: comprobar que el repositorio
   `Fulkrodev/Fulkrosys` aparece con rol `Write`, que es lo que permite al
   workflow volver a publicar.

**No medido**: no se ha publicado ninguna imagen desde aquí, así que no hay
constancia empírica de que el paquete aparezca con ese nombre exacto hasta el
primer run.

### 5.2 El Dockerfile puede caerse por una descarga de terceros

`infra/docker/Dockerfile:36` descarga nuclei de github.com **sin respaldo**,
mientras que las otras nueve descargas de herramientas del mismo fichero llevan
`|| echo WARNING`. Y `infra/docker/Dockerfile:132-139` lo verifica en duro
(`which nuclei && ... && nuclei -version`). Si GitHub no responde o esa release
cambia de nombre, el build se cae en duro y no hay imagen, aunque ninguna de esas
herramientas de pentest haga falta para ver la aplicación.

Decisión de este workflow: **fallar, no avisar**. Publicar una imagen a la que le
falta un binario que su propia verificación declara obligatorio sería publicar una
imagen que miente sobre lo que contiene. Lo que sí hace el workflow es
diagnosticar: comprueba esa URL **antes** de gastar el build y emite un
`::warning::` si no responde 200, y si el build cae escribe en el resumen la causa
conocida.

El arreglo hay que hacerlo en el Dockerfile, y son **dos sitios** (por eso nadie
lo había arreglado del todo: poner el respaldo en la línea 36 sin tocar la
verificación deja el build igual de roto). Propuesta exacta:

```dockerfile
# línea 36-39, añadir el mismo respaldo que llevan httpx/subfinder
RUN (curl -sfL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.0/nuclei_3.3.0_linux_amd64.zip -o /tmp/nuclei.zip \
      && cd /tmp && python3 -c "import zipfile; zipfile.ZipFile('nuclei.zip').extractall('/usr/local/bin/')" \
      && chmod +x /usr/local/bin/nuclei && rm -f /tmp/nuclei.zip) \
    || echo "WARNING: nuclei install failed (webpentest nuclei_tool degrada a stub)"

# líneas 132-139, sacar nuclei de la verificación DURA y dejarlo en el
# reporte SOFT de capacidades que ya existe en las líneas 145-148
RUN which nmap && \
    which testssl.sh && \
    which lynis && \
    which dig && \
    which ldapsearch && \
    nmap --version | head -1
```

### 5.3 Lo que el smoke de la imagen sí comprueba

No levanta la aplicación: haría falta base de datos y las cuatro variables que
exige `backend/app/startup_checks.py` (`DATABASE_URL`, `FULKRO_AUTH_PRIVATE_KEY`,
`FULKRO_ML_PRIVATE_KEY`, `FULKRO_BACKUP_SIGNING_KEY`). Comprueba lo que se puede
comprobar sin nada montado: que `fastapi`, `sqlalchemy` y `uvicorn` están dentro
del contenedor, y que existen los binarios que el propio Dockerfile declara
obligatorios.

Lo que sí está medido en local es que el Dockerfile es sintácticamente válido y
no tiene avisos del linter de buildkit:

```
$ docker buildx build --check -f infra/docker/Dockerfile .
Check complete, no warnings found.
$ echo $?
0
```

El build completo **no se ha ejecutado** desde aquí: es no medido cuánto tarda y
si termina.

---

## 6. Protección de rama: pasos exactos

Esto es configuración de GitHub, no código. **Hay que hacerlo a mano**, con
permisos de administrador del repositorio, y en este orden.

### Paso 0 · antes de nada, poner `main` en verde

Marcar `lint` como obligatorio con `main` en rojo bloquea todos los PR desde el
primer minuto. Hoy `lint` falla por el `F811` de `backend/tests/conftest.py`
(líneas 121 y 436). Arreglar eso primero.

### Paso 1 · crear la regla

1. `https://github.com/Fulkrodev/Fulkrosys/settings/rules` →
   **New ruleset** → **New branch ruleset**.
   (La pantalla clásica `Settings → Branches → Add branch protection rule`
   también sirve; los rulesets son lo que GitHub recomienda hoy.)
2. **Ruleset Name**: `main protegida`.
3. **Enforcement status**: `Active`.
4. **Target branches** → **Add target** → **Include default branch**.

### Paso 2 · marcar los checks obligatorios

Dentro de **Rules**, activar **Require status checks to pass** y añadir, con
**Add checks**, exactamente estos nombres (son literales, se escriben tal cual):

| Nombre literal del check | De qué workflow | Por qué obligatorio |
|---|---|---|
| `lint` | `ci.yml` | Es el único gate de Python que corre en todos los PR y falla de verdad |
| `frontend-typecheck` | `ci.yml` | `tsc --noEmit`, corre en todos los PR y falla de verdad |
| `evals-arnes` | `evals.yml` | Determinista, sin secretos, corre en todos los PR |
| `bandit · Python SAST` | `security-scan.yml` | Falla de verdad ante hallazgos |
| `npm audit · Node dep vulnerabilities` | `security-scan.yml` | Falla de verdad ante hallazgos |

**Antes de escribir un nombre, confírmalo.** El nombre del check es el `name:` del
job, o su id si no lo declara, y otro trabajo en curso está reescribiendo `ci.yml`
y `security-scan.yml`. La forma segura de confirmarlo: abrir un PR cualquiera,
pestaña **Checks**, y copiar el nombre tal cual aparece ahí.

Marcar también **Require branches to be up to date before merging**.

**No marcar como obligatorios**, y la razón de cada uno:

| Check | Por qué NO |
|---|---|
| `playwright` | Lleva `if: github.event_name == 'workflow_dispatch'`: en un PR sale `skipped` y nunca reporta |
| Los tres de `admin-polish-empirical.yml` | Filtro de paths `frontend/**`: no se disparan en todos los PR |
| `evals-llm` | Desde D6 queda **saltado** cuando no hay clave (PR de un fork, típicamente). Un check obligatorio que se salta complica el merge. Además depende de `evals-arnes` con `needs:` |
| `publicar` (`publish-image.yml`) | Filtro de paths: no se dispara en todos los PR |
| `Security Scan` | Filtro de paths (`backend/**/*.py`, `frontend/package*.json`, …): no se dispara en un PR que sólo toque documentación |

Tres filas que estaban aquí **ya no valen**, y conviene decir por qué en vez de
borrarlas en silencio:

- `typecheck` ya **no** lleva `continue-on-error: true` (el único que queda en
  `ci.yml:334` es el paso informativo que cuenta la suite, dentro del job `test`).
  Se puede exigir, con la advertencia de que sólo cubre la lista de
  `.github/mypy-clean-modules.txt`.
- `test` ya **no** lleva `if: workflow_dispatch`: corre en cada push y cada PR.
  Se puede exigir.
- `safety` ya **no** lleva `|| true`: captura el código de salida a propósito y
  lo aplica en su gate. `deploy.yml` no existe: se retiró a `docs/historia/`.

### Paso 3 · el resto de la regla

En el mismo ruleset, activar:

- **Restrict deletions** (impide borrar `main`).
- **Block force pushes**.
- **Require a pull request before merging** → **Required approvals: 0** si el
  repositorio lo mantiene una sola persona (con 1 aprobación y un solo
  mantenedor, nadie puede fusionar nunca). Con 0 la regla sigue sirviendo:
  obliga a pasar por PR y por los checks.
- **Require conversation resolution before merging** (opcional).

Guardar con **Create**.

### Paso 4 · comprobar que ha quedado puesto

```
$ curl -s https://api.github.com/repos/Fulkrodev/Fulkrosys/branches/main \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['protected'])"
```

Tiene que devolver `True`. Hoy devuelve `False` (medido, sección 3).

Ojo: un check sólo aparece en la lista de **Add checks** si se ha ejecutado
alguna vez recientemente. `evals-arnes` no existirá en esa lista hasta que
`evals.yml` haya corrido al menos una vez; si hace falta, se puede escribir el
nombre a mano en el buscador de esa misma caja.

---

## 7. Lo que no se ha podido verificar desde aquí

- **No se puede ejecutar un workflow desde este entorno.** Todo lo que dice este
  documento sobre `evals.yml` y `publish-image.yml` está verificado ejecutando
  sus scripts en local y validando su YAML, no viéndolos correr en un runner de
  GitHub. La primera ejecución real es la prueba que falta.
- **El build completo de la imagen no se ha ejecutado**: sólo el linter de
  buildkit (`docker buildx build --check`, sin avisos).
- **La cifra de 515 errores de mypy** viene de la auditoría previa y no se ha
  re-ejecutado: `pip install -e backend[dev]` no completa en esta máquina porque
  `pycairo` se compila desde fuente y faltan `pkg-config`, `cmake` y
  `libcairo2-dev`.
- **El coste en euros de `evals-llm` no está medido**: no se ha lanzado con una
  clave real.
