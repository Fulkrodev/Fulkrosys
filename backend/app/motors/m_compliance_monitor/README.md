# Motor `m_compliance_monitor` · FULKRO Self-Monitoring System

Verificación autónoma de la propia compliance posture de FULKRO across 6 normativas: RGPD + LOPDGDD + LSSI-CE + NIS2 + ISO 27001 + ENS. **19 checks** ejecutados en Celery beat cadence (daily/weekly/monthly/quarterly). Cada non-green transition produce `ComplianceAlert`; HIGH severity → email inmediato Marcos · MEDIUM/LOW → digest diario/semanal. Subsystem **platform-global** (no `project_id` · no RLS · admin-only).

## Funcionalidades

- **19 checks autónomos** cubriendo 6 normativas (atom 9.bis.6 → MB-10 Atom 10.1 expanded 17→19):
  - **RGPD (UE 2016/679)**: endpoint health · RoPA freshness · cookie consent renewal
  - **LOPDGDD (3/2018)**: DPO contact channel · AEPD notification readiness
  - **LSSI-CE (34/2002)**: legal pages reachability
  - **NIS2 (UE 2022/2555)**: security.txt · vulnerability inbox · supply chain DPA expirations
  - **ISO 27001:2022**: backups integrity · audit log continuity · RLS coverage · SSL cert expiry · ISMS doc review cadence
  - **ENS**: cross-check medidas Anexo II
- **CHECK_REGISTRY** (`checks.py`) registro central 19 checks declarativos.
- **Celery beat cadence** (`tasks.py`) daily/weekly/monthly/quarterly automated runs.
- **ComplianceMonitorService** (`service.py`) orquesta runs + alert lifecycle (open · auto-resolve · manual resolve).
- **Severity emails**: HIGH inmediato · MEDIUM digest diario · LOW digest semanal.
- **Norma reports** (`norma_reports_service.py` + `norma_reports_api.py`) reportes per normativa.
- **Norma tasks** (`norma_tasks.py`) Celery jobs específicos per normativa.
- **Reports service** (`reports_service.py`) status reports cross-normativa.
- **Sub-processor subscribers** (`sub_processor_subscribers.py`) tracking suscripciones cambios sub-procesadores.
- **Public API** (`public_api.py`) endpoints públicos (security.txt · vulnerability inbox).
- **Normas subdir** (`normas/`) implementaciones per-normativa específicas.
- **Sync registry** endpoint upsert `CHECK_REGISTRY` rows en BD.
- **Aggregate dashboard snapshot** + manual trigger check + alerts list/resolve.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 4.145 |
| Files | 22 (+1 subdir `normas/`) |
| Status | production-grade · atom 9.bis.6 + MB-10 Atom 10.1 (17→19 checks) |
| Tests | `backend/tests/motors/m_compliance_monitor/` · 75 PASS cumulative pre-Block 1 |
| API prefix | `/admin/compliance/monitor/*` + public-api (security.txt) |
| RBAC | Admin-only · `require_owner` · platform-global (no RLS · no tenant context) |

## Key files

- `api.py` · admin endpoints (status + checks list + run + alerts CRUD + reports + sync-registry)
- `public_api.py` · endpoints públicos (security.txt + vulnerability inbox)
- `norma_reports_api.py` · per-normativa reports endpoints
- `service.py` · `ComplianceMonitorService` core
- `checks.py` · `CHECK_REGISTRY` declarative 19 checks
- `norma_reports_service.py` · per-normativa reports logic
- `reports_service.py` · cross-normativa status reports
- `norma_tasks.py` · Celery jobs per-normativa
- `tasks.py` · Celery beat scheduled jobs
- `sub_processor_subscribers.py` · sub-processor tracking
- `schemas.py` · Pydantic in/out
- `normas/` · subdir per-normativa implementations

## DB tables

Motor-specific (ORM en `sub_processor_subscribers.py` + compartidos):

- `sub_processor_subscribers` · suscripciones cambios sub-procesadores

Y modelos compartidos:
- `ComplianceCheck` (`backend/app/models/compliance_monitor.py`) · 19 checks registry
- `ComplianceAlert` · alerts lifecycle (open → resolved)
- `ComplianceCheckResult` · resultados runs históricos
- `ComplianceReport` · status reports per-normativa + cross

NO RLS · platform-global.

## Cross-motor integration

- **Inbound** (subdirs internas): `normas/` (per-normativa checks)
- **Outbound**: `m_compliance` (cross-feed cookies + RoPA freshness checks)
- **LLM agents**: ninguno (motor monitoreo determinístico estricto)

## Limitaciones conocidas

### Platform-global · NO multi-tenant

Subsystem audita la propia compliance de FULKRO **como organización** · NO compliance de proyectos cliente. No tiene `project_id` ni RLS. Distinto de M21 Diagnosis (que evalúa cliente compliance) · este audita FULKRO.

## ADRs referenced

- ADR-013 · separación arquitectónica de portales
- ADR-020 · tablas sessions separadas + cookie común + dual dispatcher

## Cement OPS

Atom 9.bis.6 (MB-9.bis) · MB-10 Atom 10.1 expanded 17→19 checks. Subsystem platform-global (no `project_id` · no RLS) es invariante arquitectónico (audita FULKRO no clientes). Severity-based email cadence (HIGH inmediato · MEDIUM diario · LOW semanal) es cement institutional anti-spam Marcos.
