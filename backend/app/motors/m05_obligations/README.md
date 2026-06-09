# Motor 5 · Obligations + Gantt Planning

Instancia obligaciones legales ENS a partir de gaps M04 priorizados, y planifica su ejecución vía Gantt con dependencias circulares detectadas, esfuerzo y personalización por cliente. Hermano sibling de M05_signing (pattern motor parallel M10/M21).

## Funcionalidades

- **Instantiation de obligaciones** desde gaps M04 (`instantiate_obligations_for_multiple_gaps`) con `ClientContext` + `ProjectContext` + `GapInput`.
- **Gantt planner determinístico** (`gantt_planner.py` + `gantt_service.py`) calcula ordenamiento topológico + fechas inicio/fin.
- **Detección de dependencias circulares** vía `CircularDependencyError` (DAG validation).
- **Library loader** (`library_loader.py`) carga catálogo de obligaciones desde `library/` subdir versionado.
- **Personalización per cliente** (`personalization.py`) ajusta obligations según contexto cliente.
- **Export Gantt a XLSX** (`export_gantt_to_xlsx_bytes`) para entrega cliente / planificación interna.
- **Tipos canónicos**: `GapItem` · `ClientContext` · `ProjectContext` · `GapInput`.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.662 |
| Files | 10 (+1 subdir `library/`) |
| Status | production-grade |
| Tests | `backend/tests/motors/m05_obligations/` |
| API prefix | `/api/v1/obligations/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP (instantiate + Gantt + export XLSX)
- `gantt_planner.py` · algoritmo planificación topológica + scheduling
- `gantt_service.py` · `build_gantt_for_project` · `export_gantt_to_xlsx_bytes`
- `gantt_types.py` · `CircularDependencyError` + tipos Gantt
- `instantiation_service.py` · `instantiate_obligations_for_multiple_gaps` core
- `instantiation_types.py` · `ClientContext` · `ProjectContext` · `GapInput`
- `library_loader.py` · carga catálogo `library/` versionado
- `personalization.py` · per-cliente customization
- `types.py` · tipos compartidos
- `library/` · subdir con catálogo de obligaciones YAML/JSON

⚠️ NO existe `service.py` único · scope split en `gantt_service.py` + `instantiation_service.py` por responsabilidad.

## DB tables

N/A motor-specific · usa modelo `Obligation` (`backend/app/models/ens.py`). RLS por `obligations`.

## Cross-motor integration

- **Inbound**: M04 Gap Analysis (gaps priorizados como input)
- **Outbound**: M21_portal_cliente (cliente view obligations + Gantt)
- **LLM agents**: ninguno (motor determinístico)

## ADRs referenced

- ADR-013 · separación arquitectónica de portales (admin / radar / client)
- ADR-020 · tablas sessions separadas con cookie común + dual dispatcher

## Cement OPS

Sibling de M05_signing (numbering anomaly intencional · pattern motor parallel M10_audit_sim/M10_ens_radar y M21_diagnosis/M21_portal_cliente).
