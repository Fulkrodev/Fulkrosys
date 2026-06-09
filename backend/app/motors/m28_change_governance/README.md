# Motor 28 · Change Impact & Governance

Gobernanza de cambios (addendum v2.2 §8): clasificación cambios (MINOR / RELEVANT / MATERIAL) + árbol de decisión determinista de 10 preguntas + recategorización + auditoría extraordinaria + topology library (5 patrones predefinidos) + excepciones de roles (memos formales). Dominio compartido con M27 Conformity (ADR-023).

## Funcionalidades

- **Materiality engine** (`materiality_engine.py`) `IMPACT_QUESTIONS` (10 preguntas) + `assess` + `classify_change`.
- **Clasificación cambios** 3 niveles: MINOR (no afecta conformidad) · RELEVANT (revisión necesaria) · MATERIAL (recategorización + auditoría extraordinaria).
- **Impact assessor** (`impact_assessor.py`) evaluación impacto cambio cross-motor.
- **Recategorization service** (`recategorization_service.py`) recategoriza sistema post-cambio material (BÁSICA→MEDIA→ALTA).
- **Extraordinary audit service** (`extraordinary_audit_service.py`) abre auditoría extraordinaria post-cambio MATERIAL.
- **Topology library** (`topology_service.py` + `role_topology_extensions_api.py`) 5 patrones topology predefinidos (typical infra setups).
- **Role exceptions** memos formales para excepciones de roles ENS (responsable seguridad · DPO · etc.).
- **Service container** (`service.py`) `ChangeGovernanceService` wrapper para callers que prefieren service class sobre free functions.
- **Jobs** (`jobs.py`) Celery jobs gobernanza scheduled.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.166 |
| Files | 11 |
| Status | production-grade · 8 endpoints addendum v2.2 §8.9 |
| Tests | `backend/tests/motors/m28_change_governance/` |
| API prefix | `/api/v1/changes/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · 8 endpoints addendum v2.2 §8.9
- `service.py` · `ChangeGovernanceService` wrapper
- `materiality_engine.py` · `IMPACT_QUESTIONS` + `assess` + `classify_change`
- `impact_assessor.py` · impact assessment
- `recategorization_service.py` · recategorización post-MATERIAL
- `extraordinary_audit_service.py` · auditoría extraordinaria
- `topology_service.py` · topology library (5 patterns)
- `role_topology_extensions_api.py` · role exceptions API
- `jobs.py` · Celery jobs
- `schemas.py` · Pydantic in/out

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `Change` (`backend/app/models/operations.py`) + `metadata_jsonb` extended
- `ChangeTopologyRow` (`backend/app/models/change_governance.py`)
- `RecategorizationRow` + `ExtraordinaryAuditRow` (`backend/app/models/conformity_lifecycle.py` · cross-motor M27 ADR-023)

Mapping cement: `_CHANGES` → `Change` · `_RECATEGORIZATIONS` → M27 cross-motor · `_EXTRAORDINARY_AUDITS` → M27 cross-motor · `_TOPOLOGIES` → `change_topologies`.

RLS por `changes` + topology tables.

## Cross-motor integration

- **Inbound**: M16 Onboarding (consume change events post-onboarding)
- **Outbound**: M30 Client Contacts (notificación stakeholders cambio)
- **LLM agents**: ninguno (motor decision tree determinístico)

## ADRs referenced

- ADR-023 · dominio compartido m27/m28 (cement cross-motor recategorización + extraordinary audit)

## Cement OPS

Dominio compartido con M27 Conformity (ADR-023 cement). 10 preguntas decision tree son **invariante institutional** (modificación require ADR formal). Topology library 5 patterns extensible (forward más patrones cuando emerge demanda). Sub-fase 5.5.F.0.H refactor in-memory → DB-backed (TODO-M28-CHANGE-GOVERNANCE-PERSISTENCE-001).
