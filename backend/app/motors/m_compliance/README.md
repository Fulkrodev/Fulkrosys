# Motor `m_compliance` · GDPR Compliance Features

Agrupa endpoints de funcionalidad GDPR/compliance expuestos a clientes y admin: RoPA (Art. 30 GDPR) + DPA (Art. 28 GDPR) + breach notification + cookies management + RGPD art. 15/17/20 derechos cliente. **Distinto de `m_compliance_monitor`** (este motor expone features cliente · `m_compliance_monitor` audita la propia compliance de FULKRO).

## Funcionalidades

- **RoPA Art. 30 GDPR** (`ropa_api.py` + `ropa_service.py`) Record of Processing Activities · per cliente · Excel export.
- **DPA Art. 28 GDPR** (`dpa_api.py` + `dpa_template.py`) Data Processing Agreement template generation + cliente sign workflow.
- **RGPD endpoints cliente** (`rgpd_api.py` + `rgpd_services.py`) art. 15 (acceso) · art. 17 (olvido) · art. 20 (portabilidad).
- **Breach service** (`breach_service.py`) notification breach datos personales workflow (art. 33 + 34 RGPD · 72h window).
- **Cookies management** (`cookies_api.py`) consent banner management + cookies inventory + renewal cadence.
- **Compliance admin API** (`compliance_admin_api.py`) endpoints admin para gestión cross-feature.
- **Email design subdir** (`email_design/`) templates email para breach notifications + DPA + cliente comms.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.034 |
| Files | 14 (+1 subdir `email_design/`) |
| Status | production-grade · GDPR features cliente + admin |
| Tests | `backend/tests/motors/m_compliance/` |
| API prefix | múltiples sub-routers · `/api/v1/ropa/*` · `/api/v1/dpa/*` · `/api/v1/rgpd/*` · `/api/v1/cookies/*` · `/api/v1/compliance/*` |
| RBAC | Mixed · cliente vía portal endpoints + admin vía `compliance_admin_api` |

## Key files

- `compliance_admin_api.py` · endpoints admin cross-feature
- `ropa_api.py` + `ropa_service.py` · RoPA Art. 30 GDPR
- `dpa_api.py` + `dpa_template.py` · DPA Art. 28 GDPR
- `rgpd_api.py` + `rgpd_services.py` · derechos cliente art. 15/17/20
- `breach_service.py` · breach notification art. 33/34
- `cookies_api.py` · cookies management
- `email_design/` · subdir email templates

⚠️ NO existe `api.py` único · scope split por feature (ropa · dpa · rgpd · cookies · breach · compliance_admin). NO existe `service.py` único · scope split per feature service.

## DB tables

N/A motor-specific declarado · usa modelos compartidos:
- `RopaActivity` (`backend/app/models/compliance.py`)
- `DpaAgreement` + `DpaSignature`
- `RgpdRequest` (acceso/olvido/portabilidad)
- `BreachNotification` (breach tracking)
- `CookieConsent` + `CookieInventory`

RLS por compliance tables.

## Cross-motor integration

- **Inbound**: `email_design` (cross-feature email assembly) · `normas` (compliance_monitor consume m_compliance features)
- **Outbound**: ninguno directo (motor self-contained · features endpoints)
- **LLM agents**: ninguno (motor jurídico determinístico)

## Limitaciones conocidas

### Breach notification 72h window automation manual gating

El cálculo de la ventana 72h art. 33 RGPD es automático, pero el envío real a AEPD es **manual gating Marcos** (revisión jurídica obligatoria pre-submit · mismo cement que M19 CCN-CERT decision tree).

## ADRs referenced

(no ADRs referenciados directamente en código · cement vía patrones canónicos)

## Cement OPS

Motor jurídico determinístico estricto. Distinto de `m_compliance_monitor` (este expone features · aquél audita propia compliance). Email design subdir cross-feature reuse (DPA + breach + RGPD requests comparten templates).
