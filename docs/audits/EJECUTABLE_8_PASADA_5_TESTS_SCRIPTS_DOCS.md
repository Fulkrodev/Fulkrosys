# Ejecutable 8 · Pasada 5 · Tests + Scripts + Docs Deep Dive

> Inventario empírico de cobertura de tests, scripts y documentación. Todas las cifras de output real (`find … | wc -l`, `pytest --collect-only`, `ls`). Filesystem WSL-sobre-Windows. Fecha: 2026-05-30.

---

## 1. Tests backend (`backend/tests/`)

**Conteo empírico**: `find backend/tests -name 'test_*.py' | wc -l` → **484 ficheros**.

Distribución por subdirectorio (top):

| Subdir | # test_*.py |
|--------|------------:|
| `motors/` | 355 |
| `agents/` | 23 |
| `core/` | 18 |
| `notifications/` | 15 |
| `api/` | 11 |
| `corpus/` | 8 |
| `audit_fixes/` | 7 |
| `auth/` | 7 |
| `security/` | 7 |
| `billing/` | 6 |
| (resto: integration, mcp_servers, etc.) | ~27 |

Motores con más cobertura de test (top 6 dentro de `motors/`):

| Motor | # test files |
|-------|-------------:|
| m10_ens_radar | 45 |
| m_cloud_connectors | 23 |
| m06_document_factory | 22 |
| m21_portal_cliente | 21 |
| m08_verification | 20 |
| m09_audit_prep | 19 |

## 2. Tests frontend (`frontend/tests/`)

**Conteo empírico**: `find frontend/tests -name '*.spec.ts' | wc -l` → **297 specs** (`*.test.tsx` → 0).

| Categoría | # specs | Detalle |
|-----------|--------:|---------|
| E2E (`e2e/`) | 199 | 25 carpetas `fase_9` … `fase_39` (NO existe `fase_40`; SÍ existen `fase_9`–`fase_12`) |
| Polish (axe-core a11y) | 97 | p2 35 · p3 21 · p1 14 · auditor 12 · cliente 10 · probe 5 |
| (otros / raíz) | 1 | |

## 3. Coverage cumulative (collect-only · empírico parcial)

`python -m pytest backend/tests --collect-only` (desde raíz; `cd backend` falla por `ModuleNotFoundError: No module named 'backend'` en conftest L61):

- **4659 tests recolectados**
- **106 módulos en ERROR de colección** por dependencias ausentes en el intérprete usado:
  loguru (59) · docxtpl (11) · fastembed (9) · rapidfuzz (8) · minio (6) · respx (3) · phonenumbers (3) · reportlab (2) · mjml (2) · bs4 (2) · …

⚠️ **Honestidad empírica (OPS-049)**: los 106 errores de colección son **de entorno** (deps no instaladas en el intérprete usado para el collect), NO regresiones de test. El README declara 2769 PASS en la `.venv` correcta (`pip install -e backend[dev]`). El número de **casos recolectados creció a 4659** (vs 2769 README) → crecimiento real de la suite. **Verificación pendiente**: correr la suite completa en `.venv` WSL con todas las deps (`-m 'not llm'`) para obtener PASS/FAIL real — diferido a Pasada 9/16 con entorno completo.

## 4. Scripts

| Ubicación | # ficheros | Propósito aparente |
|-----------|-----------:|--------------------|
| `backend/scripts/` | ~50 | seed (`seed_all_fulkro.py`), demos E2E (`demo_s8_*`), generadores PDF (`generate_propuesta_pdf.py`, `generate_signed_sample_pdf.py`), radar (`radar_detect_pliegos_defectuosos.py`, `resume_radar_run.py`), claves dev (`generate_dev_signing_keys.py`), etc. |
| `scripts/` (raíz) | 18 | `load_magerit_catalogs.py`, `corpus_ingest.py`, `m10/` (radar helpers), etc. |

(Inventario script-por-script detallado diferido; no listado en CLAUDE.md → candidato a catalogación Pasada 18 SYSTEM_KNOWLEDGE_BASE.)

## 5. Docs (`docs/`)

- 26 subdirectorios (Pasada 1): architecture, archive, audit, audits, catalogs, compliance, copilot, decisions, deploy, dev, differentiators, ens-manuales, infra, landing, limitations, magerit_catalog, master_plan, mcps, operations, patterns, pricing, runbooks, schemas, spec.
- **Hallazgo deuda doc**: CLAUDE.md referencia inline **ADR-001 … ADR-054** pero solo existen **9 ficheros ADR físicos** (ADR-046 … ADR-054) en `docs/architecture/` (o `docs/decisions/`). Los ADR 001-045 se citan pero no tienen fichero dedicado → deuda documental (candidato Pasada 6 dead-code/coherencia + Pasada 16/20).
- `docs/audits/` contiene los audits per ejecutable (AUDIT_EJECUTABLE_*.md) + los nuevos EJECUTABLE_8_PASADA_*.
- `docs/spec/` = biblia (ENS_PLATFORM_MASTER_SPEC v2.1) + correcciones + ENS_RADAR_SPEC.
- `docs/ens-manuales/` = 3 ground-truth (Pasada 1).

## 6. CIFRAS EMPÍRICAS (resumen)

| Métrica | Valor empírico | Stale declarado |
|---------|---------------:|-----------------|
| Test files backend | **484** | CLAUDE.md ~353 / README "2769 passed" (casos) |
| Specs frontend | **297** (199 e2e + 97 polish + 1) | CLAUDE.md 140+ |
| Tests recolectados (collect-only) | **4659** (+106 error de entorno) | README 2769 |
| Carpetas fase E2E | 25 (`fase_9`…`fase_39`) | CLAUDE.md "fase_17 a fase_40" |
| Scripts | ~50 backend + 18 raíz | no inventariado |
| ADR físicos | 9 (046-054) | CLAUDE.md cita 001-054 |

## 7. Discrepancias vs stale

1. **Test files**: 484 reales vs ~353 (CLAUDE.md) → +37%.
2. **Specs Playwright**: 297 reales vs 140+ (CLAUDE.md); carpetas `fase_9`–`fase_39` (no `fase_40`; sí `fase_9`–`fase_12` que CLAUDE.md no menciona).
3. **Tests README**: 2769 PASS stale; collect-only recolecta 4659 (crecimiento real de suite).
4. **README motores/agentes**: 28 motores / 11 LLM agents — no reconcilia con `tests/motors` (62 dirs) ni `tests/agents` (23 files).
5. **ADRs**: CLAUDE.md cita ADR-001..054 pero solo 9 ficheros físicos (046-054) → deuda documental.
6. **Scripts**: ~68 scripts totales no catalogados en CLAUDE.md.

## 8. Commands unavailable (honestidad empírica)

- Suite pytest completa NO ejecutada (evitar bloqueo en mount WSL lento) — solo collect-only.
- `cd backend && pytest --collect-only` falla (`ModuleNotFoundError: backend` en conftest L61); workaround desde raíz.
- 106 módulos no colectables por deps ausentes en el intérprete del collect (no contados en 4659).
- Coverage % real (pytest-cov) NO ejecutado — bloqueado por deps + tiempo WSL. → Pasada 9/16 con `.venv` completo.

## Conclusión Pasada 5

Cobertura de test **mayor de lo documentado**: 484 ficheros backend + 297 specs frontend, suite recolectando 4659 casos (vs 2769 README). Carpetas E2E `fase_9`–`fase_39` (25). Deuda documental detectada: **solo 9 ADR físicos** pese a citarse 54 inline, y ~68 scripts sin catalogar. **Verificación PASS/FAIL real diferida** a entorno `.venv` completo (Pasada 9/16). Ninguna regresión confirmada — los 106 errores de colección son de entorno, no de código.
