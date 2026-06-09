# Ejecutable 8 EXPANDED FRESH-EYES · Pasada 1 · Top-Level Reconnaissance

> **Fecha**: 2026-05-30 · **Branch**: `fix/radar-sector-widen-and-cleanup-20260529`
> **Doctrina**: fresh-eyes empirical · solo `ls`/`find`/`view` · cero asunciones · cifras stale NO dadas por sentado.
> **Objetivo**: Mapear estructura repo top-level sin profundizar. Las cifras reales se establecen Pasadas 2-5.

---

## 1. Top-level files (raíz repo)

```
.env
.env.example
.gitignore
.pre-commit-config.yaml
CLAUDE.md            (83.358 bytes · guía proyecto · 2026-05-27)
DECISIONS.md
MEMORY.md            (índice memorias auto-persistentes)
README.md            (12.350 bytes · STALE Sesión 10.5 2026-04-24 · ver §6)
docker-compose.yml   (config 3 core + clamav + perfiles opt-in)
start_backend.sh
start_frontend.sh
```

## 2. Top-level directories (level 1)

| Dir | Propósito (empirical) |
|-----|------------------------|
| `.claude/` | Config sesión Claude Code (untracked, nuevo) |
| `.github/workflows/` | CI: `ci.yml` + `security-scan.yml` + `admin-polish-empirical.yml` |
| `_incoming/` | `corpus_cache/` (ingest corpus normativo) |
| `backend/` | App FastAPI (app/ + mcp_servers/ + migrations/ + scripts/ + tests/ + assets/) |
| `frontend/` | Next.js 14 (app/ + components/ + hooks/ + lib/ + tests/ + styles/ + public/) |
| `data/` | `ccn/` + `pliegos/` (datos radar/normativa) |
| `docs/` | 26 subdirectorios doc (architecture, audits, spec, ens-manuales, runbooks, ...) |
| `infra/` | `caddy/` + `docker/` (init SQL extensions/functions/roles) |
| `logs/` · `out/` · `progress/` · `scripts/` · `var/` | runtime/output/sesión/scripts/datos generados |

## 3. Estructura backend/ (level 1)

```
backend/
  alembic.ini
  pyproject.toml
  app/            # núcleo FastAPI (deep dive Pasada 2)
  assets/
  mcp_servers/    # MCP servers pentest (deep dive Pasada 2)
  migrations/     # Alembic (deep dive Pasada 4)
  scripts/        # scripts CLI
  tests/          # suite pytest (deep dive Pasada 5)
```

## 4. Estructura frontend/ (level 1)

```
frontend/
  package.json · package-lock.json · tsconfig.json · next.config.mjs
  middleware.ts · tailwind.config.ts · postcss.config.mjs
  playwright.config.ts · playwright.polish.config.ts · Dockerfile.e2e
  app/          # App Router pages (deep dive Pasada 3)
  components/   # componentes TSX (deep dive Pasada 3)
  hooks/ · lib/ · styles/ · public/
  tests/        # Playwright E2E + polish (deep dive Pasada 5)
  polish-report/ · polish-test-results/ · test-results/   # artefactos generados
  node_modules/
```

## 5. Stack técnico (empirical · pyproject.toml + package.json + docker-compose.yml)

**Backend** (Python ≥3.12):
- FastAPI ≥0.115 + uvicorn + sse-starlette · SQLAlchemy 2.0 async + asyncpg · Alembic ≥1.13 · Pydantic v2
- Redis ≥5 + Celery ≥5.4 · httpx · anthropic ≥0.40 · fastembed ≥0.4.2 + pgvector
- Auth: python-jose + PyJWT + pyotp + passlib[bcrypt] + PyNaCl + py-webauthn
- Docs: docxtpl + pdfplumber + python-docx + reportlab ≥4 + svglib + openpyxl
- Notif: Jinja2 + mjml-python · AV: clamd · Radar: rapidfuzz + playwright · Cloud: boto3 + paramiko
- dev: pytest (+asyncio/cov/timeout/rerunfailures) + ruff + mypy + moto + python-gvm

**Frontend** (Next.js 14.2.33 App Router):
- React 18 + TypeScript 5 + Tailwind 3.4 + shadcn/Radix UI
- @tanstack/react-query 5 + react-table + react-virtual · zustand 4.5 · react-hook-form + zod
- @simplewebauthn/browser · jose · react-signature-canvas (Ejecutable 7.7) · recharts · lucide-react
- @dnd-kit · cmdk · react-markdown + rehype-sanitize + remark-gfm · sonner
- dev: @playwright/test 1.59 + @axe-core/playwright (polish a11y suite)

**Infra** (docker-compose.yml):
- Core (default): postgres `fulkro/postgres:pg16` (5433, pgaudit preload) + redis 7-alpine + minio + clamav
- Profile `workers`: celery-worker + celery-beat
- Profile `scanner`: ZAP (zaproxy/zap-stable 2.15)
- Profile `pentest`: 14 MCP services (scope-enforcer, recon, vulnscan, webpentest, infra, redteam, cloud, config, phishing, sast, cracking, apisec, mobile, wireless) + openvas (immauss/openvas)
- Networks: pentest-net (internal) + pentest-external

## 6. ⚠️ DISCREPANCIA CRÍTICA detectada (README vs CLAUDE.md)

`README.md` está **STALE** — refleja Sesión 10.5 (2026-04-24), MUY anterior al estado CLAUDE.md (2026-05-27):

| Métrica | README.md (stale) | CLAUDE.md (2026-05-27) | Real → Pasadas 2-5 |
|---------|-------------------|------------------------|---------------------|
| Motores | 28 | "42 motors reales" | **TBD Pasada 2** |
| Tests | 2769 passed | "~353 archivos test_*.py" | **TBD Pasada 5** |
| Agentes LLM | 11 reales | "31 IDs registry" | **TBD Pasada 2** |
| Migraciones | (no cifra) | 160 | **TBD Pasada 4** |
| MCP servers | 14 (3 reales) | 14 / "~6 según Marcos" | **TBD Pasada 2** |
| Páginas frontend | "5-7 a conectar" | "120+ páginas" | **TBD Pasada 3** |

**Acción**: README.md candidato a refresh en Pasada 16/20 (corrección/handoff). Cifras reales NO se asumen de ninguna fuente — discovery empírico Pasadas 2-5.

## 7. Ground-truth ENS manuales (criterio cobertura Pasada 10)

✅ Confirmados presentes en `docs/ens-manuales/`:
- `ENS_BASICA_Manual_Implantacion_Completo.md` (429 líneas · 25.064 bytes)
- `ENS_MEDIA_Manual_Implantacion_Completo.md` (453 líneas · 25.934 bytes)
- `ENS_ALTA_Manual_Implantacion_Completo.md` (435 líneas · 27.044 bytes)

Nota menor: existen ficheros `*.md:Zone.Identifier` (Windows Alternate Data Stream de descarga) junto a cada manual — artefactos inocuos, candidatos a limpieza Pasada 16.

## 8. CI/CD workflows (`.github/workflows/`)

- `ci.yml` · pipeline principal
- `security-scan.yml` · Ejecutable 3 base security
- `admin-polish-empirical.yml` · Ejecutable 7 (3 jobs: admin 80 + cliente 10 + auditor 12 pages axe-core)

(Contenido detallado de workflows → cross-ref Pasada 5/9.)

---

## Conclusión Pasada 1

Estructura top-level mapeada empíricamente. Hallazgo principal: **README.md stale ~5 semanas** con cifras divergentes de CLAUDE.md — refuerza la necesidad del discovery empírico Pasadas 2-5 (cero asunciones de cifras motores/agentes/MCPs/pages/tests/migraciones). Ground-truth manuales presentes. Stack confirmado. Siguiente: Pasada 2 backend deep dive.
