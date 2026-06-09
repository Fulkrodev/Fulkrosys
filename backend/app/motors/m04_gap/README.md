# Motor 4 · Gap Analysis Engine

Comparativa entre el estado actual de controles y el target derivado de la DdA (M03). Genera lista priorizada de gaps usando reglas determinísticas del catálogo de severidad. Enriquecimiento LLM contextual disponible vía `llm_prioritizer.py` para ranking refinado.

## Funcionalidades

- **Cálculo determinístico de gaps** comparando `EnsMeasure` (target) vs `Finding` (current) per categoría sistema.
- **Catálogo de severidad** versionado (`catalog_loader.py`) con scoring `LOW`/`MED`/`HIGH`/`CRIT` per medida.
- **Esfuerzo + quick-wins** clasificación per categoría (`is_quick_win_for_categoria` · `get_esfuerzo_for_categoria`).
- **Identificación de medidas nucleares** (`is_nuclear`) prioritarias para el plan de tratamiento.
- **LLM prioritizer** opcional (`llm_prioritizer.py` + `prompt_prioritize.py`) para ranking contextual avanzado.
- **Dashboard de gaps** con KPIs agregados (`GapDashboardResponse` · open/closed/critical counts).
- **Close gap workflow** con tracking de cierre justificado.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.857 |
| Files | 9 |
| Status | production-grade |
| Tests | `backend/tests/motors/m04_gap/` |
| API prefix | `/api/v1/gap/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP CRUD + dashboard + analyze-project
- `service.py` · `GapAnalysisService` (core logic determinístico)
- `catalog_loader.py` · carga + versioning catálogo severidad
- `llm_prioritizer.py` · ranking LLM opcional contextual
- `prompt_prioritize.py` · prompt templates LLM
- `enums.py` · `SEVERITY_SCORING_STR` · `LEVEL_ORDER` · `CATEGORY_TARGET_LEVEL`
- `exceptions.py` · dominio (GapNotFoundError · DdANotReadyError · etc.)
- `schemas.py` · Pydantic in/out

## DB tables

N/A motor-specific · usa modelos `Finding` (`backend/app/models/findings.py`) + ENS (`DdaEntry` · `EnsMeasure`). RLS por `findings`.

## Cross-motor integration

- **Inbound**: ninguno directo (consumido vía API por admin UI + dashboards)
- **Outbound**: M05_obligations (instantiation downstream post-gap closure)
- **LLM agents**: opcional via `llm_prioritizer.py` (ranking contextual)

## Limitaciones conocidas

### Análisis bloqueado si DdA no congelada

`analyze_project` levanta `DdANotReadyError` si la DdA del proyecto no está congelada (`fecha_aprobacion IS NULL`). Esto es invariante: gap analysis sin baseline DdA aprobado no produce target consistente.

**Workflow esperado**: M01 Categorization → M03 DdA freeze → M04 Gap analyze → M05 Obligations instantiate.

## ADRs referenced

(no ADRs referenciados directamente en código · alineado con patrones M03/M19)

## Cement OPS

Patrón consistente con M19 Project Risks y M03 DdA Engine: async methods, AsyncSession, exception-driven errors, no internal commits (delegate a caller), RLS enforcement via `set_tenant_context`.
