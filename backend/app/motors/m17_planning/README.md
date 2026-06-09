# Motor 17 · Project Planning

Planificación de proyecto ENS cliente: WBS (Work Breakdown Structure) catalog + effort estimator + PDA (Plan de Aplicación) generator + Gantt scheduling. Convierte el alcance ENS (categoría · número activos · sector · políticas) en plan ejecutable con esfuerzo estimado per tarea + dependencias + cronograma.

## Funcionalidades

- **WBS catalog** (`wbs_catalog.py`) catálogo tareas estándar per fase ENS (K.0 · K.1 · K.2 · K.4 · K.6 · retainer mensual).
- **Effort estimator** (`effort_estimator.py`) estimación esfuerzo per tarea basado en categoría sistema + número de activos + sector + complejidad.
- **PDA generator** (`pda_generator.py`) genera Plan de Aplicación documento con cronograma + hitos + entregables.
- **Planning service** (`planning_service.py`) core orchestration · ensambla WBS + esfuerzos → cronograma Gantt.
- **Patrones de planificación** alineados a Sesión 11 ADR-007 (orquestación guiada D17 Opción A).
- **API REST CRUD** para edición manual de plan cliente.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.074 |
| Files | 6 |
| Status | production-grade |
| Tests | `backend/tests/motors/m17_planning/` |
| API prefix | `/api/v1/planning/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP planning CRUD + estimator
- `planning_service.py` · core orchestration
- `effort_estimator.py` · estimación esfuerzo per tarea
- `pda_generator.py` · Plan de Aplicación documento gen
- `wbs_catalog.py` · catálogo Work Breakdown Structure

⚠️ NO existe `service.py` único · core en `planning_service.py`.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `ProjectPlan` + `PlanTask` (`backend/app/models/planning.py`)

RLS por `project_plans`.

## Cross-motor integration

- **Inbound**:
  - M13 Commercial (pricing factor desde effort estimator)
  - M18 Communication (report data del plan para informes cliente)
- **Outbound**: ninguno directo (motor consumido por upstream)
- **LLM agents**: ninguno (motor determinístico template-driven)

## ADRs referenced

(no ADRs referenciados directamente en código motor)

## Cement OPS

Motor template-driven · WBS catalog extensible per sector ENS. Effort estimator es input al pricing M13 (anti-alucinación económica: estimación NO LLM).
