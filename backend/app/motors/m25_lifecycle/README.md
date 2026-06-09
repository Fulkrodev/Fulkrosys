# Motor 25 · Project Lifecycle & Archival

Gestiona el ciclo de vida completo del proyecto: `DRAFT → ACTIVE → ... → ARCHIVED → PURGED`. State machine con transiciones explícitas (`VALID_TRANSITIONS`). Archive packages con SHA-256 + firma Ed25519. Purge condicionado a `purge_after <= hoy`. Exit checklist + grace period + backup ZIP + public tokens (acceso post-baja). Reutiliza modelos `ProjectLifecycleState` + `ArchivedProject`.

## Funcionalidades

- **State machine lifecycle** (`lifecycle_service.py`) `ALL_STATES` + `VALID_TRANSITIONS` enforced.
- **Default retention** (`DEFAULT_RETENTION_YEARS`) configurable per cliente.
- **Exit checklist** (`exit_checklist_service.py` + `exit_checklist_api.py`) checklist de salida cliente (export · settle · revoke · archive).
- **Backup builder** (`backup_builder.py`) generador de archive package con SHA-256 + firma Ed25519.
- **Paso 4 lifecycle** (`lifecycle_paso4.py` + `api_paso4.py`) lifecycle phase K.4 specific endpoints.
- **Public API** (`public_api.py`) endpoints públicos para acceso cliente post-baja vía public tokens.
- **Tasks Celery** (`tasks.py`) jobs async (purge sweep · archive cleanup · retention enforcement).
- **Grace period** post-archive antes de purge irreversible.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.504 |
| Files | 10 |
| Status | production-grade |
| Tests | `backend/tests/motors/m25_lifecycle/` |
| API prefix | `/api/v1/lifecycle/*` (+ exit-checklist sub-router + public-api) |
| RBAC | Cat A · Marcos-only admin · público vía public-api tokens |

## Key files

- `api.py` · endpoints HTTP lifecycle core
- `api_paso4.py` · paso4 lifecycle endpoints
- `exit_checklist_api.py` · exit checklist endpoints
- `public_api.py` · endpoints públicos post-baja
- `lifecycle_service.py` · `LifecycleService` + `ALL_STATES` + `VALID_TRANSITIONS` + `DEFAULT_RETENTION_YEARS`
- `exit_checklist_service.py` · exit checklist logic
- `backup_builder.py` · archive package SHA-256 + Ed25519
- `lifecycle_paso4.py` · paso4 specific logic
- `tasks.py` · Celery jobs (purge · archive cleanup)

⚠️ NO existe `service.py` único · core en `lifecycle_service.py`.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `ProjectLifecycleState` (`backend/app/models/lifecycle.py`)
- `ArchivedProject` (archived state)
- `ExitChecklistItem` (exit checklist tracking)

RLS por `project_lifecycle_states` + `archived_projects`.

## Cross-motor integration

- **Inbound**: M23 Retainer (lifecycle events trigger retainer state changes)
- **Outbound**:
  - M09 Audit Prep (audit prep state cross-feed)
  - M12 Magic Link (renewal links + public tokens)
  - M20 Workspace (workspace events posted)
  - M21 Portal Cliente (cliente VE lifecycle state)
  - M23 Retainer (retainer lifecycle coupling)
- **LLM agents**: ninguno (motor state machine determinístico)

## Limitaciones conocidas

### Purge irreversible post grace period

Purge state es **irreversible** post `purge_after <= hoy` + grace period expirado. Workflow obligatorio: ARCHIVED → grace → PURGED. NO undo post-purge (compliance RGPD art. 17 derecho al olvido + retention policy enforcement).

## ADRs referenced

- ADR-020 · in-portal review pattern
- ADR-046 · capability vs feature_flag

## Cement OPS

State machine con `VALID_TRANSITIONS` explícitas es invariante (no skip states). Archive package SHA-256 + Ed25519 es invariante integrity (audit trail ENAC post-baja). Public tokens permiten cliente acceder archive post-baja sin reactivar cuenta (compliance + cliente UX).
