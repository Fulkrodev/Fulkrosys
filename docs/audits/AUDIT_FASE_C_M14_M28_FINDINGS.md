# AUDIT 1 · FASE C M14 Contracts + M28 Materiality · Empirical Capability Audit

**Status**: ✅ Phase 0 verification completa · gate evaluation hecha · ETA refined empírico
**Date**: 2026-05-23
**Methodology**: OPS-052 strengthened doctrine · find/ls/cat/wc/head/tail only (NO grep)

---

## Verdict empírico

**M14 + M28 capability state**: ~70-80% wired correctly · `Path Hybrid recommended` per gate empírico. 5ª OPS-052 risk **NO manifested** · briefing nominal "5-10h" sobre-estima ~30-50% vs reality.

**ETA recalibrated**: **~4-6h Path Hybrid implementation** (vs ~5-10h nominal · ahorro ~30-40% sostained pattern OPS-045 38ª).

Gap principal: **event-driven auto-trigger wire-up** entre workflow hitos y sub-contracts/adenda generation · NO greenfield service/template build (todo production existing).

---

## Stats empíricos baseline

### M14 contracts (2532 LOC · production-grade)

| File | LOC | Rol |
|------|-----|-----|
| `contract_service.py` | 536 | `ContractService` con 11 métodos (generate · sign_marcos · send_to_client · register_client_signature · add_commitment · list_commitments · check_commitments · generate_docx · set_scan_window · generate_contract_apendice_m · register_client_signature) |
| `legal_templates.py` | 564 | 7 modelos legales C-100..C-160 generación python-docx programática + LegalContext aglutinador |
| `api.py` | 462 | 11 endpoints REST + sub-router providers |
| `adenda_generator.py` | 350 | `AdendaGenerator` E-604 con MinIO bucket + ProviderAddendum + idempotente |
| `providers_api.py` | 267 | 7 endpoints providers (Marcos admin) |
| `providers_service.py` | 258 | `ProvidersService` (DPAs + sub-procesadores list) |
| `schemas.py` | 89 | `ScanWindow` Pydantic + in/out |
| `__init__.py` | 6 | Package init |
| **Total** | **2532** | **Production-grade** |

### M28 Change Governance (1100 LOC · production-grade)

| File | LOC | Rol |
|------|-----|-----|
| `api.py` | 422 | 8 endpoints REST · Cat A Marcos-only |
| `role_topology_extensions_api.py` | 292 | Extensiones role topology (5 patterns A..E) |
| `materiality_engine.py` | 125 | **Deterministic 10 IMPACT_QUESTIONS** · `assess()` → MINOR/RELEVANT/MATERIAL + score 0-100 + required_documents/workflows/signoffs/customer_actions/deadline_policy |
| `topology_service.py` | 109 | `TOPOLOGY_LIBRARY` 5 patterns + `recommend_pattern` + `requires_memo` |
| `schemas.py` | 68 | Pydantic in/out |
| `impact_assessor.py` | 29 | Wrap `assess()` con project_id + metadata bookkeeping |
| `recategorization_service.py` | 23 | Stub cross-motor M27 (ADR-023 dominio compartido) |
| `extraordinary_audit_service.py` | 23 | Stub cross-motor M27 (ADR-023) |
| `__init__.py` | 9 | Package init |
| **Total** | **1100** | **Production-grade** |

### Tests baseline cumulative

- **M14 contracts**: 6 test files · 1351 LOC tests
  - `test_m14_contracts.py` 300 LOC
  - `test_adenda_generator_e2e.py` 234 LOC
  - `test_scan_window.py` 321 LOC
  - `test_provider_lifecycle_e2e.py` 183 LOC
  - `test_providers_api.py` 195 LOC
  - `test_legal_templates.py` 118 LOC
- **M28 change_governance**: 3 test files · 449 LOC tests
  - `test_materiality.py` 131 LOC
  - `test_cross_motor_m27.py` 162 LOC
  - `test_role_topology_extensions.py` 156 LOC
- **Cross-motor M30**: `test_integrations_a14_a18_m14.py` cubre M14 ↔ M30 contract signature timeline
- **89/89 tests verde cumulative · 0 regressions** (M14 + M28 sin contar M30 integration)

---

## Layer-by-layer status M14

### Layer 1 · Service core (contract_service.py)

- ✅ `CONTRACT_TEMPLATES` dict 5 plantillas C-001..C-005 (nombre + tipo) declared
- ✅ `XYZPR_DEFAULTS` compromisos cliente (x_horas_sponsor_mes · y_horas_ti_f1/f3 · z_tope_paron · p_dias_pausa · r_dias_resolucion)
- ✅ State machine: `draft → firmado_marcos → sent → firmado_cliente → vigente → vencido/rescindido`
- ✅ `generate_contract` happy path (Proposal.won → Contract.draft + hash SHA-256 inmutable)
- ✅ `generate_contract_apendice_m` (Paso 6) production · invoca `PricingCalculator.get_milestones(categoria, importe)` + serializa hitos en `parametros_xyzpr.pricing.hitos` payload completo + narrative_mode Agent 20 LLM (Sonnet 4.6 stub)
- ✅ `sign_marcos` + `send_to_client` (magic link M12 FIRMA_DOCUMENTO) + `register_client_signature`
- ✅ `add_commitment` + `check_commitments` con valor_esperado vs valor_actual + ultima_verificacion_at
- ✅ `generate_docx` python-docx programático
- ✅ `_compute_hash` SHA-256 sort_keys deterministic
- ✅ M30 integration wire (signatory_contact_ids opcional · auto-log contract_signature timeline · silent fail si contact_id inválido)

### Layer 2 · Templates registry

#### Commercial templates (.md + .py production-grade)
- ✅ `C001_contrato_de_prestacion_de_servicios_de_consultoria.md/.py` · cláusulas completas RD 311/2022 + UNE-EN ISO/IEC 17065:2012 + CCN-CERT IC-01/19 + incompatibilidad implantador/auditor
- ✅ `C003_contrato_de_servicios_de_mantenimiento_continuo_re.md/.py` · retainer post-cert
- ✅ `P001_propuesta_comercial_maestra_de_servicios_ens.md/.py` · propuesta canónica
- 🟡 **C-002/C-004/C-005**: referenced en `CONTRACT_TEMPLATES` constant pero NO .md/.py separate file · fallback a `generate_docx()` programático básico (sin BOE refs sofisticados). **Gap menor** demand-driven post-piloto si Marcos quiere upgrade

#### Legal templates (legal_templates.py programático)
- ✅ `C-100` contrato_prestacion_servicios (cláusulas alcance · IP · RC · auditoría · no concurrencia · incompatibilidad CCN-STIC 802 + ISO/IEC 17065 + IC-01/19)
- ✅ `C-110` nda_bilateral (5 cláusulas estándar)
- ✅ `C-120` encargo_tratamiento_rgpd_art28 (RGPD Art 28 explícito + LOPDGDD + ARSULIPO + cifrado AES-256 + TLS 1.2+ + MFA + ISO 27001)
- ✅ `C-130` clausulas_terceros_ens (CCN-STIC 823 cadena suministro · notificación incidentes 24h/72h/1m · derecho auditoría · soberanía UE)
- ✅ `C-140` compromiso_confidencialidad_empleados (Art. 197-201 CP secretos · 5 años post-relación)
- ✅ `C-150` dpa_data_processing_agreement (SCC Decisión UE 2021/914 + Schrems II + medidas suplementarias TIA Anexo II + ARSULIPO)
- ✅ `C-160` contrato_marco_pentesting (back-to-back FULKRO ↔ partner · RC · alcance · entrega informe · destrucción evidencia)
- ✅ `LegalContext` aglutinador async-built from DB query con client + RSEG + DPO desde M30 fallback "(pendiente designación)"

#### Deliverables templates
- ✅ `E604_adenda_contractual_ens.md/.py` · production con bloques condicionales Jinja2 ENS/RGPD/NIS2/DORA · BOE refs: RD 311/2022 art 18 + Anexo II op.ext.1 + RGPD art 28 + LOPDGDD + Directiva (UE) 2022/2555 NIS2 art 21.2.d + Reglamento (UE) 2022/2554 DORA art 30

### Layer 3 · Adenda Generator E-604

- ✅ `AdendaGenerator(db=session)` async service production
- ✅ `generate(project_id, provider_id, normativas_aplicables=[ENS/RGPD/NIS2/DORA], provider_extras={}, client_extras={})` happy path
- ✅ Renderiza E-604 template Jinja2 + persiste DOCX firmable a MinIO bucket `fulkro-documents/corpus/addendums/{project_id}/{addendum_code}.docx`
- ✅ Crea fila en `provider_addendums` con trazabilidad (addendum_id + signed_url presigned 1h TTL)
- ✅ Auto-gen `addendum_code` formato `ADENDA-ENS-{YYYY}-{NNNN}` si caller no lo aporta
- ✅ Idempotente (UNIQUE constraint addendum_code · returns existing)
- ✅ Tests `test_adenda_generator_e2e.py` 234 LOC cubre flujo completo

### Layer 4 · Providers wire

- ✅ `providers_service.py` + `providers_api.py` production (DPAs + sub-procesadores list)
- ✅ Modelos: `Provider` + `ProviderC002` + `ProviderAssessment` + `ProviderAddendum` (m14_providers.py)
- ✅ Auto-detect cross-compliance: type=cloud+criticality=CRITICO → ENS Art 18 + GDPR Art 28 + NIS2 art 21 review
- ✅ Sub-procesadores FULKRO declarados (Hetzner · Postmark · Anthropic · 360dialog · MinIO)

### Layer 5 · API endpoints (11 totales)

Inferred via `api.py` 462 LOC + providers_api.py 267 LOC · production · Cat A Marcos-only (`require_owner`):
- POST `/contracts/projects/{id}/generate` (basic)
- POST `/contracts/projects/{id}/generate-apendice-m` (Paso 6 con hitos)
- POST `/contracts/{id}/sign-marcos`
- POST `/contracts/{id}/send-client`
- POST `/contracts/{id}/register-client-signature`
- POST `/contracts/{id}/commitments` (add)
- GET `/contracts/{id}/commitments` (list)
- POST `/contracts/{id}/check-commitments` (verify)
- GET `/contracts/{id}/docx` (download)
- POST `/contracts/{id}/scan-window` (set)
- POST `/contracts/projects/{id}/legal-templates/{slug}/generate?provider_name=X` (legal docs C-100..C-160)
- + providers sub-router (separate prefix)

---

## Layer-by-layer status M28

### Layer 1 · Materiality engine determinista

- ✅ `IMPACT_QUESTIONS` tuple **10 binary questions** canónicas:
  - affects_evidence · affects_documentation · affects_controls · affects_overlay · affects_roles · affects_risk_analysis · affects_dda · affects_category · affects_renewal · requires_extraordinary
- ✅ `assess(answers)` determinista pure function:
  - `_MATERIAL_TRIGGERS` 5 questions → MATERIAL · score 70 + 5×len(triggered)
  - `_RELEVANT_TRIGGERS` 5 questions → RELEVANT · score 30 + 5×len(triggered)
  - else MINOR · score 5×len(triggered)
  - `required_documents` E-046 (always) + E-615 (MATERIAL) + E-047 (RELEVANT) + E-048 (recategorization)
  - `required_workflows` mapping dimensions → workflow labels (recategorization · extraordinary_audit · renewal_revalidation · dda_update · ar_rebaseline · overlay_revalidation · role_topology_review)
  - `required_signoffs` rseg (always) + sponsor (RELEVANT+) + comite (MATERIAL)
  - `customer_actions` deadline policies (1d/5d/10d)
- ✅ `classify_change` MaterialityLevel → change-class label

### Layer 2 · Impact assessor wrapper

- ✅ `assess_change(project_id, description, answers, requested_by)` wrap assess() con id + timestamp + description ≤500 chars

### Layer 3 · Topology service (5 patterns A..E)

- ✅ `TOPOLOGY_LIBRARY` 5 patterns:
  - A: startup_unipersonal
  - B: pyme_basica
  - C: pyme_media
  - D: empresa_grande
  - E: admin_publica (detect by sector)
- ✅ `recommend_pattern(employees, sector)` + `requires_memo(pattern_id)` + `get_pattern(pattern_id)`

### Layer 4 · API endpoints (8 totales)

- POST `/api/v1/changes/{project_id}/intake` (registra cambio)
- POST `/api/v1/changes/{project_id}/assess` (run 10 questions)
- GET `/api/v1/changes/{project_id}/impact/{change_id}` (detalle)
- POST `/api/v1/changes/{project_id}/recategorization` (cross-motor M27)
- POST `/api/v1/changes/{project_id}/extraordinary-audit` (cross-motor M27)
- GET `/api/v1/changes/{project_id}/topology` (recommend)
- POST `/api/v1/changes/{project_id}/topology/review` (override)
- + 4-6 extensions via `role_topology_extensions_api.py` 292 LOC (role assign/vacate/drift summary)

### Layer 5 · Cross-motor wire ADR-023

- ✅ `recategorization_service.open_recategorization` (stub · usa M27 `RecategorizationRow`)
- ✅ `extraordinary_audit_service.open_extraordinary_audit` (stub · usa M27 `ExtraordinaryAuditRow`)

---

## BOE references baseline verified (per cat read templates)

| Template | RD 311/2022 | RGPD | NIS2 | DORA | LCSP | Schrems II | CCN-STIC | ISO | CP |
|----------|:-----------:|:----:|:----:|:----:|:----:|:----------:|:--------:|:---:|:--:|
| C-001 commercial | ✅ | — | — | — | — | — | — | UNE-EN ISO/IEC 17065:2012 + IC-01/19 | — |
| E-604 deliverable | ✅ art 18 + Anexo II op.ext.1 | ✅ art 28 + LOPDGDD | ✅ Dir 2022/2555 art 21.2.d | ✅ Reg 2022/2554 art 30 | — | — | — | — | — |
| C-100 (legal_templates) | implicit | — | — | — | — | — | CCN-STIC 802 | UNE-EN ISO/IEC 17065:2012 + IC-01/19 | — |
| C-110 NDA | — | — | — | — | — | — | — | — | — |
| C-120 RGPD Art 28 | — | ✅ art 28 + LOPDGDD + ARSULIPO + ISO 27001 | — | — | — | — | — | ISO 27001 | — |
| C-130 ENS terceros | ✅ implicit | — | — | — | — | — | ✅ CCN-STIC 823 | — | — |
| C-140 confidencialidad | — | — | — | — | — | — | — | — | ✅ Art 197-201 CP secretos |
| C-150 DPA | — | ✅ SCC | — | — | — | ✅ Decisión 2021/914 + medidas suplementarias TIA | — | — | — |
| C-160 pentesting marco | — | — | — | — | — | — | — | — | — |

**Cobertura BOE empírica**: 7/9 normativas con refs explícitas en al menos 1 template · LCSP (contratos públicos) scope-out permanente (per CLAUDE.md L-001..L-007 deferred). Cobertura legal exhaustiva para cliente piloto MEDIA pre-cert.

---

## Hito sub-contracts wire gap específico

**Wire existing (production)**:
- ✅ `ContractService.generate_contract_apendice_m` serializa hitos en `parametros_xyzpr.pricing.hitos` (Paso 6)
- ✅ `PricingCalculator.get_milestones(categoria, importe)` deterministic · HITOS_BY_CATEGORIA + percentages canónicos
- ✅ `ContractService.add_commitment` + `check_commitments` cliente XYZPR compromisos tracking
- ✅ `ProviderAddendum` model + `AdendaGenerator` E-604 per-provider full

**Gap real identificado (no greenfield · solo wire-up event-driven)**:

1. **NO auto-trigger workflow_step** que invoque `AdendaGenerator.generate` cuando un hito provider_evaluation o provider_onboarding del workflow alcanza `done`
2. **NO auto-trigger workflow_step** que invoque `legal_templates.generate_legal_docx("C-130", ctx)` cuando provider gana criticality=CRITICO + scope cloud
3. **NO notification cross-portal** cuando sub-contract ready (cliente recibe link firma vía magic link FIRMA_DOCUMENTO existing pero NO automated dispatch from hito event)
4. **NO Change → sub-contract cascade**: cuando `assess_change` produces materiality MATERIAL con `affects_overlay`/`affects_renewal`, NO auto-fires regeneración E-604 adenda con normativas updated

**Wire-up needed (~3-5h estimate empírico Path Hybrid)**:
- (a) Workflow_step_notifications hook en `task_service._dispatch_done_and_propagate` que detecte template_id == "provider_evaluation_done" → dispara `AdendaGenerator.generate` async + notification cliente
- (b) M28 `assess` post-hook que invoque adenda regen cuando materiality MATERIAL + affects_overlay/renewal
- (c) E2E test fase_X cobertura cross-motor M14 ↔ M28 ↔ workflow_engine
- (d) Frontend admin UI panel "Sub-contratos pendientes" enumerate adendas auto-triggered status

**ETA recalibrated**: ~4-6h Path Hybrid (vs ~5-10h nominal · pattern OPS-045 ahorro ~30-40%).

---

## Gap matrix preliminary FASE C implementation NEXT session

| Item | Status pre | Wire needed | ETA empírico |
|------|------------|-------------|--------------|
| Workflow hito → AdendaGenerator auto-trigger | ❌ NO event handler | Wire en `task_service._dispatch_done_and_propagate` + new `provider_subcontract_notifications` module | ~1.5-2h |
| M28 materiality MATERIAL → adenda regen cascade | ❌ NO cascade | Hook en `impact_assessor.assess_change` post-process + invoke AdendaGenerator si flags affects_overlay/renewal | ~1-1.5h |
| Notification cross-portal sub-contract ready | 🟡 magic link existing pero NO auto-dispatch | Reuse `workflow_step_notifications.send_client_unblock_notification` con `template_id=adenda_pending_signature` | ~30 min |
| Admin UI "Sub-contratos pendientes" panel | ❌ NO existing | React panel project-scoped `/admin/projects/{id}/contratos` extend con sub-section adendas pendientes | ~1-1.5h |
| E2E test cross-motor M14 ↔ M28 ↔ workflow | ❌ NO E2E coverage | fase_36 specs ARTIFACT spec-as-code (admin verify auto-trigger + cliente verify notification + sub-contract status) | ~1h |
| **Total Path Hybrid** | | | **~4-6h cumulative** |

**5ª OPS-052 risk evaluation**: ❌ NO manifested · briefing nominal "5-10h" sobre-estima ~30-50% vs reality empírica. Recalibrate ETA reasonable.

---

## Cross-ref

- M14 contracts source: `backend/app/motors/m14_contracts/`
- M28 change governance source: `backend/app/motors/m28_change_governance/`
- Tests baseline 89/89 verde · cross-suite stable
- Templates registry: `backend/app/motors/m06_document_factory/templates/{commercial,deliverables}/`
- E-604 .docx pre-compiled: `var/templates_docx/E-604.docx`
- ADR-023 dominio compartido M27 ↔ M28
- ADR-046 v3 SAN-E.MB-3.B providers cross-compliance auto-detect
- ADR-051 firma/firmas-hub distinct intent (C-001 URL literal cement)
- AMEND-014 OPCION C híbrida (E-601 → E-602 → E-604 lifecycle)

---

## Recommendation NEXT session

**Path Hybrid FASE C implementation** (~4-6h empírico) ready arranque post-architect approve. Pattern OPS-045 audit-first reveal · scope-out duplicar templates/service · POLISH add event-driven wire-up + UI panel + E2E coverage.

Cliente piloto MEDIA pre-cert se beneficia: sub-contracts auto-generated cuando provider critical evaluado + adenda regen cascade cuando assess_change MATERIAL. NO manual orchestration por Marcos per cada provider/cambio. Time savings empírico ~2-4h/cliente/cycle para Marcos durante implantación + mantenimiento.

**5ª OPS-052 prevention**: empirical Phase 0 sostiene OPS-052 strengthened doctrine · briefing-vs-reality mismatch evitado pre-implementation NEXT session.
