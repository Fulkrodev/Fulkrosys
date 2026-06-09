# Motor 14 · Contracts Engine

Gestión del ciclo de vida de contratos FULKRO: plantillas C-001 a C-005 + sub-procesadores Providers · firma vía magic link (M12 `FIRMA_DOCUMENTO`) + hash SHA-256 inmutable + compromisos del cliente (modelo XYZPR). Source of truth contractual para todos los acuerdos cliente-FULKRO + proveedor-FULKRO.

## Funcionalidades

- **Plantillas C-001 a C-005** (`CONTRACT_TEMPLATES` constant + `legal_templates.py`):
  - C-001 · Contrato firma electrónica (referenced en M02 plantilla cláusula 14 — ADR-010 cement)
  - C-002 · Retainer mensual
  - C-003 · Onboarding inicial
  - C-004 · Adendum DPA cliente
  - C-005 · Confidencialidad mutua
- **Contract service** (`contract_service.py`) `ContractService` + `ContractError` core lifecycle (create · send · sign · revoke).
- **Hash SHA-256 inmutable** post-firma · garantiza non-repudiation contractual.
- **Compromisos cliente XYZPR** modelo embedded en contratos · trazabilidad obligaciones cliente.
- **Providers service** (`providers_service.py` + `providers_api.py`) sub-procesadores FULKRO (Hetzner · Postmark · Anthropic · 360dialog · MinIO · etc.) + DPAs.
- **Scan window** (`schemas.py` · `ScanWindow`) override de ventanas pentest configurables vía contrato.
- **Wire-up M12 firma** purpose `FIRMA_DOCUMENTO` vía magic link.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.110 |
| Files | 7 |
| Status | production-grade |
| Tests | `backend/tests/motors/m14_contracts/` |
| API prefix | `/api/v1/contracts/*` + providers sub-router |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP contratos CRUD + firma + send
- `contract_service.py` · `ContractService` core + `CONTRACT_TEMPLATES` + `ContractError`
- `legal_templates.py` · texto canónico C-001..C-005
- `providers_api.py` · endpoints sub-procesadores (Marcos admin)
- `providers_service.py` · `ProvidersService` (DPAs + sub-procesadores list)
- `schemas.py` · `ScanWindow` + Pydantic in/out

⚠️ NO existe `service.py` único · scope split en contract/providers services.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `Contract` (`backend/app/models/contracts.py`)
- `Provider` + `ProviderDPA` (providers compartidos)
- `ClientCommitment` (XYZPR embedded)

RLS por `contracts` + `client_commitments`.

## Cross-motor integration

- **Inbound**: M08 Verification (consume `scan_window` overrides contractuales para pentest scheduling)
- **Outbound**:
  - M12 Magic Link (firma vía `FIRMA_DOCUMENTO` purpose)
  - M30 Client Contacts (lista firmantes contractuales)
- **LLM agents**: ninguno directo (motor jurídico determinístico)

## Limitaciones conocidas

### Plantilla C-001 URL literal cement

La cláusula 14 C-001 (firma electrónica) cita literalmente la URL `/client-portal/firma`. Modificar esta URL = breaking change en contratos cliente ya firmados.

**Cement institutional**: ADR-051 `firma/firmas-hub distinct intent` · `firma/` página NO eliminable (preserva 5 puntos consistentes trazabilidad ADR-010).

## ADRs referenced

- ADR-046 · capability vs feature_flag clarification (referenced en código motor)

## Cement OPS

Source of truth contractual cement. Templates C-001..C-005 canónicos (modificación require ADR formal). XYZPR compromisos cliente trackeados forward audit ENS.
