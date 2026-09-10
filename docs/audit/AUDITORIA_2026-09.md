# Auditoría técnica de Fulkrosys · septiembre de 2026

> **Nota de estado, añadida al versionar este informe.**
>
> Esto es una **foto del 10 de septiembre de 2026** y se conserva sin retocar sus
> mediciones: un informe editado a posteriori para que cuadre con el presente deja
> de ser evidencia. Lo que ha cambiado DESPUÉS de tomarla:
>
> - **Hallazgo 3 (fixture de tests con guías CCN-STIC y AEPD) · RESUELTO.**
>   `backend/tests/fixtures/corpus_seed.sql.gz` se recortó a las cinco fuentes de
>   libre redistribución (RD 311/2022 y legislación UE): 1.031 chunks de 1.977,
>   de 11.198.978 a 5.744.465 bytes. El blob antiguo se purgó del historial con
>   `git filter-repo --strip-blobs-with-ids`. Lo que este informe describe ya no
>   está en el repositorio.
> - **Detector de verdad vacua · CONSTRUIDO.** Lo que aquí aparece como 8 tests
>   que pasan en vacío se instrumentó después: 299 sospechosos sobre 3.294
>   ejecutados, 5 vacuos confirmados por triaje y arreglados. Ver
>   `scripts/vacuity_check.py` y la sección correspondiente del README.
> - **Licencia · RESUELTA.** Se añadió `LICENSE` (Apache-2.0) y el README ya no
>   dice «Privado propietario».
> - **`.dockerignore` · AÑADIDO.** El contexto de build ya no incluye `.git` ni
>   `backend/tests/`.
>
> Sigue abierto todo lo demás, en particular el `[MOCK]` silencioso de los
> agentes, el CI que da verde sin comprobar nada y
> `docs/catalogs/ens_measures_catalog_v1.yaml`.


Se ha auditado el árbol publicado en `/home/usuario/dev/Fulkrosys` (rama `main`) en ocho dimensiones ejecutadas en paralelo: arranque en máquina limpia (A1), suite de tests (A2), capa de IA (A3), autorización y datos (A4), código muerto y deuda (A5), CI y despliegue (A6), lo que se afirma frente a lo que es (A7) y material de terceros y licencias (A8). Cada cifra publicada por un auditor pasó después por un verificador adversarial cuyo trabajo era reproducir el comando, comprobar que la población medida es la que la etiqueta nombra e intentar refutar la conclusión; sus dictámenes están recogidos, sin suavizar, en la línea de Verificación de cada hallazgo. El entorno condiciona lo que se pudo medir: el checkout no tiene entorno virtual propio, no hay Docker en la distribución (`docker: command not found`), no hay PostgreSQL escuchando (5432 y 5433 rechazan conexión) y no existe `frontend/node_modules`. En consecuencia, todo lo que exija base de datos viva, contenedores o navegador está medido estáticamente o directamente no está medido, y así se declara: no se ejecutó la suite completa contra una base provisionada, no se abrió ninguna página en un navegador y no se lanzó ningún workflow de GitHub Actions. Lo que sí se pudo hacer —y se hizo— es instalar en limpio en `/tmp`, arrancar el backend sin base de datos, importar la aplicación real para enumerar sus 1.201 rutas, ejecutar la suite sin infraestructura dos veces, parsear las 268 migraciones, y consultar la API de GitHub para el histórico de 120 ejecuciones de CI.

Recuento final: 68 bloques de hallazgo, de los cuales **30 confirmados**, **16 corregidos por mal etiquetado** y **22 sin verificar** (el verificador no llegó a cubrirlos). **Ninguno fue refutado.** Varios hallazgos son el mismo hecho encontrado por dimensiones distintas —la contradicción de licencia aparece tres veces, el CI sin tests cuatro—, así que 68 no equivale a 68 problemas distintos.

---

## 1. Las diez cosas que más avergonzarían a su autor

Ordenadas por daño, la peor primero. El criterio es el de un ingeniero senior que abre el repositorio mañana por la mañana y le dedica cinco minutos antes de decidir si sigue leyendo.

**1. El README declara "Privado propietario" en un repositorio publicado bajo Apache-2.0.**
`README.md:194` cierra con «Privado propietario. Contacto comercial: marcosmata@fulkro.es»; `LICENSE` es la Apache License 2.0 íntegra con «Copyright 2026 Marcos Mata García» en la línea 190, y el commit que la añade (`0a73baf7`) es HEAD. Es la última línea que se lee y contradice al fichero legal del mismo árbol: quien forkee no sabe bajo qué términos puede hacerlo. Coste: una línea. Ver [A1](#a1--arranca-en-una-máquina-limpia), [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es) y [A8](#a8--terceros-y-licencias).

**2. `CLAUDE.md`, al que el README manda como "especificación canónica", apoya 120 líneas de "CERRADO / PASS / ZERO regression / empirical" sobre una cadena de evidencia que no existe en el repositorio publicado.**
0 de los 15 tags git citados existen (`git tag` devuelve 0), 0 de 12 hashes de commit muestreados resuelven, 10 de los 11 documentos de auditoría enlazados no están en el árbol y `docs/archive/` no existe. El historial se rehízo como snapshot limpio el 2026-06-09 y la documentación viajó intacta desde otra vida del proyecto. Un evaluador que comprueba dos punteros y falla en los dos extiende la sospecha al resto del repositorio. Ver [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es).

**3. El fixture de tests contiene el texto íntegro de nueve guías CCN-STIC —incluida su propia página de aviso legal que prohíbe reproducirlas— y una guía de la AEPD bajo CC BY-NC-SA 4.0.**
`backend/tests/fixtures/corpus_seed.sql.gz` (11,2 MB versionados) trae 697 chunks / 975.277 caracteres de las guías 800 a 808 (450 páginas de PDF) y 249 chunks / 357.355 caracteres de la guía de la AEPD, cuya cláusula NonCommercial y ShareAlike es incompatible con redistribuir el repositorio bajo Apache-2.0. Es el único hallazgo con superficie legal real, y está en un blob del commit raíz. *No confirmado por el verificador.* Ver [A8](#a8--terceros-y-licencias).

**4. Siguiendo el README al pie de la letra, el backend no arranca: `cp .env.example .env` produce un fichero sin ninguna de las cuatro variables que el arranque exige.**
`startup_checks.py` aborta con `CriticalConfigError: Env vars críticas ausentes: ['DATABASE_URL', 'FULKRO_AUTH_PRIVATE_KEY', 'FULKRO_ML_PRIVATE_KEY', 'FULKRO_BACKUP_SIGNING_KEY']`. Son unas seis líneas de `.env.example`, y por debajo el sistema está sano: instala limpio, importa limpio y arranca sin Postgres sirviendo `/docs`. Que la distancia entre "no arranca" y "arranca en dos minutos" sea de seis líneas es precisamente lo que duele. Ver [A1](#a1--arranca-en-una-máquina-limpia).

**5. El `pytest` que el README manda ejecutar aborta en colección en 3,48 s y no ejecuta ni un test.**
Tres dependencias no declaradas (`bs4`, `pypdf`, `respx`) rompen la importación de 7 ficheros y pytest interrumpe la sesión: `7 errors during collection`, exit 2, cero tests corridos. Detrás hay 6.464 tests recolectables. *No confirmado por el verificador.* Ver [A1](#a1--arranca-en-una-máquina-limpia) y [A2](#a2--pasan-los-tests-suite-backend-pytest).

**6. El CI está en verde y no comprueba casi nada, y además nada bloquea nada.**
De los cinco jobs de `ci.yml` sólo dos son gates reales; el job de tests está condicionado a `workflow_dispatch` y pytest no ha corrido nunca; `mypy` lleva `continue-on-error: true` y encima aborta sin analizar un solo fichero; el job `safety` crashea, no escribe informe y su parser "tolerante" lo convierte en éxito. Y no hay branch protection ni rulesets, así que los comentarios que dicen "block merge" en tres YAML son falsos. Ver [A6](#a6--ci-y-despliegue).

**7. Cuando falta la clave de API o falla cualquier llamada, los agentes devuelven texto `[MOCK]` fabricado y se registra en el ledger como `status="success"` con tokens inventados.**
`AgentBase._call_llm` degrada en silencio y el diccionario devuelto no lleva ninguna bandera; se verificó que el Agente 04, el que redacta entregables ENS, produce mock sin clave y que ningún consumidor del repositorio comprueba el prefijo. En un producto de cumplimiento normativo eso significa entregables falsos indistinguibles de los reales. Ver [A3](#a3--la-capa-de-ia-agentes-router-llm-evaluación-rag).

**8. Cuatro flujos públicos con puerta propia —firma del cliente por magic-link, aprobación de acta, agente on-prem y webhook de 360dialog— devuelven 401 antes de llegar a su propio control.**
Se quedaron fuera de la whitelist de la dependencia global, así que el HMAC y el gate Bearer que los protegen son código muerto que nunca se ejecuta. Falla en cerrado (no expone datos) pero deja la firma Ed25519 de actas y el agente de remediación completamente inoperativos. Ver [A4](#a4--autorización-y-datos).

**9. El README describe un repositorio que no es este: "1 head" de Alembic, un cuarto portal que no existe y dos directorios de documentación inexistentes.**
`README.md:156` afirma «1 head: m8_autopilot_canonical_001», revisión que ni siquiera es head porque otra migración la declara como `down_revision`; `README.md:30` vende «Cuatro portales: admin, cliente, auditor y ENS Radar» de un subsistema del que no queda un solo fichero Python; y `docs/doctrine/` y `docs/audits/`, dibujados en el árbol del README, no existen. Tres callejones sin salida en la misma página de entrada. Ver [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es).

**10. Hay nueve líneas de código ejecutable que apuntan a otro checkout de la máquina del autor.**
`load_dotenv(Path("/home/usuario/fulkro/.env"))` en tres ingestores de corpus, constantes `REPO_ROOT` y `HTML_PATH` hacia `var/corpus/boe/…` y `_incoming/` que no existen, más el fallback de `scripts/build_test_db.sh` a `/home/usuario/fulkro/.venv` y el `PATH` cableado de `scripts/run_tsc.sh`. `git grep '/home/usuario'` lo encuentra en diez segundos y dice, sin necesidad de más, que el repositorio nunca se ha ejecutado fuera de una máquina. Ver [A5](#a5--código-muerto-y-deuda).

---

## 2. Hallazgos por dimensión

Formato de cada bloque: qué es, dónde, cómo se midió (comando y salida), gravedad, coste con su justificación y el dictamen del verificador adversarial. Cuando el dictamen fue MAL ETIQUETADO, la cifra que aparece es la corregida y se explica qué se corrigió. Los hallazgos SIN VERIFICAR están marcados como no confirmados: son medidas del auditor que nadie reprodujo de forma independiente.

### A1 · ¿Arranca en una máquina limpia?

> **Dimensión escalada.** Motivo del auditor: cuatro bloqueantes, no tres, y los cuatro en la ruta feliz que el propio README describe. El diagnóstico agregado es que el repositorio no es arrancable hoy por un tercero siguiendo su documentación. Lo relevante para decidir es la asimetría entre gravedad y coste: los cuatro bloqueantes suman unas 6 líneas de `.env.example`, 3 de `pyproject.toml`, 3 de `docker-compose.yml` y ~4 del README, porque el sistema por debajo está sano. La recomendación del auditor es tratarlo como un único ejecutable de quickstart y añadir a CI un job que ejecute la secuencia mínima en un runner limpio; sin ese job, cualquier arreglo documental caduca en semanas.

Un tercero que siga el README literalmente no llega a nada funcionando: el paso 3 produce un `.env` sin ninguna variable crítica y uvicorn aborta; el paso 5 aborta en colección sin ejecutar un test; y el `docker-compose.yml` de desarrollo nunca aplica los init SQL que sí aplica el de producción. La contrapartida medida: la instalación limpia funciona, la app importa sin nada extra y con sólo cuatro variables arranca sin PostgreSQL y sirve la API documentada. Cronometrado: pip 30,3 s (caché caliente), `npm ci` 11 s, `next build` 54,9 s.

#### BLOQUEANTE 1 · `.env.example` no contiene ninguna de las 4 variables que el arranque exige

**Qué es.** `startup_checks.py` exige `DATABASE_URL`, `FULKRO_AUTH_PRIVATE_KEY`, `FULKRO_ML_PRIVATE_KEY` y `FULKRO_BACKUP_SIGNING_KEY`, y `run_startup_checks()` corre en el lifespan de `main.py`. Las cuatro están ausentes o comentadas en `.env.example`. El README dice literalmente `cp .env.example .env`, así que el arranque falla siempre. Existe `scripts/generate_dev_signing_keys.py`, que funciona y genera tres de las cuatro, pero el README sólo lo menciona de pasada y no cubre `DATABASE_URL`.

**Dónde.** `backend/app/startup_checks.py:35-40` · `backend/app/main.py:378` · `.env.example:23` y `:38` · `backend/app/config.py:10`

**Cómo se midió.**
```bash
$ cp .env.example /tmp/a1_env_from_example
$ PYTHONPATH=. python -m uvicorn backend.app.main:app --env-file /tmp/a1_env_from_example
backend.app.startup_checks.CriticalConfigError: Env vars críticas ausentes:
  ['DATABASE_URL', 'FULKRO_AUTH_PRIVATE_KEY', 'FULKRO_ML_PRIVATE_KEY', 'FULKRO_BACKUP_SIGNING_KEY']
ERROR:    Application startup failed. Exiting.

# segunda corrida, ya con generate_dev_signing_keys.py ejecutado (EXIT=3):
backend.app.startup_checks.CriticalConfigError: Env vars críticas ausentes: ['DATABASE_URL'].
```

**Gravedad.** Bloqueante.

**Coste.** 10-15 min. Un fichero: descomentar `DATABASE_URL`, añadir tres placeholders de claves Ed25519 y una línea que remita al generador. Son ~6 líneas. La verificación es reejecutar el comando.

**Verificación.** CONFIRMADO. Reproducido dos veces con entorno limpio (`env -i`). `verify_critical_env()` es el primer check de `run_startup_checks()`, así que la excepción es la declarada. Cifra: 4/4 variables ausentes (`grep -c '^VAR='` da 0/0/0/0 en `.env.example` y 1/1/1/1 en `.env.prod.template`). Imprecisión incidental detectada: el default de `config.py:10` existe pero usa la contraseña `changeme` mientras `init-roles.sql:15` crea `fulkro_app` con `fulkro_app_dev_password`, así que ese default tampoco autenticaría.

#### BLOQUEANTE 2 · Tres dependencias no declaradas (`bs4`, `pypdf`, `respx`) hacen que `pytest` aborte sin ejecutar un test

**Qué es.** En un venv limpio construido sólo con lo declarado, pytest aborta en colección: 7 ficheros fallan al importar por `ModuleNotFoundError`. Ninguno de los tres paquetes aparece en `backend/pyproject.toml`. El origen de `bs4`/`pypdf` son imports a nivel de módulo en el corpus. De 52 módulos de terceros importados por `backend/app`, 12 no están cubiertos, pero sólo estos 3 rompen: los otros 9 son imports perezosos, verificado por AST.

**Dónde.** `backend/pyproject.toml` · `backend/app/corpus/rd311_parser.py:22` · `backend/app/corpus/ccn_pdf_ingest.py:43` · `backend/tests/motors/m16_onboarding/test_oauth_service.py` · `backend/tests/corpus/test_pdf_ingest.py`

**Cómo se midió.**
```bash
$ python3 -m venv /tmp/a1_venv && /tmp/a1_venv/bin/pip install -e "/tmp/a1_clone/backend[dev]"
Successfully installed ... fulkro-0.1.0 ...   (exit 0)
$ PYTHONPATH=. /tmp/a1_venv/bin/python -m pytest backend/tests -q      # EXIT=2
ERROR backend/tests/corpus/test_pdf_ingest.py       ModuleNotFoundError: No module named 'pypdf'
ERROR backend/tests/corpus/test_rd311_parser.py     ModuleNotFoundError: No module named 'bs4'
ERROR backend/tests/motors/m16_onboarding/test_m16_cierre.py        No module named 'respx'
ERROR backend/tests/motors/m16_onboarding/test_m16_connectors.py    No module named 'respx'
ERROR backend/tests/motors/m16_onboarding/test_oauth_service.py     No module named 'respx'
ERROR backend/tests/motors/m_remediation/test_cloud_writers_simulator.py  No module named 'respx'
ERROR backend/tests/test_corpus_clean.py            No module named 'bs4'
!!!!!!!!!!!!! Interrupted: 7 errors during collection !!!!!!!!!!!!!
6 warnings, 7 errors in 3.48s
```

**Gravedad.** Bloqueante.

**Coste.** 15 min. Tres líneas en `backend/pyproject.toml`: `beautifulsoup4` y `pypdf` en dependencias, `respx` en las de desarrollo.

**Verificación.** SIN VERIFICAR — el verificador no cubrió este hallazgo. **No confirmado.**

#### BLOQUEANTE 3 · El compose de desarrollo nunca provisiona la BD, y 88 migraciones mencionan el rol `fulkro_app` (corregido)

**Qué es.** `docker-compose.prod.yml` monta los tres init SQL en `/docker-entrypoint-initdb.d`; el compose de desarrollo no lo hace, y `Dockerfile.postgres` sólo copia `pgbackrest.conf`. Tras `docker compose up -d postgres`, la base `fulkro` existe sin extensiones, sin `current_client_id()`/`current_project_id()` y sin los roles `fulkro_app`/`fulkro_app_bypassrls`/`fulkro_migrate`. Las migraciones ejecutan `GRANT … TO fulkro_app` con `op.execute` sin guarda, así que fallarían con «role fulkro_app does not exist». `build_test_db.sh` sí aplica los init SQL, pero sólo sobre `fulkro_test`. El README no documenta ningún paso de provisión; la receta correcta existe, escrita en `.github/workflows/admin-polish-empirical.yml`.

**Dónde.** `docker-compose.yml:2-26` · `docker-compose.prod.yml:53-55` · `infra/docker/Dockerfile.postgres` · `scripts/build_test_db.sh:41-56` · `README.md` (sección "Levantar en desarrollo")

**Cómo se midió.**
```bash
$ grep -rn 'docker-entrypoint-initdb' docker-compose.yml docker-compose.prod.yml infra/docker/Dockerfile.postgres
docker-compose.prod.yml:53:  - ./infra/docker/init-extensions.sql:/docker-entrypoint-initdb.d/01-extensions.sql:ro
docker-compose.prod.yml:54:  - ./infra/docker/init-functions.sql:/docker-entrypoint-initdb.d/02-functions.sql:ro
docker-compose.prod.yml:55:  - ./infra/docker/init-roles.sql:/docker-entrypoint-initdb.d/03-roles.sql:ro
# docker-compose.yml: 0 coincidencias · Dockerfile.postgres: 0 coincidencias
$ grep -rl 'fulkro_app' backend/migrations/versions/ | wc -l
88
```

**Gravedad.** Bloqueante.

**Coste.** 30-45 min. Tres líneas de `volumes` copiadas del compose de producción y una sección de ~10 líneas en el README, ya escrita en el workflow de CI. El coste real está en la verificación, que exige Docker.

**Verificación.** MAL ETIQUETADO (reproduce, pero mide otra cosa). **Corrección:** el 88 del titular original era un conteo de *ficheros que mencionan* el rol presentado como *ficheros que le hacen GRANT*. Las cifras correctas son: **88 ficheros mencionan `fulkro_app`, 75 contienen un target `TO fulkro_app` y 46 llevan `GRANT` y `fulkro_app` en la misma línea**, sobre un total de 268 ficheros en `versions/`. Trece de los 88 no otorgan nada (son comentarios, docstrings o políticas RLS). La parte (a) del hallazgo —que el compose de desarrollo no aplica los init SQL— está plenamente confirmada, y el verificador añadió que el README no menciona nunca `init-roles`/`init-extensions`/`init-functions`/`fulkro_app`/`fulkro_migrate`.

#### BLOQUEANTE 4 · El frontend no puede autenticar a nadie: `FULKRO_AUTH_PUBLIC_KEY` no está en el README

**Qué es.** `frontend/middleware.ts:32` lee `process.env.FULKRO_AUTH_PUBLIC_KEY` y, si falta, `getClaims()` devuelve null para cualquier petición: «todos los requests autenticados caerán a unauthenticated», dice el comentario del propio código. El README ordena `cd frontend && npm install && npm run dev` sin mencionar que hay que crear `frontend/.env`; la variable existe en `frontend/.env.example` pero comentada. `start_frontend.sh` sí exige ese fichero y aborta con «FATAL: frontend/.env NOT found». Consecuencia práctica: el build es verde y la home carga, pero no hay forma de ver el producto siguiendo la documentación.

**Dónde.** `frontend/middleware.ts:32-43` · `frontend/.env.example:9-13` · `README.md` (sección "Frontend") · `start_frontend.sh:9-17`

**Cómo se midió.**
```bash
$ grep -nE 'process\.env\.[A-Z_0-9]+' frontend/middleware.ts
32:const PUBLIC_KEY_PEM = process.env.FULKRO_AUTH_PUBLIC_KEY;
# contexto: if (!PUBLIC_KEY_PEM) { // Sin PUBLIC_KEY = todos los requests caerán
#            a unauthenticated (degradación segura: redirect a /login).
$ grep -c '^FULKRO_AUTH_PUBLIC_KEY=' frontend/.env.example
0
$ ls -a frontend/.env*
frontend/.env.example      # no hay frontend/.env ni .env.local
```

**Gravedad.** Bloqueante.

**Coste.** 15 min. `scripts/generate_dev_signing_keys.py` ya escribe `frontend/.env` con la clave pública derivada; el arreglo es documental: ~4 líneas de README para incluirlo antes del `npm run dev`.

**Verificación.** SIN VERIFICAR — el verificador no cubrió este hallazgo. **No confirmado.** El auditor advierte además que no observó el redirect en runtime: el hallazgo se apoya en el flujo del middleware, no en una traza HTTP.

#### GRAVE · `build_test_db.sh` depende del nombre del directorio del clon y cae a un venv personal

**Qué es.** El script trabaja con `docker exec -i "${CONTAINER}"` y `CONTAINER` vale por defecto `fulkro-postgres-1`, nombre que sólo existe si el directorio del clon se llama `fulkro`. El repositorio real es `github.com/Fulkrodev/Fulkrosys`, así que un clon por defecto genera `fulkrosys-postgres-1` y todos los pasos fallan con «No such container». Segundo problema en el mismo fichero: si no existe `./.venv`, cae a `/home/usuario/fulkro/.venv/bin/python`, la ruta personal del autor. Ambos son sobreescribibles por variable de entorno, pero eso no está en el README.

**Dónde.** `scripts/build_test_db.sh:12`, `:17-24`, `:39` · `README.md` (paso 4)

**Cómo se midió.**
```bash
$ sed -n '9,24p;39p' scripts/build_test_db.sh
CONTAINER="${FULKRO_PG_CONTAINER:-fulkro-postgres-1}"
VENV_PY="${FULKRO_VENV_PY:-.venv/bin/python}"
  VENV_PY="/home/usuario/fulkro/.venv/bin/python"
psql_super() { docker exec -i -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -v ON_ERROR_STOP=1 -U fulkro "$@"; }
$ git remote -v
origin  https://github.com/Fulkrodev/Fulkrosys.git (fetch)
```

**Gravedad.** Grave.

**Coste.** 15-20 min. ~3 líneas: derivar el contenedor con `docker compose ps -q postgres` y sustituir el fallback personal por un error accionable (el bloque de error ya existe).

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.** El propio auditor declara que no ejecutó el script (no hay Docker) y que la conclusión se apoya en la regla de nombrado de Compose.

#### GRAVE · Tras `build_test_db.sh`, `pytest` apunta a la BD live `fulkro`, no a `fulkro_test`

**Qué es.** `conftest.py` reescribe el nombre de la base a `fulkro_test` leyendo `os.environ['DATABASE_URL']`. Pero el README dice explícitamente «NO usar `source .env`» y apoya la carga vía `--env-file`, y pydantic-settings lee el fichero sin poblar `os.environ`. Verificado: con un `.env` que contiene `DATABASE_URL`, `os.environ.get('DATABASE_URL')` es `None` mientras `get_settings().database_url` resuelve a `…/fulkro`. La reescritura es un no-op y el motor se construye contra la base live, contra la promesa del README de que «nunca toca la BD live fulkro».

**Dónde.** `backend/tests/conftest.py:73-78` · `backend/app/config.py:206-210` · `README.md` (nota "NO usar `source .env`" y paso 5)

**Cómo se midió.**
```bash
$ echo 'DATABASE_URL=postgresql+asyncpg://fulkro_app:...@localhost:5433/fulkro' >> .env
$ PYTHONPATH=. python -c "import os; print('os.environ:', repr(os.environ.get('DATABASE_URL')));
   from backend.app.config import get_settings; print('settings:', get_settings().database_url)"
os.environ DATABASE_URL: None
settings.database_url: postgresql+asyncpg://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro
```

**Gravedad.** Grave.

**Coste.** 20-30 min. O cambiar la guarda de `conftest.py` (~5 líneas) para leer de `get_settings()`, o añadir un `export DATABASE_URL=…fulkro_test` al README. La verificación real exige PostgreSQL.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.** El auditor acota lo que afirma: mide la resolución de la URL, no que los tests escriban en una base live.

#### GRAVE · El CI que se ve verde no ejecuta ningún test, y el job que los ejecutaría tiene una ruta de runner que ya no existe

**Qué es.** En `ci.yml` los jobs `test` y `playwright` llevan `if: github.event_name == 'workflow_dispatch'`, así que en push y en pull request sólo corren lint, typecheck (con `continue-on-error: true`) y frontend-typecheck. Además el job `playwright` hace `cd /home/runner/work/fulkro/fulkro`, ruta que GitHub deriva del nombre del repositorio: siendo `Fulkrodev/Fulkrosys`, la real sería `/home/runner/work/Fulkrosys/Fulkrosys`. Y el job `test` fallaría hoy igualmente por las tres dependencias ausentes y por levantar un Postgres sin roles.

**Dónde.** `.github/workflows/ci.yml:55-57`, `:96-98`, `:179`, `:31-37`

**Cómo se midió.**
```bash
$ grep -n "if: github.event_name\|continue-on-error\|home/runner/work" .github/workflows/ci.yml
56:    if: github.event_name == 'workflow_dispatch'
97:    if: github.event_name == 'workflow_dispatch'
37:        continue-on-error: true
179:          cd /home/runner/work/fulkro/fulkro
```

**Gravedad.** Grave.

**Coste.** 10 min para la ruta y el badge honesto; 2-4 h para un job de tests que realmente pase (exige las tres dependencias, provisionar roles y extensiones —receta copiable de `admin-polish-empirical.yml`— y comprobar cuántos de los 6.383 tests recolectados pasan sin BD sembrada).

**Verificación.** SIN VERIFICAR en esta dimensión — **no confirmado aquí**, pero el mismo hecho fue confirmado de forma independiente en [A4](#a4--autorización-y-datos) y ampliamente medido en [A6](#a6--ci-y-despliegue).

#### GRAVE · El pipeline de corpus está muerto fuera de la máquina del autor

**Qué es.** De 34 ocurrencias de `/home/usuario` en 26 ficheros versionados, 13 son código ejecutable y 21 comentarios o documentación. Las que importan: tres `load_dotenv(Path('/home/usuario/fulkro/.env'))` que no lanzan excepción sino que devuelven `False` en silencio —el fallo no es un crash, es un pipeline corriendo sin configuración—, más `REPO_ROOT` y `HTML_PATH` apuntando a `var/corpus/boe/…` y `_incoming/`, directorios que no existen en este repositorio. El daño está acotado: ninguno de esos módulos está en el grafo de arranque y los tests obtienen el corpus del fixture versionado.

**Dónde.** `backend/app/corpus/ccn_pdf_ingest.py:38` y `:63` · `backend/app/corpus/rd311_ingest.py:40` · `backend/app/corpus/rd311_embed.py:26` · `backend/app/corpus/ccn_stic_ingest.py:26` · `frontend/scripts/visual-audit.mjs:9` · `frontend/tests/capturas/video-walkthrough.mjs:26` · `scripts/run_tsc.sh:7`

**Cómo se midió.**
```bash
$ git grep -c '/home/usuario' -- . | wc -l   # ficheros versionados
26
$ git grep -n '/home/usuario' -- . | wc -l   # ocurrencias
34
$ ls var _incoming
var: templates_docx        # no existe var/corpus
ls: cannot access '_incoming': No such file or directory
$ python3 -c "from dotenv import load_dotenv; from pathlib import Path;
   print('returns:', load_dotenv(dotenv_path=Path('/tmp/definitely-not-here-xyz/.env')))"
returns: False       # load_dotenv con ruta inexistente NO lanza excepción
```

**Gravedad.** Grave.

**Coste.** 45-60 min. 13 líneas ejecutables en 8 ficheros; las cinco de `backend/app/corpus` se resuelven con el patrón que ya usa `startup_checks.py:23`. Aparte queda que los datos de origen no estén versionados, que es una decisión de producto.

**Verificación.** SIN VERIFICAR aquí — **no confirmado en esta dimensión**. El mismo hecho fue verificado en [A5](#a5--código-muerto-y-deuda) con dictamen MAL ETIQUETADO: la clasificación correcta es **9 líneas funcionales y 9 comentarios**, no 13 y 21, porque tres líneas ejecutables de shell estaban clasificadas como comentarios.

#### MENOR · El README dice "Licencia: Privado propietario" en un repositorio Apache-2.0

**Qué es.** Ver la entrada 1 de la sección anterior. Confirmado también en A7 y A8.

**Dónde.** `README.md` (última sección) · `LICENSE`

**Cómo se midió.**
```bash
$ tail -3 README.md ; git log --oneline -1 ; head -2 LICENSE
## Licencia

Privado propietario. Contacto comercial: marcosmata@fulkro.es
0a73baf7 chore: anade LICENSE con Apache License 2.0
                                 Apache License
                           Version 2.0, January 2004
```

**Gravedad.** Menor por esfuerzo, alta por daño reputacional.

**Coste.** 2 min. Una línea del README.

**Verificación.** CONFIRMADO. Ambos ficheros conviven en el mismo commit; `git log --all -- LICENSE` confirma que `0a73baf7` es el único que lo toca. Nota de contexto del verificador: el snapshot de `gitStatus` de su prompt mencionaba `e63d214` como HEAD, mientras el árbol real auditado tiene HEAD `0a73baf7`.

#### MENOR · Cifras de la documentación de entrada desincronizadas con el árbol

**Qué es.** El README afirma que hay «1 head: m8_autopilot_canonical_001» y que producción tiene «12 servicios» (son 11). `CLAUDE.md`, que el README presenta como especificación canónica viva, dice «160 migraciones» y «~353 archivos test_*.py» frente a 268 y 581. Los «44 directorios de motores» del README sí cuadran (`CLAUDE.md` dice 42).

**Dónde.** `README.md` (Estructura del repositorio) · `CLAUDE.md` (Estado runtime) · `backend/migrations/versions/` · `docker-compose.prod.yml`

**Cómo se midió.**
```bash
$ python -m alembic heads
provider_c002_generado_status_001 (head)
$ ls migrations/versions/*.py | wc -l                    ; # 268
$ find backend/tests -name 'test_*.py' | wc -l           ; # 581
$ python -c "import yaml;print(len(yaml.safe_load(open('docker-compose.prod.yml'))['services']))"  ; # 11
$ ls -d backend/app/motors/m*/ | wc -l                   ; # 44
```

**Gravedad.** Menor.

**Coste.** 10-15 min. 3-4 líneas entre `README.md` y `CLAUDE.md`; los comandos de arriba dan los valores correctos.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado aquí.** Las mismas cifras fueron medidas y verificadas de forma independiente en [A5](#a5--código-muerto-y-deuda) y [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es). Atención: la afirmación «1 head» de este bloque contradice la medición de A7, que encuentra 4; véase la nota sobre esa discrepancia en A7 y en la sección 3.

#### MENOR · Scripts de arranque incoherentes con el gestor de paquetes del repo

**Qué es.** `start_frontend.sh` invoca `pnpm build` y `pnpm start`, pero el repositorio sólo tiene `package-lock.json`: no hay `pnpm-lock.yaml` ni `yarn.lock`, el CI usa `npm ci` y el README usa `npm install`. En la misma línea, `scripts/run_tsc.sh` fija `PATH` y ejecuta el binario de `npx` bajo `/home/usuario/.nvm/versions/node/v20.20.2/bin`; el fichero documenta que el hardcode es deliberado (workaround de PATH de Windows en WSL), pero no funciona en ninguna otra máquina.

**Dónde.** `start_frontend.sh:21` y `:24` · `scripts/run_tsc.sh:7` y `:10` · `frontend/package-lock.json`

**Cómo se midió.**
```bash
$ grep -n 'pnpm' start_frontend.sh
21:    pnpm build
24:exec pnpm start --port 3000 "$@"
$ ls frontend/package-lock.json frontend/pnpm-lock.yaml frontend/yarn.lock
-rw-r--r-- 356844 frontend/package-lock.json
ls: cannot access 'frontend/pnpm-lock.yaml': No such file or directory
ls: cannot access 'frontend/yarn.lock': No such file or directory
```

**Gravedad.** Menor.

**Coste.** 5 min. Dos líneas en `start_frontend.sh`. `run_tsc.sh` es un helper local; hacerlo portable son otras dos líneas, o borrarlo, porque `npm run typecheck` hace lo mismo.

**Verificación.** CONFIRMADO. El verificador ajusta las líneas citadas (21 y 24, no 22-26) y confirma que la cadena documentada es npm en ambos extremos: `README.md:112` y `ci.yml:50`/`:152`.

### A2 · ¿Pasan los tests? (suite backend pytest)

La recolección está impecable: 6.464 tests se recolectan en 9,9 s con cero errores de recolección sobre 581 ficheros, lo que descarta podredumbre de imports en un árbol de este tamaño. Pero la suite no se puede ejecutar aquí: 3.204 de esos 6.464 (49,6%) mueren por una única causa homogénea —conexión rechazada a `127.0.0.1:5433`— y la única vía documentada para levantar esa base está acoplada a `docker exec`. De lo que sí corre, 3.160 pasan y sólo un fallo es un defecto real del repositorio. Dos hechos agravan el cuadro: el job de tests de CI está condicionado a `workflow_dispatch`, y arrancar la suite descarga 2,1 GB de modelo, lo que rompe la promesa de "probarlo en cinco minutos". El resultado es reproducible bit a bit entre dos ejecuciones independientes.

#### El 49,6% de la suite (3.204 de 6.464 tests) no puede ejecutarse: exige PostgreSQL en 127.0.0.1:5433

**Qué es.** Sin infraestructura, 3.202 tests terminan en ERROR y 2 de los 3 FAILED comparten la misma causa raíz. Clasificados con un parser sobre la sección ERRORS acotada por líneas: 3.197 `ConnectionRefusedError` (asyncpg) y 5 `psycopg2.OperationalError`, todos contra el 5433. Cero errores de cualquier otra naturaleza, es decir, ninguna regresión real escondida detrás del muro. El fallo se origina en el fixture `db`, que abre un engine contra `settings.database_url`.

**Dónde.** `backend/tests/conftest.py:233-234` · `backend/app/config.py:10` · `backend/tests/motors/m11_copiloto/test_portal_copilot_tenant_context.py:218` y `:244`

**Cómo se midió.**
```bash
$ PYTHONPATH=/tmp/a2/Fulkrosys pytest backend/tests -q -p no:cacheprovider --timeout=45 -rfs --tb=no
3 failed, 3160 passed, 99 skipped, 24 warnings, 3202 errors in 45.33s
# clasificador sobre la sección ERRORS acotada (3202 bloques parseados):
  3197  ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5433)
     5  psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5433 failed
```

**Gravedad.** Bloqueante.

**Coste.** ~1,5-2 h para que la suite sea auto-degradante; la provisión real de BD ya está escrita. Son dos trabajos: (a) un hook `pytest_collection_modifyitems` en `conftest.py` que pruebe el socket y marque skip los ítems que pidan el fixture `db` (~20 LOC, el fichero ya tiene un hook análogo para el marcador `llm`); (b) desacoplar `build_test_db.sh` de Docker parametrizando su función `psql_super` (~10 LOC).

**Verificación.** CONFIRMADO. Reproducido en copia limpia independiente con el mismo sumario byte a byte; recolección independiente de 6.464 ítems; partición exacta 3202+3+3160+99 = 6464. El verificador clasificó las causas con un método distinto (`--tb=line`) y obtuvo el mismo desglose. La población comparada es la correcta: ítems recolectados, no ficheros (581) ni definiciones `def test_` (5.786), cifras que el auditor separa bien.

#### La única vía documentada para levantar la BD de test exige Docker, que no existe en esta máquina

**Qué es.** El README manda `docker compose up -d postgres redis minio` y luego `bash scripts/build_test_db.sh`. Ese script no habla con Postgres por TCP: entra al contenedor con `docker exec`. Sin Docker no hay camino documentado alguno hacia los 3.204 tests bloqueados, y los cuatro puertos que la suite espera están cerrados.

**Dónde.** `README.md:70` y `:79` · `scripts/build_test_db.sh:39` y `:11`

**Cómo se midió.**
```bash
$ grep -n 'docker' scripts/build_test_db.sh | head -3
39:psql_super() { docker exec -i -e PGPASSWORD="${SUPER_PW}" "${CONTAINER}" psql -v ON_ERROR_STOP=1 -U fulkro "$@"; }
$ grep -c 'psql_super' scripts/build_test_db.sh   # 10 (1 definición + 9 usos)
$ for P in 5432 5433 6379 9000 8080; do timeout 3 bash -c "</dev/tcp/localhost/$P" && echo "$P OPEN" || echo "$P CLOSED"; done
5432 CLOSED / 5433 CLOSED / 6379 CLOSED / 9000 CLOSED / 8080 CLOSED
```

**Gravedad.** Grave.

**Coste.** ~1 h. Un único punto de acoplamiento (la función `psql_super`) usado nueve veces; sustituirla por un wrapper que use `psql` local cuando no hay Docker en el PATH son ~10 LOC. El resto del script es agnóstico al transporte.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### Arrancar la suite descarga 2,1 GB: la promesa de "probarlo en 5 minutos" no se sostiene

**Qué es.** `backend/tests/core/ai/test_embeddings.py` instancia un `FastEmbedBGEMProvider()` real —sin mock, sin marcador, sin skipif— en un fixture de módulo, lo que dispara la descarga del modelo ONNX multilingüe. Reproducido de forma aislada apuntando la caché a un directorio virgen. Consecuencia doble: la suite no es hermética (necesita internet) y el arranque en frío es de gigabytes.

**Dónde.** `backend/tests/core/ai/test_embeddings.py:16` · `backend/app/core/ai/embeddings.py:56` y `:15`

**Cómo se midió.**
```bash
$ ss -tnp | grep <pid-pytest>          # 15 conexiones TLS establecidas hacia CloudFront/EC2
$ ls ~/.cache/huggingface/xet/logs/
xet_20260909T235408484+0200_423456.log     # el nombre lleva el PID del pytest
$ rm -rf /tmp/a2/fe_probe && mkdir -p /tmp/a2/fe_probe
$ FASTEMBED_CACHE_PATH=/tmp/a2/fe_probe pytest backend/tests/core/ai/test_embeddings.py -q
$ du -sh /tmp/a2/fe_probe
2.1G    /tmp/a2/fe_probe
```

**Gravedad.** Grave.

**Coste.** ~30 min. Un `pytest.mark.skipif` a nivel de módulo condicionado a una variable de entorno, con el mismo patrón que ya usa el repo para `FULKRO_RUN_LLM_TESTS`, más una línea de README.

**Verificación.** CONFIRMADO por tres vías independientes, incluida una que el auditor no citó: `/tmp/fastembed_cache` contiene un blob de 2,1 GB con la marca de tiempo exacta de la primera pasada. El verificador añadió la prueba decisiva de no-hermeticidad que faltaba: con la red cortada, los 7 tests del módulo dan 1 failed + 6 errors. Dos matices honestos: 2,1 GB es tamaño en disco medido con `du`, no bytes de red; y con `HF_HUB_OFFLINE=1` el módulo sigue materializando los 2,1 GB por una ruta de descarga alternativa, así que "de HuggingFace" es una de dos rutas posibles.

#### `test_legal_audit_score_100` falla siempre en un clon limpio: escribe en `progress/`, que no está versionado

**Qué es.** Único fallo de los tres que no es infraestructura. El test lanza por subprocess `backend/scripts/legal_audit_77_templates.py`, que hace `write_text` sobre `PROJECT_ROOT/progress/legal_audit_autocheck.json` sin crear antes el directorio. `progress/` no existe ni está versionado, y el `.gitignore` ignora explícitamente ese JSON. Resultado: `FileNotFoundError` → returncode 1 → assert falla. Reproducible sin BD, sin Docker y sin red. Efecto secundario: es un test que escribe dentro del árbol del repositorio.

**Dónde.** `backend/tests/test_legal_audit_paso5_5.py:267` y `:269` · `backend/scripts/legal_audit_77_templates.py:284-285` · `.gitignore:90`

**Cómo se midió.**
```bash
$ git ls-files progress | wc -l ; ls -d progress
0
ls: cannot access 'progress': No such file or directory
$ grep -n 'progress' .gitignore
90:progress/legal_audit_autocheck.json
# traza en la pasada completa:
E   FileNotFoundError: [Errno 2] No such file or directory: '/tmp/a2/Fulkrosys/progress/legal_audit_autocheck.json'
E   assert 1 == 0
```

**Gravedad.** Grave.

**Coste.** ~5 min. Una línea: `out_path.parent.mkdir(parents=True, exist_ok=True)`.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### CI nunca ejecuta la suite: el job de tests está condicionado a `workflow_dispatch`

**Qué es.** De los 5 jobs de `ci.yml`, `test` y `playwright` no corren ni en push a main ni en pull request. De lo que sí corre automáticamente, `typecheck` lleva `continue-on-error: true`. El único gate automático real son `lint` (ruff con un select reducido a F y W) y `frontend-typecheck`. Un badge verde de CI no significa que ningún test haya pasado; el propio comentario del workflow lo reconoce y fija la cifra local en 5.978 passed.

**Dónde.** `.github/workflows/ci.yml:60`, `:99`, `:35`, `:57`

**Cómo se midió.**
```bash
$ grep -n '^  [a-z-]*:$\|if: github.event_name\|continue-on-error' .github/workflows/ci.yml
11:  lint:     24:  typecheck:     35:        continue-on-error: true
40:  frontend-typecheck:
54:  test:     60:    if: github.event_name == 'workflow_dispatch'
95:  playwright:  99:    if: github.event_name == 'workflow_dispatch'
```

**Gravedad.** Grave.

**Coste.** ~2-3 h. Quitar el `if:` es una línea, pero no basta: el job levanta un `pgvector/pgvector:pg16` sin aplicar `init-roles.sql`. El trabajo real es portar a steps de Actions la secuencia ya probada de `build_test_db.sh`.

**Verificación.** SIN VERIFICAR aquí — **no confirmado en esta dimensión**; el mismo hecho está confirmado en [A4](#a4--autorización-y-datos) y desarrollado en [A6](#a6--ci-y-despliegue), donde además se corrige que el job sí se ejecutó una vez, en el primer run del repositorio, y falló en la instalación de dependencias sin llegar a lanzar pytest.

#### Aunque se dispare a mano, el job `test` de CI no puede pasar: le falta el rol `fulkro_app_bypassrls`

**Qué es.** El helper `_admin_setup` de conftest ejecuta `SET LOCAL ROLE fulkro_app_bypassrls`. Ese rol se crea en `infra/docker/init-roles.sql`, fichero que `build_test_db.sh` aplica en su paso [3/6] pero que el job `test` de CI no ejecuta en ningún momento: su servicio arranca sólo con `POSTGRES_USER=fulkro` y pasa directo a `pytest`.

**Dónde.** `backend/tests/conftest.py:151` · `infra/docker/init-roles.sql:53` · `scripts/build_test_db.sh:50` · `.github/workflows/ci.yml:78`

**Cómo se midió.**
```bash
$ grep -n 'SET LOCAL ROLE' backend/tests/conftest.py
151:    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
$ grep -n 'CREATE ROLE' infra/docker/init-roles.sql
15: CREATE ROLE fulkro_app ...   53: CREATE ROLE fulkro_app_bypassrls ...   84: CREATE ROLE fulkro_migrate ...
# steps del job test en ci.yml: checkout, setup-python, pip install -e .[dev], pytest backend/tests/
```

**Gravedad.** Grave.

**Coste.** Incluido en el hallazgo anterior (mismo fichero y mismos steps).

**Verificación.** CONFIRMADO como análisis estático, y así lo etiqueta el auditor. El verificador comprobó los tres eslabones por separado y añadió un matiz que refuerza la conclusión: el rol ausente no es el único bloqueante, el job tampoco ejecuta `alembic upgrade head` ni el seed, de modo que la base arranca sin esquema. El título atribuye el fallo a una causa cuando hay al menos dos independientes.

#### Tres tests dependen del orden de ejecución: fallan aislados y pasan en la pasada completa

**Qué es.** Los tres tests puros de `backend/tests/core/encryption/test_sqlalchemy_types.py` fallan con `RuntimeError: Encryption master key unavailable` en las cinco invocaciones parciales probadas, y sin embargo no aparecen ni en ERRORS ni en FAILURES de ninguna de las dos pasadas completas. El mecanismo está en el código: `get_master_fernet()` lleva `@lru_cache(maxsize=1)` y el fixture que limpia esa caché está declarado sólo dentro de `test_master_key.py`. Es fragilidad de test, no regresión de producto.

**Dónde.** `backend/tests/core/encryption/test_sqlalchemy_types.py` · `backend/app/core/encryption/master_key.py:40` y `:52` · `backend/tests/core/encryption/test_master_key.py:24`

**Cómo se midió.**
```bash
$ pytest backend/tests/core/encryption -q --timeout=30
3 failed, 7 passed, 3 errors in 4.71s
E   RuntimeError: Encryption master key unavailable: set FULKRO_MASTER_ENCRYPTION_KEY ...
$ grep -c 'test_encrypted_text' /tmp/a2/fullrun.txt
0        # cero menciones en las 24 MB de la pasada completa
# pero el módulo SÍ se ejecutó allí: línea 44502 ERROR at setup of test_workspace_chat_message_encrypted_at_rest
```

**Gravedad.** Menor.

**Coste.** ~20 min. Mover el fixture autouse de reseteo de caché a un `conftest.py` del directorio para que cubra los dos módulos: un fichero nuevo de 8 líneas y borrar 5 de otro.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.** El propio auditor declara que no aisló el test contaminante pese a cinco intentos.

#### 44 de los 99 tests saltados son tests de funcionalidad retirada (corregido)

**Qué es.** Desglose completo de los 99 skips por motivo real de ejecución: 46 son el opt-out limpio de los tests `@llm` (correcto) y **53 son skips incondicionales**. De esos 53, **44 son funcionalidad retirada** (40 por el drop de `magic_link` en M16/M21 y 4 por la tabla `ens_reinforcements` eliminada en FASE 9.0), **7 apuntan a un router comercial no montado** —no retirado— y **2 son scaffolds de activación futura**, que es lo contrario de código muerto.

**Dónde.** `backend/tests/motors/m16_onboarding/test_m16_client_flow.py` y `test_m16_sessions.py` · `backend/tests/motors/m21_portal_cliente/test_cockpit_create_user_extensions.py` · `backend/tests/motors/m13_commercial/test_m13_commercial.py:111` · `backend/tests/scripts/test_load_ens_measures_catalog.py:96`

**Cómo se midió.**
```bash
$ grep '^SKIPPED' fullrun2.txt | sed -E 's/^SKIPPED \[([0-9]+)\] //; s/^[^ ]+: //' | sort | uniq -c | sort -rn
46 llamada LLM real · opt-in con FULKRO_RUN_LLM_TESTS=1
20 MB-4.bis3 ADR-020 · M16 magic_link consume drop
14 MB-4.bis3 ADR-020 · M16 create_session drop magic_link · tests legacy obsoletos
 7 API comercial m13 (pricing/proposals) no montada en Batch 2 · router comercial dormido
 6 MB-4.bis3 ADR-020 · cockpit_create_user drop magic_link emit · tests legacy obsoletos
 4 FASE 9.0 (ADR-029): tabla ens_reinforcements drop
 1 future M19 activation · post-piloto T1 demand-driven
 1 future M01 activation · post-piloto T1 demand-driven
```

**Gravedad.** Menor.

**Coste.** ~1-2 h. Los 53 se reparten en 5 ficheros y los tres de magic_link concentran 40. Borrar bloques ya marcados como obsoletos es mecánico; el tiempo se va en comprobar que ninguno cubre un camino vivo.

**Verificación.** MAL ETIQUETADO. **Corrección:** el titular original decía «53 son tests muertos de funcionalidad retirada» y esa etiqueta no cubre la población. Sólo 44 lo son; 7 corresponden a un router no montado y 2 a scaffolds de activación futura. Segunda inexactitud corregida: sólo 20 skips llevan la frase literal «tests legacy obsoletos», no 40. El recuento (99 = 46 + 53) reproduce exacto y el verificador confirmó que los 53 son efectivamente incondicionales.

#### `conftest.py` escribe dentro del árbol del repo al importarse, incluso en `--collect-only`

**Qué es.** `conftest.py` llama a `_ensure_m6_signing_dev_key()` a nivel de módulo, que hace `mkdir` de `var/keys/` y genera dos ficheros PEM Ed25519. Ocurre en cualquier invocación de pytest, incluida una recolección en seco. No ensucia `git status` porque `.gitignore` cubre `var/*`, pero es un efecto secundario en disco de un `--collect-only`, y por eso toda la dimensión se ejecutó sobre una copia en `/tmp`.

**Dónde.** `backend/tests/conftest.py:118`, `:91`, `:108`, `:110`

**Cómo se midió.**
```bash
$ diff -rq --exclude=.git --exclude=__pycache__ /home/usuario/dev/Fulkrosys /tmp/a2/Fulkrosys
Only in /home/usuario/dev/Fulkrosys: .ruff_cache
Only in /tmp/a2/Fulkrosys/var: keys        # único artefacto que la suite escribió en el árbol
```

**Gravedad.** Menor.

**Coste.** ~15 min. Una línea: convertir la llamada de nivel de módulo en un fixture de sesión o redirigir el directorio a `tmp_path_factory`.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### El marcador `requires_db` se usa en 5 ficheros pero no está registrado ni hace nada

**Qué es.** Cinco ficheros declaran `pytest.mark.requires_db`. Ese marcador no aparece en la lista `markers` de `pyproject.toml`, así que pytest emite `PytestUnknownMarkWarning` y, más importante, no existe ningún hook que lo use para saltar nada. Es la intención correcta abandonada a medias: 5 ficheros marcados frente a los 346 que realmente dependen de la BD.

**Dónde.** `backend/pyproject.toml:138` · `backend/tests/motors/m11_copiloto/test_client_id_fk.py:26` · `…/test_conversation_crud.py:18` · `backend/tests/motors/m21_portal_cliente/test_approve_plan.py:23` · `backend/tests/motors/m27_conformity/test_readiness_pentest_tier.py:18`

**Cómo se midió.**
```bash
$ grep -rln 'requires_db' backend/tests | wc -l   ; # 5
$ grep -c 'requires_db' backend/pyproject.toml    ; # 0
$ sed -n '138,143p' backend/pyproject.toml
markers = [ "llm: ...", "flaky: ...", "real_auth: ...", "golden: ..." ]
# PytestUnknownMarkWarning: Unknown pytest.mark.requires_db - is this a typo?
```
Los 346 ficheros que sí dependen de la BD se obtienen cruzando los 3.146 nombres de test únicos de las cabeceras de los 3.202 bloques ERROR contra el mapa fichero::test de la recolección.

**Gravedad.** Menor.

**Coste.** ~5 min el registro. El gating real ya está presupuestado en el primer hallazgo de esta dimensión (el hook de skip-si-no-hay-BD), no pasa por marcar 346 ficheros a mano.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

### A3 · La capa de IA (agentes, router LLM, evaluación, RAG)

El núcleo es mejor de lo que sugieren las semillas: `llm_router.py` (456 líneas) es un router serio con SDK oficial, reintentos con backoff 2/8/32 s más jitter, timeout de 120 s, jerarquía de excepciones tipadas, prompt caching real y contabilidad de tokens de caché; y los 13 agentes tienen sus prompts en módulos separados, todos con temperatura ≤ 0,2 declarada. Tres cosas hunden el posicionamiento: la degradación silenciosa a texto `[MOCK]` registrada como éxito, un arnés de evaluación que cubre 0 de 13 agentes (no 1 de 13) y una tabla de precios que cobra Opus 3× de más. Sobre la pregunta del RRF la respuesta es concluyente y negativa: `k=60` está citado al paper de Cormack y no existe ninguna medición, dataset, métrica de recuperación ni notebook en todo el repositorio; además los "pesos" que la pregunta presuponía no existen, la fusión es RRF de libro sin ponderar.

#### Los agentes devuelven texto `[MOCK]` fabricado como si fuera un entregable real, y ningún consumidor lo detecta

**Qué es.** `AgentBase._call_llm` tiene dos caminos de degradación silenciosa: sin clave de API devuelve `_mock_response`, y ante cualquier excepción devuelve `_mock_response` con tag `[MOCK-FALLBACK]`. El diccionario que devuelve `invoke()` no contiene ninguna bandera que distinga mock de real: el único indicio es el prefijo dentro del campo de texto. Además `_mock_response` inventa `tokens_input` contando palabras y fija `tokens_output=50`, y `_log_interaction` los persiste con `status="success"` y con `cost_usd` calculado sobre esos tokens ficticios. Se verificó empíricamente con el Agente 04, el redactor de diagnósticos E-090.

**Dónde.** `backend/app/agents/base.py:176`, `:206` (`except Exception`), `:211` (return del fallback), `:216`, `:301`

**Cómo se midió.**
```bash
$ env -u ANTHROPIC_API_KEY python -c "…from backend.app.agents.agent_04_redactor import Agent04RedactorDiagnosticos…"
{'text': '[MOCK] Agent 4 (Redactor Diagnosticos E-090). Model: sonnet-4.6. Message length: 8.',
 'tokens_input': 3, 'tokens_output': 50, 'cache_creation_input_tokens': 0, ..., 'model': 'sonnet-4.6'}

$ grep -rn "\[MOCK\]\|MOCK-FALLBACK\|is_mock\|_mock_response" --include="*.py" backend/app/ | grep -v "agents/base.py"
# sin salida: ningún consumidor comprueba el prefijo
```

**Gravedad.** Bloqueante.

**Coste.** 1-2 h. `base.py` son 310 líneas y hay dos puntos de retorno más el diccionario de `invoke()` y el `status` del log: añadir `"degraded": True`, propagarlo a `status="degraded"` y devolver tokens 0 son ~15 líneas en un fichero. La hora restante es decidir la política en los consumidores.

**Verificación.** CONFIRMADO. El verificador reprodujo la salida literal y leyó el mecanismo: `_mock_response` fabrica `tokens_input` como suma de palabras de system y user; el diccionario de retorno tiene 13 claves y ninguna bandera; `_log_interaction` persiste `status="success"` y coste sobre tokens ficticios. Amplió el grep de consumidores a frontend y a `.ts/.tsx` sin encontrar guarda alguna. Único atenuante hallado: `response_preview` guarda los primeros 500 caracteres, así que el prefijo queda en la base de datos como indicio pasivo. Corrección menor de referencias de línea, ya aplicada arriba.

#### `claude-opus-4-8` se llama con `temperature`, parámetro que ese modelo rechaza; la lista de exención sólo cubre 4-7

**Qué es.** El router mantiene `_MODELS_WITHOUT_TEMPERATURE = frozenset({"claude-opus-4-7"})` y sólo omite `temperature` para los modelos de ese conjunto. El agente de triaje de hallazgos de seguridad usa `TRIAGE_MODEL = "claude-opus-4-8"` y le pasa `temperature=0.0`. Según la tabla vigente de la API, el muestreo está eliminado y devuelve 400 en Opus 4.7 y 4.8: la lista de exención se quedó congelada en 4.7. La consecuencia es que toda llamada de triaje deriva a `reason="llm_error"` —falla en cerrado, el hallazgo permanece sin triar— pero la funcionalidad está muerta y nada lo señala. El reverso: para los agentes 11 y 19 (`MODEL="opus-4.7"`) la temperatura declarada se descarta en silencio, así que la regla R3 no se aplica realmente en 2 de 13 agentes.

**Dónde.** `backend/app/core/ai/llm_router.py:104` y `:111` · `backend/app/motors/m08_verification/agent/triage_agent.py:33` y `:183` · `backend/app/agents/agent_11_auditor_virtual.py:75` · `backend/app/agents/agent_19_propuestas.py:68`

**Cómo se midió.**
```bash
$ sed -n '104,113p' backend/app/core/ai/llm_router.py
_MODELS_WITHOUT_TEMPERATURE: frozenset[str] = frozenset({ "claude-opus-4-7", })
$ grep -n "TRIAGE_MODEL\|TEMPERATURE" backend/app/motors/m08_verification/agent/triage_agent.py
33:TRIAGE_MODEL = "claude-opus-4-8"
35:TEMPERATURE = 0.0
183:            temperature=TEMPERATURE,
```
El 400 no es una medición: no hay clave ni red para emitir la llamada. Procede de la tabla de referencia oficial de la API. Lo verificable en el repositorio es la asimetría: 4-7 exento, 4-8 no.

**Gravedad.** Grave.

**Coste.** 5 min el parche (una línea en el frozenset), 30 min con test. `backend/tests/core/ai/test_llm_router.py` ya tiene montado el patrón de mock del SDK.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### El arnés de evaluación cubre 0 de 13 agentes, no 1 de 13

**Qué es.** Existe un único dataset dorado con 10 entradas y un único evaluador registrado, ambos para `deliverable_text_auditor`. Ese objetivo no es uno de los 13 agentes: su módulo no declara ninguna clase, no hereda de `AgentBase` y no aparece en el registry. La intersección entre lo evaluado y los 13 agentes es vacía, y también lo es con los 31 IDs del registry. El arnés en sí está bien construido (2.428 líneas, cargador Pydantic `frozen`, umbrales de regresión con semántica de exit code, runner, API de runs, migración propia y vista admin con su spec de Playwright): la infraestructura no es el cuello de botella, los datos sí.

**Dónde.** `docs/catalogs/golden_datasets/deliverable_text_auditor/v1.json` · `backend/app/motors/m_observability/evaluators/deliverable_text_auditor_evaluator.py:41` y `:179` · `backend/app/motors/m_observability/deliverable_text_auditor_capability.py` · `backend/app/agents/registry.py`

**Cómo se midió.**
```bash
$ find docs/catalogs/golden_datasets -type f
docs/catalogs/golden_datasets/README.md
docs/catalogs/golden_datasets/deliverable_text_auditor/v1.json     # entries = 10
$ grep -n "^class \|AgentBase\|AGENT_ID" backend/app/motors/m_observability/deliverable_text_auditor_capability.py
# sin salida: no hay clase, no hereda de AgentBase
$ grep -n "deliverable_text_auditor" backend/app/agents/registry.py       # sin salida
$ grep -rn "class .*(AgentBase)" --include="*.py" backend/app/agents/ | wc -l
13
```

**Gravedad.** Grave.

**Coste.** 3-5 h por agente para poblar; el arnés no requiere obra. La referencia empírica es el único dataset existente: 10 entradas por objetivo, más un evaluador de ~180 líneas con su registro como plantilla.

**Verificación.** CONFIRMADO. El verificador enumeró las 13 subclases una a una (sin dobles conteos), comprobó que sólo hay un evaluador registrado y que no existe otro golden dataset en el árbol. Dos matices que no invalidan la etiqueta: el propio dataset se autodescribe con un campo `agent_name`, que es el origen de la ilusión "1 de 13"; y la capability sí hace una llamada LLM real, así que "0 agentes evaluados" no equivale a "cero comportamiento LLM evaluado". La cifra decorativa de 2.428 líneas no se pudo reproducir exactamente (1.980 en los nueve módulos obvios, 2.371 sumando migración, página y tests): está en el orden de magnitud pero depende del recorte.

#### La tabla de precios que alimenta el tope de gasto cobra Opus 3× de más y Haiku un 20% de menos

**Qué es.** `pricing.py` se autodescribe como «fuente ÚNICA del coste por interacción» y existe porque el tope mensual de gasto sumaba 0. El emparejamiento es por substring de familia, así que `claude-opus-4-7` y `claude-opus-4-8` caen ambos en `opus` y reciben la tarifa inflada. Efecto neto: el guardarraíl de dinero dispara demasiado pronto en los dos agentes Opus (los caros: 8.000 y 16.000 tokens de salida máximos) y demasiado tarde en Haiku. Además, como el mock hereda el alias `sonnet-4.6`, las filas fabricadas del hallazgo anterior también devengan coste ficticio contra ese tope.

| Familia | Codificado (in/out $ por Mtok) | Tarifa vigente | Desviación |
|---|---|---|---|
| haiku | 0,80 / 4,00 | 1,00 / 5,00 | −20% (infracobra) |
| sonnet | 3,00 / 15,00 | 3,00 / 15,00 | correcto |
| opus | 15,00 / 75,00 | 5,00 / 25,00 | ×3 (sobrecobra) |

**Dónde.** `backend/app/core/ai/pricing.py:15-18` y `:27`

**Cómo se midió.**
```bash
$ sed -n '13,32p' backend/app/core/ai/pricing.py
MODEL_PRICE_USD: dict[str, tuple[float, float]] = {
    "haiku": (0.80, 4.00),
    "sonnet": (3.00, 15.00),
    "opus": (15.00, 75.00),
}
_DEFAULT_PRICE: tuple[float, float] = (3.00, 15.00)
```
La tarifa correcta no vive en el repositorio: procede de la tabla de referencia oficial de la API. El ratio ×3 es aritmética sobre esos dos números.

**Gravedad.** Grave.

**Coste.** 15 min. Dos tuplas en un fichero de 53 líneas. El coste real es decidir si se mantiene el match por familia —que no puede distinguir versiones con tarifas distintas— o se pasa a claves exactas enumerando los identificadores válidos del mapa de abajo.

**Verificación.** CONFIRMADO. El verificador contrastó la tarifa contra la tabla oficial y verificó además la cadena que el comando no medía: `compute_cost_usd` tiene 5 call-sites y todos escriben `LLMInteractionLog.cost_usd`, y `copilot_rate_limit.py:176/186` hace `SUM(cost_usd)` para el tope mensual, así que «alimenta el tope de gasto» es real y no retórico. Matiz de población: la mayoría de agentes usan el alias `sonnet-4.5`, que cae en la misma familia, así que la afirmación de que sonnet es correcto se sostiene para lo que el código realmente ejecuta.

#### La jerarquía de excepciones tipadas del router no tiene un solo consumidor, y la clave ausente escapa como `TypeError` crudo

**Qué es.** El router define y documenta cuatro excepciones declarándolas «contrato público estable para callers», y `complete()` documenta en su `Raises:` cuál corresponde a cada código HTTP. Cero ficheros fuera del propio router las importan o capturan. Peor: el caso que `LLMAuthError` dice cubrir (credencial ausente) no se cumple. Construir el router sin clave funciona —sólo emite un warning— y la llamada revienta con un `builtins.TypeError` del SDK, lanzado al construir la petición, antes de que exista un error HTTP que mapear. Ninguna de las ocho cláusulas de `_call_with_retries` atrapa `TypeError`.

**Dónde.** `backend/app/core/ai/llm_router.py:59`, `:63`, `:67`, `:71`, `:190`, `:199`

**Cómo se midió.**
```bash
$ grep -rn "except LLM\|LLMAuthError\|LLMRateLimitError\|LLMBackendError\|LLMBadRequestError" \
    --include="*.py" backend/app/ | grep -v "core/ai/llm_router.py"
# sin salida: ningún consumidor
$ env -u ANTHROPIC_API_KEY python -c "from backend.app.core.ai.llm_router import LLMRouter; r=LLMRouter(); ...r.complete(...)"
ANTHROPIC_API_KEY not set — LLM calls will fail. Set it in .env or environment.
router constructed OK, api_key repr= ''
RAISED: builtins.TypeError "Could not resolve authentication method. Expected either api_key or auth_token to be set..."
```

**Gravedad.** Grave.

**Coste.** 30-45 min. Dos cambios en el router: validar la clave en `__init__` (donde ya existe el `if not self._api_key` que hoy sólo hace `logger.warning`) y añadir `TypeError` a las cláusulas de reintento. Que los consumidores adopten las excepciones es trabajo aparte: son los 14 ficheros que hoy usan el router.

**Verificación.** CONFIRMADO. El verificador amplió el grep más allá del alcance declarado —añadiendo `backend/tests/` y `scripts/`— y sigue devolviendo cero: ni un import, ni un `except`, ni una referencia en tests.

#### No existe ninguna evidencia que justifique `k=60` ni los pesos del recuperador híbrido; y los pesos no existen

**Qué es.** Respuesta concluyente. `RRF_K = 60` lleva el comentario `# Standard constant (Cormack et al.)` y el docstring cita el paper de 2009: el propio código declara que el valor viene del paper, no de una medición local. La búsqueda de evidencia contraria es negativa por cuatro vías. Segunda corrección a la premisa: no hay pesos; `_rrf_fuse` suma exactamente `1.0/(k+rank)` por lista, sin coeficiente, así que BM25 y vector pesan igual por construcción. Sobre los tests: `test_rrf_fuse_basic` calcula el valor esperado a partir de la propia constante `RRF_K`, así que pasaría igual con k=1 o k=9999.

**Dónde.** `backend/app/corpus/retrieval.py:33`, `:15`, `:161-166` · `backend/tests/corpus/test_hybrid_search.py:92` y `:99` · `docs/spec/ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md:2337`

**Cómo se midió.**
```bash
$ grep -n "RRF_K" backend/app/corpus/retrieval.py
33:RRF_K = 60  # Standard constant (Cormack et al.)
$ sed -n '161,177p' backend/app/corpus/retrieval.py
    """RRF fusion: score(d) = sum(1/(k + rank_i(d))) across all lists."""
        if cid in bm25_ranks:   score += 1.0 / (k + bm25_ranks[cid])
        if cid in vector_ranks: score += 1.0 / (k + vector_ranks[cid])
$ grep -rn -i "ndcg\|mrr\|recall@\|precision@\|hit_rate" --include="*.py" --include="*.md" --include="*.ipynb" .
# ninguna métrica de recuperación: todos los 'mrr' son Monthly Recurring Revenue; todos los 'hit_rate', caché de prompt
$ find . -name "*.ipynb"        # cero notebooks
$ grep -rn -i "rrf\|reciprocal rank" docs/ --include="*.md"
docs/spec/…v2.1 (2).md:2337:3. Fusión por Reciprocal Rank Fusion → top 30 únicos.   # sin valor de k
```

**Gravedad.** Menor (el valor es un default defendible; lo que falta es la medición).

**Coste.** 6-10 h construir la evaluación mínima. El corpus son ~127 chunks y el patrón consulta→medida-ENS-esperada ya existe en dos casos; extrapolarlo a 30-50 consultas etiquetadas más una función de recall@5 y un barrido de k son un fichero de datos y uno de runner. Dependencia dura: PostgreSQL con pgvector poblado.

**Verificación.** CONFIRMADO. El verificador atacó la afirmación negativa por vías adicionales (grep de `cormack|k=60`, inventario de `scripts/`) sin encontrar contraejemplo, y confirmó la tautología del test. Precisión menor: hay más smoke tests de relevancia con consultas escritas a mano en otros ficheros del directorio (3+3+4), pero ninguno agrega métrica ni fija k.

#### El modelo que queda en el rastro de auditoría está codificado a mano, no leído de la respuesta real

**Qué es.** Dos sitios escriben metadatos de trazabilidad con literales: `audit_dry_run_service.py:254` persiste `model_used="claude-opus-4-7"` en la fila del resultado, y `autopilot/orchestrator.py:480` pasa `model_version="claude-opus-4-8"` al manifiesto, cuyo resultado se hashea en `run_manifest_hash` bajo una cabecera que invoca «determinismo». Hoy coinciden por casualidad con el modelo efectivo, pero están desacoplados: cambiar el `MODEL` del agente no actualiza el literal. La respuesta real ya trae el dato correcto y `AgentBase` ya lo propaga. En un producto cuyo argumento de venta es la trazabilidad y la cadena de hash, un campo de procedencia que no procede de la ejecución es una debilidad de la tesis.

**Dónde.** `backend/app/agents/services/audit_dry_run_service.py:254` · `backend/app/motors/m08_verification/autopilot/orchestrator.py:480` · `backend/migrations/versions/sand_audit_dry_run_001.py:66` · `backend/app/core/ai/llm_router.py:299`

**Cómo se midió.**
```bash
$ sed -n '253,256p' backend/app/agents/services/audit_dry_run_service.py
            a11_payload=a11_payload,
            model_used="claude-opus-4-7",
$ sed -n '476,482p' backend/app/motors/m08_verification/autopilot/orchestrator.py
            model_version="claude-opus-4-8",
$ grep -n "model_used" backend/migrations/versions/sand_audit_dry_run_001.py
66:  sa.Column("model_used", sa.String(50), server_default="claude-opus-4-7")
```

**Gravedad.** Menor.

**Coste.** 45 min. Dos sitios de escritura en dos ficheros; el valor correcto ya viaja en la clave `model` del diccionario de `invoke()`. Lo que añade tiempo es comprobar que el payload lo arrastra hasta ese punto del servicio.

**Verificación.** CONFIRMADO. El verificador confirmó además, midiendo lo que el comando no cubría, que `manifest.py` incluye `model_version` en la tupla canónica que se hashea, así que el literal entra de verdad en `run_manifest_hash`. Agravante que encontró y que el hallazgo no explotaba: si la llamada al A11 falla, el payload queda como `{'error': …, 'fallback': True}` y `model_used` se sigue escribiendo, es decir, la fila afirma un modelo incluso cuando no hubo modelo.

#### Nueve cadenas de modelo dispersas y tres mapas de alias duplicados: no hay registro central

**Qué es.** No existe registro central de modelos. El mapa de alias está triplicado literalmente en tres ficheros y las dos copias de copiloto omiten dos alias, así que ya han divergido. De las nueve cadenas distintas, ocho son identificadores válidos; la novena, `claude-sonnet` a secas, no lo es, pero vive dentro de un docstring y jamás alcanza el runtime.

| Cadena | Ocurrencias | ¿Identificador válido? | Nota |
|---|---|---|---|
| `claude-opus-4-7` | 9 | Sí | modelo vigente |
| `claude-sonnet-4-5` | 7 | Sí | activo (legacy) |
| `claude-haiku-4-5` | 7 | Sí | vigente |
| `claude-sonnet-4-6` | 5 | Sí | vigente |
| `claude-opus-4-6` | 5 | Sí | vigente |
| `claude-opus-4-8` | 3 | Sí | vigente |
| `claude-haiku-4-5-20251001` | 2 | Sí | ID completo legítimo |
| `claude-sonnet-4-5-20250929` | 1 | Sí | ID completo legítimo |
| `claude-sonnet` | 1 | **No** | sólo en docstring (`m11_copiloto/api.py:295`); no ejecuta |

**Dónde.** `llm_router.py:185` y `:188` · `config.py:20-21` · `agents/base.py:30` · `copilot_cliente_service.py:306` · `copilot_admin_service.py:362` · `agent_14_copiloto/prompts.py:21` · `m08_verification/llm_classifier.py:32`, `agent/triage_agent.py:33`, `remediation/guide_generator.py:307`, `external/findings_ingester.py:149` · `m04_gap/llm_prioritizer.py:323` · `m23_retainer/agent_15_vigilancia.py:219` · `m_observability/deliverable_text_auditor_capability.py:69` · `m11_copiloto/api.py:295`

**Cómo se midió.**
```bash
$ grep -rhoE "claude-[a-z0-9.-]+" --include="*.py" backend/app/ backend/migrations/ | sed 's/[.·]$//' | sort | uniq -c | sort -rn
      9 claude-opus-4-7 / 7 claude-sonnet-4-5 / 7 claude-haiku-4-5 / 5 claude-sonnet-4-6
      5 claude-opus-4-6 / 3 claude-opus-4-8 / 2 claude-haiku-4-5-20251001
      1 claude-sonnet-4-5-20250929 / 1 claude-sonnet
$ sed -n '295p' backend/app/motors/m11_copiloto/api.py
    """Chat con streaming SSE de tokens desde el LLM (anthropic/claude-sonnet)."""
```

**Gravedad.** Menor.

**Coste.** 2-3 h. De los ficheros afectados, ~14 son sitios ejecutables de selección de modelo; el resto son comentarios, docstrings y la columna de migración. Crear un módulo de constantes y reescribir los tres mapas duplicados es mecánico; el tiempo lo consume la suite, que afirma cadenas literales.

**Verificación.** CONFIRMADO. El verificador reprodujo la tabla y contrastó la validez contra la referencia oficial. Dos imprecisiones de alcance, ambas conservadoras: las cadenas viven en **21 ficheros** (19 de `backend/app` más dos migraciones), no 19, porque el conteo de ficheros se hizo sólo sobre `app` mientras la tabla se computó sobre `app` + `migrations`; y como una de las nueve cadenas no es un identificador de modelo, **los IDs distintos son 8**. Ninguna toca la tesis.

### A4 · Autorización y datos

La superficie de autorización es mejor de lo que sugiere una lectura por grep: hay una dependencia global `authenticate_request` cableada en `main.py:408` que cubre las 1.201 rutas, y se verificó contra la aplicación importada que ningún endpoint fuera de la whitelist responde sin sesión. La RLS tampoco tiene agujeros de cobertura: las 154 tablas con `client_id`/`project_id` tienen `ENABLE ROW LEVEL SECURITY` declarado en migraciones y los GUC fallan cerrados. Los problemas son otros tres: cuatro flujos públicos legítimos inalcanzables, un test de la cadena de hashes que no comprueba la cadena, y una función de verificación de encadenamiento que sólo es correcta invocada desde un rol BYPASSRLS, cosa que ningún camino de producción hace.

#### Cuatro routers públicos con puerta propia quedaron fuera de la whitelist: la dependencia global los rechaza antes de su gate

**Qué es.** Cuatro conjuntos de endpoints están diseñados para llamantes sin sesión —su credencial es un magic-link, un Bearer de agente o una firma HMAC— pero no están en la whitelist, así que reciben 401 antes de ejecutar su propia validación. Los docstrings son inequívocos: «El firmante firma SIN cuenta: la PUERTA es el magic-link»; «Agente (auth por token · SIN require_owner · el token ES la auth)». Efecto colateral: `_webhook_authorized` y el gate Bearer nunca llegan a ejecutarse, son código muerto no ejercitado. Falla en cerrado (no expone datos) pero deja inoperativos la firma Ed25519 de actas E-012/MAGERIT E-028/DdA E-040, la aprobación de actas y el agente on-prem completo. Los comentarios de la propia whitelist documentan haber sufrido ya cuatro veces el mismo bug.

**Dónde.** `backend/app/auth/global_dep.py:56` y `:109` · `backend/app/motors/m05_signing/document_public_api.py:49` · `backend/app/motors/m18_communication/minutes_public_api.py:43` · `backend/app/motors/m_remediation/agent_api.py:45` · `backend/app/motors/m31_whatsapp/api.py:329` y `:333` · `frontend/lib/api/document-signing.ts:5`

**Cómo se midió.** Con la aplicación real importada y `TestClient`, sin cookie:
```bash
401 POST /api/v1/webhooks/360dialog        -> {"detail":"Authentication required"}
401 POST /api/v1/document-signing/sign     -> {"detail":"Authentication required"}
401 POST /api/v1/minutes-signing/approve   -> {"detail":"Authentication required"}
401 POST /api/v1/agent/remediation/enroll  -> {"detail":"Authentication required"}
401 GET  /api/v1/agent/remediation/commands-> {"detail":"Authentication required"}
200 GET  /api/v1/health                    -> {"status":"ok","environment":"development"}
```
La línea de control (`/health` en 200) demuestra que el 401 no es un artefacto del entorno de test sino discriminación real por whitelist.

**Gravedad.** Bloqueante.

**Coste.** 1-2 h. Cuatro entradas en un único fichero (dos prefijos y dos exactos, ~8 líneas con su comentario justificativo), siguiendo el patrón ya existente de `/api/v1/contract-signing/`. El resto es escribir cuatro tests de regresión que afirmen `status != 401` sin cookie.

**Verificación.** CONFIRMADO. El verificador reprodujo la sonda y añadió el discriminador decisivo que faltaba: parcheando en memoria `_is_whitelisted -> True`, las mismas peticiones pasan a 200, 422 y a un 401 con detalle propio («Falta token de agente»), lo que prueba que el 401 original lo emite la dependencia global y no un 404 de ruta inexistente ni otra dependencia. Comprobó además que el agente on-prem sólo envía `Authorization: Bearer`, nunca cookie, así que el flujo está roto de verdad.

#### El test de la cadena de hashes no comprueba manipulación: 0 asserts negativos y 0 intentos de mutación en toda la suite (corregido)

**Qué es.** En `test_audit_log_integrity_checker.py` el único `assert report.ok is True` está dentro del caso vacío, que consulta un UUID aleatorio inexistente: afirma la integridad de un conjunto de 0 filas, que es vacuamente cierta. El docstring del fichero enumera como cubierto el punto «6. Tampered chain detection» y ese test no existe. Y el test de inmutabilidad verifica que los triggers están declarados en `information_schema.triggers`, no que rechacen nada. La regla R6 («audit log inmutable con hash chain») no está respaldada por ninguna aserción negativa ejecutable sobre `audit_log`.

**Dónde.** `backend/tests/motors/m09_audit_prep/test_audit_log_integrity_checker.py:11`, `:29`, `:43`, `:84`

**Cómo se midió.**
```bash
$ grep -n "report.ok\|\.ok is\|tamper" motors/m09_audit_prep/test_audit_log_integrity_checker.py
43:    assert report.ok is True          # dentro de test_integrity_per_project_scan_empty (0 filas)
$ grep -rn "UPDATE audit_log\|DELETE FROM audit_log" backend/tests | wc -l
0
```

**Gravedad.** Grave.

**Coste.** 1-2 h. Todo cae en un fichero de 129 líneas y reutiliza fixtures ya importados: tres tests nuevos (cadena poblada en verde, cadena manipulada en rojo con su `first_bad_seq`, e intento de UPDATE/DELETE dentro de `pytest.raises`), ~50 LOC sin tocar producción.

**Verificación.** MAL ETIQUETADO. **Corrección:** el comando estaba acotado a un fichero y las conclusiones se enunciaban sobre todo el repositorio. Ampliando la población hay **2 ficheros que ejercitan el verificador**, no 1: `test_corrective_loop_concurrent.py` inserta 5 loops × 3 transiciones y afirma `report.ok is True` sobre una **cadena poblada de ~15 filas**. Son falsas, por tanto, las frases «es el único fichero» y «ningún test afirma ok is True sobre una cadena poblada». También es demasiado fuerte «ninguna aserción ejecutable»: existe una detección de manipulación real con `assert is_valid is False; assert broken_at == 1` en `test_audit_log_service.py:113-135`, aunque sobre otra tabla (`client_user_audit`). Lo que sí sobrevive intacto y es el hallazgo real: **0 asserts `ok is False` sobre `audit_log` y 0 intentos de UPDATE/DELETE en toda la suite** (verificado también sin distinguir mayúsculas y buscando variantes ORM), más el punto 6 del docstring sin test.

#### La detección de borrado o reordenación sólo la hace una función `SECURITY INVOKER` sobre una tabla con `FORCE RLS`

**Qué es.** Hay dos algoritmos de verificación y sólo uno comprueba el enlace de la cadena. `fn_audit_log_verify_chain()` recorre `audit_log` arrastrando `prev_hash` y comprueba dos condiciones, incluida `hash_prev IS DISTINCT FROM prev_hash`, que es la que detecta que falte o se reordene una fila. El camino Python per-project compara cada fila contra su propio `hash_prev` *almacenado*, y su docstring lo admite: por diseño no puede detectar un borrado intermedio. El problema es que la función completa es plpgsql sin `SECURITY DEFINER` y `audit_log` tiene `ENABLE` + `FORCE ROW LEVEL SECURITY`: invocada por el rol de la aplicación, el `SELECT` se filtra y el resultado deja de ser fiable. Sólo es correcta desde un rol BYPASSRLS, y el único consumidor no escala rol. Colateral: el portal del auditor promete en dos docstrings que la cadena es verificable para ENAC, pero ningún endpoint la expone.

**Dónde.** `backend/migrations/versions/d4f8b2a90001_audit_log_hash_chain_trigger.py:171` y `:197` · `backend/migrations/versions/audit_log_rls_001.py:76` y `:84` · `backend/app/motors/m09_audit_prep/audit_log_integrity_checker.py:88` y `:104` · `backend/app/motors/m09_audit_prep/public_api.py:886`

**Cómo se midió.**
```bash
$ sed -n '197,199p' backend/migrations/versions/d4f8b2a90001_audit_log_hash_chain_trigger.py
        IF r.hash_current IS DISTINCT FROM expected
           OR r.hash_prev IS DISTINCT FROM prev_hash THEN  ok := FALSE;
$ sed -n '76,77p' backend/migrations/versions/audit_log_rls_001.py
op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
$ grep -c 'SECURITY DEFINER' backend/migrations/versions/d4f8b2a90001_*.py   ; # 0
$ grep -c bypassrls backend/app/motors/m09_audit_prep/simulacro_pre_enac_service.py ; # 0
```
El paso final —que bajo el rol de aplicación la función devuelva `ok=FALSE`— es deducción de la semántica de PostgreSQL, no una ejecución: no hay base de datos.

**Gravedad.** Grave.

**Coste.** 2-4 h. Una migración nueva que haga `CREATE OR REPLACE` de la función añadiendo `SECURITY DEFINER` y `SET search_path` (el cuerpo son 37 líneas ya escritas), más extender el camino Python para arrastrar el `hash_current` previo (~15 LOC).

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### La suite no se ejecuta en push ni PR: ninguna prueba de autorización, aislamiento RLS o cadena de hashes actúa como gate

**Qué es.** El job `test` está condicionado a `workflow_dispatch`. Los que sí corren son lint, mypy con `continue-on-error: true` y frontend-typecheck. Para esta dimensión eso significa que `test_audit_log_rls_isolation.py` y `test_audit_log_integrity_checker.py` no bloquean ninguna integración. Riesgo añadido si se reactivase tal cual: el job define `DATABASE_URL` con el usuario `fulkro`, que es el `POSTGRES_USER` del servicio y por tanto superusuario, mientras el fixture `db` crea el engine desde esa URL sin ningún `SET ROLE`, pese a que su docstring promete «as fulkro_app (NOSUPERUSER) · RLS is enforced». Un superusuario ignora RLS incluso con FORCE.

**Dónde.** `.github/workflows/ci.yml:59`, `:33`, `:89` · `backend/tests/conftest.py:225` y `:231`

**Cómo se midió.**
```bash
$ grep -n "^  [a-z-]*:$\|if: github.event_name\|continue-on-error\|DATABASE_URL:" .github/workflows/ci.yml
  test:      if: github.event_name == 'workflow_dispatch'
          DATABASE_URL: postgresql+asyncpg://fulkro:test@localhost:5432/fulkro_test
$ sed -n '225,239p' backend/tests/conftest.py | grep -c 'SET ROLE'
0
```

**Gravedad.** Grave.

**Coste.** 2-4 h. El script de provisión ya existe (110 líneas); portarlo al runner y alinear `DATABASE_URL` a `fulkro_app` son ~15 líneas de YAML más una para quitar el `if:`. El grueso es la primera pasada roja: es previsible que aflore fallos hoy enmascarados, sobre todo en los tests de RLS al pasar de superusuario a `fulkro_app`.

**Verificación.** CONFIRMADO. El verificador leyó los bloques completos en vez del grep, comprobó los tres disparadores del workflow e intentó refutarlo buscando otro gate: sólo hay cuatro workflows y una única invocación ejecutable de pytest, dentro del job condicionado. Comprobó además la cifra con más riesgo de mal etiquetado: `find backend/tests -name 'test_*.py' | wc -l` = 581 exacto, mientras `CLAUDE.md` dice ~353.

#### 205 escaladas a rol BYPASSRLS en código, 91 de ellas en ficheros de API (corregido)

**Qué es.** La RLS está bien declarada, pero en el camino de petición se desactiva con frecuencia. La decisión no es accidental ni indocumentada: la migración `fulkro_pii_rls_002.py:8` lo dice con todas las letras, «bajo fulkro_app_bypassrls (el aislamiento real lo dan los filtros app-layer)», y el muestreo confirma que los filtros están (por ejemplo `portal_project` filtra por el `client_id` del usuario autenticado, no de un parámetro del request). Se reporta como riesgo estructural, no como fallo presente: convierte cada uno de esos puntos en un sitio donde un `WHERE` olvidado produce fuga cross-tenant sin que ninguna defensa de base de datos lo detecte.

**Dónde.** `backend/app/motors/m21_portal_cliente/api.py:413` y `:439` · `backend/app/motors/m09_audit_prep/public_api.py:127` · `backend/app/motors/m31_whatsapp/api.py:385` · `backend/migrations/versions/fulkro_pii_rls_002.py:8`

**Cómo se midió.**
```bash
$ grep -rn 'SET LOCAL ROLE fulkro_app_bypassrls' backend/app --include=*.py | wc -l   ; # 231 líneas
# clasificación por capa (líneas): 102 en ficheros *api*.py, 70 servicios/tareas, 37 otros, 22 dev-only
# análisis AST posterior: 7 de esas líneas son comentarios y 19 docstrings -> 205 ejecutables
```

**Gravedad.** Menor (riesgo estructural, no fuga demostrada).

**Coste.** 4-8 h. No se propone eliminar el patrón, sino acotar el riesgo: un test de aislamiento por cada handler cliente-facing con bypass (los del portal son 16, con patrón de test ya existente) y opcionalmente un helper único que envuelva escalada más filtro obligatorio de tenant.

**Verificación.** MAL ETIQUETADO. **Corrección:** el hallazgo se vendía como la corrección de un conteo inflado (265 → 231) y esa corrección no llegó a fondo. Analizando con AST cada ocurrencia, 7 líneas son comentarios y 19 docstrings: las sentencias realmente ejecutables son **205**, y el titular baja de 102 a **91** en ficheros de API. Reparto corregido: 91 request-path, 60 servicios/tareas, 32 otros, 22 dev-only. Segundo error de población: es falsa la frase «no encontré ningún test que afirme que un handler con bypass filtra por el tenant del sujeto autenticado». Existen `test_client_portal_idor_cross_tenant.py` (4 tests que ejecutan el guard bajo bypassrls y afirman 404, nunca 403) y `test_client_portal_idor_tripwire.py`, que rompe el build estáticamente si algún handler del portal deja de llamar al guard. El riesgo estructural es real, pero está mejor defendido de lo que el hallazgo decía.

### A5 · Código muerto y deuda

Las semillas de deuda son casi todas falsos positivos: de las 178 apariciones de "TODO" en `backend/app`, 81 son la palabra castellana y 97 referencias a un ticket, de las cuales 24 dicen explícitamente "cierre/RESOLVED" y 30 son anotaciones de categoría RBAC colocadas justo encima de un `Depends(require_owner)` realmente aplicado. Las 16 "XXX" y el único "FIXME" son placeholders dentro de cadenas: cero marcadores de deuda. El código muerto real es cero: 202 módulos sin import estático, 201 descartados por carga dinámica verificada (registro de plantillas 116=116 exacto, generadores Excel 16=16, autodiscovery por glob, registros de agentes por string) y el único superviviente es un CLI con `__main__`. El hallazgo grave no estaba en las semillas: tres clientes API del frontend apuntan a un prefijo que el backend no monta.

#### Tres clientes API del frontend usan un prefijo que el backend no monta: 64 URLs a 404 y 2 colisiones silenciosas (corregido)

**Qué es.** `frontend/lib/api/magerit.ts` declara `BASE = "/api/v1"` y llama a `/api/v1/analysis/...`, pero el backend monta M02 en `/api/v1/magerit/analysis/...`. `admin-discovery/api.ts` y `admin-workspace/api.ts` declaran `BASE = "/api/v1/projects"` mientras el backend monta `/api/v1/discovery/projects/...` y `/api/v1/workspace/projects/...`. No hay reescritura que lo salve: `next.config.mjs` sólo hace un proxy identidad y los helpers `api()`/`clientApi` no reescriben. Peor que el 404: `getDiscoverySummary` cae en `/api/v1/projects/{id}/summary`, que **sí existe** pero lo sirve otro motor, y `listDiscoveryAlerts` lo mismo con `/alerts`: renderizan datos plausibles de otro motor en vez de fallar.

**Dónde.** `frontend/lib/api/magerit.ts:12` · `frontend/lib/admin-discovery/api.ts:358` · `frontend/lib/admin-workspace/api.ts:157` · `frontend/app/(admin)/admin/projects/[id]/discovery/page.tsx` · `frontend/hooks/useDiscovery.ts:45` · `useWorkspace.ts` · `useMagerit.ts`

**Cómo se midió.** Simulando el cambio de la única constante `BASE` de cada fichero y revalidando contra la tabla de rutas volcada del objeto FastAPI real:
```
frontend/lib/api/magerit.ts:            /api/v1 -> /api/v1/magerit            | 30 URLs, sin match tras el cambio: 0
frontend/lib/admin-discovery/api.ts:    /api/v1/projects -> /api/v1/discovery/projects | 21 URLs, sin match: 0
frontend/lib/admin-workspace/api.ts:    /api/v1/projects -> /api/v1/workspace/projects | 15 URLs, sin match: 0

# antes del cambio, contra la tabla runtime:
grep -c '/api/v1/analysis' runtime_routes.txt -> 0
# colisiones, por introspección del objeto app:
['GET'] /api/v1/projects/{project_id}/summary -> backend.app.api.v1.projects.get_project_summary
['GET'] /api/v1/projects/{project_id}/alerts  -> backend.app.motors.m18_communication.alerts_api.list_project_alerts
```
El control contra un falso positivo del matcher es la simulación: si el emparejador fuese defectuoso, cambiar sólo la constante no podría llevar los 66 casos a cero fallos simultáneamente.

**Gravedad.** Bloqueante.

**Coste.** 1,5-2 h. El cambio es de tres líneas (una constante `BASE` por fichero). El coste está en verificar: 1.600 líneas de cliente y 18 ficheros consumidores que hay que abrir en navegador, lo que exige levantar Postgres y `npm install`.

**Verificación.** MAL ETIQUETADO por doble conteo en el titular. **Corrección:** las **66 plantillas de URL rotas son el total**, y dentro de ellas están las 2 colisiones; el titular original sumaba «66 + 2». Además esas 2 precisamente **no dan 404, dan 200 con datos de otro motor**, así que el reparto correcto es **64 a 404 y 2 a 200**. Por fichero: magerit 30 únicas, discovery 21 únicas (24 call sites), workspace 15 únicas (17 call sites). El verificador reprodujo la sustancia de forma independiente volcando su propia tabla de rutas, resolvió el módulo de los dos endpoints colisionados y confirmó que los tres módulos tienen consumidores reales.

#### `sign_facturae_xades` lanza excepción siempre, incluso cuando `is_xades_available()` devuelve True

**Qué es.** La comprobación de disponibilidad y la implementación están desacopladas: `is_xades_available()` devuelve `(True, "Lib + cert FNMT disponibles")` si encuentra las librerías y el certificado, y aun así `sign_facturae_xades()` cae en un `raise` incondicional (el código real está comentado). El llamador en `invoices_aapp_api.py:248` consulta la disponibilidad antes de firmar, así que un lector concluye que con el certificado puesto la firma funciona. Nunca funciona: el campo `xades_signed` de la respuesta no puede valer True jamás.

**Dónde.** `backend/app/motors/m15_billing/xades_signer.py:92`, `:84`, `:31` · `backend/app/motors/m15_billing/invoices_aapp_api.py:248`

**Cómo se midió.**
```bash
$ sed -n '58,96p' backend/app/motors/m15_billing/xades_signer.py
    available, reason = is_xades_available(certificate_path)
    if not available:  raise FacturaeSignatureNotAvailable(...)
    # Implementacion real (cuando cert disponible):
    # from signxml.xades import XAdESSigner ...
    raise FacturaeSignatureNotAvailable("Implementacion XAdES pendiente - TODO-FACE-XADES-CERT-FNMT-001")
$ grep -rn 'sign_facturae_xades\|is_xades_available' backend/ --include=*.py | grep -v xades_signer.py
invoices_aapp_api.py:248:    available, reason = is_xades_available()
invoices_aapp_api.py:251:            xml_signed = sign_facturae_xades(xml)
```

**Gravedad.** Grave.

**Coste.** 20-30 min. El arreglo honesto no es implementar XAdES sino que `is_xades_available()` devuelva False mientras el cuerpo sea un stub: un fichero, una función de 26 líneas, más ajustar dos aserciones del test que hoy consagran el comportamiento.

**Verificación.** CONFIRMADO. El verificador leyó la función completa: no tiene ningún `return`, el último statement es un `raise` incondicional. Matiz menor: el llamador captura la excepción y degrada con `xades_skip_reason`, así que no rompe en runtime, cosa que el hallazgo no afirmaba.

#### Nueve líneas funcionales apuntan a otro checkout de la máquina del autor (corregido)

**Qué es.** Los ingestores de corpus cargan el `.env` y sus ficheros fuente desde `/home/usuario/fulkro/...`, que es otro checkout, no el repositorio publicado. No son comentarios: son `load_dotenv(dotenv_path=...)` y constantes de módulo evaluadas al importar. A ellos se suman el fallback de venv de `build_test_db.sh` y las dos líneas de `run_tsc.sh` que cablean el `PATH` y el binario de `npx` bajo `~/.nvm`.

**Dónde.** `backend/app/corpus/ccn_stic_ingest.py:26` · `rd311_embed.py:26` · `ccn_pdf_ingest.py:38` y `:63` · `rd311_ingest.py:40` · `backend/tests/corpus/test_rd311_parser.py:14` · `scripts/build_test_db.sh:23` · `scripts/run_tsc.sh:7` y `:10`

**Cómo se midió.**
```bash
$ grep -rIn '/home/usuario' --include=*.py --include=*.ts --include=*.tsx --include=*.yml --include=*.sh . | grep -v node_modules
backend/app/corpus/ccn_pdf_ingest.py:38:load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))
backend/app/corpus/ccn_pdf_ingest.py:63:REPO_ROOT = Path("/home/usuario/fulkro")
backend/app/corpus/rd311_ingest.py:40:HTML_PATH = Path("/home/usuario/fulkro/var/corpus/boe/RD_311_2022_consolidado.html")
backend/app/corpus/rd311_embed.py:26:load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))
backend/app/corpus/ccn_stic_ingest.py:26:load_dotenv(dotenv_path=Path("/home/usuario/fulkro/.env"))
backend/tests/corpus/test_rd311_parser.py:14:HTML_PATH = Path("/home/usuario/fulkro/var/corpus/...")
(+12 apariciones más)
```

**Gravedad.** Grave.

**Coste.** 30-45 min. La sustitución es mecánica: `Path(__file__).resolve().parents[3]` ya se usa en `startup_checks.py:22` como patrón del propio repositorio. El tiempo real se va en decidir si el ingestor debe degradar o fallar cuando el fichero fuente no está.

**Verificación.** MAL ETIQUETADO en la clasificación. **Corrección:** de las 18 apariciones, **9 son funcionales y 9 comentarios**, no 6 y 12. El auditor metió en el saco de comentarios tres líneas ejecutables de shell: `build_test_db.sh:23` (`VENV_PY="/home/usuario/fulkro/.venv/bin/python"` dentro de un `if`), y `run_tsc.sh:7` y `:10`. Siete apuntan a `/home/usuario/fulkro` y dos a `/home/usuario/.nvm`. La consecuencia del hallazgo es mayor de lo que se declaraba, no menor.

#### 194 endpoints sin consumidor en el frontend según el matcher, con infracuento demostrado (corregido)

**Qué es.** De las 1.201 rutas registradas en desarrollo, 194 no tienen correspondencia literal en los 1.231 ficheros del frontend según un emparejamiento por n-gramas de segmentos. No todas son deuda: 24 son de portal/magic-link, 6 son `_dev` y un bloque grande son endpoints legítimamente backend-only. El núcleo accionable es M17 planning: **20 de sus 21 rutas** no tienen consumidor, porque el único cliente envuelve una sola ruta.

**Dónde.** `backend/app/motors/m17_planning/api.py:21` · `frontend/lib/api/planning.ts:12` · `backend/app/motors/m22_discovery/api.py:40` · `backend/app/main.py:715`

**Cómo se midió.**
```
frontend files: 1231   n-grams: 9252   runtime routes: 1201
SIN match de >=2 segmentos contiguos en el frontend: 194
    28 /api/v1/projects · 20 /api/v1/discovery · 20 /api/v1/planning · 10 /api/v1/agents · 9 /api/v1/backup ...
verificación manual: frontend/lib/api/planning.ts sólo contiene ${BASE_PLANNING}/projects/${projectId}/pda/generate
```

**Gravedad.** Menor.

**Coste.** No cuantificable como arreglo único: parte desaparece con el arreglo del prefijo, otra parte es backend-only legítimo y el resto exige una decisión de producto. Lo único costeable es documentar la frontera (~1 h para una tabla en el README de qué motores exponen UI y cuáles son API-only).

**Verificación.** MAL ETIQUETADO. **Corrección:** el método se rompe justo en el cluster que el hallazgo del prefijo demuestra roto. El matcher declara **consumidas** 17 de las 37 rutas de `/api/v1/discovery` y las 23 de `/api/v1/workspace` en bloque, cuando ninguna lo está: al normalizar `${BASE}` a un hueco, segmentos que en la URL real no son contiguos quedan contiguos en la tupla y casan por accidente. Es decir, **194 infracuenta en al menos 40 rutas**. El sub-hallazgo «los 20 endpoints de M22 discovery» es falso: discovery tiene **37 rutas en runtime, las 37 sin consumidor real**. Sólo el dato de M17 planning es correcto (20 de 21), verificado a mano. Mislabel adicional menor: los «1.231 ficheros .ts/.tsx» incluyen `.js/.jsx/.mjs`; sólo `.ts/.tsx` son 1.223.

#### Dos de los 37 propósitos de magic-link devuelven 501 Not Implemented (corregido)

**Qué es.** `DESCARGA_CERTIFICADO_CONFORMIDAD` y `DESCARGA_DOSSIER_FINAL` están en el enum público —se pueden generar enlaces con ellos— pero el resolvedor devuelve 501 con un mensaje que nombra el ticket. Es un stub honesto: avisa en runtime, no finge.

**Dónde.** `backend/app/motors/m25_lifecycle/public_api.py:220`, `:231`, `:254`

**Cómo se midió.**
```bash
$ grep -rn 'HTTP_501_NOT_IMPLEMENTED\|status_code=501' backend/app --include=*.py
m25_lifecycle/public_api.py:220 / :231 / :254
m21_diagnosis/api.py:137: "docxtpl no disponible en este entorno"     # otra población
m22_discovery/api.py:744: "docxtpl no disponible en este entorno"     # otra población
```

**Gravedad.** Menor.

**Coste.** 15 min para documentarlo; no procede arreglarlo, porque implementarlo requiere que exista un primer certificado ENS emitido, como dice el propio código.

**Verificación.** MAL ETIQUETADO en el denominador. **Corrección:** el auditor declaró explícitamente que tomaba el «23» de `CLAUDE.md` «no de un conteo mío», que es justo el error que la auditoría persigue. Instanciando el enum, `len(list(MagicLinkPurpose))` = **37** miembros (ni el docstring del propio enum acierta: dice 35). Con 37 el ratio pasa del 8,7% al 5,4%. Formulación más precisa de la población real: **2 de los 3 `DOWNLOAD_PURPOSES`**, el único conjunto que pasa por ese resolvedor.

#### Las cifras de cabecera de `CLAUDE.md` están desviadas entre un 4,8% y un 67,5% (corregido)

**Qué es.** `CLAUDE.md` declara «~879 endpoints REST · ~353 archivos test_*.py · 160 migraciones Alembic» y «42 motors reales». Ninguna cuadra. Un examinador que abra el fichero raíz y compruebe la primera cifra encuentra un desfase inmediato. El README, en cambio, acierta con los 44 motores.

| Magnitud | Declarado | Medido | Desviación |
|---|---|---|---|
| Motores | 42 | 44 | +4,8% |
| Endpoints REST | ~879 | 1.201 (dev) / 1.185 (producción) | +36,6% |
| Ficheros `test_*.py` | ~353 | 581 | +64,6% |
| Migraciones | 160 | 268 | +67,5% |

**Dónde.** `CLAUDE.md:11` y `:15` · `README.md:156`

**Cómo se midió.**
```bash
$ find backend/tests -name 'test_*.py' | wc -l                                   ; # 581
$ ls backend/migrations/versions/*.py | wc -l                                     ; # 268
$ find backend/app/motors -maxdepth 1 -mindepth 1 -type d | grep -v __pycache__ | wc -l ; # 44
$ cd backend && python -m alembic heads
provider_c002_generado_status_001 (head)      # README dice "1 head: m8_autopilot_canonical_001"
# endpoints, del objeto app real: 1201 APIRoute (dev) / 1185 (producción)
```

**Gravedad.** Menor.

**Coste.** 20 min. Cinco líneas de texto en dos ficheros; los comandos de arriba dan directamente los valores correctos.

**Verificación.** MAL ETIQUETADO en el rango del titular. **Corrección:** el rango real es **4,8% a 67,5%**, no «36% a 65%»: el titular original agrupaba cuatro cifras bajo un intervalo que sólo describe a dos, dejando fuera motores (prácticamente al día) y migraciones (por encima del techo declarado). Las cuatro mediciones reproducen exactas y de forma independiente. El verificador añadió que la cifra de motores de `CLAUDE.md` es internamente inconsistente: dice «41 + 1 + m_cloud_connectors = 42», que suma 43.

#### Las semillas de deuda inducen a error: las 16 "XXX" y el único "FIXME" son cero deuda real

**Qué es.** Ninguna de las 16 apariciones de "XXX" es un marcador de código roto: son máscaras de placeholder dentro de cadenas y docstrings (`E-XXX` como formato de código de entregable, `CVE-2024-XXXX` en un prompt de ejemplo, `PXXXXXXXX` como formato de CIF, un teléfono ficticio, un patrón de URL). El único "FIXME" del backend es el valor de un diccionario que describe un patrón de falso positivo: literalmente, el catálogo que enseña al motor de verificación a ignorar comentarios TODO/FIXME. Quien audite este repositorio por grep concluirá que hay 17 marcadores de deuda; hay cero.

**Dónde.** `backend/app/motors/m08_verification/fp_patterns/catalog.py:391` · `backend/app/dev/router.py:1232` · `backend/app/agents/prompts/agent_18_reunion_exploratoria.py:40` · `backend/app/motors/m09_audit_prep/dossier_generator.py:68` · `backend/app/models/audit_sim.py:90`

**Cómo se midió.**
```bash
$ grep -rn 'XXX' backend/app --include=*.py     # 16 ocurrencias en 14 líneas, todas en strings/comentarios
m09_audit_prep/dossier_generator.py:68:# Mapeo exacto E-XXX -> carpeta
models/audit_sim.py:90:    documento_esperado: ... String(20))  # E-XXX
dev/router.py:1232:    run.contacto_ir_telefono = "+34 6XX XXX XXX"
$ grep -rn 'FIXME' backend/app --include=*.py
m08_verification/fp_patterns/catalog.py:391: "reason": "Comentarios HTML 'TODO/FIXME' sin info sensible",
```

**Gravedad.** Cosmético.

**Coste.** 0 h: no hay nada que arreglar. El valor está en no volver a contarlas como deuda en la siguiente pasada.

**Verificación.** CONFIRMADO. El verificador leyó las líneas enteras y clasificó las 16 ocurrencias una a una. Única corrección: son **14 líneas, no 13** —el auditor afirmaba haberlas leído «una a una» y se dejó una—, y la conclusión se sostiene igualmente para las 14.

### A6 · CI y despliegue

> **Dimensión escalada.** Motivo del auditor: cinco bloqueantes. El patrón común, que es lo que hay que llevarse, es que el CI tarda 1 m 15 s y sale verde porque de los cinco jobs de `ci.yml` sólo dos comprueban algo. La suma de "el job de tests nunca ha corrido" + "mypy enmascarado y abortando" + "safety crasheado y verde" es que el backend no tiene ni tests, ni tipos, ni escaneo de dependencias efectivo en CI; y la ausencia de branch protection hace que ni siquiera importe. Orden de arreglo recomendado por el auditor, y el orden importa: primero `deploy.yml` (10 min, hoy muestra un fallo rojo permanente en un repositorio público), luego `safety` y `typecheck` (baratos y eliminan dos gates que mienten activamente), después el job de tests (2-4 h, con la receta de BD ya copiable), y **la protección de rama al final**: activarla ahora congelaría como obligatorio un CI que no ejecuta tests, consolidando la mentira en vez de resolverla.

#### `deploy.yml` apunta a un host que hoy no responde y sus tres secretos siguen puestos, así que no cae por la rama de skip limpio (corregido)

**Qué es.** El workflow se dispara en todo push a main. El job sólo se omite en verde si los secretos `HETZNER_HOST` o `HETZNER_SSH_KEY` están vacíos; los tres siguen existiendo, así que intenta el SSH. El último fallo observado (18:42Z) no fue por host caído: el SSH conectó y el `git pull --ff-only` falló con «fatal: Not possible to fast-forward, aborting» tras un force-push a main. A esa hora el servidor seguía vivo. Ahora mismo no responde, así que el próximo disparo fallará en la fase SSH.

**Dónde.** `.github/workflows/deploy.yml:8`, `:75`, `:85`, `:93`, `:97`

**Cómo se midió.**
```bash
$ gh api repos/Fulkrodev/Fulkrosys/actions/secrets
{"total_count":3,"secrets":[{"name":"HETZNER_HOST",...},{"name":"HETZNER_SSH_KEY",...},{"name":"HETZNER_USER",...}]}
$ nc -z -w 8 49.13.136.91 22 ; echo $?          # 1 (cerrado)
$ ping -c 3 49.13.136.91                        # 3 transmitted, 0 received, 100% packet loss
$ gh api .../actions/jobs/102598284604/logs | tail -12
 + c4c82e52...0a73baf7 main -> origin/main (forced update)
fatal: Not possible to fast-forward, aborting.
##[error]Process completed with exit code 128.
```

**Gravedad.** Bloqueante (por lo que va a ocurrir en el próximo push, no por lo ocurrido).

**Coste.** 10 min para dejarlo honesto (cambiar el trigger a `workflow_dispatch`, dos líneas, o borrar el workflow y los tres secretos huérfanos); 1-2 h si se quiere CD real de nuevo, que es trabajo nuevo y no reparación.

**Verificación.** MAL ETIQUETADO en dos puntos del titular. **Corrección:** (a) «falla en rojo en cada push a main» es falso como enunciado histórico: de los últimos 25 runs de `deploy.yml`, **24 son success y 1 failure** (4%), y el run de las 18:11Z tiene gate, migrations y deploy los tres en verde, es decir, el despliegue completo funcionó media hora antes del único fallo; lo que el cuerpo describe es una predicción correcta del próximo disparo, no el comportamiento observado. (b) «un servidor que ya no existe» excede lo medido: el valor del secreto no es legible por API, la IP sólo consta en un comentario del YAML, y el silencio a ICMP/TCP desde una máquina no prueba inexistencia. Lo probado: el host desplegó a las 18:11Z y `49.13.136.91` no responde ahora. El verificador comprobó con un control (`1.1.1.1` y `github:22` sí responden) que no es un bloqueo de salida local. Mérito real que se mantiene: el auditor **no** etiquetó el fallo de hoy como «host caído», leyendo el log en vez de asumir la premisa del encargo.

#### El job de tests: 119 de 120 runs saltado, y el único que lo ejecutó murió antes de pytest (corregido)

**Qué es.** `ci.yml` declara cinco jobs, pero `test` y `playwright` llevan `if: github.event_name == 'workflow_dispatch'` y jamás se ha lanzado uno. Lo que corre en cada push es ruff (8 s), mypy enmascarado (17 s) y tsc (1 m). De ahí que el CI entero dure 1 m 15 s teniendo 581 ficheros de test. El comentario del YAML es honesto sobre el motivo y declara que «el gate REAL de tests es LOCAL», pero el efecto neto es que un badge verde no significa que la suite pase.

**Dónde.** `.github/workflows/ci.yml:60`, `:99`, `:102`

**Cómo se midió.**
```bash
$ gh api repos/Fulkrodev/Fulkrosys/actions/runs/34390613589/jobs --jq '.jobs[] | "\(.name) => \(.conclusion)"'
lint => success / typecheck => success / frontend-typecheck => success / test => skipped / playwright => skipped
$ gh api '.../workflows/ci.yml/runs?per_page=1' --jq '.total_count'                        ; # 120
$ gh api '.../workflows/ci.yml/runs?event=workflow_dispatch&per_page=1' --jq '.total_count'; # 0
$ find backend/tests -name 'test_*.py' -type f | wc -l                                      ; # 581
```

**Gravedad.** Bloqueante.

**Coste.** 2-4 h. Quitar el `if:` no basta: el job correría sobre una base vacía sin roles ni extensiones. La receta que falta ya existe y pasa en verde en `admin-polish-empirical.yml:106-135`; el trabajo es portar esas ~30 líneas y ajustar el nombre de base de datos.

**Verificación.** MAL ETIQUETADO en el absoluto. **Corrección:** el enunciado «nunca se ha ejecutado / 0 corridos en 120 runs» es falso para el job, porque el `if:` no estuvo siempre (lo introduce el commit `0eb646bf`). En el run número 1 el job `test` aparece con conclusión **failure**, no skipped, con «Install dependencies» en failure y «Run tests» en skipped. Cifras corregidas: **119 de 120 runs con `test` en skipped y 1 que lo ejecutó y falló en la instalación**; `playwright` 120/120 skipped. La conclusión de fondo —pytest no ha corrido nunca en CI— sobrevive, pero por una razón distinta de la declarada. Las demás cifras (120 runs, 0 workflow_dispatch, 581 ficheros) reproducen exactas, y el auditor separa bien ficheros de casos.

#### El job `typecheck` es doblemente falso: mypy no analiza nada y además está enmascarado

**Qué es.** Dos fallos superpuestos. `continue-on-error: true` convierte cualquier fallo en verde: la API devuelve `conclusion=success` para el paso mientras la anotación del run dice `exit code 2`. Y aunque se quitara la máscara, mypy no comprueba tipos: aborta en la resolución de módulos porque el mismo fichero se alcanza por dos rutas de import, y lo dice su propia salida, «errors prevented further checking». El job tarda 17 s, dice éxito, y el número de ficheros comprobados es cero.

**Dónde.** `.github/workflows/ci.yml:34` y `:35`

**Cómo se midió.**
```bash
$ gh api .../actions/jobs/102597721324/logs | grep -n 'error:\|Found .* error'
205: backend/app/core/email/sender.py: error: Source file found twice under different module names:
     "app.core.email.sender" and "backend.app.core.email.sender"
210: Found 1 error in 1 file (errors prevented further checking)
211: ##[error]Process completed with exit code 2.
$ gh api .../runs/34390613589/jobs --jq '.jobs[]|select(.name=="typecheck")|{conclusion, steps:[...]}'
{"conclusion":"success","steps":[{"name":"Type check","conclusion":"success"}]}
```
Nota de lectura: interpretar el `exit code 2` como «mypy encontró 1 error de tipos» sería la conclusión contraria y falsa; la frase «errors prevented further checking» es el mensaje canónico de aborto previo al análisis.

**Gravedad.** Bloqueante.

**Coste.** 30-60 min. Quitar la máscara es una línea; que mypy analice de verdad es otra (`--explicit-package-bases`, `MYPYPATH`, o invocarlo desde `backend/`). Lo no acotable es el volumen de errores que aparezca la primera vez que corra de verdad sobre 1.055 ficheros; lo honesto sería dejarlo primero como job informativo declarado como tal.

**Verificación.** CONFIRMADO. Las dos mitades se sostienen por separado y el verificador subraya que este es justo el punto donde una lectura ingenua del código de salida daría la conclusión opuesta.

#### El job `safety` crashea, no produce informe y su parser "tolerante" lo pinta de verde

**Qué es.** El paso ejecuta `safety check --json --output safety-report.json --continue-on-error || true`. El binario revienta al importarse por una incompatibilidad typer/click, luego no llega a escribir el informe. A continuación el script Python de filtrado abre el fichero dentro de un `try/except` y, al no existir, imprime «safety report no legible … se trata como sin CRITICAL» y hace `sys.exit(0)`. El job termina en éxito habiendo escaneado cero dependencias. Los comentarios del YAML que afirman «gate REAL (CRITICAL bloquea)» y «safety corre de verdad y sube report» son empíricamente falsos.

**Dónde.** `.github/workflows/security-scan.yml:75`, `:100`, `:104-105`, `:113-115`

**Cómo se midió.**
```bash
$ gh api .../actions/jobs/101726206038/logs | sed -n '920,927p'
RuntimeError: Type not yet supported: <class 'safety.cli_util.CustomContext'>
safety report no legible ([Errno 2] No such file or directory: 'safety-report.json') · se trata como sin CRITICAL
$ gh run download 34117049372 -D /tmp/a6art && find /tmp/a6art -type f
/tmp/a6art/npm-audit-report/npm-audit-report.json
/tmp/a6art/bandit-report/bandit-report.json        # safety-report NO está
```
No se reporta ninguna cifra de vulnerabilidades porque la población escaneada es cero: un «0 CVEs críticos» reproduciría siendo falso, ya que 0 aquí no es «ninguna vulnerabilidad» sino «ninguna medición». Esa distinción es el hallazgo.

**Gravedad.** Bloqueante.

**Coste.** 20-40 min. Sustituir el comando roto (`safety scan` o `pip-audit`, que no necesita cuenta) y reescribir el bloque de 18 líneas para que un informe ilegible sea fallo y no éxito. El resto del job no se toca.

**Verificación.** CONFIRMADO por doble vía independiente: la traza del log y el listado de artefactos del run (`total_count=2`, sin `safety-report`, pese a que el paso de subida es `if: always()`).

#### No hay branch protection ni rulesets: ningún job bloquea nada, pese a que tres workflows dicen "block merge"

**Qué es.** La API devuelve 404 «Branch not protected» para main y una lista de rulesets vacía. No existe ningún required status check. Por tanto se puede pushear directo a main —de hecho así se trabaja: los 120 runs de `ci.yml` son de evento push y ninguno de pull request—, un PR con CI en rojo es mergeable, y las frases que venden gates son literalmente falsas. El force-push a main que rompió el deploy es síntoma directo de esta ausencia.

**Dónde.** `.github/workflows/security-scan.yml:4`, `:5`, `:14` · `.github/workflows/admin-polish-empirical.yml:21` · `.github/workflows/deploy.yml:29`

**Cómo se midió.**
```bash
$ gh api repos/Fulkrodev/Fulkrosys/branches/main/protection
{"message":"Branch not protected","status":"404"}
$ gh api repos/Fulkrodev/Fulkrosys/rulesets
[]
$ gh api repos/Fulkrodev/Fulkrosys --jq '{private,visibility,default_branch}'
{"default_branch":"main","private":false,"visibility":"public"}
$ gh run list --workflow=ci.yml --limit 100 --json event --jq '[.[].event]|group_by(.)|map({event:.[0],n:length})'
[{"event":"push","n":100}]
```
Se consultan los dos mecanismos (protección clásica y rulesets) porque basta con que uno esté activo para que sí haya bloqueo.

**Gravedad.** Bloqueante.

**Coste.** 15 min la configuración (es UI/API de GitHub, no toca ficheros) y 10 min el texto: cinco líneas en tres ficheros que hoy afirman bloqueos inexistentes. Atención al orden: hacerlo antes que los tres hallazgos anteriores consolidaría el problema.

**Verificación.** CONFIRMADO. El verificador añadió una tercera comprobación que el auditor no hizo y que refuerza la conclusión: `/repos/.../rules/branches/main` —reglas efectivas, que incluirían rulesets heredados de organización— también devuelve `[]`. Único desliz: la frase «gate HIGH severity = block merge» está en la línea 4, no en la 5.

#### `landing/` es el directorio más activo del repo y no tiene ninguna cobertura de CI (corregido)

**Qué es.** Los filtros de paths de los workflows no contemplan `landing/`: `security-scan.yml` sólo se dispara con `backend/**/*.py` y ficheros de dependencias, y `admin-polish-empirical.yml` sólo con `frontend/**`. `ci.yml` sí se dispara (no tiene filtro de paths) pero sus tres jobs activos sólo miran `backend/` y `frontend/`, así que sobre `landing/` no ejecuta absolutamente nada. Confirmación observacional: los Security Scan recientes son todos de evento `schedule`, ninguno de push.

**Dónde.** `.github/workflows/security-scan.yml:23` · `admin-polish-empirical.yml:37` y `:42` · `ci.yml:22` y `:52`

**Cómo se midió.**
```bash
$ git log -5 --name-only --format="" | grep -v '^$' | cut -d/ -f1 | sort | uniq -c | sort -rn
      3 landing    2 docs    1 LICENSE    1 .gitignore        # cuidado: son FICHEROS, no commits
$ gh run list --workflow=security-scan.yml --limit 5
completed success Security Scan main schedule 34117049372 2026-09-07
completed success Security Scan main schedule 33392728569 2026-08-31      # todos schedule, ninguno push
$ grep -ric landing .github/workflows/*.yml      # 0 en los cuatro
```

**Gravedad.** Grave.

**Coste.** 1-3 h. Depende de qué sea `landing/`, que queda fuera de esta auditoría: si es HTML/CSS estático, un job con un linter y un check de enlaces son ~30 líneas de YAML; si tiene toolchain propia, hay que descubrirla primero.

**Verificación.** MAL ETIQUETADO en el soporte, no en la conclusión. **Corrección:** el comando cuenta **ficheros** y el texto los presenta como commits; el reparto real de los cinco últimos commits es **3 que tocan `landing/` y 1 que toca `docs/`**, no 2. Además dos de los hashes iterados en el segundo comando (`e63d214`, `e72ceca`) **no son ancestros de HEAD**: son huérfanos del force-push, así que se midió otra población (verificados los cinco reales, la conclusión aguanta: 0 ficheros de `frontend/`). Medida más sólida de la actividad, aportada por el verificador: en los últimos 30 commits hay **128 ficheros de `landing/` frente a 49 de `backend/` y 11 de `frontend/`**, y `frontend/` no se toca desde el 2026-06-20 ni `backend/` desde el 2026-06-17.

#### El gate de bandit deja pasar los 174 hallazgos que el propio escáner detecta, incluido el único de severidad alta

**Qué es.** Bandit escanea de verdad (1.055 ficheros, 194.625 LOC). El problema es la calibración: `--severity-level high` **y** `--confidence-level high` a la vez. El informe real muestra 117 LOW + 56 MEDIUM + 1 HIGH = 174 detectados, y sin embargo la lista `results` —la que decide el código de salida— está vacía: ni siquiera el único HIGH supera el filtro, porque su confianza no es alta. El gate está calibrado para no dispararse nunca con el estado actual del código.

**Dónde.** `.github/workflows/security-scan.yml:56-59`

**Cómo se midió.**
```bash
$ python3 -c "import json; r=json.load(open('/tmp/a6art/bandit-report/bandit-report.json'));
   print('results:',len(r['results'])); print(r['metrics']['_totals']); print('ficheros:',len(r['metrics'])-1)"
results: 0
{"CONFIDENCE.HIGH":105,"CONFIDENCE.LOW":39,"CONFIDENCE.MEDIUM":30,
 "SEVERITY.HIGH":1,"SEVERITY.LOW":117,"SEVERITY.MEDIUM":56,"loc":194625,"nosec":0}
ficheros: 1055
```
Aquí hay dos poblaciones que dan conclusiones opuestas: `results` (lo que supera los filtros y decide el gate) y `metrics._totals` (todo lo detectado). Reportar desde `results` daría «bandit: 0 problemas», cifra reproducible y conclusión falsa. La consistencia interna lo confirma: ambos desgloses suman 174 mientras `results` es 0.

**Gravedad.** Grave.

**Coste.** 10 min el cambio (dos líneas: bajar a `medium` y quitar el filtro de confianza); el triaje de los 57 hallazgos que entrarían es aparte y no cabe en esos 10 minutos.

**Verificación.** CONFIRMADO. El verificador reprodujo el artefacto y validó la prueba de consistencia. Matiz que corrige a mejor: «`--exclude __pycache__,tests` es inoperante» es impreciso; no es inoperante, es mal apuntado: no excluye ningún test (no hay ninguno bajo `backend/app`) pero sí descarta en silencio un fichero legítimo, `m08_verification/tools/testssl_runner.py`, porque «testssl» contiene la subcadena «tests». De ahí el 1.056 en disco frente al 1.055 del informe.

#### `npm audit` calibrado en `critical` deja pasar 3 advisories HIGH

**Qué es.** El gate usa `--audit-level=critical` y el informe real muestra `{info:0, low:1, moderate:0, high:3, critical:0, total:4}`: hay tres advisories altos (nanoid, next, postcss) y ninguno crítico, así que el job pasa siempre. A diferencia de safety, esto sí está documentado con honestidad en el YAML: el fix de Next.js 14 sería next@16, cambio mayor, y se difiere. Aun así, el umbral está colocado justo por encima de todo lo que existe. El job no hace `npm ci` en ningún paso: audita directamente contra el lockfile, y npm avisa de que `--production` está obsoleto.

**Dónde.** `.github/workflows/security-scan.yml:155-157`

**Cómo se midió.**
```bash
$ python3 -c "import json; r=json.load(open('/tmp/a6art/npm-audit-report/npm-audit-report.json'));
   print(r['metadata']['vulnerabilities']); [print(' -',k,v['severity']) for k,v in r['vulnerabilities'].items()]"
{'info': 0, 'low': 1, 'moderate': 0, 'high': 3, 'critical': 0, 'total': 4}
 - nanoid high / - next high / - postcss high / - postcss-selector-parser low
```

**Gravedad.** Grave.

**Coste.** 5 min el umbral (una línea); el cierre real de los tres advisories pasa por el salto Next 14 → 16, que el propio comentario descarta por romper el App Router y que no se estima aquí.

**Verificación.** CONFIRMADO sobre el mismo artefacto que el job usó para decidir su código de salida. El verificador añade que `next` y `postcss` son dependencias directas y `nanoid` transitiva, y valora que el auditor no convirtiera el desglose `prod: 339` en «los cuatro son de runtime».

#### El gate de heads de Alembic en `deploy.yml` es fail-open: si Alembic revienta, el gate pasa

**Qué es.** El paso captura `heads="$(python -m alembic heads 2>&1 || true)"` y falla sólo si `grep -c '(head)'` es ≥ 2. El `2>&1 || true` mete el mensaje de error en la variable y anula el código de salida, así que si Alembic revienta (import roto, migración con error, base inalcanzable) el texto no contiene «(head)», el contador vale 0 y el gate pasa en verde. Sólo detecta el caso multi-head, nunca el caso «Alembic no arranca». Hoy funciona de verdad; el diseño sólo puede fallar hacia el lado permisivo, que es el peligroso en un gate previo a producción.

**Dónde.** `.github/workflows/deploy.yml:69-72`

**Cómo se midió.**
```bash
$ gh api .../actions/jobs/102597721393/logs | sed -n '966,982p'
966: heads="$(python -m alembic heads 2>&1 || true)"
968: n="$(echo "$heads" | grep -c '(head)' || true)"
969: if [ "${n:-0}" -ge 2 ]; then echo "::error::Multiple Alembic heads (${n}) · prod-breaker"; exit 1; fi
981: provider_c002_generado_status_001 (head)
982: Alembic heads = 1
```

**Gravedad.** Menor (riesgo latente, no fallo observado).

**Coste.** 10 min. Cuatro líneas del mismo bloque: quitar el `|| true`, dejar que un fallo tumbe el paso y añadir la condición simétrica de fallar también si el contador es 0.

**Verificación.** CONFIRMADO, y el verificador ejecutó en `/tmp` la parte que el auditor declaró no poder ejecutar: replicando el shell con un comando que revienta, la variable captura el error, el contador da 0, la condición es falsa y el bloque termina en `exit 0` imprimiendo «Alembic heads = 0». El fail-open queda demostrado empíricamente, no sólo por lectura. Se valora que el auditor no exagerase: el gate sí mide bien hoy.

#### `admin-polish-empirical`, el único gate de calidad serio del repo, lleva 81 días sin ejecutarse (corregido)

**Qué es.** Es con diferencia el mejor de los cuatro workflows: levanta postgres pgvector, provisiona extensiones, funciones y roles, aplica `alembic upgrade head`, arranca uvicorn y next, y corre Playwright con axe sobre tres portales, generando claves Ed25519 efímeras por run para no depender de secretos. Y funciona: sus últimos runs son verdes en 11-12 minutos. El problema es que su filtro de paths es `frontend/**` y el desarrollo se ha movido a `landing/`, así que su verde es histórico, no actual.

**Dónde.** `.github/workflows/admin-polish-empirical.yml:37-38` y `:42-43`

**Cómo se midió.**
```bash
$ gh run list --workflow=admin-polish-empirical.yml --limit 5 ; date -u +%F
completed success ... 11m33s 2026-06-20T17:36:52Z
completed success ... 12m37s 2026-06-17T15:53:30Z
2026-09-09
```

**Gravedad.** Menor.

**Coste.** 5 min para reactivarlo (`workflow_dispatch` ya está declarado: basta lanzarlo) y ~12 min de runner para saber si sigue verde. Dejarlo cableado son dos líneas añadiendo `landing/**` a los bloques de paths.

**Verificación.** CONFIRMADO, con corrección de redondeo: son **81 días** (2026-06-20 → 2026-09-09), unos dos meses y veinte días, algo más que los «2 meses y medio» declarados. El verificador ató la causa con una medición propia: el último commit que toca `frontend/` es del 2026-06-20, exactamente el que disparó ese último run. Se valora que el hallazgo diga «sin ejecutarse» y no «roto», y que explicite que un verde de junio no es evidencia de que pase hoy.

#### 45 usos de acciones de GitHub que ya se fuerzan a Node 24; el aviso sale en todos los runs (corregido)

**Qué es.** `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`, `actions/upload-artifact@v4` y `actions/cache@v4` declaran Node 20, deprecado; el runner ya los ejecuta sobre Node 24 y emite un aviso en cada job. No rompe nada ni afecta a ningún gate, pero ensucia todos los logs.

**Dónde.** `.github/workflows/ci.yml:14` · `deploy.yml:33` · `security-scan.yml:41` · `admin-polish-empirical.yml:77`

**Cómo se midió.**
```bash
$ gh run view 34390613589 2>&1 | grep -c 'Node.js 20 is deprecated'
3        # una anotación por cada job ejecutado (3 de 5; los otros 2 están skipped)
$ grep -rn 'uses: actions/' .github/workflows/ | sed 's/.*uses: //' | sort | uniq -c
     13 actions/checkout@v4   6 actions/setup-node@v4   11 actions/setup-python@v5
     15 actions/upload-artifact@v4    1 actions/cache@v4
```

**Gravedad.** Cosmético.

**Coste.** 10 min. Cinco identificadores con 45 ocurrencias en cuatro ficheros; el único que merece leerse antes de subir es `upload-artifact`, que cambió de comportamiento entre v4 y v5.

**Verificación.** MAL ETIQUETADO: **la cifra publicada no reproduce**. El auditor declaraba 30 ocurrencias y 4 identificadores; el mismo grep da **46 líneas `uses: actions/`, de las cuales 45 son acciones afectadas**, con el desglose de arriba, y omitía `actions/cache@v4`, que también se basa en Node. Se descartó que fuese diferencia de estado: `.github/workflows/` no se toca desde el 2026-06-16. La sustancia (los cuatro workflows afectados y el aviso en cada job) sí reproduce.

### A7 · Lo que se afirma frente a lo que es

> **Dimensión escalada.** Motivo del auditor: cuatro bloqueantes, y los cuatro comparten una causa raíz que ninguna corrección individual resuelve. El repositorio se republicó como snapshot limpio el 2026-06-09 arrastrando intacta la documentación de una vida anterior: otro historial, otra licencia, otro producto con Radar, otra estructura de directorios. Corregir las cuatro frases sin decidir qué papel juega `CLAUDE.md` en el repositorio público deja el problema vivo: son 929 líneas escritas como bitácora interna de sesiones, no como documentación de un proyecto abierto, y en su forma actual son el mayor pasivo de credibilidad del repositorio pese a ser lo primero a lo que el README manda al lector. La decisión que el auditor pide antes de seguir es si `CLAUDE.md` se queda y se le retira el rol de "especificación canónica", si se poda a un documento de estado con cifras medidas, o si sale del árbol publicado; de eso depende que los hallazgos 2 y 6 sean media hora o media jornada. Los otros tres bloqueantes son independientes y suman 20 minutos entre los tres. Zonas sin barrer por el escalado: los 40+ README de motor, los ~331 marcadores TODO/FIXME contrastados contra lo declarado, `docs/SYSTEM_KNOWLEDGE_BASE.md` y los docstrings.

#### El README declara licencia propietaria sobre un repositorio publicado bajo Apache-2.0

Ver el bloque homónimo en [A1](#a1--arranca-en-una-máquina-limpia). Mismo hecho, misma medición, mismo dictamen (CONFIRMADO): `README.md:192-194` frente a `LICENSE:190`, ambos en el commit HEAD `0a73baf7`. Coste 5 minutos, una sección de tres líneas.

#### Toda la cadena de evidencia de `CLAUDE.md` es irresoluble en el repositorio publicado: 0/15 tags, 0/12 commits, 10/11 documentos

**Qué es.** El README dirige al evaluador a `CLAUDE.md` como fuente canónica. Ese documento sostiene 120 líneas con «CERRADO», «PASS», «ZERO regression», «empirical» y «shipped», y las respalda con tres tipos de puntero verificable: tags git, hashes de commit y documentos de auditoría enlazados. Ninguno de los tres resuelve. El efecto en entrevista es el peor posible: cada «empirical» queda sin nada detrás y el evaluador extiende la sospecha al resto.

**Dónde.** `CLAUDE.md:3`, `:301`, `:519`, `:793`, `:918` · `README.md:14`

**Cómo se midió.**
```bash
$ git tag | wc -l
0
$ for c in 85ef44dd f1b26d6e bbaa2770 dc98c119 064571f9 bcb56e4 db880da 29da928 4d3fb18 6e7f800 73f21c2 b20f135; do
    git cat-file -e "$c^{commit}" 2>/dev/null && echo "OK $c" || echo "MISS $c"; done
MISS (los 12)
$ grep -oE '\]\(([^)]+\.md)\)' CLAUDE.md | sed 's/](//;s/)//' | sort -u | while read -r l; do [ -e "$l" ] || echo "MISS $l"; done
MISS docs/audits/AUDIT_EJECUTABLE_4_PHASE_7_0_PRE_FIX_DB_STATE.md
MISS docs/audits/AUDIT_EJECUTABLE_5_SESION_3B_2B_10_SIMULACRO_PRE_ENAC_STATE.md
MISS docs/audits/AUDIT_EJECUTABLE_7_7_ESIGNATURE_STATE.md      ... (10 de 11 rotos)
$ ls docs/archive
ls: cannot access 'docs/archive': No such file or directory
$ grep -cE 'CERRADO|PASS|ZERO regression|empirical|shipped' CLAUDE.md
120
```
Se mide si la evidencia ofrecida existe, no si el trabajo se hizo alguna vez: eso es indecidible desde el árbol publicado y se declara en la sección 3.

**Gravedad.** Bloqueante.

**Coste.** 2-4 h. 39 líneas contienen punteros no resolubles y 120 contienen afirmaciones de estado que hay que triar una a una sobre un fichero de 929 líneas. Dos salidas: traer los documentos y crear los tags —sólo posible si el historial viejo se conserva en algún sitio— o reescribir el bloque de estado sin punteros muertos.

**Verificación.** CONFIRMADO. Las tres mediciones reproducen exactas. El verificador comprobó además el denominador del titular contando los nombres citados como tag: son exactamente 15. El único enlace vivo es `docs/pricing/CANONICAL_PRICING.md`.

#### El README afirma que Alembic tiene 1 head y el análisis del grafo encuentra 4; además el head que nombra no lo es

**Qué es.** El diagrama del README documenta «migrations/versions/ # Migraciones Alembic (1 head: m8_autopilot_canonical_001)». El análisis estático del grafo de las 268 revisiones encuentra 4 heads. Y `m8_autopilot_canonical_001` no puede ser head: `invoice_correlative_unique_001.py:25` la declara como su `down_revision`. Esta segunda medición es autosuficiente e independiente del recuento. Además la afirmación contraria ya vive dentro del repositorio: `CLAUDE.md` habla repetidamente de «alembic multi-head DEFER» como deuda conocida.

**Dónde.** `README.md:156` · `backend/migrations/versions/invoice_correlative_unique_001.py:25` · `CLAUDE.md:422`

**Cómo se midió.** Parseando `revision` y `down_revision` de los 268 ficheros (incluidas las tuplas de merge) y quedándose con las revisiones que nadie referencia:
```
revisiones: 268
HEADS: 4
   cluster6_client_mfa_001
   provider_c002_generado_status_001
   radar_v9_perfect_f_001
   remediation_enhancement_b35_e_001
$ grep -n 'down_revision' backend/migrations/versions/invoice_correlative_unique_001.py
25:down_revision: Union[str, None] = "m8_autopilot_canonical_001"
```

**Gravedad.** Bloqueante.

**Coste.** 5 min la documentación (una línea del README); el merge real de las ramas es otra decisión, de ingeniería, y `CLAUDE.md` ya la registra como deuda deliberada.

**Verificación.** CONFIRMADO. El verificador reprodujo los 268/4 y validó que la definición de head implementada es la correcta.

> **Discrepancia abierta que este informe no puede cerrar.** Tres dimensiones independientes (A1, A5 y el log de CI leído en A6) ejecutaron `alembic heads` y obtuvieron **una sola línea**, `provider_c002_generado_status_001 (head)`, y A5 recorrió además el grafo desde los heads declarando 268 revisiones alcanzables y cero huérfanas. A7 parseó los ficheros con una expresión regular y encontró **cuatro** revisiones no referenciadas. Ambas mediciones están en el paquete, ambas pasaron verificación adversarial en su dimensión y son incompatibles. Antes de tocar el README conviene resolverlo con una medida decisiva —`alembic heads --verbose` sobre el árbol actual, contrastado con el listado de las cuatro revisiones candidatas— porque de ella depende si el README está desactualizado en una palabra o si hay tres ramas colgando.

#### El README describe un cuarto portal (ENS Radar) y dos directorios de documentación que no existen

**Qué es.** `README.md:30` afirma «Cuatro portales: admin (Marcos), cliente, auditor (ENAC) y ENS Radar (captación)». El subsistema fue retirado por completo —lo declara el propio `CLAUDE.md:166`— y no queda ni un fichero Python ni un directorio de frontend. En paralelo, el README manda al lector a `docs/doctrine/` y dibuja `docs/doctrine/` y `docs/audits/` en el árbol del repositorio. Ninguno de los dos existe. Un evaluador que siga el README acaba en tres callejones sin salida en la misma página.

**Dónde.** `README.md:30`, `:40`, `:164`, `:165` · `CLAUDE.md:166`

**Cómo se midió.**
```bash
$ grep -rl 'ens_radar' backend/app --include=*.py | wc -l   ; # 0
$ ls backend/app/motors/ | grep -ci radar                    ; # 0
$ find frontend -type d -name '*radar*' | wc -l              ; # 0
$ for d in docs/doctrine docs/audits; do [ -d "$d" ] && echo "OK $d" || echo "MISS $d"; done
MISS docs/doctrine
MISS docs/audits
```
Alcance declarado: quedan migraciones con prefijo `radar_v9_*` en `versions/`, pero migraciones históricas no son un portal.

**Gravedad.** Bloqueante.

**Coste.** 10 min. Cuatro líneas en un único fichero: borrar un portal de una enumeración y dos filas de un bloque ASCII.

**Verificación.** CONFIRMADO. El verificador amplió la búsqueda a «ENS Radar» y «/radar» sobre todo `backend/app` y `frontend`: sólo quedan dos comentarios que lo mencionan como patrón histórico, y los grupos de rutas del frontend son `(admin)`, `(client-portal)`, `(legal)`, `(portal)` y `(public)`.

#### `docs/spec/README.md` llama "traducción oficial ISO/IEC 27001:2022" a un entregable que no está en el repositorio, y el script de corpus lo etiqueta "From our own deliverables"

**Qué es.** El índice de la especificación lista como entregable 17 una «traducción oficial ISO/IEC 27001:2022». El fichero no existe en `docs/spec/`. En paralelo, `scripts/corpus_download.py` registra esos dos ficheros como fuentes P0 del corpus normativo bajo el comentario «ISO 27001 (from our own deliverables)» y la nota «From our own deliverables, not a download». Llamar «traducción oficial» y «nuestro propio entregable» a una traducción de una norma ISO —contenido licenciado, no publicable— es la afirmación con más superficie legal de esta dimensión. Agravante técnico independiente: la resolución de esas fuentes locales está cableada a `Path.home() / "fulkro"`, otro checkout, así que el script no puede funcionar en ningún clon.

**Dónde.** `docs/spec/README.md:112-113` · `scripts/corpus_download.py:146`, `:150`, `:154`, `:211`

**Cómo se midió.**
```bash
$ grep -n 'oficial ISO' docs/spec/README.md
112:17. `ISO27001_ES_PARTE1.md` — traducción oficial ISO/IEC 27001:2022
$ ls docs/spec/ | grep -ci iso
0
$ grep -n 'own deliverables' scripts/corpus_download.py
146:    # --- ISO 27001 (from our own deliverables) ---
150:           "From our own deliverables, not a download"),
$ grep -n 'Path.home()' scripts/corpus_download.py
211:        local_path = Path.home() / "fulkro" / src.url.replace("local://", "")
```
La oficialidad no se puede medir desde el repositorio y no se afirma; lo medido es que el índice lo llama oficial, que no está, y que el script lo reclama como entregable propio.

**Gravedad.** Grave.

**Coste.** 30 min. Dos líneas en el índice y cinco en el script. El único trabajo con sustancia es decidir si las dos fuentes salen del catálogo o se reetiquetan como material interno no distribuible.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### Las cifras del bloque "Estado runtime" de `CLAUDE.md` están desviadas en todas las magnitudes medibles

**Qué es.** Ampliación del hallazgo homónimo de [A5](#a5--código-muerto-y-deuda), con las magnitudes del frontend añadidas. La desviación es por defecto, no por exceso, así que el daño no es de inflar sino de credibilidad de proceso: un documento fechado que se presenta como «estado runtime» y no coincide con nada de lo que se cuenta en treinta segundos dice que las cifras no se miden, se escriben.

| Magnitud | Declarado (`CLAUDE.md`) | Medido |
|---|---|---|
| Motores | 42 | 44 (el README dice 44, correcto) |
| Ficheros `test_*.py` | ~353 | 581 |
| Migraciones | 160 | 268 |
| Modelos ORM | 52 | 62 |
| Páginas frontend | 120+ | 167 |
| Componentes TSX | 331+ | 426 |
| Specs Playwright | 140+ | 300 |

**Dónde.** `CLAUDE.md:11`, `:15`, `:17` · `README.md:23`

**Cómo se midió.**
```bash
$ find backend/tests -name 'test_*.py' | wc -l                    ; # 581
$ ls backend/migrations/versions/*.py | wc -l                     ; # 268
$ find backend/app/models -name '*.py' ! -name '__init__.py' | wc -l ; # 62
$ find backend/app/motors -mindepth 2 -maxdepth 2 -name '__init__.py' | wc -l ; # 44 (paquetes reales, no __pycache__)
$ find frontend/app -name 'page.tsx' | wc -l                      ; # 167
$ find frontend/components -name '*.tsx' | wc -l                  ; # 426
$ find frontend/tests -name '*.spec.ts' | wc -l                   ; # 300
```
Los «~879 endpoints REST» quedan fuera: el conteo de decoradores da 1.001 pero mide otra población (decoradores en el fuente, no rutas registradas), y arrancar la app para contar paths del OpenAPI requiere dependencias y base de datos.

**Gravedad.** Grave.

**Coste.** 15 min. Tres líneas de `CLAUDE.md` y dos del README; los siete comandos ya están escritos. La práctica de pegar el comando medidor junto a la cifra ya la aplicó el propio proyecto en la landing.

**Verificación.** SIN VERIFICAR en esta dimensión — **no confirmado aquí**; las cuatro magnitudes de backend sí fueron verificadas de forma independiente en [A5](#a5--código-muerto-y-deuda), donde reproducen exactas.

#### `docs/spec/README.md` enumera 24 nombres de fichero como índice de lectura y 16 no resuelven (corregido)

**Qué es.** El índice ordena «sigue este orden al abrir los ficheros. No te saltes pasos» y nombra los entregables con backticks como rutas exactas. Los ficheros existen en disco pero renombrados con sufijos de descarga duplicada: el índice dice `ENS_PLATFORM_MASTER_SPEC_v2.1.md` y en disco está `ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md`. El daño es doble: el índice no se puede seguir, y los sufijos « (1)» y « (2)» en los nombres de la especificación canónica son la huella visible de un paquete copiado de una carpeta de descargas.

**Dónde.** `docs/spec/README.md:32`, `:68`, `:112`, `:113`

**Cómo se midió.**
```bash
$ cd docs/spec && grep -oE '`[A-Z][A-Z0-9_]+[A-Za-z0-9_.()]*\.md`' README.md | tr -d '`' | sort -u |
    while read -r f; do [ -e "$f" ] && echo "OK   $f" || echo "MISS $f"; done | sort | uniq -c
      8 OK
     16 MISS
$ ls | grep -E 'MASTER_SPEC|F1_1'
ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md
F1_1_POLITICAS_CRITICAS_E100_E104 (1).md
```
Deliberadamente no se normalizan los sufijos antes de comprobar: lo que se audita es la usabilidad del índice, no la existencia del contenido. Por eso se reporta «nombres que no resuelven» y no «documentos que faltan», que sería falso para catorce de ellos y cierto sólo para los dos ISO.

**Gravedad.** Grave.

**Coste.** 30 min. Las rutas están en un único fichero de 321 líneas. Alternativa del mismo orden: renombrar los ficheros en disco quitando el sufijo y ajustar las referencias cruzadas, que obliga a un grep de cierre (al menos `docs/catalogs/template_catalog_v1.yaml` apunta al nombre con sufijo).

**Verificación.** MAL ETIQUETADO: **la cifra no reproduce**, aunque la metodología es correcta y la población es la que se declara. Ejecutando el mismo comando salen **16 MISS y 8 OK sobre 24**, no 14 y 10. El fallo va en la dirección de subestimar el problema. El fenómeno del renombrado está verificado y el matiz del auditor —catorce existen con otro nombre y sólo dos faltan de verdad— es correcto.

#### Se presentan 31 IDs de agente de los que 13 son invocables y 14 están deprecados (corregido)

**Qué es.** De las 31 entradas del registry, 12 tienen estado «activo», 14 «deprecated» (eliminados por redundantes con motores deterministas), 2 «externalized_to_motor» (el stub LLM nunca se implementó y `/invoke` devuelve 410), 2 «reservado» y 1 «scaffolding_covered_by_engine». En disco hay 15 ficheros `agent_*.py`. La cifra 31 es literalmente cierta como «IDs registrados»; el problema es publicarla sin la partición en un documento que la usa como indicador de tamaño del sistema junto a endpoints y motores.

**Dónde.** `CLAUDE.md:11` · `backend/app/agents/registry.py:51` · `docs/spec/README.md:154`

**Cómo se midió.**
```bash
$ python3 -c "import re,collections; s=open('backend/app/agents/registry.py').read();
   print('entradas:',len(re.findall(r'^\s{4}\d+:\s*\{',s,re.M)));
   print(collections.Counter(re.findall(r'\"status\":\s*\"([a-z_]+)\"',s)))"
entradas: 31
Counter({'deprecated': 14, 'activo': 12, 'reservado': 2, 'externalized_to_motor': 2, 'scaffolding_covered_by_engine': 1})
$ find backend/app/agents -maxdepth 1 -name 'agent_*.py' | wc -l    ; # 15
```

**Gravedad.** Grave.

**Coste.** 10 min. Una línea de `CLAUDE.md` y una cláusula del README. El desglose ya lo da el comando y la justificación por agente ya está escrita dentro del registry.

**Verificación.** MAL ETIQUETADO en el encuadre. **Corrección:** (a) el titular original decía «se presentan 31 agentes IA», pero `CLAUDE.md:11` dice literalmente «31 IDs registry agentes (taxonomía en registry.py)» —ya usa la etiqueta honesta que el hallazgo reclamaba y remite al fichero— y `README.md:23-26` no da ninguna cifra de agentes, así que la cita del README no sostiene la acusación de inflado. (b) «sólo 12 tienen código real» toma `activo=12` como equivalente a «con código», pero el propio docstring del registry describe `scaffolding_covered_by_engine` como stub funcional invocable: los **invocables son 13**, y también son 13 los IDs distintos con fichero en disco. El sustrato —14 de 31 son agentes eliminados y la cifra se publica sin partición— es cierto y está verificado.

#### Se publica "73 medidas del Anexo II" mientras el catálogo canónico del propio repositorio declara 79

**Qué es.** `landing/index.html` afirma seis veces «73 medidas». El catálogo que el backend usa como fuente declara en su cabecera `medidas_count: 79` y contiene 79 entradas. El mismo fichero explica la tensión: su campo `codigos_validados_contra` dice «magerit_ens_mapping (73 códigos confirmados en DB)», y sus notas admiten que tres medidas tienen la descripción pendiente. El repositorio tiene dos poblaciones y publica una sin decir cuál.

**Dónde.** `landing/index.html:1294` y `:1298` · `docs/catalogs/ens_measures_catalog_v1.yaml:6` y `:12`

**Cómo se midió.**
```bash
$ grep -c '73 medidas' landing/index.html                                     ; # 6
$ grep -n 'medidas_count\|codigos_validados_contra' docs/catalogs/ens_measures_catalog_v1.yaml
6:  codigos_validados_contra: magerit_ens_mapping (73 códigos confirmados en DB)
12: medidas_count: 79
$ grep -cE '^- codigo: ' docs/catalogs/ens_measures_catalog_v1.yaml           ; # 79
```
No se afirma cuál de los dos números es correcto frente al RD 311/2022: el texto de la norma no está en el repositorio en forma consultable para ese conteo.

**Gravedad.** Menor.

**Coste.** 20 min si el catálogo tiene razón; más si hay que resolver el RD. Seis ocurrencias en un fichero más una cifra de cabecera; el coste no está en editar sino en abrir el Anexo II y determinar si 79 incluye refuerzos o submedidas.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### El README de ADRs declara una convención de nombres y un registro de anomalías que sus propios ficheros incumplen

**Qué es.** `docs/architecture/README.md` fija como obligatorio el naming `ADR-XXX_{slug-kebab-case}.md` para los ADR ≥ 046, declara un registro de anomalías explícitamente vacío y publica una tabla de «ADRs publicados aquí» que termina en ADR-053. En el directorio hay ADR-054 y ADR-055, ninguno en la tabla; ADR-054 está citado dos veces en `CLAUDE.md` como ADR canónico vigente; y `ADR-055-auto-remediation.md` usa guion en vez del guion bajo que el mismo README impone. Es el hallazgo de menor daño de la lista, pero es el mismo patrón en miniatura: un documento que describe una disciplina que el árbol no sigue.

**Dónde.** `docs/architecture/README.md:25`, `:43`, `:57` · `docs/architecture/ADR-055-auto-remediation.md`

**Cómo se midió.**
```bash
$ ls docs/architecture/ | grep -E '^ADR-05[0-9]'
ADR-050_copilot_admin_guided_mode_vision_defer_mb14.md
...
ADR-054_project_scoped_admin_ux.md
ADR-055-auto-remediation.md
$ grep -oE 'ADR-0[0-9]{2}' docs/architecture/README.md | sort -u | tail -1   ; # ADR-053
$ grep -c 'ADR-054' CLAUDE.md                                                ; # 2
```
No se reporta salto de numeración: 054 y 055 son consecutivos. Lo que falla es la tabla y el naming, no la continuidad.

**Gravedad.** Cosmético.

**Coste.** 15 min. Dos filas nuevas en la tabla y un renombrado de fichero con su grep de referencias.

**Verificación.** CONFIRMADO. El verificador comprobó que la convención aplica explícitamente a los ADR ≥ 046 y que `ADR-055` es el único de los diez ficheros del directorio que la incumple. Valora expresamente que el auditor no inventase un salto de numeración inexistente.

### A8 · Terceros y licencias

Además del caso conocido del catálogo de medidas ENS, el barrido encuentra material de terceros mucho más grande y peor situado, todo él dentro del fixture de tests. El resto sale limpio: las 131 plantillas del document factory, los catálogos de reglas y los DOCX no reproducen prosa del CCN —verificado con un cruce de n-gramas contra los 975.277 caracteres de guías que sí están en el repositorio—, no hay código de terceros vendorizado ni fuentes tipográficas empaquetadas, y MAGERIT y los textos UE sólo necesitan atribución. No existe fichero `NOTICE`. **Aviso importante: cinco de los seis hallazgos de esta dimensión no fueron cubiertos por el verificador adversarial, incluidos los dos bloqueantes.**

#### Texto íntegro de nueve guías CCN-STIC embebido en `corpus_seed.sql.gz`, incluida su propia cláusula que prohíbe la reproducción

**Qué es.** `backend/tests/fixtures/corpus_seed.sql.gz` es un volcado `pg_dump` de 28,7 MB descomprimidos que puebla las tablas del corpus. Entre sus fuentes hay nueve guías CCN-STIC (800 a 808), con publisher declarado en el propio dump, parseadas con pdfplumber y troceadas en chunks de ~1.400 caracteres. No es un índice ni un mapping: es el cuerpo del texto, incluidas las páginas de créditos (NIPO, «© Autor y editor, 2025») y el aviso legal de cada guía. Las guías CCN-STIC no son disposiciones legales, así que el problema es la reproducción, no la atribución.

**Dónde.** `backend/tests/fixtures/corpus_seed.sql.gz` (11.198.978 bytes versionados) · `scripts/build_test_db.sh:97`

**Cómo se midió.** Cruzando por clave foránea los chunks contra su fuente dentro del propio dump:
```
UE/EUR-Lex           chunks=  904 chars= 1186788
CCN-STIC             chunks=  697 chars=  975277
AEPD-RIESGO-EIPD     chunks=  249 chars=  357355
RD_311_2022          chunks=  127 chars=  224513

$ zcat ... | grep -ao '"pages": [0-9]*, "parser": "pdfplumber+pypdf", "category": "ccn_stic"' | grep -o '[0-9]*' | paste -sd+ | bc
450                     # páginas de PDF ingeridas
$ zcat ... | grep -aoc "Quedan rigurosamente prohibidas, sin la autorizaci.n escrita del Centro Criptol.gico Nacional"
9                       # una por guía
```
Media de 1.399 caracteres por chunk y **cero chunks por debajo de 200 caracteres**: son párrafos de cuerpo, no titulares ni índices.

**Gravedad.** Bloqueante.

**Coste.** 3-5 h. Un fichero binario a eliminar; `build_test_db.sh` ya carga el fixture bajo un `if [ -f ]` con aviso de fallback, así que no rompe al faltar. Cuatro ficheros de test consultan esas tablas y hay que decidir entre regenerar un seed sólo con RD 311/2022 y textos UE o marcarlos skip. El coste real no es el borrado sino la reescritura de historia: el blob entra en el commit raíz, con 292 commits descendientes.

**Verificación.** SIN VERIFICAR — el verificador no cubrió este hallazgo. **No confirmado.** Dado que es el hallazgo con más superficie legal del informe, conviene reproducir las mediciones antes de actuar; el comando está arriba y no necesita infraestructura.

#### Guía de la AEPD bajo CC BY-NC-SA 4.0 en el mismo fixture: NonCommercial y ShareAlike son incompatibles con Apache-2.0

**Qué es.** La fuente `AEPD-RIESGO-EIPD` («Gestión de riesgo y evaluación de impacto en tratamientos de datos personales», junio 2021) está ingerida completa en el mismo dump, y su primer chunk contiene la propia declaración de licencia de la obra. NonCommercial choca con que el repositorio sea la plataforma de una consultoría comercial, y ShareAlike choca de raíz con conceder el material bajo Apache-2.0 a cualquier tercero. Es un caso distinto del CCN: aquí no es que falte permiso, es que la licencia que sí existe prohíbe el uso que hace el repositorio.

**Dónde.** `backend/tests/fixtures/corpus_seed.sql.gz` (fila `knowledge_sources` con `code=AEPD-RIESGO-EIPD` y las 249 filas de chunks asociadas)

**Cómo se midió.**
```bash
$ zcat backend/tests/fixtures/corpus_seed.sql.gz | LC_ALL=C grep -ao "Creative Commons[^|]\{0,80\}" | sort | uniq -c
      1 Creative Commons Atribución-NoComercial-CompartirIgual 4.0\nInternacional.\nRESUMEN EJECUTIVO
# volumen, con el mismo agregado por fuente: AEPD-RIESGO-EIPD  chunks=249  chars=357355
```
La incompatibilidad NC/SA con Apache-2.0 es lectura jurídica, no medición, y se marca como tal. Lo medido es que la guía entera está y que su propia licencia va copiada dentro.

**Gravedad.** Bloqueante.

**Coste.** 1 h adicional. Comparte fichero y reescritura de historia con el hallazgo anterior. El trabajo extra es regenerar el dump excluyendo dos de las quince fuentes: quedarían cinco (RD 311/2022 y cuatro textos UE) con 1.031 chunks, que es la parte redistribuible.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### Fichero `CCN_STIC_809.md` versionado en el árbol como si fuera la guía del CCN

**Qué es.** `backend/app/corpus/data/CCN_STIC_809.md` (14.727 bytes, 103 líneas) se titula como la guía CCN-STIC-809 y se subtitula «Guía de Seguridad de las TIC · Centro Criptológico Nacional · Abril 2026». El módulo que lo ingiere lo declara como fuente con publisher CCN y lo comenta como «Texto curado versionado en el repo». Contiene una parte reproducible (artículos 31 y 38 del RD 311/2022) y una parte que es la exposición de la guía.

**Dónde.** `backend/app/corpus/data/CCN_STIC_809.md:1-103` · `backend/app/corpus/ccn_stic_ingest.py:195-212`

**Cómo se midió.**
```bash
$ wc -c -w -l backend/app/corpus/data/CCN_STIC_809.md
  103  2141 14727
$ head -3 backend/app/corpus/data/CCN_STIC_809.md
# CCN-STIC-809 — Declaración, Certificación y Aprobación Provisional de conformidad con el ENS ...
Guía de Seguridad de las TIC · Centro Criptológico Nacional · Abril 2026.
$ sed -n '195,205p' backend/app/corpus/ccn_stic_ingest.py
CCN_STIC_809 = { "code": "CCN_STIC_809", ... # Texto curado versionado en el repo
  "source_url": "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad.html", ...
```
Se mide lo que el fichero declara ser y su tamaño, no el porcentaje de copia: el PDF original no está en el repositorio, la 809 no está entre las nueve guías ingeridas y no hay red. El cruce de n-gramas devuelve 70 coincidencias de 10 palabras, pero al inspeccionarlas son títulos de normas y frases del articulado del RD, lo que apunta a reescritura y no a copia literal.

**Gravedad.** Grave.

**Coste.** 30-60 min. Dos ficheros: borrar uno de 103 líneas y retirar el bloque de 18 líneas del registro de ingesta; el módulo no tiene otros consumidores. Alternativa: reescribirlo como resumen propio, retitulado y con nota de que no es la guía.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### README declara "Privado propietario" mientras el repositorio se publica bajo Apache-2.0

Tercera aparición del mismo hecho (ver [A1](#a1--arranca-en-una-máquina-limpia) y [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es)). Aquí importa por su efecto legal: quien llegue al repositorio recibe dos concesiones contradictorias sobre el mismo código y la que más se lee es la del README.

**Cómo se midió.**
```bash
$ tail -4 README.md ; grep -n 'Copyright' LICENSE
## Licencia

Privado propietario. Contacto comercial: marcosmata@fulkro.es
190:   Copyright 2026 Marcos Mata García
```

**Gravedad.** Grave. **Coste.** 5 min, una línea.

**Verificación.** CONFIRMADO. El verificador comprobó que ambos ficheros están versionados y que la etiqueta se limita a constatar la coexistencia, sin pronunciarse sobre cuál prevalece.

#### No existe fichero `NOTICE` pese a que el repositorio redistribuye material que exige atribución

**Qué es.** Apache-2.0 contempla `NOTICE` como vehículo estándar de atribución, y hay tres bloques que la necesitan: (a) MAGERIT v3 Libro II, con 57 descripciones de amenaza literales (10.263 caracteres) más 67.894 bytes de taxonomía, publicación del Ministerio reutilizable citando fuente; (b) los textos UE ingeridos en el fixture (904 chunks), cuya reutilización EUR-Lex pide reconocer; (c) diez componentes de `frontend/components/ui` construidos sobre Radix (MIT), sin el aviso correspondiente. Los YAML de MAGERIT sí llevan atribución interna (autores, NIPO, URL oficial), lo que rebaja la gravedad: falta el `NOTICE` de nivel repositorio, no la trazabilidad.

**Dónde.** (ausente) `NOTICE` en la raíz · `docs/catalogs/magerit_libro2_catalog_v1.yaml:1-12` y el campo `descripcion` de las 57 amenazas · `docs/magerit_catalog/*.yaml` · `frontend/components/ui/`

**Cómo se midió.**
```bash
$ find . -path ./.git -prune -o -iname 'NOTICE*' -print | wc -l     ; # 0
$ grep -ciE 'magerit|ccn|aepd|creative commons|tercero' LICENSE README.md
README.md:2   LICENSE:0     # y las 2 del README no son atribución
$ python3 -c "import yaml;a=yaml.safe_load(open('docs/catalogs/magerit_libro2_catalog_v1.yaml'))['amenazas'];
   print('amenazas:',len(a),'chars_descripcion:',sum(len(x['descripcion']) for x in a))"
amenazas: 57 chars_descripcion: 10263
ejemplo: N.1 | incendios: posibilidad de que el fuego acabe con recursos del sistema. | fuente: MAGERIT v3 Libro II - sección 5.1.1
$ grep -rl '@radix-ui' frontend/components/ui | wc -l               ; # 10 de 28 ficheros
```
Los 10.263 caracteres son suma sobre el campo `descripcion` únicamente, no bytes de fichero, que incluirían metadatos propios e inflarían la cifra. Los 10 componentes son los que importan Radix, no los 28 del directorio.

**Gravedad.** Menor.

**Coste.** 40 min. Un fichero nuevo con tres bloques de atribución. Las fuentes ya están identificadas dentro de los propios ficheros, así que es transcribir, no investigar.

**Verificación.** SIN VERIFICAR — no cubierto. **No confirmado.**

#### Cuatro de las cinco definiciones DICAT del catálogo llevan etiqueta de norma UNE/AENOR, y sólo en el YAML (corregido)

**Qué es.** El catálogo de MAGERIT lleva definiciones de dimensión con campos `norma: UNE 71504:2008` y `norma: UNE-ISO/IEC 27001:2007`. A primera vista parece reproducción de norma AENOR (no redistribuible), pero no lo es: son las definiciones que el propio ENS incorpora a su glosario, y el glosario CCN-STIC-800 ingerido las atribuye a «ENS», no a la UNE. Lo que procede es corregir la etiqueta de procedencia, no retirar el texto.

**Dónde.** `docs/catalogs/magerit_libro2_catalog_v1.yaml:17-41` (bloque `dimensiones_valoracion`)

**Cómo se midió.**
```bash
$ grep -n -A2 'norma: UNE' docs/catalogs/magerit_libro2_catalog_v1.yaml
  norma: UNE-ISO/IEC 27001:2007
- codigo: A
  nombre: Autenticidad
  definicion: Propiedad o característica consistente en que una entidad es quien dice ser...
  norma: UNE 71504:2008
# glosario CCN-STIC-800 ingerido en el fixture, con su fuente al final:
"1.63. DISPONIBILIDAD 74. Propiedad o característica de los activos consistente en que
 las entidades o procesos autorizados tienen acceso a los mismos cuando lo requieren. ENS."
```

**Gravedad.** Cosmético.

**Coste.** 10 min. Cambiar la etiqueta a «RD 311/2022, glosario (definición procedente de UNE 71504:2008)» para que no parezca copia de la norma.

**Verificación.** MAL ETIQUETADO, y uno de los dos comandos no reproduce. **Correcciones:** (a) son **4 de las 5** definiciones las que llevan etiqueta UNE, no 5: la quinta (Integridad) lleva «ISO/IEC 13335-1:2004», que no es UNE; el grep original capturaba de menos y presentaba el subconjunto como total. (b) El título decía «en catálogos **y código**», pero en `m01_categorization/service.py` no hay ninguna referencia a UNE: las cinco descripciones cierran con «[RD 311/2022 Anexo IV]», es decir, el código **ya atribuye correctamente**. (c) El segundo comando declarado devuelve cero líneas porque el dump escapa los saltos de línea; con el patrón ajustado el texto sí aparece, así que la conclusión sustantiva —el texto llega vía el ENS y no vía AENOR— se sostiene.

---

### Hallazgos descartados en verificación

Ninguno. De los 68 bloques de hallazgo, el verificador adversarial no dictaminó REFUTADO en ningún caso: 30 quedaron confirmados, 16 corregidos por mal etiquetado (la conclusión sobrevive, la cifra o la población no) y 22 no llegaron a cubrirse. Esta subsección se deja escrita a propósito, para que su ausencia de contenido conste como resultado y no como omisión.

Sí conviene registrar los tres casos en los que **la cifra publicada no reprodujo** al ejecutar el mismo comando, que son el aviso más serio sobre la disciplina de medición: el conteo de acciones de GitHub deprecadas en [A6](#a6--ci-y-despliegue) (30 declaradas frente a 45 reales), el de nombres irresolubles del índice de especificación en [A7](#a7--lo-que-se-afirma-frente-a-lo-que-es) (14 frente a 16) y el segundo comando del hallazgo DICAT en [A8](#a8--terceros-y-licencias). En los tres, el error iba en la dirección de subestimar el problema.

---

## 3. Lo que no se pudo verificar

Agrupado por la causa que lo impidió, con lo que haría falta para cerrarlo.

### 3.1 Falta de infraestructura (sin Docker, sin PostgreSQL, sin `node_modules`, sin red saliente)

Es la causa dominante. Todo lo siguiente está sin medir y no debe leerse como sano ni como roto:

- **Si la suite pasa con la base de datos levantada.** El repositorio afirma 5.978 tests en verde en un comentario de `ci.yml:57`. Lo único acotado es el techo aritmético: 6.464 recolectados menos 99 saltados = 6.365 posibles, así que la cifra es al menos compatible. *Haría falta*: `scripts/build_test_db.sh` ejecutado de principio a fin con un PostgreSQL 16 con pgvector, y después `pytest backend/tests`.
- **Que `docker compose up -d postgres redis minio` levante realmente los servicios**, y cuánto tarda el primer build: `infra/docker/Dockerfile.postgres` compila Apache AGE clonando desde git en tiempo de build, así que depende de red y de varios minutos de compilación. *Haría falta*: Docker instalado y una medición cronometrada.
- **El error literal de `alembic upgrade head` contra una base sin roles.** La cadena de evidencia del bloqueante 3 de A1 es documental (ausencia de montaje de los init SQL más las migraciones que otorgan a `fulkro_app`), no una traza de ejecución.
- **Que las 154 tablas tengan RLS activa en una base real.** Lo medido es el *código* de las migraciones, no el catálogo de PostgreSQL. Una migración posterior que hiciera `DISABLE`, una rama sin aplicar o un `init-functions.sql` no ejecutado producirían un estado distinto del declarado. *Haría falta*: `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class`.
- **Que `fn_audit_log_verify_chain()` devuelva `ok=FALSE` invocada por el rol de la aplicación.** Las premisas están medidas una a una; el salto a la conclusión es semántica documentada de PostgreSQL. *Haría falta*: poblar la cadena, insertar filas de dos proyectos y comparar el veredicto como `fulkro_app` frente a `fulkro_app_bypassrls`.
- **El comportamiento real del recuperador híbrido** (calidad de recuperación, efecto de variar `k`) y **la tasa de acierto de la caché de prompt**, que sólo se puede medir sobre filas reales de `llm_interaction_log`.
- **Que una llamada a `claude-opus-4-8` con `temperature` devuelva efectivamente 400**, y **si el texto `[MOCK]` ha llegado alguna vez a un entregable firmado**. Lo primero requiere clave y red; lo segundo, ejecutar el pipeline completo de generación.
- **Todo el frontend en ejecución**: que las páginas de MAGERIT, Discovery y Workspace fallen visiblemente, el redirect a `/login` del middleware, los specs de Playwright, axe y WCAG. La rotura del prefijo está demostrada estáticamente al 100%, pero no observada en navegador.
- **Si los nueve módulos de import perezoso no declarados degradan con elegancia o revientan al usarse.** Se verificó por AST que no están a nivel de módulo; no se ejercitó cada función. Algunos exigen además binarios del sistema (tesseract, poppler, libxmlsec1) que no están declarados en ninguna parte.
- **Tiempo de instalación con caché fría.** Las cifras dadas (pip 30,3 s, `npm ci` 11 s) son con caché caliente; purgarla habría mutado el entorno del usuario fuera del repositorio. Como orden de magnitud del volumen real: el venv resultante ocupa 858 MB y `node_modules` 642 MB.
- **Los 15 servicios del perfil `pentest`.** Sí se verificó lo relevante para el arranque: están tras `profiles: [pentest]`, así que un `docker compose up -d` normal levanta 4 servicios, no 22.

### 3.2 Falta de acceso (secretos, red, ficheros ausentes, escritura sobre el remoto)

- **El valor real de los secretos `HETZNER_*`.** La API expone nombre y fechas, nunca el contenido. La IP 49.13.136.91 procede de un comentario del YAML, no del secreto: si alguien lo cambió sin actualizar el comentario, el destino real es otro.
- **Cómo fallará exactamente el próximo despliegue.** No se puede provocar un run nuevo sin hacer push, y hacerlo mutaría el historial.
- **Si `admin-polish-empirical` seguiría en verde contra el HEAD actual.** Lanzarlo es una escritura sobre el remoto. *Haría falta*: un `workflow_dispatch` y doce minutos de runner.
- **Que el job `test` de CI falle por el rol `fulkro_app_bypassrls` ausente.** Es análisis estático encadenando tres hechos medidos; no se puede lanzar Actions ni levantar el servicio para observarlo.
- **La identidad del único hallazgo HIGH de bandit.** La lista `results` viene vacía por efecto de los filtros, así que el detalle no está en el artefacto. *Haría falta*: reejecutar bandit sin `--confidence-level high`.
- **Si la traducción ISO/IEC 27001 fue "oficial" y en qué términos.** Los dos ficheros no están en el repositorio, así que no se puede leer su cabecera. Y **el número correcto de medidas del Anexo II** (73 frente a 79): el texto del RD no está en forma consultable para ese conteo, de modo que sólo se demuestra la inconsistencia interna, no cuál de los dos gobierna.
- **Si `CCN_STIC_809.md` es copia literal o reescritura.** El PDF original no está y la 809 no figura entre las nueve guías ingeridas, así que el cruce de n-gramas no la alcanza. Lo mismo para cualquier copia de guías fuera de ese conjunto (815, 824/825, 844, 887, 122, 612), que se citan por número en las plantillas pero cuyo original no se puede contrastar.
- **La procedencia de las cuatro imágenes JPEG de `backend/assets/propuesta_images`**, que van embebidas en el PDF que se envía a clientes: tienen los metadatos EXIF/XMP eliminados y no hay ninguna nota de licencia, banco de imágenes ni autoría en el repositorio.
- **Las licencias de las dependencias declaradas.** Sin `node_modules` ni entorno Python no se puede resolver el árbol real ni pasar un verificador de licencias. Lo que sí se verificó es que no hay dependencias vendorizadas en el árbol.

### 3.3 Límites de tiempo, alcance y escalado

- **22 de los 68 hallazgos no pasaron por verificación adversarial**, incluidos los dos bloqueantes de material de terceros de A8 y siete de los once de A1. No están refutados: están sin comprobar por un segundo par de ojos.
- **La discrepancia sobre los heads de Alembic** entre A7 (4, por parseo estático) y A1/A5/A6 (1, por `alembic heads`) queda abierta, y es la primera que conviene cerrar porque afecta a una línea del README y potencialmente a tres ramas de migración.
- **Zonas de A7 sin barrer por el escalado**: los más de 40 README de motor, los ~331 marcadores TODO/FIXME/NotImplementedError contrastados uno a uno contra lo que se declara entregado, `docs/SYSTEM_KNOWLEDGE_BASE.md` y los docstrings del código. Su ausencia de hallazgos no significa que estén limpias.
- **Si los 91 puntos de escalada BYPASSRLS en camino de petición filtran todos por el tenant autenticado.** Sólo se inspeccionó una muestra, que resultó correcta. Afirmar que los 91 lo son exigiría leer cada handler; afirmar que alguno no lo es exigiría un contraejemplo concreto. Por eso se reporta como riesgo estructural y no como fuga demostrada.
- **Qué test concreto contamina el estado** y hace pasar los tres tests de cifrado en la pasada completa: cinco invocaciones distintas no lograron reproducir el paso. El fenómeno está medido; el causante no.
- **La cobertura de código.** No se midió a propósito: con la mitad de la suite muerta por falta de base de datos, cualquier porcentaje hablaría del entorno, no del repositorio.
- **Consumidores de endpoints fuera del frontend** (curl, Postman, integraciones, cron). El cruce cubre los ficheros del frontend, no cualquier consumidor externo; por eso el hallazgo se etiqueta «ninguna vista del frontend consume» y no «muerto».
- **Si el trabajo que `CLAUDE.md` declara CERRADO se realizó.** Es indecidible desde el árbol publicado: la ausencia de commits y tags es igual de consistente con que se hiciera en el historial descartado que con que no se hiciera. El hallazgo afirma únicamente que la evidencia ofrecida no resuelve.

---

## 4. Lo que está bien

Esta sección no es de cortesía: es el inventario de piezas que aguantan un examen y sobre las que conviene apoyar el README en vez de reescribirlas. Cada una va con la evidencia de por qué aguanta.

### Arranque e instalación

- **La instalación de dependencias declaradas funciona limpia y sin trucos.** `python3 -m venv` vacío + `pip install -e "backend[dev]"` termina en exit 0 (`Successfully installed … fulkro-0.1.0`), cronometrado en 30,3 s con caché caliente.
- **El grafo de imports del backend está sano.** `import backend.app.main` funciona con *sólo* las dependencias declaradas, en un venv construido únicamente desde `pyproject.toml`. Eso es lo que convierte los módulos no declarados en deuda acotada y no en un muro.
- **Arreglando sólo las variables de entorno, el backend arranca sin base de datos y sirve la API documentada.** El log muestra «Startup checks completados OK», luego una degradación honesta («refresh_pricing_from_db: [Errno 111] Connect call failed») que no aborta, y «Application startup complete». `curl /docs` responde 200 y `/openapi.json` declara 1.099 paths. El fallo de base de datos está aislado como best-effort.
- **`scripts/generate_dev_signing_keys.py` hace bien su trabajo y es idempotente:** genera las tres claves Ed25519 del backend y sincroniza la pública del frontend derivándola de la privada. Sólo le falta figurar en la secuencia del README.
- **El frontend se instala y compila en verde, con lockfile versionado.** `npm ci` añade 622 paquetes en 11 s y `npm run build` completa un build de Next.js 14.2.33 en 54,9 s.
- **La receta correcta de provisión de la base de datos existe y está probada en CI**, aunque no esté en el README: `admin-polish-empirical.yml` ejecuta extensiones → `init-functions` → `init-roles` → `alembic upgrade head` → re-GRANT, y es copiable tal cual.
- **Los servicios de pentesting no estorban al arranque**: de los 22 servicios del compose, 15 están tras `profiles: [pentest]`, 2 tras `workers`, 1 tras `scanner` y sólo 4 sin perfil.

### Tests

- **La recolección es perfecta**: 6.464 tests recolectados en 9,9 s con cero errores de recolección sobre 581 ficheros. Para un grafo de imports que arrastra FastAPI, SQLAlchemy y fastembed, no tener ni un import roto es una señal fuerte. Además, los 581 ficheros aportan todos al menos un test: no hay ficheros zombis.
- **3.160 tests pasan sin ninguna infraestructura**: ni base de datos, ni Redis, ni MinIO, ni Docker. Casi la mitad de la suite en verde en una máquina pelada.
- **La superficie de error es perfectamente homogénea**: 3.202 de 3.202 errores comparten una única causa ambiental. Ni un `ImportError`, `AttributeError` o `TypeError` escondido entre ellos, lo que significa que no hay regresiones camufladas detrás del muro.
- **El resultado es reproducible bit a bit** entre dos ejecuciones independientes (mismos cuatro números, mismos tres fallos nominales) y **ningún test se colgó** ni agotó el timeout, ni siquiera con toda la infraestructura caída.
- **El opt-out de los tests LLM funciona**: por defecto no se hace ni una llamada de pago, verificado por dos vías que cuadran (`-m llm` da 46 skipped, y el desglose por motivo de la pasada completa da los mismos 46).
- **Marcador `golden`**: 24 tests, todos verdes en 5,67 s, sin infraestructura, con los cuatro marcadores correctamente declarados en `pyproject.toml`.
- **La suite apenas ensucia el árbol**: un `diff -rq` antes y después de dos pasadas completas sólo reporta dos ficheros PEM, y `var/*` está en `.gitignore`.
- **No hay tests huérfanos del subsistema ENS Radar retirado**: cero coincidencias en `backend/tests` y en `backend/app`. Cuando se retira un motor entero es habitual dejar tests colgando; aquí la limpieza fue completa.

### Autorización, aislamiento y auditoría

- **No hay ningún endpoint alcanzable sin autenticación fuera de la whitelist explícita.** Una dependencia global cableada a nivel de aplicación cubre las 1.201 rutas; sólo 10 carecen además de dependencia de rol y las 10 devuelven 401 sin cookie. Es una arquitectura de un único punto de control, no una lista endpoint a endpoint que se degrada con cada PR.
- **Los 85 endpoints whitelisteados son públicos legítimos, cada uno con su propia puerta**: 16 son `_dev` con doble gate de producción (que devuelve 404 y no 403, para no revelar su existencia), 5 son pre-auth necesarios, 4 son criptografía pública por diseño y 25 son el portal del auditor, cuyo gate valida firma, existencia en base de datos, propósito, revocación, caducidad y tope de usos, respondiendo 403 genérico.
- **Cobertura RLS completa**: las 154 tablas con columna de tenant tienen `ENABLE ROW LEVEL SECURITY` declarado, sin huecos, más 99 ocurrencias de `FORCE ROW LEVEL SECURITY` en 55 migraciones, que es lo que impide que el propietario esquive la política.
- **Los GUC de tenant fallan cerrados**: `current_project_id()` devuelve NULL sin contexto y la política evalúa a NULL, no a TRUE, así que olvidar fijar el contexto produce cero filas, no todas.
- **La inmutabilidad del audit log está defendida en la base de datos, no sólo en la aplicación**: triggers `BEFORE UPDATE`/`BEFORE DELETE` que lanzan excepción con `ERRCODE 'insufficient_privilege'`, más un `REVOKE UPDATE, DELETE` que alcanza incluso al rol de bypass. Dos capas independientes; lo que falta es el test que las ejercite.
- **El acceso de soporte está restringido a lectura en el chokepoint**, no endpoint por endpoint: si el token lleva `support=true`, cualquier método fuera de los seguros devuelve 403 antes del handler, con una única excepción explícita para poder salir del modo soporte.
- **Las dependencias de rol validan contra la base de datos y no contra los claims del JWT**, con la razón documentada en el propio código: degradar a un usuario surte efecto inmediato sin esperar a que expire su token.

### Capa de IA

- **El router LLM tiene una política de reintentos y timeout de verdad**: backoff 2/8/32 s con jitter del ±20% contra thundering herd, timeout de 120 s y `max_retries=0` en el SDK deliberadamente, para controlar el backoff con log propio. Reintenta 429 y 5xx; no reintenta 401 ni 400. Es la política correcta. (Conviene contrastar el peor caso, ~8,7 minutos de reloj de pared, con el timeout del servidor HTTP.)
- **Prompt caching implementado correctamente y con contabilidad separada** de tokens de creación y de lectura de caché, que el cálculo de coste descuenta al factor 0,10. Diez de los trece agentes lo activan, y el docstring razona cuándo conviene: es criterio, no imitación.
- **Los prompts están al 100% separados del código**, uno por agente: 15 módulos y 1.823 líneas, con sólo cuatro ficheros de motores llevando prompt embebido. (Matiz: están en ficheros aparte pero no versionados; no hay constante de versión ni hash de prompt, así que no se puede correlacionar una salida con la revisión que la produjo.)
- **La regla de temperatura ≤ 0,2 se cumple en los trece agentes** a nivel declarado, y también fuera de ellos.
- **El logging de interacciones no puede envenenar la transacción del llamante**: va dentro de un SAVEPOINT con doble `try/except` que degrada a `logger.debug`. Es el patrón correcto para telemetría best-effort.
- **El agente de triaje de seguridad falla en cerrado**: sin LLM devuelve `llm_unavailable` sin aplicar veredicto, dejando el hallazgo vivo en lugar de cerrarlo. Contrasta favorablemente con la degradación a mock de `AgentBase`.
- **El arnés de evaluación, aunque vacío, está bien construido**: cargador con esquemas Pydantic inmutables, umbrales de regresión con semántica de código de salida, registro de evaluadores, runner, API de runs, migración propia y vista admin con su spec. La infraestructura no es el cuello de botella; los datos sí.

### Datos, catálogos y documentación honesta

- **Las dos cifras de la landing reproducen exactamente y con la población declarada**: 131 plantillas y 46 entregables. Y el mensaje del commit que las fijó documenta el razonamiento —revirtió un 135 anterior explicando que contaba `var/templates_docx/*.docx`, «que es otra población»—. Es la disciplina que esta auditoría exige, aplicada por el propio proyecto y dejada por escrito. Es el modelo a seguir para el resto de cifras del README.
- **`backend/app/agents/registry.py` es honesto por diseño**: define seis estados y describe cada uno sin eufemismo, incluido «el stub LLM original NO se implementó jamás; se eliminó para evitar confusión». La deshonestidad de la cifra 31 está en los documentos de cabecera, no en el código.
- **`ens_measures_catalog_v1.yaml` declara sus fuentes, su fecha y sus lagunas** en lugar de presentarse como completo: dice que CCN-STIC 804 v2017 se basa en la versión anterior del ENS y que tres medidas tienen descripción pendiente. Un catálogo normativo que se autodeclara desfasado en su cabecera es lo contrario del patrón que esta auditoría persigue.
- **El corpus normativo de los tests no depende del pipeline roto ni de descargas externas**: viene de un fixture versionado, y el script explica por qué («la ingesta RAG real necesita fastembed y PDFs que NO están en el repo»).
- **Higiene de secretos correcta en el punto de entrada**: no hay ningún `.env` versionado; sólo plantillas, con `.gitignore` cubriendo las variantes y una excepción explícita para el template de producción.
- **`backend/pyproject.toml` separa extras de runtime y de desarrollo con la razón escrita donde se aplica**: la imagen de producción instala `.[runtime]` y no arrastra pytest, ruff ni mypy al contenedor.
- **Los catálogos de reglas no llevan texto de guías embebido** (la cadena más larga de todo el YAML de severidades son 143 caracteres) y **las plantillas del document factory no reproducen prosa del CCN**: su solapamiento máximo son títulos completos de normas —el RGPD, la NIS2, resoluciones de ITS—, es decir, lo que cualquier documento que cite las mismas normas compartiría.
- **No hay código de terceros vendorizado ni fuentes tipográficas empaquetadas**, y **los DOCX son generados por la propia plataforma** (`dc:description` = «generated by python-docx»), no plantillas compradas.
- **El `LICENSE` Apache-2.0 está íntegro y con la línea de copyright rellenada.** El problema no es el `LICENSE`, es el README que lo contradice.

### CI y despliegue

- **El gate de ruff es real, honesto y rápido**: versión fijada, la misma en CI y en el gate de despliegue, pasa en 8 s, y la reducción del conjunto de reglas está documentada en `pyproject.toml` explicando qué se excluye y por qué. Es un gate estrecho pero no miente sobre su alcance.
- **`frontend-typecheck` es un gate real sin máscara** (`tsc --noEmit`, 1 minuto, sin `continue-on-error`). Junto a ruff, son los dos únicos checks que pueden tumbar el CI hoy.
- **`admin-polish-empirical` es ingeniería de CI de nivel alto**: genera claves Ed25519 efímeras por run con openssl —lo que elimina la dependencia de secretos y permite que un fork lo ejecute—, provisiona la base de datos completa y usa el rol `fulkro_app` para tener paridad de RLS con producción, con runs reales en verde en 11-12 minutos. Es, con diferencia, el mejor workflow del repositorio y el modelo sobre el que reconstruir el job de tests.
- **El despliegue no se dispara si el gate previo falla** (`needs: [gate, migrations]`, verificado en el orden real de un run) y **la espera de healthy post-deploy es real**, no un `sleep` ciego: 60 intentos de 4 s consultando el estado de salud, con volcado de logs y salida en error si no converge. El `concurrency group` evita despliegues solapados.
- **bandit escanea de verdad una superficie grande** (1.055 ficheros, 194.625 LOC): el problema está en dónde se puso el umbral, no en que no mire.
- **Los artefactos de diagnóstico se suben con `if: always()` y retención explícita**, lo que permitió medir bandit y npm audit sin ejecutar nada.
- **Los comentarios del YAML documentan decisiones, no sólo el "qué"**: explican por qué el job de tests es on-demand y por qué el umbral de npm está en `critical` y no en `high`. Se puede discrepar de las decisiones, pero están escritas y fechadas, lo que hace auditable el repositorio. La excepción es el comentario de `safety`, que sí contradice la realidad.

---

## Nota de método

Ocho auditores trabajaron en paralelo sobre el árbol en `main`, cada uno con el mandato de medir antes de afirmar y de declarar la población exacta que mide cada cifra. Un verificador adversarial recibió después cada hallazgo con su comando y su salida, y su encargo era el contrario: reproducir, comprobar que la etiqueta y la población coinciden, y refutar si podía.

**Resultado del contraste sobre 68 bloques de hallazgo: 30 confirmados, 16 corregidos por mal etiquetado, 22 sin cubrir y 0 refutados.** De los 16 corregidos, la conclusión sobrevivió en todos los casos y lo que cambió fue la cifra o la población; en tres de ellos —acciones de GitHub deprecadas en A6, nombres irresolubles del índice de especificación en A7 y el segundo comando del hallazgo DICAT en A8— el número publicado no llegó siquiera a reproducir, y en los tres el error subestimaba el problema. Tres dimensiones escalaron por superar el umbral de tres bloqueantes: A1 (arranque), A6 (CI y despliegue) y A7 (afirmaciones frente a hechos).

Dos advertencias sobre cómo leer los recuentos. La primera: 68 no son 68 problemas distintos. La contradicción de licencia aparece en tres dimensiones, el CI que no ejecuta tests en cuatro, las cifras desincronizadas de `CLAUDE.md` en dos, y las rutas absolutas a otro checkout en dos; los bloques duplicados están enlazados entre sí para que se cuenten una sola vez al planificar. La segunda: los 22 sin verificar no están limpios, están sin comprobar, y entre ellos se cuentan los dos bloqueantes de material de terceros de A8, que son los de mayor exposición legal de todo el informe y los primeros que convendría reproducir —su comando no necesita infraestructura alguna—.

Finalmente, el sesgo del entorno tira en una sola dirección: sin Docker, sin PostgreSQL, sin `node_modules` y sin red, casi todo lo que quedó sin medir es *comportamiento en ejecución*. Este informe es sólido sobre lo que el repositorio dice de sí mismo, sobre su estructura y sobre lo que se puede arrancar en frío; es deliberadamente silencioso sobre si el producto funciona.
