# Motor 23 · Retainer Management

Gestión post-certificación multi-cliente con 4 perfiles (R_LITE / R_STD / R_PLUS / R_CRITICAL), cadencias automáticas, renewal clock, drift detector + dashboard RAG (Red/Amber/Green). **Escalabilidad cement**: 20-40 clientes simultáneos para Marcos sin contratar. **Outbound más grande FULKRO**: 9 motores downstream consumidos. Incluye 2 agentes propios (A15 Vigilancia · A26).

## Funcionalidades

- **4 perfiles retainer** (`VALID_PROFILES`) R_LITE / R_STD / R_PLUS / R_CRITICAL con cadencias + horas + SLA distintos.
- **Cadencias automáticas** (`CADENCES_BY_PROFILE`) per perfil · scheduled checks + renewal trigger + alerts.
- **Horas mensuales** (`HOURS_BY_PROFILE`) per perfil · presupuesto horas Marcos.
- **SLA per perfil** (`SLA_BY_PROFILE`) per perfil · tiempos respuesta + escalation.
- **Drift detector** (`drift_compute_service.py`) compute drift sobre `DRIFT_DIMENSIONS` · `DRIFT_IMPACTS` · `DRIFT_SEVERITIES` per cliente.
- **Renewal clock** automatic countdown bienal renovación ENS.
- **Timesheet system** (`timesheet_service.py` + `timesheet_api.py` + `timesheet_models.py`) Marcos timesheet entries · tracking horas per cliente.
- **Retainer checkin** (`retainer_checkin_service.py` + `retainer_checkin_portal_api.py`) cliente in-portal checkin mensual.
- **Pricing catalog seed** (`pricing_catalog_seed.py`) seed inicial catálogo pricing retainer.
- **Billing integration** (`billing_integration.py`) wire-up M15 emisión factura mensual retainer.
- **Reports** (`report_renderer.py` + `report_service.py`) `render_annual_report_docx` + `render_quarterly_report_docx`.
- **CCN-STIC scraper** (`ccn_stic_scraper.py`) scraping CCN-STIC para detectar cambios normativos · feed forward A26.
- **Agent 15 Vigilancia** (`agent_15_vigilancia.py`) agente especializado vigilancia regulatoria.
- **Agent 26** (`agent_26.py`) agente especializado retainer-specific.
- **Paso 2 extensions** (`paso2_extensions.py` + `api_paso2.py`) extensiones K.0 commercial cycle.
- **Addendum v22** (`addendum_v22.py`) extensiones MB-9.bis multi-norma.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 6.533 |
| Files | 20 |
| Status | production-grade · escalabilidad 20-40 clientes cement |
| Tests | `backend/tests/motors/m23_retainer/` |
| API prefix | `/api/v1/retainer/*` (+ timesheet + checkin sub-routers) |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP retainer core
- `api_paso2.py` · endpoints paso2 commercial extensions
- `timesheet_api.py` · timesheet endpoints
- `retainer_checkin_portal_api.py` · cliente checkin portal
- `retainer_service.py` · `RetainerService` core + perfiles constants
- `retainer_checkin_service.py` · cliente checkin logic
- `timesheet_service.py` · timesheet logic
- `timesheet_models.py` · ORM `marcos_timesheet_entries`
- `drift_compute_service.py` · drift detection compute
- `billing_integration.py` · wire-up M15
- `report_renderer.py` + `report_service.py` · DOCX reports
- `ccn_stic_scraper.py` · CCN-STIC scraping
- `agent_15_vigilancia.py` · A15 Vigilancia agent
- `agent_26.py` · A26 agent
- `paso2_extensions.py` · paso2 extensions
- `pricing_catalog_seed.py` · pricing seed
- `tasks.py` · Celery jobs (cadencias · drift compute · alerts)
- `addendum_v22.py` · extensiones MB-9.bis

⚠️ NO existe `service.py` único · scope split por concern (retainer · checkin · timesheet · drift · billing · reports).

## DB tables

Motor-specific (ORM en `timesheet_models.py`):

- `marcos_timesheet_entries` · timesheet entries Marcos per cliente

Y modelos compartidos `Retainer` (per project · perfiles) + `DriftDetection` (drift state).

## Cross-motor integration

- **Inbound**: M25 Lifecycle (lifecycle events trigger retainer state changes)
- **Outbound** (**9 motores · más outbound del cluster H7.C**):
  - M05 Signing (firma retainer mensual)
  - M07 Evidence (evidence tracking obligation completion)
  - M08 Verification (pentest retainer scope mensual)
  - M10 Audit Sim (simulación incluida en retainer)
  - M15 Billing (factura mensual retainer)
  - M18 Communication (alerts + reports cliente)
  - M21 Portal Cliente (cliente VE retainer status)
  - M25 Lifecycle (lifecycle state transitions)
  - M27 Conformity (renewal clock cross-motor)
- **LLM agents**: A15 Vigilancia + A26 (propios) · A28 Diagnosis cross-feed

## Limitaciones conocidas

### Escalabilidad 20-40 clientes cement

Diseño objetivo: Marcos solo manejando 20-40 clientes simultáneos sin contratar. Si demanda excede, **trigger contratación**: refactor pattern multi-Marcos / team retainer (forward post-piloto).

## ADRs referenced

(no ADRs referenciados directamente en código motor · cement via patrones M03/M19)

## Cement OPS

Outbound más grande del cluster H7.C (9 motores downstream). 4 perfiles + cadencias + drift detector son cement institutional escalabilidad. 2 agentes propios (A15 + A26) embebidos en motor (anti-pattern parcial · cement compatible por motor scope retainer-specific).
