# Motor 21 · Organizational Diagnosis

Diagnóstico organizacional del cliente: dashboard maturity + KPIs + ISO27001 coverage + processes inventory + stakeholder analysis + compliance obligations cross-norm (ENS · ISO27001 · RGPD · NIS2 · etc.) + quick-wins identification. Sibling de M21_portal_cliente (numbering anomaly intencional · pattern motor parallel).

## Funcionalidades

- **Dashboard maturity** (`dashboard_service.py` + `dashboard_api.py` + `dashboard_schemas.py`) KPIs agregados estado ENS readiness per área.
- **Maturity service** (`maturity_service.py`) cálculo de madurez per dominio (L0-L5).
- **ISO27001 coverage** (`iso27001_coverage.py`) cobertura controles ISO27001 cross-check con ENS Anexo II.
- **Compliance service** (`compliance_service.py` + `cross_compliance_service.py`) cross-norm obligations detection (DORA · NIS2 · RGPD · ENS).
- **Stakeholder analysis** (`stakeholder_service.py` + `stakeholders_service.py`) análisis de stakeholders + roles + responsabilidades.
- **Process inventory** (`process_service.py` + `processes_service.py`) inventario de procesos cliente.
- **M1/M2 feeds** (`m1_m2_feeds.py`) integración con outputs M01 Categorization + M02 MAGERIT para diagnosis enriquecido.
- **Quick wins** (`quickwins.py`) identificación de mejoras de bajo esfuerzo / alto impacto.
- **Paso 5 orchestrator** (`paso5_orchestrator.py`) orquestación fase K.4 entrega diagnosis.
- **Report generator** (`report_generator.py`) generación informes DOCX (`generate_report_docx`) + PDF.
- **Templates subdir** templates de diagnosis per sector.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.342 |
| Files | 18 (+1 subdir `templates/`) |
| Status | production-grade |
| Tests | `backend/tests/motors/m21_diagnosis/` |
| API prefix | `/api/v1/diagnosis/*` (+ dashboard sub-router) |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP diagnosis CRUD + report download
- `dashboard_api.py` · endpoints dashboard KPIs cliente
- `service.py` · `DiagnosisError` + `run_diagnosis` + `get_latest_diagnosis` + `list_diagnosis_runs`
- `dashboard_service.py` · KPIs agregados
- `maturity_service.py` · `calculate_maturity` L0-L5
- `compliance_service.py` · `detect_compliance_obligations` cross-norm
- `cross_compliance_service.py` · DORA + NIS2 + ENS + RGPD detection
- `iso27001_coverage.py` · ISO27001 controls coverage
- `stakeholder_service.py` + `stakeholders_service.py` · stakeholder analysis
- `process_service.py` + `processes_service.py` · process inventory
- `m1_m2_feeds.py` · cross-motor M01/M02 inputs
- `quickwins.py` · quick wins identification
- `paso5_orchestrator.py` · fase K.4 orchestration
- `report_generator.py` · DOCX + PDF generation
- `templates/` · subdir diagnosis templates

## DB tables

N/A motor-specific declarado en api.py · usa modelo `DiagnosisRun` (`backend/app/models/diagnosis.py`). RLS por `diagnosis_runs`.

## Cross-motor integration

- **Inbound**: ninguno directo (consumido vía API por admin UI)
- **Outbound**:
  - M02 MAGERIT (cross-feed riesgos)
  - M09 Audit Prep (consume audit readiness en dashboard)
  - M16 Onboarding (consume onboarding completion state)
- **LLM agents**: ninguno directo (motor data aggregation + reporting)

## ADRs referenced

- ADR-035 · referenced en código motor

## Cement OPS

Sibling de M21_portal_cliente (numbering anomaly intencional). Motor entrega fase K.4 (diagnosis) input para retainer post-cierre cliente. Token encryption Fernet reused from M16 onboarding para credentials cliente.
