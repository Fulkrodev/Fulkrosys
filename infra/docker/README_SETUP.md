# FULKRO — Setup y reset total

Guia operativa para dejar una copia limpia de FULKRO funcionando en
menos de 12 minutos. Probada en Sesion 7 Paso 9.3, Sesion 8 Paso 4.5 y
reconfirmada en Sesion 8 Paso 9.1 (V-CHECK global final).

---

## Requisitos previos

- WSL2 Ubuntu 22.04 o Linux nativo
- Docker + Docker Compose v2
- Python 3.12 con `.venv` creado en la raiz del repo
- ~4 GB de espacio libre (MinIO + PostgreSQL + pgvector + Redis)

## Nombres reales de servicios

Tras `docker compose up`, los contenedores se llaman:

| Servicio | Nombre contenedor | Puerto host |
|---|---|---|
| PostgreSQL | `fulkro-postgres-1` | 5433 -> 5432 |
| Redis | `fulkro-redis-1` | 6379 |
| MinIO | `fulkro-minio-1` | 9000 / 9001 |
| OWASP ZAP | `fulkro-fulkro-scanner-1` | 8090 |

Superuser PostgreSQL: **`fulkro`** (NO `postgres`).
Usuarios aplicacion: `fulkro_app` (RLS), `fulkro_migrate` (DDL).

## Reset total desde cero

> **Nombre de los contenedores**: Docker Compose los llama
> `<proyecto>-<servicio>-<índice>`, y el proyecto por defecto es el nombre del
> directorio del clon. Los `fulkro-postgres-1` de abajo asumen que el clon se
> llama `fulkro`; en un clon de `Fulkrodev/Fulkrosys` el directorio es
> `Fulkrosys` y el contenedor es `fulkrosys-postgres-1`. Comprueba el tuyo con
> `docker ps --format '{{.Names}}'` y sustitúyelo.

```bash
cd "$(git rev-parse --show-toplevel)"

# 1. Tirar volumenes FULKRO (destructivo; no usar prune global para no
#    afectar otros proyectos Docker en la maquina)
docker compose down -v

# 2. Levantar solo servicios de datos
docker compose up -d postgres redis minio

# 3. Esperar PostgreSQL (healthcheck propio)
sleep 30

# 4. Inicializar extensiones + funciones + roles (orden IMPORTA)
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    < infra/docker/init-extensions.sql
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    < infra/docker/init-functions.sql
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    < infra/docker/init-roles.sql

# 5. Activar venv + aplicar migraciones Alembic
source .venv/bin/activate
cd backend && alembic upgrade head && cd ..

# 6. Seed completo (catalogos + corpus + clientes + KG + pricing)
PYTHONPATH=. python backend/scripts/seed_all_fulkro.py

# 7. Verificar suite completa
PYTHONPATH=. python -m pytest backend/tests/ -q

# 8. Demo end-to-end Sesion 8 (cierre)
PYTHONPATH=. python backend/scripts/demo_s8_paso8_e2e_year_dataforma.py
```

**Target verificado Paso 9.1**:
- Alembic head: `a5c2f8e9d417`
- Suite: **2550 passed / 1 skipped / 0 failures** (~3:20 wall clock)
- Demos 7 + 8 (8 scripts): 8/8 PASS
- Tiempo total reset -> working state: **< 12 minutos**

## Suite de demos Sesion 8

Ejecutables en cadena (~2-3 min total):

```bash
bash backend/scripts/run_all_demos.sh
```

Incluye:

| Demo | Pasos | Cobertura |
|---|---|---|
| `demo_s7_paso7_full.py` | - | Baseline fin Sesion 7 |
| `demo_s8_paso1_templates.py` | - | Filtros Jinja ES + 3 nuevos templates |
| `demo_s8_paso2_retainer.py` | - | M23 retainer 5 tiers + facturacion |
| `demo_s8_paso3_client_portal.py` | - | Login + TOTP + scopes por rol |
| `demo_s8_paso4_lifecycle.py` | 13/13 | Cierre + grace + backup ZIP firmado |
| `demo_s8_paso5_conformity.py` | 12/12 | M27 Conformity + overlays PCE |
| `demo_s8_paso6_pricing.py` | 4/4 | Pricing M13/M14/M15 + quick scan discount |
| `demo_s8_paso8_e2e_year_dataforma.py` | 16/16 | E2E anho 1 DataForma — 12.700 EUR |

---

## Troubleshooting

### 1. `extension "vector" does not exist`

Causa: `init-extensions.sql` no se ejecuto o se ejecuto antes de
que postgres estuviera listo.

Fix:

```bash
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS age;"
```

### 2. `function current_client_id() does not exist`

Causa: `init-functions.sql` no se ejecuto. Las funciones RLS son
prerrequisito de las politicas `project_isolation` / `client_isolation`.

Fix:

```bash
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    < infra/docker/init-functions.sql
```

### 3. `role "fulkro_app" does not exist`

Causa: `init-roles.sql` no se ejecuto. El role `fulkro_app`
(NOSUPERUSER) es el que los tests usan para verificar que RLS
funciona — el role `fulkro` (SUPERUSER) se usa para bypass en
setup de tests y en tareas Celery.

Fix:

```bash
docker exec -i fulkro-postgres-1 psql -U fulkro -d fulkro \
    < infra/docker/init-roles.sql
```

### 4. Alembic error `column "deleted_at" of relation "projects" already exists`

Causa: `SoftDeleteMixin` anhade `deleted_at` automaticamente a
`Project`. Una migracion manual no debe re-anhadirlo.

Fix: ya solventado en migration `d2e6f4a9b812` (Paso 4). Si te
toca una version futura que lo intenta, elimina la linea
`op.add_column("projects", sa.Column("deleted_at", ...))` de la
migracion.

### 5. Alembic tarda > 2 minutos

Causa: cold start con muchas migraciones. Normal en primera
ejecucion. Head actual: `a5c2f8e9d417`.

### 6. Demo falla con `ForeignKeyViolationError`

Causa: reruns dejan residuos de un demo anterior. El script
`_cleanup` tolera tablas inexistentes via `begin_nested` savepoints.

Fix: si persiste, recrear desde cero con los pasos 1-6 de arriba.

### 7. MinIO buckets no existen

Causa: primer arranque. Los tests usan un fallback `local://` y no
dependen de MinIO. Para demos con MinIO real:

```bash
docker exec -i fulkro-minio-1 mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec -i fulkro-minio-1 mc mb -p local/fulkro-documents local/fulkro-evidence local/fulkro-exports
docker exec -i fulkro-minio-1 mc retention set --default compliance 7y local/fulkro-evidence-worm || true
```

### 8. `workers/Celery not installed`

Causa: `celery[redis]` no esta en `pyproject.toml`. Los tests usan
un stub automatico (`CELERY_AVAILABLE = False`). Para correr workers
de produccion:

```bash
pip install "celery[redis]==5.*"
celery -A backend.app.core.celery_app worker -l info
celery -A backend.app.core.celery_app beat -l info
```

---

## Comandos de diagnostico

```bash
# Estado de tablas (168 tras Sesion 8)
docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
    -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'"

# Estado de migraciones (head = a5c2f8e9d417 tras Paso 7 final)
cd backend && alembic current && alembic heads

# Corpus ingestado (chunks en pgvector)
docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
    -c "SELECT COUNT(*) FROM corpus_chunks"

# Motores registrados + magic_link_purposes
docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
    -c "SELECT COUNT(*) FROM ens_measures"              # 80
docker exec fulkro-postgres-1 psql -U fulkro -d fulkro \
    -c "SELECT COUNT(*) FROM pricing_catalog"           # 10

# Magic link purposes (23 tras Sesion 8)
python -c "from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose; print(len(list(MagicLinkPurpose)))"
```
