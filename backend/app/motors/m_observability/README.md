# Motor `m_observability` · LLM Observability

Admin observability sobre uso LLM en FULKRO: cost summary per period (daily/weekly/monthly) + top consumers (motores/agentes) + anomaly alerts + paginated interactions log. Lectura sobre `llm_interaction_log` tabla central. **SMALLEST motor FULKRO** (355 LOC · 3 files). NO cliente access · admin-only.

## Funcionalidades

- **Cost summary per period** (`get_cost_summary`) agregación coste LLM per period configurable (PERIODS constant).
- **Top consumers** (`get_top_consumers`) ranking motores/agentes con mayor consumo LLM.
- **Anomaly alerts** (`get_anomaly_alerts`) detección anomalías consumo (spike · sustained high · cost cap breached).
- **Paginated interactions log** (`get_interactions_paginated`) lectura paginada `llm_interaction_log` para investigation.
- **PERIODS constant** define periods soportados (daily · weekly · monthly · quarterly).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 355 (**SMALLEST motor FULKRO**) |
| Files | 3 |
| Status | production-grade · MB-7 Q3.A cement |
| Tests | `backend/tests/motors/m_observability/` (si existe) |
| API prefix | `/admin/llm-observability/*` |
| RBAC | Admin-only · `require_owner` · NO cliente access |

## Key files

- `api.py` · endpoints HTTP admin (cost-summary · top-consumers · anomalies · interactions paginated)
- `llm_observability_service.py` · `get_cost_summary` + `get_top_consumers` + `get_anomaly_alerts` + `get_interactions_paginated` + `PERIODS`

⚠️ NO existe `service.py` único · core en `llm_observability_service.py`.

## DB tables

N/A motor-specific declarado · lectura sobre tabla compartida central:

- `llm_interaction_log` (`backend/app/models/llm.py`) · log unificado de TODAS las LLM calls FULKRO (motor/agente · tokens · coste · latency · etc.)

NO RLS · platform-global · admin-only.

## Cross-motor integration

- **Inbound**: ninguno (motor lectura observability · admin dashboards consumen)
- **Outbound**: ninguno (motor self-contained read-only)
- **LLM agents**: ninguno directo (motor OBSERVA agents · no los consume)

## Limitaciones conocidas

### Read-only · NO control LLM routing aquí

Motor es **read-only sobre observability**. NO controla LLM routing (eso vive en `core/ai/llm_router.py`). NO controla cost caps (eso vive en M10_ens_radar `radar_settings` per cluster). Solo provee visibility para investigation + cost forecasting.

### Anomaly detection rules deterministas

Anomaly detection es deterministas (rules-based · spike thresholds · sustained averages). NO ML anomaly detection. Adecuado para volumen FULKRO actual (single-tenant Marcos · pre-escalabilidad multi-cliente intensivo).

## ADRs referenced

(no ADRs referenciados directamente en código motor)

## Cement OPS

SMALLEST motor FULKRO (355 LOC). MB-7 Q3.A cement. Lectura sobre tabla unificada `llm_interaction_log` es invariante arquitectónico (single source of truth para LLM costs cross-motor cross-agent). Audit O7 confirmó "M_observability 355 smallest" cement empírico.
