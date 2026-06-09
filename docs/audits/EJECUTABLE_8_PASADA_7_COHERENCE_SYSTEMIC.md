# Ejecutable 8 · Pasada 7 · Coherencia Sistémica + Interconexión

> Verificación empírica file-by-file (no discovery ciego). Cada hallazgo clave citado con `path:línea`.
> Ground-truth heredado Pasadas 1-5 reutilizado sin re-conteo.

---

## 1. WORKFLOWS TRAZADOS (frontend page -> lib/api -> backend endpoint -> motor)

### 1.1 Cliente · signup -> MFA (TOTP) -> dashboard -> docs -> firma -> audit

| Paso | Frontend page | lib/api | Backend endpoint | Motor |
|------|---------------|---------|------------------|-------|
| MFA TOTP | `client-portal/settings` | `client-mfa.ts` (status/initiate/confirm/disable) | `/client-portal/settings/mfa/*` | `m21_portal_cliente/mfa_api.py:27-121` + `mfa_service.py` |
| Dashboard | `client-portal/dashboard` | `dashboard.ts` (`GET /dashboard/adaptive`) | `m21_portal_cliente/api.py:1424` `portal_dashboard_adaptive` | M21 |
| Firma canvas | `client-portal/firmas-pendientes/page.tsx` | `signing.ts:133` `signIntentCanvas` | `POST /portal/signing/intents/{id}/sign-canvas` (`m05_signing/api.py:539`) | `m05_signing/service.py:397` `sign_canvas` |
| Audit/certificación | `client-portal/certificacion` + `client-portal/conformidad` | — | `m_audit_accompaniment/api.py` (cliente read-only) | m_audit_accompaniment |

**Verificado**: cadena de firma completa traza los 4 niveles (page existe `firmas-pendientes/page.tsx` · `signing.ts:133` -> `/sign-canvas` -> `api.py:539` -> `service.sign_canvas`). MFA: 4 endpoints reales (`mfa_api.py:58/67/85/120`). Dashboard endpoint real (`api.py:1424`).

`client-portal/` expone 36 sub-rutas (dashboard, dda, magerit, evidencias, firma, firmas-pendientes, firmas-hub, certificacion, conformidad, plan, tasks, chat, pentest-authorization, cloud-connections, ...) — workflow cliente completo cronológico cubierto.

### 1.2 Admin · login (owner) -> selector -> proyecto -> clusters -> cierre

- Selector landing: `frontend/app/(admin)/admin/projects/page.tsx` EXISTE (gate único re-entry, arquitectura Opción 2 COEXIST).
- Project-scoped: rutas `/admin/projects/[id]/*` montadas; middleware.ts gating JWT Ed25519 para `(admin)`.
- Cierre: `m31_cierre_implantacion` + `m25_lifecycle` + gate `require_complete_audit_prep` (definido, ver GAP #1).

### 1.3 Auditor · magic-link AUDITOR_PORTAL_ENAC -> portal -> evidence/dda/draft-report

- Purpose: `MagicLinkPurpose.AUDITOR_PORTAL_ENAC = "auditor_portal_enac"` (`m12_magic_link/purposes.py:79`, policy `policy_enforcer.py:80-87`).
- Portal: `frontend/app/(portal)/auditor-portal/` (NO middleware; token-gated por magic-link).
- Backend: `m09_audit_prep/public_api.py` (auditor portal router montado main.py:204), `auditor_annotations_api.py`, `auditor_clarifications_api.py`, `dda_evidence_gap_api.py`, `draft_report_api.py` — todos montados (main.py:203-217).

---

## 2. PIPELINES + HANDOFFS VERIFICADOS

### 2.1 ENS Radar (m10_ens_radar)

`run_full_pipeline` (`pipeline.py:1344`) compone secuencialmente:
```
step_1_ingest (scrape PLACSP/CCAA)  ->  step_2_refresh_ccn
  ->  step_3_analyze_ens (scoring/análisis pliegos IT)
  ->  step_3b_scrape_participations  ->  step_4_enrich_and_ccn  ->  step_4b_dedup
  ->  step_5_score_and_dossier (leads)  ->  step_6 renewals
```
Outreach handoff: `outreach/` con `draft_generator.py` + `proposal_service.py` + `proposal_pdf.py:75+` + `proposal_gates.py` (gates de propuesta) + `proposal_context.py`. Pipeline scrape->scoring->leads->outreach **completo y secuencial**.

### 2.2 Ciclo ENS audit (M01..M10) · HANDOFFS REALES verificados

Handoffs implementados vía **workflow_gates** (raw SQL cross-motor, sin imports circulares):

| # | Handoff | Mecanismo | Evidencia | Estado |
|---|---------|-----------|-----------|--------|
| H1 | M01 categorización firmada -> M03 DdA | `require_signed_categorization` | `m03_dda/service.py:93-94` (invoca) | WIRED |
| H2 | M03 DdA congelada -> M06 docs (política/proc/entregable) | `require_frozen_dda_if_needed` | `m06_document_factory/service.py:262-264` (invoca) | WIRED |
| H3 | M02 MAGERIT -> M05 obligations | `require_magerit_analysis` | `workflow_gates.py:198` (definido) | SIN call site |
| H4 | M07 evidencia -> M09 audit_prep | `require_some_evidence` | `workflow_gates.py:166` (definido) | SIN call site |
| H5 | M09 dossier completo -> cierre proyecto | `require_complete_audit_prep` | `workflow_gates.py:133` + `m09 dossier_generator.py:491` (variante checklist propia, NO el gate de workflow_gates) | PARCIAL |
| H6 | Autorización cliente -> M08 pentest | `require_pentest_authorisation` | `workflow_gates.py:230` (definido) | SIN call site |

**Verificado empíricamente** (`grep -rn 'require_X' backend/app | grep -v 'def require'`):
- `require_signed_categorization`: invocado en `m03_dda/service.py:94`.
- `require_frozen_dda_if_needed`: invocado en `m06_document_factory/service.py:264`.
- `require_magerit_analysis`: **0 call sites** fuera de su definición.
- `require_some_evidence`: **0 call sites** (solo aparece en su propia definición `workflow_gates.py:183`).
- `require_pentest_authorisation`: **0 call sites**.
- `require_complete_audit_prep` (workflow_gates): **0 call sites**; M09 usa una función homónima distinta en `checklist_service.py:639` (lista bloqueantes, no gate raise).

=> **4 de 6 handoffs de gate NO están conectados** (gates huérfanos). Ver GAP #1.

### 2.3 Accompaniment (m_audit_accompaniment) state machine + signing (m05)

- State machine `m_audit_accompaniment/state_machine.py`: rama BÁSICO 6 estados (not_started -> declaration_drafted -> signed -> published -> periodic_review_scheduled -> completed) + rama MEDIO/ALTO 11 estados (not_started -> preparation -> ... -> enac_audit_passed -> certificate_issued -> biannual_renewal_scheduled, con bifurcación findings_resolution). `BASICO_TRANSITIONS` / `MEDIO_ALTO_TRANSITIONS` dicts + `resolve_category_branch` (:97) + `is_terminal_state` (:131).
- Handoff a firma: `m_audit_accompaniment/service.py` importa `sse_dispatcher` (Pattern #14) y el estado `declaration_signed` se conecta conceptualmente con m05_signing; advisory lock `accompaniment_<pid>` (service.py:210,318).

---

## 3. TRANSICIÓN DE FASES ENS · MECANISMO + GAPS

### Mecanismo (robusto, multi-capa)

1. **Enum canonical** `WorkflowPhase` 10 fases (`core/workflow_phase.py`): pre_venta, onboarding, diagnostico, analisis_riesgos, adecuacion, implantacion, dda_final, verificacion, conformidad, retainer_cierre. Helpers `.next()` / `.previous()` / `.ordered()`.
2. **Source of truth**: `projects.fase` VARCHAR(50) NOT NULL CHECK (migración `workflow_phase_10_canonical`).
3. **Derivación robusta** `get_current_phase` (`workflow_state/phase.py:23`): prioridad `projects.fase`, fallback `_derive_phase_cascade` con 7 EXISTS subqueries sobre motors, filtradas post-último `phase_changed` (ISSUE-W3).
4. **Avance**: `UPDATE projects SET fase` (ej. `billing/auto_billing.py:250`) -> trigger DB `tg_projects_phase_changed` emite `project_lifecycle_events(event_type='phase_changed')`.
5. **Reacción**: `m19_risk/triggers.py:77` `process_phase_changed_event` mapea `phase_changed:to:{fase}` -> magic links (MILESTONE_TO_MAGIC_LINK_MAPPING) + SSE `phase_changed` (`sse_api.py`, admin-only; cliente NO recibe `phase_changed` per `sse_client_api.py:68`).
6. **Gates de ordenación**: `workflow_gates.py` impiden artefactos fuera de orden (ver seccion 2.2).

=> El sistema **sabe en qué fase está** (projects.fase + cascade) **y qué sigue** (.next() + gates + m19 mapping).

### Gaps de transición

- **GAP-T1 (FASE 0 gobierno débil — confirmado Pasada 2)**: no existe motor de gobierno dedicado (RSI / comité de seguridad / política marco). Cubierto parcialmente por `m16_onboarding` (`addendum_v22.py`, `lms_docx.py`) pero **sin fase ni gate formal**. El enum no tiene fase "gobierno"; FASE 0 colapsa en `pre_venta`/`onboarding`. No hay gate que exija nombramiento RSI antes de M01 categorización.
- **GAP-T2 (avance NO atómico con gates)**: `projects.fase` se actualiza por UPDATE simple (auto_billing) "NO transition_to_phase" (comentario explícito `auto_billing.py:27`). No hay servicio único `transition_to_phase` que valide gate + actualice fase + emita evento en una transacción; el avance task-level (`m_workflow_engine/service.py:30` `advance_step` sobre ClientTask) y el avance de fase (`projects.fase`) son mecanismos **paralelos no acoplados**.
- **GAP-T3 (drift enum frontend-backend)**: ver GAP #2 abajo.

---

## 4. audit_log 3-way OR (Sub-atom 5.A) · MUESTRA >=8 emisiones

Helper canonical + sitios con `project_id` + `client_id` propagados (`INSERT INTO audit_log (... project_id, client_id, payload_new ...)`):

1. `m_cloud_connectors/api_cliente.py:99` `_emit_audit_log` (pid + cid) — invocado :205,:265,:362.
2. `m_cloud_connectors/digest_service.py:80` `_emit_audit_log` (`AuditLog(...)` ORM) — :104,:166.
3. `m_audit_accompaniment/service.py:108` `_emit_accompaniment_audit_log` (pid + cid nullable) — :228,:264,:278,:343.
4. `m17_planning/portal_api.py:102` `_emit_audit_log` `cliente.plan.viewed` (pid + cid).
5. `m09_audit_prep/public_api.py:170` `emit_auditor_event` (resuelve `client_id` desde projects; INSERT con pid + cid) — :1060,:1118,:1225.
6. `m_compliance/measure_translation_api.py:91` `INSERT INTO audit_log`.
7. `notifications/dlq_service.py:198` + `:242` `INSERT INTO audit_log`.
8. `m07_evidence/request_api.py` (cruza project_id+client_id+audit_log).
9. `m21_portal_cliente/audit_log_service.py:35` `log_action` (deriva `client_id` desde Project si None — hash chain SHA-256, ClientUserAudit).

Patrón consistente: `payload_new` JSON, `usuario` truncado [:255], `client_id` derivado de `projects` cuando ausente. R6 hash chain inviolable preservado (NULL+NULL no rompe cadena).

---

## 5. NAMING CONVENTIONS + PATTERN ADHERENCE

### Naming (muestra)
- Backend snake_case: `workflow_gates.py`, `require_signed_categorization`, `_emit_audit_log`, `process_phase_changed_event`. OK
- Frontend kebab (rutas/lib) + PascalCase (componentes): `client-mfa.ts`, `simulacro-pre-enac.ts`, `firmas-pendientes/`; componentes `FulkroFooter.tsx`, `ActiveProjectSync.tsx`, `SignatureCanvas.tsx`, `ClientSidebar.tsx`. OK Adherencia consistente.

### Patterns confirmados (existencia verificada)
| Pattern | Evidencia | Estado |
|---------|-----------|--------|
| #14 SSE + ClientNotification dual emit | `m_audit_accompaniment/service.py` (`_emit_sse_state_advanced` + audit_log), `m05_signing/api.py` (sse_dispatcher) | OK |
| #18 state machine | `m_audit_accompaniment/state_machine.py`: `BASICO_TRANSITIONS`/`MEDIO_ALTO_TRANSITIONS` dicts + `resolve_category_branch`:97 + `is_terminal_state`:131 | OK |
| #21 event_id replay | `core/sse_dispatcher.py:46` `event_id` UUID + :57 `deque(maxlen=100)` + :19 `subscribe(channel,last_event_id=)` + Last-Event-ID header | OK |
| #22 advisory lock | `m05_signing/service.py:434`, `m09 corrective_loop_service.py:234`, `m_audit_accompaniment/service.py:210,318` `pg_advisory_xact_lock(hashtext(...))` | OK |
| #24 PDF embed | `m05_signing/pdf_signature_embed.py:52` `append_signature_page` + `:118` `ImageReader`/`drawImage` | OK |

---

## 6. INTERCONEXIÓN FRONTEND-BACKEND (TS vs Pydantic)

| Feature | TypeScript (lib/api) | Pydantic (backend) | Correspondencia |
|---------|----------------------|--------------------|-----------------|
| Firma intent | `signing.ts:40` `SigningIntent` / `:52` `CreateSigningIntentRequest` | `m05_signing/schemas.py:11` `CreateSigningIntentRequest` / `:22` `SigningIntentResponse` | OK campos signable_type/status/document_hash_sha256 alineados |
| Firma canvas | `signing.ts:133` `signIntentCanvas` (dataurl + name) | `schemas.py:73` `SignCanvasRequest` (`signature_canvas_dataurl` + `signed_name` + `signed_surname`) | OK |
| Simulacro pre-ENAC | `simulacro-pre-enac.ts:13/19` `SimulacroLoopMetadata`/`SimulacroReport` | `m09_audit_prep/simulacro_pre_enac` SimulacroReport JSON-serializable | OK |
| Dashboard adaptativo | `dashboard.ts:21` `DashboardContext` / `:64` `AdaptiveDashboardResponse` | `m21_portal_cliente/api.py:1424` `portal_dashboard_adaptive` | endpoint existe; enum WorkflowPhase difiere (ver GAP #2) |

---

## 7. HALLAZGOS TAGGED (gaps de interconexión/transición) -> Pasada 16

- **P7-F1 (HIGH)**: 4/6 workflow_gates definidos pero SIN call site (require_magerit_analysis, require_some_evidence, require_pentest_authorisation, require_complete_audit_prep-de-workflow_gates). Handoffs H3/H4/H6 del ciclo ENS NO enforced; gate de pentest (ADR-014/ADR-020 step-up) no se aplica desde workflow_gates.
- **P7-F2 (MEDIUM)**: drift enum WorkflowPhase frontend (`dashboard.ts`: magerit/dda/auditoria/retainer_activo) vs backend canonical 10 fases (`workflow_phase.py`: analisis_riesgos/adecuacion/dda_final/pre_venta). Riesgo de mismatch en `current_phase` renderizado cliente.
- **P7-F3 (MEDIUM)**: avance de fase no atómico — `projects.fase` UPDATE directo (auto_billing) desacoplado de gates y de `advance_step` (ClientTask). No hay `transition_to_phase` único transaccional.
- **P7-F4 (LOW/INFO)**: FASE 0 gobierno sin fase ni motor dedicado (confirmación Pasada 2); cubierto parcialmente por m16_onboarding sin gate RSI->M01.

## Conclusión

El sistema está **interconectado y trazable** en sus tres workflows (cliente/admin/auditor) y dos pipelines (ENS Radar end-to-end; ciclo audit M01..M10 con 2 handoffs reales enforced). El mecanismo de transición de fases es robusto (enum 10 fases + cascade + trigger DB + m19 reactions + SSE). Los patrones arquitectónicos #14/#18/#21/#22/#24 y el patrón audit_log 3-way OR están presentes y consistentes. Los gaps son acotados: gates huérfanos (P7-F1, mayor), drift de enum FE/BE (P7-F2), avance de fase no atómico (P7-F3) y FASE 0 gobierno débil (P7-F4). Ninguno rompe la operación pre-piloto pero P7-F1 y P7-F2 merecen corrección en Pasada 16.