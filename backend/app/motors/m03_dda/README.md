# Motor 3 · Declaración de Aplicabilidad (DdA)

Generación y gestión de la Declaración de Aplicabilidad (DdA) ENS según el Anexo II del RD 311/2022 (73 medidas de seguridad). Atómico: una DdA → 73 entries instantiated. Templates estáticos para justificaciones NO_APLICA · enriquecimiento LLM contextual diferido (M3-G1).

## Funcionalidades

- **Generación atómica de 73 entries** al crear DdA (1 por cada medida del Anexo II).
- **Estados por entry**: `aplica` / `no_aplica` con justificación obligatoria (templated) + `estado_implementacion` (no_implementada / parcial / implementada / verificada).
- **Read-only enrichment** con `magerit_ens_mapping` (salvaguardas MAGERIT M02 → medidas ENS Anexo II).
- **Freeze/unfreeze** vía `aprobado_por` + `fecha_aprobacion` en entries · auditoría inmutable.
- **Firma E.040** declaración formal vía in-portal signing (M05_signing).
- **Portal cliente view** (`portal_api.py`) · cliente visualiza DdA congelada y aplica firma.
- **Trazabilidad oficial**: RD 311/2022 Anexo II · CCN-STIC 803/804.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.782 |
| Files | 8 |
| Status | production-grade |
| Tests | `backend/tests/motors/m03_dda/` |
| API prefix | `/api/v1/dda/*` (admin) + portal-api cliente |
| RBAC | Cat A · Marcos-only admin · cliente vía portal-api |

## Key files

- `api.py` · endpoints admin DdA (CRUD + freeze + firma)
- `portal_api.py` · endpoints cliente portal (view DdA + firma E.040)
- `service.py` · `DdaService` (core lifecycle + freeze logic + exceptions)
- `templates.py` · `render_no_aplica_justification` (templated estáticos)
- `enums.py` · `Aplicabilidad` · `EstadoImplementacion` · `CategoriaSistema`
- `schemas.py` · Pydantic in/out (DdaCreateRequest · DdaEntryUpdateRequest · E040)
- `signature_integration.py` · wire-up firma E.040

## DB tables

N/A motor-specific · usa modelos ENS (`DdaEntry` · `EnsMeasure`) definidos en `backend/app/models/ens.py`. RLS por `dda_entries`.

## Cross-motor integration

- **Inbound**: M04 Gap Analysis (compara estado actual vs target DdA)
- **Outbound**: M12 magic-link · M21_portal_cliente
- **LLM agents**: ninguno actualmente (M3-G1 enrichment contextual diferido)

## Limitaciones conocidas

### Justificaciones NO_APLICA templated estáticas

Las justificaciones para entries con `aplicabilidad=no_aplica` se renderan vía templates estáticos en `templates.py`. NO hay enriquecimiento contextual LLM por cliente/sector específico.

**Cuándo se implementará** · M3-G1 backlog formal cuando aparezca demanda real de personalización profunda. Hasta entonces, templates cubren las justificaciones estándar ENS adecuadas para PYMEs categoria Básica/Media.

## ADRs referenced

- ADR-020 · tablas sessions separadas con cookie común + dual dispatcher (afecta firma cliente E.040)

## Cement OPS

Motor downstream de M01 Categorization · upstream de M04 Gap. Atomicidad de las 73 entries es invariante: si falla la creación de una, rollback completo de la DdA.
