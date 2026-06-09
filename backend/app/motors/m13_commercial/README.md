# Motor 13 · Commercial Doc Factory


## Funcionalidades

- **Pricing models** catálogo versionado (`pricing_service.py`) · pricing per categoría sistema + módulos extra + retainer.
- **Discount service** (`discount_service.py`) cálculo descuentos por volumen · campaign · pricing seasonal.
- **Proposal service** (`proposal_service.py`) generación propuestas desde lead + pricing + descuentos.
- **Estados propuesta** `VALID_ESTADOS` (draft · enviada · aceptada · rechazada · expirada).
- **Anti-alucinación económica**: importes SIEMPRE del `pricing_model` registrado · NUNCA LLM-generated.
- **Tasks Celery** (`tasks.py`) seguimiento async (recordatorios · expiraciones · análisis aceptación).
- **Services subdir** (`services/`) subdir auxiliar lógica negocio especializada.
- **Bridge M13→M15** propuesta aceptada genera contrato firmable + factura.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.376 |
| Files | 10 (+1 subdir `services/`) |
| Status | production-grade |
| Tests | `backend/tests/motors/m13_commercial/` |
| API prefix | `/api/v1/commercial/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP (propuestas CRUD + pricing catalog + discounts)
- `pricing_service.py` · `PricingService` + `PricingModelNotFoundError`
- `proposal_service.py` · `ProposalService` + `ProposalError` + `VALID_ESTADOS`
- `discount_service.py` · cálculo descuentos
- `tasks.py` · Celery jobs (recordatorios · expiraciones)
- `services/` · subdir lógica auxiliar

⚠️ NO existe `service.py` único · scope split en pricing/proposal/discount services.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `Lead` (`backend/app/models/commercial.py`)
- `PricingModel` + `Proposal` + `Discount` (commercial models)

RLS por `proposals` + `leads`.

## Cross-motor integration

- **Inbound** (motores que consumen M13): M15 Billing (factura emitida post-aceptación)
- **Outbound**:
  - M12 Magic Link (firma propuesta cliente)
  - M17 Planning (effort estimation pricing factor)
  - M21 Portal Cliente (cliente ve propuesta + acepta)
- **LLM agents**: A19 Propuestas + A20 Negociación (LLM contextual NO económico)

## Limitaciones conocidas

### Anti-alucinación económica estricta

Los importes en propuestas NUNCA pueden venir del LLM · siempre `pricing_model` real. LLM SOLO genera narrativa contextual (introducción · alcance · timeline descriptive), nunca números.

**Cement institutional**: feedback Marcos S10.5 "LLM solo donde valor comercial directo · determinismo donde trazabilidad ENAC es el valor".

## ADRs referenced

- ADR-013 · separación arquitectónica de portales
- ADR-041 · referenced en código

## Cement OPS

