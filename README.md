# FULKRO

Plataforma de implantacion del **Esquema Nacional de Seguridad** (ENS, RD 311/2022)
para consultoria. Automatiza el ciclo completo de certificacion ENS de un cliente:
categorizacion (regla del maximo), analisis de riesgos MAGERIT v3, Declaracion de
Aplicabilidad, planificacion, generacion documental, recopilacion de evidencias,
verificacion tecnica (MCPs de pentest), preparacion y acompanamiento de auditoria
ENAC, y retainer post-certificacion.

Disenada para un consultor que gestiona multiples clientes en paralelo con
multi-tenancy real (RLS PostgreSQL) y un portal-cliente de minima friccion
(magic links, sin cuentas permanentes).

> La especificacion canonica y el detalle operativo vivo estan en
> [`CLAUDE.md`](CLAUDE.md) (guia del proyecto) y `docs/spec/`. Este README es la
> entrada: que es, como levantarlo, como desplegarlo.

---

## Arquitectura en una pantalla

- **Backend** — FastAPI (Python 3.12) + SQLAlchemy 2.0 async sobre PostgreSQL 16.
  La logica vive en **44 directorios de motores** bajo `backend/app/motors/m*/`
  (lifecycle ENS m01-m31 + capas transversales: `m_cloud_connectors`,
  `m_observability`, `m_compliance`, `m_meetings`, `m_workflow_engine`, etc.) y en
  los **agentes IA** bajo `backend/app/agents/` (taxonomia canonica en
  `registry.py`). Las decisiones normativas son **deterministas** (R1: motores >
  LLM para trazabilidad ENAC); el LLM enriquece, nunca decide solo.
- **Frontend** — Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui.
  Cuatro portales: admin (Marcos), cliente, auditor (ENAC) y ENS Radar (captacion).
- **Datos** — PostgreSQL 16 con pgvector (RAG), Apache AGE (grafo), pgAudit y
  pgBackRest. `audit_log` inmutable con cadena de hash (R6, append-only por
  privilegio). Redis 7 + Celery para tareas. MinIO para objetos (evidencias en
  bucket WORM con Object Lock 7 anos).
- **IA** — Anthropic SDK (Sonnet / Haiku / Opus) con prompt caching, temperatura
  <= 0.2 (R3) y citas normativas obligatorias en toda respuesta (R2). Embeddings
  e5-large (1024 dim) via micro-servicio fastembed.

Reglas inviolables, ADRs y lecciones operativas (OPS-*) estan documentadas en
`CLAUDE.md` y `docs/doctrine/`.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Lenguaje / API | Python 3.12 · FastAPI >= 0.115 |
| ORM / migraciones | SQLAlchemy 2.0 async (asyncpg) · Alembic |
| Base de datos | PostgreSQL 16 (pgvector + Apache AGE + pgAudit + pgBackRest) |
| Cache / colas | Redis 7 · Celery |
| Object storage | MinIO (3 buckets · evidencias WORM 7 anos) |
| Frontend | Next.js 14 · React · TypeScript · Tailwind · shadcn/ui |
| IA | Anthropic SDK (Sonnet/Haiku/Opus) · fastembed (e5-large 1024d) |
| Reverse proxy / TLS | Caddy |
| Empaquetado | Docker Compose (`docker-compose.yml` dev · `docker-compose.prod.yml`) |

---

## Levantar en desarrollo (WSL2 Ubuntu)

Secuencia reproducible desde cero tras clonar:

```bash
# 1. Clonar + entorno virtual
git clone <repo-url> fulkro && cd fulkro
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e "backend[dev]"

# 2. Servicios de infra (postgres + redis + minio)
docker compose up -d postgres redis minio
sleep 30   # postgres tarda en bootstrap

# 3. Config de entorno
cp .env.example .env    # apunta a postgres local (:5433)

# 4. Reconstruir la BD de test (orden inviolable: extensiones -> funciones ->
#    roles -> alembic upgrade head -> grants -> seed -> REVOKE audit_log)
bash scripts/build_test_db.sh   # referencia ejecutable del orden · usa fulkro_test

# 5. Verificar
PYTHONPATH=. pytest backend/tests/ -q
```

`scripts/build_test_db.sh` es la **referencia ejecutable** del orden de provision
y nunca toca la BD live `fulkro` (usa `fulkro_test`).

### Tests

```bash
# Suite completa (LLM mockeado por defecto · sello FULKRO_RUN_LLM_TESTS=0)
PYTHONPATH=. pytest backend/tests/ -q

# Correr tambien los tests @llm reales (requiere ANTHROPIC_API_KEY · consume tokens)
FULKRO_RUN_LLM_TESTS=1 PYTHONPATH=. pytest backend/tests/ -m llm -q
```

> Nota: lanzar `pytest`/`alembic` **desde la raiz del repo** con `PYTHONPATH=.`.

### Servidor de desarrollo

```bash
# --env-file carga .env (incl. claves Ed25519 persistentes de
# scripts/generate_dev_signing_keys.py). NO usar `source .env`.
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
# OpenAPI: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend && npm install && npm run dev   # http://localhost:3000
```

---

## Desplegar en produccion (Hetzner)

El despliegue es **turnkey** y esta documentado paso a paso en:

### [`docs/deploy/HETZNER_DEPLOY_RUNBOOK.md`](docs/deploy/HETZNER_DEPLOY_RUNBOOK.md)

Secuencia resumida (de servidor recien aprovisionado a producto verificado):

```bash
bash scripts/generate-prod-secrets.sh   # 1 · genera .env.prod (claves frescas)
# ...rellenar a mano ANTHROPIC_API_KEY + SMTP + dominio (ver runbook §0)
bash scripts/deploy-hetzner.sh          # 2 · build + provision + up (orden inviolable)
bash scripts/verify-deploy.sh           # 3 · gate post-deploy (roles/Alembic/ENS/R6/WORM)
# 4 · backups pgBackRest + restore-test mensual (R8) — runbook §5
```

Las piezas de infra-como-codigo (compose prod, generador de secretos, provision
one-shot, init de buckets MinIO WORM, gate de verificacion, pgBackRest) y la
**frontera honesta** (que se valida en dev vs. que solo corre en Hetzner) estan
detalladas en el runbook.

---

## Estructura del repositorio

```
fulkro/
  backend/
    app/
      api/                  # Routers REST compartidos + wiring
      agents/               # Agentes IA (agent_*.py) + registry.py + prompts/
      core/                 # Pricing canonico, branding, identidad Fulkro, helpers
      models/               # SQLAlchemy models (core + motors)
      motors/               # 44 motores · m01_categorization ... m31 + m_* transversales
        m01_categorization/ #   categorizacion ENS (regla del maximo)
        m02_magerit/        #   motor de riesgos MAGERIT v3
        m03_dda/            #   Declaracion de Aplicabilidad
        ...                 #   (un directorio por motor · service.py + api.py + schemas.py)
      main.py               # FastAPI app
    migrations/versions/    # Migraciones Alembic (1 head: m8_autopilot_canonical_001)
    tests/                  # Suite pytest (motors/ agents/ auth/ core/ integration/ ...)
    pyproject.toml          # Deps + pytest + coverage
  frontend/                 # Next.js 14 (app/ · components/ · lib/ · hooks/ · tests/e2e/)
  docs/
    spec/                   # ENS_PLATFORM_MASTER_SPEC (biblia) + correcciones
    deploy/                 # HETZNER_DEPLOY_RUNBOOK.md (turnkey)
    architecture/           # ADRs
    doctrine/               # R-rules + OPS-lessons
    audits/                 # Auditorias empiricas por sesion
  infra/
    docker/                 # Dockerfiles + init-{extensions,functions,roles}.sql + provision
    caddy/ pgbackrest/      # Reverse proxy + backups fisicos
  scripts/                  # build_test_db, deploy-hetzner, verify-deploy, backups, seeds
  var/templates_docx/       # Plantillas DOCX maestras (tracked · render via Document Factory)
  docker-compose.yml        # Dev: postgres + redis + minio
  docker-compose.prod.yml   # Prod: stack completo (12 servicios)
  .env.example              # Plantilla de entorno dev
  .env.prod.template        # Plantilla de secretos de produccion
  CLAUDE.md                 # Guia canonica del proyecto (estado vivo · reglas · doctrinas)
```

---

## Convenciones de commits

```
feat(motorN):   Nueva funcionalidad
fix(motorN):    Correccion de bug
test(motorN):   Tests
docs(...):      Documentacion, runbooks, ADRs
feat(corpus):   Corpus normativo, catalogos, seeds
```

---

## Licencia

Privado propietario. Contacto comercial: marcosmata@fulkro.es
