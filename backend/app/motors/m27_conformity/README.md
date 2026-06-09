# Motor 27 · Conformity Lifecycle & Submission

Gobierno integral del ciclo de conformidad ENS (addendum v2.2 §7): Ruta formal del proyecto (Declaración vs Certificación) · state machine de ruta + submission · adaptadores externos asistidos (PILAR · LUCIA · INES · Registro) · Renewal Clock + campañas de renovación bianual · overlays PCE / micro-CeENS · DPC anual alerts. **4th LARGEST motor FULKRO** (7.194 LOC · 29 files).

## Funcionalidades

- **Route machine** (`route_machine.py`) state machine ruta formal proyecto · `RouteState` + `ACTIVE_STATES`.
- **Submission machine** (`submission_machine.py`) state machine envío conformidad.
- **Conformity service paso5** (`conformity_service_paso5.py` + `api_paso5.py`) fase K.5 specific.
- **Service** (`service.py`) core stateless · validación invariantes addendum v2.2 §7.3 + orquestación declaración/submission + cálculo renewal clock + validación overlays.
- **PILAR adapter** (`adapters/` subdir) PILAR XML exporter (MAGERIT cross-feed M02).
- **LUCIA federation** (`lucia_federation.py`) integración LUCIA (Catálogo de información de Seguridad de las Administraciones · CCN-CERT plataforma).
- **INES generator** (`ines_generator.py`) generación INES (Informe Nacional del Estado de Seguridad · obligatorio ENS) annual report.
- **Registro adapter** Registro Estatal Conformidad ENS.
- **Distintivo generator** (`distintivo_generator.py`) generación distintivo ENS oficial (logo certificación cliente).
- **DPC anual service** (`dpc_anual_service.py` + `dpc_anual_alert_task.py`) Declaración Pública de Conformidad anual obligatoria.
- **Biannual alert task** (`biannual_alert_task.py`) alerta renovación bianual.
- **Audit schedule service** (`audit_schedule_service.py`) calendario auditorías ENS per cliente.
- **Readiness service** (`readiness_service.py`) readiness scoring pre-submission.
- **Renewal scheduler** (`renewal_scheduler.py`) scheduler renovación bianual.
- **Renewal extensions API** (`renewal_extensions_api.py`) extensiones renovación.
- **Portal API cliente** (`portal_api.py` + `portal_api_dpc.py`) cliente VE conformity state + DPC anual.
- **Public API** (`public_api.py`) endpoints públicos verificación distintivo.
- **Jobs** (`jobs.py`) Celery jobs (renewal · biannual · DPC anual).
- **Catalogs subdir** catálogos estados + transiciones.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 7.194 (**4th LARGEST motor FULKRO**) |
| Files | 29 (+2 subdirs: `adapters/` · `catalogs/`) |
| Status | production-grade · 15 endpoints addendum v2.2 §7.11 |
| Tests | `backend/tests/motors/m27_conformity/` |
| API prefix | `/api/v1/conformity/*` (+ portal sub-router cliente + public-api) |
| RBAC | Cat A · Marcos-only admin · cliente vía portal-api · público vía distintivo verification |

## Key files

- `api.py` · 15 endpoints addendum v2.2 §7.11
- `api_paso5.py` · paso5 conformity endpoints
- `portal_api.py` · portal cliente endpoints
- `portal_api_dpc.py` · DPC anual portal endpoints
- `public_api.py` · endpoints públicos distintivo verification
- `service.py` · core stateless service (validación + orquestación)
- `conformity_service_paso5.py` · paso5 specific service
- `route_machine.py` · state machine ruta
- `submission_machine.py` · state machine submission
- `audit_schedule_service.py` · audit calendar
- `dpc_anual_service.py` · DPC anual logic
- `readiness_service.py` · readiness scoring
- `renewal_scheduler.py` · renewal scheduler
- `renewal_extensions_api.py` · renewal extensions
- `lucia_federation.py` · LUCIA integration
- `ines_generator.py` · INES annual report gen
- `distintivo_generator.py` · distintivo ENS gen
- `dpc_anual_alert_task.py` + `biannual_alert_task.py` · alert tasks
- `jobs.py` · Celery jobs
- `schemas.py` · Pydantic in/out
- `adapters/` · subdir external adapters (PILAR · Registro · etc.)
- `catalogs/` · subdir catálogos estados

## DB tables

N/A motor-specific declarado en api.py · usa 13 tablas `conformity_lifecycle` existing pre-S11 (refactor sub-fase 5.5.F.0.G in-memory → DB-backed):
- `ConformityRouteRow` (estados ruta)
- `PceOverlayRow` (overlays PCE)
- `ConformitySubmissionRow` (submissions)
- `RenewalCampaignRow` (campañas renewal)
- `BasicDeclarationRow` (declaraciones básicas)
- `ConformityStateSnapshotRow` (route history + external exports · polimórfica nueva)

RLS por `conformity_*` tables.

## Cross-motor integration

- **Inbound**:
  - M16 Onboarding (initial conformity mapping)
  - M23 Retainer (renewal clock cross-motor)
- **Outbound**:
  - M05 Signing (firma conformidad cliente)
  - M09 Audit Prep (consume readiness)
  - M18 Communication (alerts + reports cliente)
  - M21 Portal Cliente (cliente VE conformity state)
- **LLM agents**: ninguno (motor state machine + reglas determinístico)

## ADRs referenced

- ADR-020 · in-portal review pattern
- ADR-035 · referenced en código
- ADR-046 · capability vs feature_flag

## Cement OPS

4th LARGEST motor FULKRO. Addendum v2.2 prevalece sobre spec base v2.1.1 en estas materias. Sub-fase 5.5.F.0.G refactor in-memory → DB-backed (TODO-M27-STATE-MACHINE-PERSISTENCE-001) cement. LUCIA federation + INES + Registro adapter son cement legal obligatorio ENS · NO opcionales.
