# Ejecutable 8 · Pasada 11 · Cloud Connections

## Resumen ejecutivo
La feature cloud está arquitecturalmente sólida y cliente-mínimo 100% alineada. El motor `m_cloud_connectors` es la capa unificada (ADR-053) y los conectores concretos viven en `m16_onboarding/connectors/`. El pipeline DTO→CloudResource→gap engine→CloudGap es coherente y determinista (R1). Los hallazgos son de **profundidad de cobertura** (atributos no poblados por AWS/Azure) y **consistencia de guidance** (AWS/Azure/GitHub sin entrada en `CONNECTOR_PROVIDER_ENS_GUIDANCE`), más el **DB-DRIFT-01** ya reservado a Pasada 16. No hay deuda de seguridad ni violación de ADR-014.

## 1. Estado de conectores (providers existentes)

Enum `ConnectorProvider` (`m16_onboarding/connectors/base.py:12`) + registro vía `register_connector`:

| Provider | Connector file | LOC | Registrado | OAuth | Catalog `_PROVIDER_CATALOG` |
|----------|----------------|-----|-----------|-------|------------------------------|
| microsoft_365 | `microsoft365.py:251` | 251 | sí | client_credentials | sí (service.py:102) |
| google_workspace | `google_workspace.py:206` | 206 | sí | SA domain-wide | sí (service.py:111) |
| azure | `azure_connector.py:133` | 133 | sí | sí | sí (service.py:120) |
| aws | `aws_connector.py:111` | 111 | sí | no (Access Key RO) | sí (service.py:129) |
| github | `github_connector.py:117` | 117 | sí | sí | sí (service.py:138) |
| manual_import | (sin connector class) | — | n/a | no | sí (service.py:147) |

- ADR-014 read-only sostenido: `BaseConnector` solo define `validate_credentials` + `discover_assets` + `discover_identities` (`base.py:63-70`). No hay métodos write al provider. M365 usa `_graph_get` GET-only (`microsoft365.py:61`).
- `CloudConnectorService.trigger_sync` (`service.py:304`) NO escribe al provider: ejecuta `run_full_discovery` (read) y persiste `CloudResource` vía `_upsert_resources` (`service.py:400`, INSERT ON CONFLICT idempotente).
- Guard de producción `MockModeNotAllowedError` (`service.py:73`, 336): impide auto-resolver gaps con dataset vacío en prod (protege trazabilidad ENAC). MANUAL_IMPORT exento.

## 2. Agent guidance per provider

`CONNECTOR_PROVIDER_ENS_GUIDANCE` (`gap_rules.py:473`) + `get_provider_ens_guidance` (`gap_rules.py:526`).

| Provider | guidance presente | measures_detectable | scopes | cliente_friendly_blurb |
|----------|-------------------|---------------------|--------|------------------------|
| microsoft_365 | sí | op.acc.6, op.acc.5, op.exp.1, mp.s.2, org.1 | 6 Graph scopes | sí |
| google_workspace | sí | op.acc.6, op.acc.5, op.exp.1, mp.s.2, org.1 | 4 Admin/Drive scopes | sí |
| **aws** | **NO** (DEFER comentado gap_rules.py:521) | — | — | — |
| **azure** | **NO** | — | — | — |
| **github** | **NO** | — | — | — |

**Inconsistencia (F-11-02):** AWS/Azure/GitHub están **registrados como connectors activos** y en `_PROVIDER_CATALOG` (cliente puede conectarlos), pero NO tienen entrada en `CONNECTOR_PROVIDER_ENS_GUIDANCE`. `get_provider_ens_guidance("aws")` devuelve `None`. El comentario en `gap_rules.py:521` los marca como DEFER post-piloto, pero el catálogo cliente ya los ofrece → el cliente puede conectar AWS sin que el sistema explique qué medidas le diagnostica.

## 3. Remediation OPTIONAL (ADR-014)

`remediation_orchestrator.py` — state machine `CloudRemediationApprovalStatus`:
`detected → proposed_to_cliente → approved | rejected → executing → executed | failed` (+ Phase A `executed → verification_pending → verified`).

- `approval_status` default `'detected'`, server_default `'detected'` (`models.py:355-359`).
- Flujo OPTIONAL cliente-approved: admin propone (`proposed_to_cliente`), cliente aprueba/rechaza (`cliente_approval_at`, `models.py:368`).
- **NO auto-execute destructivo:** `executed` es **admin-reportado** tras ejecución manual externa (orchestrator.py:310-311 "admin manually verified cloud action externa"); rollback también read-only sin API call cloud (orchestrator.py:482). ADR-014 sostenido empírico.
- Request-disconnect chat-mediated (api_cliente.py:331): NO ejecuta revoke; registra audit_log + crea chat thread con Marcos + SSE `cloud.connector.disconnect_requested`. Admin decide.

## 4. Matriz de cobertura ENS per provider (Anexo II)

Reglas en `RULE_CATALOG` (`gap_rules.py:396`). Cada detector es pure function R1. Atributos que cada connector realmente puebla:

| Medida (regla) | Atributo requerido | M365 | GWorkspace | AWS | Azure | GitHub |
|----------------|--------------------|------|-----------|-----|-------|--------|
| op.acc.6 MFA (`detect_users_without_mfa`) | `mfa_enabled is False` | sí (reports endpoint) | sí (`isEnrolledIn2Sv`) | no | no | no |
| op.acc.5 priv (`detect_excess_privileged_users`) | `is_privileged` | sí (directoryRoles) | sí (`isAdmin`) | parcial | parcial | no |
| op.exp.1 inventario (`detect_inventory_coverage`) | cualquier `asset.*` | sí | sí | sí | sí | sí |
| mp.info.3 cifrado at-rest (`detect_unencrypted_storage`) | `encrypted_at_rest is False` en asset.storage/bucket/volume | n/a (sin storage) | n/a | **NO puebla** | **NO puebla** | n/a |
| mp.s.2 público (`detect_public_buckets`) | `public_access/is_public is True` en bucket/storage/sharepoint_site/shared_drive | sí (sharepoint_site) | sí (shared_drive) | **NO puebla** (S3) | **NO puebla** | n/a |
| op.exp.8 logging (`detect_logging_disabled`) | `logging_enabled` en asset.* | no | no | **NO puebla** | **NO puebla** | no |
| op.cont.3 backup (`detect_no_backup_strategy`) | `backup_enabled` en storage | n/a | n/a | **NO puebla** | **NO puebla** | n/a |
| org.1 documental (`detect_documental_policy_missing`) | siempre emite | sí | sí | sí | sí | sí |

**Hallazgo F-11-01 (cobertura shallow AWS/Azure):** `aws_connector.py:96-105` descubre buckets S3 (`asset_type="storage"`) pero `raw_data` solo incluye `BucketName`+`CreationDate`; NO consulta `get_bucket_encryption`, `get_public_access_block`, `get_bucket_logging`, ni versioning/backup. Igual Azure (`azure_connector.py:123` genérico). Los detectores usan `.get("...") is False` (explícito), y como las claves faltan (→`None`), **mp.s.2 / mp.info.3 / op.cont.3 / op.exp.8 NUNCA disparan para AWS/Azure**. La extensión `detect_public_buckets` para `asset.sharepoint_site`/`asset.shared_drive` (gap_rules.py:245, Ejecutable 4) sí funciona porque M365/GWorkspace SÍ pueblan `public_access`/`is_public` (microsoft365.py:240, google_workspace.py:197).

**Mapeo DTO→resource_type verificado coherente:** `normalize_asset_to_resource_dict` (`base_connector.py:65`) genera `f"asset.{asset.asset_type}"` → `sharepoint_site`→`asset.sharepoint_site`, `shared_drive`→`asset.shared_drive`, `storage`→`asset.storage`. Concuerda con los `resource_type` esperados por los detectores.

## 5. Cliente-mínimo cross flows (R29 / ADR-013 / ADR-014)

`api_cliente.py` (4 endpoints `require_client_user`):
- **CONECTA/AUTORIZA:** `POST /connect/{provider}` (api_cliente.py:230) crea connector PENDING_OAUTH y delega el flujo OAuth a M16 portal_api (`m16_portal_init_path`), NO duplica state/PKCE (ADR-025).
- **VE:** `GET /` (api_cliente.py:176) resumen R29 con `friendly_message` (api_cliente.py:74, sin jargon, sin presión, "puedes volver a conectarlo cuando quieras"). Catalog `GET /providers/catalog` con blurbs amigables.
- **RECIBE:** digest mensual filtrado `GET /cloud-monitoring/digest/latest` (api_cliente.py:452) vía `build_client_digest_view` (NO serializa ORM admin, evita leak campos sensibles).
- **NO opera técnico:** request-disconnect chat-mediated (api_cliente.py:331), cliente nunca ve scopes técnicos ni IDs M16. Audit_log Sub-atom 5.A 3-way OR (project_id+client_id) en las 3 mutaciones cliente (api_cliente.py:99).

## 6. Scope expansion preview Future-X (post-piloto, documentado)

Ya catalogado en CLAUDE.md `Future-3B-2B-7-EXPANDED`: github/gitlab/aws/azure connectors ENS-audit-agent profundización + dropbox-business + cross-provider orchestrator + ens-measures-coverage-completeness-per-provider-matrix (~31-45h cumulative). Observación: AWS/Azure/GitHub connector **scaffolds ya existen** (registrados) pero son shallow; la "expansión" real es poblar atributos de seguridad + añadir guidance, no crear los connectors de cero.

## DB-DRIFT-01 (NO tocar · reservado Pasada 16)
`cloud_gaps.approval_status` definido en `models.py:355` + migración `backend/migrations/versions/cloud_remediation_orchestrator_b35_001.py`, pero NO aplicada al DB running (alembic multi-head tangle / upgrade bloqueado por radar alembic version_num widen, ver CLAUDE.md Sesión 3B-2B.7 Phase 7.0). Los ~50 fallos m_cloud_connectors de la suite derivan de la columna ausente en runtime DB — **NO es gap de feature**. (DB no alcanzable desde este entorno: connection refused localhost:5432, confirma no-tocar.)

## Conclusión
Cloud Connections production-ready a nivel arquitectura para piloto MEDIA con M365/GWorkspace (cobertura ENS real: op.acc.6, op.acc.5, op.exp.1, mp.s.2, org.1). AWS/Azure conectables pero diagnóstico de seguridad shallow (solo inventario op.exp.1 + org.1). 0 violaciones ADR-014. 4 findings TAGGED para Pasada 16.