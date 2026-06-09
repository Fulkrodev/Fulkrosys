# Motor 7 · Evidence Management

Gestión del ciclo de vida completo de evidencias ENS: ingestion (upload cliente + admin) · scan antivirus ClamAV · verificación criptográfica · freshness/caducidad tracking · renewal workflow. Pieza nuclear del audit trail ENAC.

## Funcionalidades

- **Ingestion service** (`ingestion_service.py`) acepta upload de evidence (cliente vía portal · Marcos vía admin) con `IngestionRequest`.
- **Hash SHA256 + firma Ed25519** per evidence al ingerirse · trazabilidad inmutable.
- **Antivirus scan ClamAV** (`antivirus_scan_service.py` + `antivirus_admin_api.py`) integración ClamAV daemon · scan obligatorio pre-ingest.
- **Freshness service** (`freshness_service.py`) calcula caducidad per tipo evidence · alertas pre-expiry.
- **Renewal service** (`renewal_service.py`) workflow de renovación cliente vía magic-link OR portal.
- **Verification service** (`verification_service.py`) verifica integridad criptográfica + firma + hash chain.
- **Public router** (`public_router.py`) endpoints públicos (verificación firma post-download).
- **Catalog subdir** versioned catalog de tipos de evidence con metadata (periodicidad · obligatoriedad · ENS measure mapping).
- **Addendum v22** (`addendum_v22.py`) extensiones multi-norma.
- **Tasks Celery** (`tasks.py`) jobs async (freshness sweep · scan retries · cleanup).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.278 |
| Files | 16 (+1 subdir `catalog/`) |
| Status | production-grade |
| Tests | `backend/tests/motors/m07_evidence/` |
| API prefix | `/api/v1/evidence/*` |
| RBAC | Cat C · cliente sube/lista propias · Marcos lista/modera todas (`require_marcos_or_client`) |

## Key files

- `api.py` · endpoints HTTP (upload · list · freshness · renewal · verify)
- `public_router.py` · endpoints públicos verificación post-download
- `antivirus_admin_api.py` · admin endpoints ClamAV (status · scan logs · quarantine)
- `ingestion_service.py` · `ingest_evidence` core (hash + sign + scan + persist)
- `ingestion_types.py` · `IngestionRequest` · `IngestionError`
- `antivirus_scan_service.py` · ClamAV daemon wrapper + scan execution
- `freshness_service.py` · `check_freshness_for_project` (caducidad calc)
- `renewal_service.py` · `create_renewal_request` workflow
- `verification_service.py` · `verify_evidence` crypto check
- `catalog_loader.py` · carga catálogo `catalog/`
- `signing.py` · Ed25519 wire-up M05_signing
- `tasks.py` · Celery jobs (freshness sweep · cleanup · scan retries)
- `types.py` · tipos compartidos
- `addendum_v22.py` · extensiones MB-9.bis
- `catalog/` · subdir catálogo tipos evidence versionado

⚠️ NO existe `service.py` único · scope split en servicios especializados por responsabilidad (ingestion · freshness · renewal · verification · antivirus).

## DB tables

N/A motor-specific · usa modelo `Evidence` (`backend/app/models/evidence.py`). RLS por `evidences`.

## Cross-motor integration

- **Inbound**: M23 Retainer (evidence trackeada como obligation completion)
- **Outbound**: ninguno directo (motor self-contained con ClamAV daemon externo)
- **LLM agents**: ninguno (motor determinístico crypto + scan)

## Limitaciones conocidas

### ClamAV daemon dependency externa

`antivirus_scan_service.py` requiere ClamAV daemon corriendo en sidecar (docker-compose). Si daemon down → ingestion bloqueada (fail-safe sostained: NO se acepta evidence sin scan).

**Decisión**: fail-safe es correcto · evidence sin scan compromete audit trail ENAC. Si ClamAV down: alertar Marcos + bloquear hasta recovery.

## ADRs referenced

(no ADRs referenciados directamente en código)

## Cement OPS

Motor multi-service · scope split por responsabilidad (no monolithic). Pattern Celery tasks para jobs async (freshness sweep weekly · cleanup monthly). ClamAV daemon dependency es invariante de arquitectura · sidecar en docker-compose obligatorio.
