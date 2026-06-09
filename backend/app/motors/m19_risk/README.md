# Motor 19 · Project Risk Management

CRUD de riesgos del proyecto · BIA (Business Impact Analysis) + incidents workflow (admin + portal cliente) + CCN-CERT decision tree para notificación incidentes ENS · catalog instantiation desde catálogo riesgos templated. Lifecycle completo: monitor → materialize → close.

## Funcionalidades

- **CRUD ProjectRisk** (`service.py` · `ProjectRiskService`) create + update + monitor + materialize + close per project.
- **Catalog instantiation** (`catalog_loader.py`) instancia riesgos desde catálogo templated (`VALID_CATEGORIES` + `VALID_STATUS`).
- **BIA (Business Impact Analysis)** (`bia_service.py` + `bia_api.py`) análisis impacto negocio per asset + escenario.
- **Incidents workflow** (`incident_workflow_service.py` + `incident_admin_api.py` + `incident_portal_api.py`) ciclo de vida incidentes: report (cliente) → triage (admin) → escalation → close.
- **CCN-CERT decision tree** (`ccn_cert_decision_tree.py`) decision tree para notificación incidentes a CCN-CERT (art. NIS2 + ENS § obligatorio).
- **Risk dashboard** (`RiskDashboardResponse`) KPIs agregados (open/closed/critical · por categoría).
- **Triggers** (`triggers.py`) eventos automáticos (riesgo materializa → alerta + incidente auto-created).
- **Incident portal API cliente** cliente reporta incidente desde portal in-portal review (ADR-020).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.544 |
| Files | 13 |
| Status | production-grade |
| Tests | `backend/tests/motors/m19_risk/` |
| API prefix | `/api/v1/risk/*` (admin) + portal-api cliente |
| RBAC | Cat A · Marcos-only admin · cliente vía portal-api |

## Key files

- `api.py` · endpoints HTTP risks CRUD + dashboard
- `service.py` · `ProjectRiskService` core CRUD
- `bia_api.py` + `bia_service.py` · BIA endpoints + lógica
- `incident_admin_api.py` · endpoints admin incidents
- `incident_portal_api.py` · endpoints cliente portal incidents
- `incident_workflow_service.py` · lifecycle incidents
- `ccn_cert_decision_tree.py` · decision tree notificación CCN-CERT
- `catalog_loader.py` · instantiation desde catálogo templated
- `triggers.py` · eventos automáticos
- `exceptions.py` · domain errors
- `schemas.py` · Pydantic in/out

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `ProjectRisk` (`backend/app/models/planning.py`)
- `Incident` (`backend/app/models/incidents.py`)
- `BiaAnalysis` (BIA per asset)

RLS por `project_risks` + `incidents`.

## Cross-motor integration

- **Inbound**: ninguno directo (consumido vía API por dashboards admin + portal cliente)
- **Outbound**:
  - M05 Signing (firma valoración riesgos · documento BIA)
  - M12 Magic Link (notificación cliente)
  - M18 Communication (alertas + escalation)
  - M21 Portal Cliente (cliente reporta incidentes in-portal)
- **LLM agents**: ninguno (motor determinístico)

## Limitaciones conocidas

### CCN-CERT notification manual gating

Decision tree GENERA recomendación notificar/no-notificar CCN-CERT, pero el envío real es **manual gating Marcos** (revisión jurídica obligatoria pre-submit). Decisión: no auto-submit · riesgo legal alto.

## ADRs referenced

- ADR-020 · in-portal review pattern (cliente reporta incidente sin magic-link)
- ADR-026 · referenced en código motor
- ADR-034 · cement determinismo

## Cement OPS

Patrón consistente con M03 DdA y M12 Magic Link · async + AsyncSession + exceptions-driven + no internal commits + RLS enforcement. CCN-CERT manual gating es cement institucional (legal review obligatoria).
