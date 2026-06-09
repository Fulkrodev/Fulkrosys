# Motor 24 · Intelligent Document Management System (IDMS)

El "Drive de FULKRO": 15 carpetas estándar por proyecto, intake pipeline con deduplicación SHA-256, búsqueda ILIKE sobre nombre + `full_text_content`, etiquetado manual con medidas ENS. + Awareness tracker para tracking de progreso formación cliente. **Future** (requiere LLM): embeddings semánticos, clasificación LLM, deduplicación semántica.

## Funcionalidades

- **15 carpetas estándar per proyecto** (`STANDARD_FOLDERS`) estructura canónica IDMS · alineada flow ENS.
- **Intake pipeline** con deduplicación SHA-256 (file hash) para evitar storage duplicado.
- **Búsqueda ILIKE** sobre nombre archivo + `full_text_content` (texto extraído documento).
- **Etiquetado manual** con medidas ENS Anexo II per documento.
- **Roles + statuses** (`VALID_ROLES` + `VALID_STATUSES`) per documento (draft · reviewed · approved · archived).
- **IDMS service** (`idms_service.py`) core CRUD + intake + search + tagging.
- **Awareness tracker** (`awareness_tracker.py` + `awareness_api.py`) tracking de awareness training cliente (cursos completados · evaluaciones · scoring).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.976 |
| Files | 5 |
| Status | production-grade core · LLM semantic features future |
| Tests | `backend/tests/motors/m24_idms/` |
| API prefix | `/api/v1/idms/*` (+ awareness sub-router) |
| RBAC | Cat C · Marcos crea/gestiona + cliente firma documentos (`require_marcos_or_client`) |

## Key files

- `api.py` · endpoints HTTP IDMS CRUD + intake + search + tags
- `awareness_api.py` · endpoints awareness training
- `idms_service.py` · `IDMSService` + `STANDARD_FOLDERS` + `VALID_ROLES` + `VALID_STATUSES`
- `awareness_tracker.py` · awareness tracking logic

⚠️ NO existe `service.py` único · core en `idms_service.py`.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `IdmsDocument` + `IdmsFolder` + `IdmsTag` (`backend/app/models/idms.py`)
- `AwarenessProgress` (awareness tracker)

RLS por `idms_documents` + `awareness_progress`.

## Cross-motor integration

- **Inbound**: M09 Audit Prep (consume IDMS para dossier compilation)
- **Outbound**: ninguno directo (motor storage + search self-contained)
- **LLM agents**: ninguno actualmente (semantic features future)

## Limitaciones conocidas

### Búsqueda solo ILIKE (NO semántica)

Búsqueda actual ILIKE sobre nombre + `full_text_content` extraído. NO hay embeddings semánticos ni clasificación LLM ni deduplicación semántica (solo SHA-256 byte-level).

**Cuándo se implementará semantic** · trigger demanda cliente categoria ALTA con volumen alto documental · candidate embeddings + LLM classifier + semantic dedup post-piloto multi-cliente.

## ADRs referenced

- ADR-034 · cement determinismo (referenced en código)

## Cement OPS

15 carpetas estándar es invariante estructural · alineado flow ENS canónico (K.0..K.6 + retainer). SHA-256 dedup es invariante storage efficiency. Awareness tracker es complemento institutional (cumplimiento RGPD + ENS formación obligatoria).
