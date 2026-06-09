# Motor 15 · Billing Engine

Facturación fiscal española completa: IVA 21% + IRPF + correlativo secuencial reglamentario + Verifactu hash chain + Facturae 3.2.x XML + XAdES signing + envío FACe AAPP (Administraciones Públicas) + intereses mora calc. Compliance directa con AEAT + FACe + RD 1619/2012 facturación.

## Funcionalidades

- **Facturación AAPP Facturae 3.2.x** (`facturae_generator.py`) generación XML conformant esquema oficial.
- **XAdES signer** (`xades_signer.py`) firma electrónica XAdES-BES advanced obligatoria FACe.
- **FACe submitter** (`face_submitter.py`) envío automático plataforma FACe (Administraciones Públicas).
- **Verifactu hash chain** correlativo secuencial inmutable · cumplimiento RD 2024 AEAT.
- **Invoices AAPP API** (`invoices_aapp_api.py`) endpoints facturación AAPP dedicados.
- **Financial extensions API** (`financial_extensions_api.py`) extensiones financieras (notas crédito · provisional · etc.).
- **Late interest calculator** (`late_interest_calculator.py`) cálculo intereses mora reglamentarios.
- **IVA + IRPF** defaults (`IVA_DEFAULT` 21% · `IRPF_DEFAULT`) configurable per cliente.
- **Billing service** (`billing_service.py`) `BillingService` + `BillingError` core lifecycle (create · emit · pay · cancel).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.978 |
| Files | 9 |
| Status | production-grade |
| Tests | `backend/tests/motors/m15_billing/` |
| API prefix | `/api/v1/billing/*` (+ AAPP sub-router) |
| RBAC | Marcos-only (no Cat marker · scope financiero owner) |

## Key files

- `api.py` · endpoints HTTP billing core
- `billing_service.py` · `BillingService` core + `IVA_DEFAULT` + `IRPF_DEFAULT`
- `facturae_generator.py` · Facturae 3.2.x XML generation
- `xades_signer.py` · XAdES-BES firma electrónica
- `face_submitter.py` · envío FACe plataforma AAPP
- `invoices_aapp_api.py` · endpoints AAPP dedicados
- `financial_extensions_api.py` · extensiones financieras (notas crédito · provisional)
- `late_interest_calculator.py` · intereses mora calc

⚠️ NO existe `service.py` único · core en `billing_service.py` + servicios especializados (Facturae · XAdES · FACe · late interest).

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `Invoice` (`backend/app/models/billing.py`)
- `InvoiceLine` (líneas factura)
- `VerifactuChain` (correlativo + hash chain)

RLS por `invoices`.

## Cross-motor integration

- **Inbound**: M23 Retainer (factura mensual retainer auto-emit)
- **Outbound**: M13 Commercial (pricing reference + propuesta aceptada → factura)
- **LLM agents**: ninguno (motor fiscal determinístico estricto)

## Limitaciones conocidas

### Compliance fiscal española estricta

Motor compliance directa AEAT + FACe + RD 1619/2012. Cambios requieren legal review + tax-compliance verification. Verifactu hash chain es invariante reglamentario (modificar = sanción).

### XAdES-BES level (NO -T / -A / -LT)

Firma XAdES-BES (Basic Electronic Signature) suficiente para FACe AAPP actual. Niveles superiores (XAdES-T timestamp · XAdES-A archival) NO implementados · forward si normativa o cliente lo requiere.

## ADRs referenced

- ADR-046 · capability vs feature_flag clarification (referenced en código motor)

## Cement OPS

Compliance fiscal española estricta. Verifactu chain es invariante reglamentario. Facturae 3.2.x esquema oficial NO modificable.
