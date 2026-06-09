# Motor 22 · Technical Discovery

Discovery técnico end-to-end de la infraestructura cliente: assets + configuraciones + datos + identidades + flujos de datos + vulnerabilidades · vía AWS connector + Microsoft 365 connector · MAGERIT categories mapper · E.090 technical document generator. **2nd LARGEST motor FULKRO** (8.459 LOC · 23 files).

## Funcionalidades

- **Asset discovery** (`asset_discovery.py` + `paso6_asset_discoverer.py`) inventario de activos cloud/on-prem con MAGERIT categorization.
- **AWS connector** (`paso6_aws_connector.py`) integración SDK AWS · descubre EC2 · S3 · IAM · VPCs · RDS · etc.
- **Microsoft 365 connector** (`paso6_m365_connector.py`) integración Graph API · descubre Users · Groups · SharePoint · OneDrive · Teams · etc.
- **Configuration discovery** (`config_discovery.py` + `paso6_config_detector.py`) detección configuraciones de seguridad (CIS Benchmark · etc.).
- **Data discovery** (`data_discovery.py`) descubrimiento de datos personales (RGPD scope) en infra cliente.
- **Identity discovery** (`identity_discovery.py`) inventario identidades + permisos + RBAC analysis.
- **Vuln discovery** (`vuln_discovery.py` + `paso6_vuln_inventory.py`) inventario vulnerabilidades detectadas (cross-feed M08).
- **Data flow mapper** (`dataflow_service.py` + `paso6_data_flow_mapper.py`) mapeo flujos de datos personales (RGPD art. 30 RoPA).
- **Continuity service** (`continuity_service.py`) análisis de continuidad de negocio (BIA cross-feed M19).
- **Log assessment** (`log_assessment.py`) evaluación logs habilitados infra cliente.
- **MAGERIT categories** (`magerit_categories.py`) mapper assets → MAGERIT v3 Libro II tipos.
- **E.090 Technical Document** (`paso6_e090_technical.py`) generación documento técnico paso 6 fase K.2.
- **Orchestrator** (`orchestrator.py` + `paso6_orchestrator.py`) pipeline coordination phase K.2.
- **Alerts service** (`alerts_service.py`) alertas durante discovery (asset crítico expuesto · config inseguro · etc.).
- **Demo mocks** (`paso6_demo_mocks.py`) mocks para demos pre-cliente real.
- **Report generator** (`report_generator.py`) reportes DOCX + PDF post-discovery.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 8.459 (**2nd LARGEST motor FULKRO** post M08) |
| Files | 23 (+1 subdir `templates/`) |
| Status | production-grade · paso6 K.2 complete |
| Tests | `backend/tests/motors/m22_discovery/` |
| API prefix | `/api/v1/discovery/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP discovery CRUD + reports + E.090
- `orchestrator.py` + `paso6_orchestrator.py` · pipeline coordination
- `paso6_asset_discoverer.py` · core discovery
- `paso6_aws_connector.py` · AWS SDK integration
- `paso6_m365_connector.py` · M365 Graph API integration
- `paso6_config_detector.py` · CIS + security config detection
- `paso6_data_flow_mapper.py` · data flow mapping RGPD
- `paso6_e090_technical.py` · E.090 document gen
- `paso6_vuln_inventory.py` · vuln inventory cross-feed M08
- `paso6_demo_mocks.py` · demo mocks
- `asset_discovery.py` · asset discovery helpers
- `config_discovery.py` · config discovery helpers
- `data_discovery.py` · data discovery helpers
- `identity_discovery.py` · identity discovery helpers
- `vuln_discovery.py` · vuln discovery helpers
- `dataflow_service.py` · data flow service
- `continuity_service.py` · continuity / BIA
- `log_assessment.py` · log assessment
- `magerit_categories.py` · MAGERIT mapper
- `alerts_service.py` · discovery alerts
- `report_generator.py` · DOCX + PDF reports
- `templates/` · subdir discovery templates

⚠️ NO existe `service.py` único · scope split por concern (asset · config · data · identity · vuln · dataflow · continuity).

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `DiscoveredAsset` + `DiscoveredIdentity` (`backend/app/models/onboarding.py`)
- `DiscoveredConfiguration` + `DiscoveredDataStore` + `VulnerabilityFinding` (`backend/app/models/discovery.py`)

RLS por `discovered_*` tables.

## Cross-motor integration

- **Inbound**: ninguno directo (consumido vía API por dashboards admin)
- **Outbound**:
  - M02 MAGERIT (cross-feed assets para risk analysis)
  - M16 Onboarding (consume discovery completion state)
- **LLM agents**: ninguno (motor data ingestion + classification determinístico)

## Limitaciones conocidas

### Demo mocks habilitados para entornos sin cliente real

`paso6_demo_mocks.py` permite ejecutar discovery con datos mock para demos comerciales pre-cliente. Activable vía `_dev/` env-gated endpoint (CASE A production-safe confirmed en FASE 1 B1.1).

## ADRs referenced

(no ADRs referenciados directamente en código motor)

## Cement OPS

2nd LARGEST motor FULKRO post M08. Pattern paso6_* indica fase K.2 cement (discovery técnico antes de K.4 diagnosis). OAuth credentials encryption Fernet via M16 token_encryption shared (cross-motor reuse).
