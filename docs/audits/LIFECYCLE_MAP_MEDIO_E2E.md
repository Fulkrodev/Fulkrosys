# LIFECYCLE MAP — Simulación E2E full-cloth ENS MEDIO

> Mapa maestro único para una simulación Playwright end-to-end de un encargo ENS **MEDIO**:
> admin contacta empresa ficticia → diagnostica → implanta ENS completo → auditor ENAC certifica → fase retainer.
> Una captura (`page.screenshot`) por fase en `out/sim_medio_e2e/NN_<phase>.png`.
>
> Síntesis de 9 mapas de área (dev-toolkit, comercial, implantación cronológica, portal cliente, portal auditor,
> state machine M25, entregables E-code, inventario specs, recipe runtime).
> **Verificado empíricamente** contra `backend/app/dev/router.py`, `backend/app/motors/m25_lifecycle/api_paso4.py`,
> `frontend/playwright.config.ts`, `frontend/tests/e2e/` y `frontend/app/(client-portal)/...` el 2026-06-12.
>
> Notación: rutas siempre absolutas. Selectores reales (no inventados). Donde no hay `data-testid` se indica el
> selector role/text realmente usado por los specs probados, y se marca en "gaps" si falta.

---

## 1. Fases ordenadas (first contact → retainer)

Numeración end-to-end. **Actor**: `admin` (Marcos), `cliente` (ClientUser), `auditor` (magic-link ENAC), `system` (cascada/seed backend).

| Nº | Fase | Actor | Ruta UI | Acción + selector que avanza | Lever seed/dev | Output / entregable | Gap conocido |
|----|------|-------|---------|------------------------------|----------------|---------------------|--------------|
| **0** | Bootstrap entorno | system | (dev API) | `GET /seed-info` → resuelve `marcos_user_id`; `POST /create-test-client`; `POST /set-test-project-category?tier=MEDIA` | `/api/v1/_dev/*` (gate `not is_production`) | Cliente `Test E2E Client` (cif `B00000000`), `ClientUser` (`test-client-e2e@example.com` / `TestP@ssw0rd123!`), Project `MEDIA` `lifecycle_state=ACTIVE` | Email lookup de Marcos hardcoded; falla si no seedeado |
| **1** | Login admin | admin | `/login` → `/admin/projects` | `loginAsMarcos(context)` → `POST /login-as-marcos` (cookies `fulkro_session` + `fulkro_csrf`) | `/api/v1/_dev/login-as-marcos` (bypassa MFA) | Sesión real `auth_sessions` indistinguible de login real | — |
| **2** | Intake lead CRM | admin | `/admin/pipeline` + `/admin/pipeline/leads/[id]` | Kanban `PipelineKanban` (8 cols) · drag → `PATCH /api/v1/commercial/leads/{lead_id}/stage` | Lead seedeado / Celery `m13_b` | Lead con `stage`, `categoria_objetivo_ens` | **No hay botón "Crear Lead" en UI** — backend-driven |
| **3** | Generar propuesta | admin | Lead detail · tab Proposals | `POST /api/v1/commercial/projects/{project_id}/proposals/generate` (sin botón UI) · enviar: `POST .../proposals/{id}/send` | m13 `PricingService` · Agente 19 LLM si `use_llm=true` | Propuesta `importe_total`, magic-link token | **No hay wizard de generación en UI**; LLM no visualizado |
| **4** | Generar contrato | admin | `/admin/projects/[id]/contratos` | `data-testid='contracts-generate-button'` → `ContractGenerateWizard` (3 pasos) → `POST /api/v1/contracts/projects/{project_id}/contracts/generate` | Propuesta "won" + `client-prefill` | Contrato `estado=draft`, `documento_sha256` congelado | Estructura modal poco clara; versionado UI ausente |
| **5** | Admin firma contrato | admin | Contract detail modal en `/admin/projects/[id]/contratos` | Botón "Firmar como Marcos" → `POST /api/v1/contracts/projects/{project_id}/contracts/{contract_id}/sign-marcos` | JWT Marcos (sin OTP) · intent m05 | `estado=firmado_marcos` | Botón no localizado explícitamente en lecturas |
| **6** | Enviar contrato al cliente | admin | Contract detail | Botón "Enviar al cliente" → `POST .../contracts/{contract_id}/send-client` | `recipient_email` variable; OTP en respuesta (dev) | Magic link `{token, otp, tipo_operacion='firma_contrato'}`, `estado=sent` | Template/reenvío email no cableado en UI |
| **7** | Cliente firma contrato (canvas público) | cliente | `/sign/[token]` → `ContractCanvasSignFlow` | OTP `Input /Código OTP/` · `data-testid='contract-signature-name-input'` + `-surname-input` · canvas `data-testid='contract-signature-pad'` · submit `data-testid='contract-signature-submit'` → `POST /api/v1/contract-signing/confirm` | Cadena admin (`create-test-client → sign-marcos → send-client`) · `drawSignature(page, testId)` | `estado=firmado_cliente`, **ClientUser creado (#7)**, project promovido, SSE `signing.signed` a admin, sello Ed25519 | Hash `X-Document-Sha256` no mostrado; geo puede fallar en silencio; spec `fase_43` en modo scaffold (falta `_dev seed-ready-to-sign-contract`) |
| **8** | Login cliente | cliente | `/client-portal/login` | `Input#email` + `Input#password` · `Button[type=submit]` → `POST /client-auth/login`; MFA OTP `Input#mfa_code` → `Button 'Verificar'` | `loginAsClient(page, {email, password})` + `email_backend='mock'` | Cookie `fulkro_session` httpOnly + `fulkro_csrf` → `/client-portal/dashboard` | Force-password-change no en specs principales |
| **9** | Dashboard cliente | cliente | `/client-portal/dashboard` | `ClientDashboardV3` (3 zonas) → `GET /api/v1/client-portal/dashboard/adaptive` + suscripción SSE `useClientProject` | `seedDdaAltaProject(request)` | Dashboard con contexto proyecto; SSE activo | Sin `data-testid` ni spec que valide render |
| **10** | FASE 1 — Categorización + Dimensiones | admin | `/admin/projects/[id]/dimensiones` | `DimensionsWizardPanel` (6 pasos) · `[data-testid='dimensions-wizard-step-*']` → `POST /api/v1/projects/{id}/dimensions`; calcular: `POST .../categorize` | `PHASE_GUIDES.dimensiones()` · `TooltipENS` | 19 dims captadas, `categoria_objetivo=MEDIA`, E-012 acta | **Firma E-012 no localizada** en `dimensiones/page.tsx` |
| **11** | FASE 2 — MAGERIT (admin) | admin | `/admin/projects/[id]/magerit` | `MageritPanel` botón "Crear análisis MAGERIT" · "Calcular intrínseco/efectivo/residual" · "Generar plan" · "Congelar" (`useFreezeAnalysis`) → `POST /api/v1/analyses/{id}/calculate-*` + `/freeze` | `seedMageritAltaData(request)` (8 assets + 12 riesgos) | Análisis con riesgos calculados + plan tratamiento; assets CIDA | UI edición Gantt no detallada; cloud connector selector poco claro |
| **12** | FASE 3 — DdA (admin) | admin | `/admin/projects/[id]/dda` | `[data-testid='dda-generate-button']` → modal `[data-testid='dda-generate-modal']` (Select MEDIA) → `POST /api/v1/dda/generate`; congelar `[data-testid='dda-freeze-button']` | `PHASE_GUIDES.dda()` · `mockDdaAdmin` (specs) | DdA ~68 medidas MEDIA (BOE RD 311/2022), aplicable/no_aplicable, frozen | Firma cliente vía portal aparte (no en admin UI) |
| **13** | FASE 4 — Registro de riesgos | admin | `/admin/projects/[id]/risks` | `RiskDashboard` (read-only) `[data-testid='risk-dashboard-stats']` + `-critical-table`; retry `[data-testid='risk-dashboard-retry']` → `GET /api/v1/projects/{id}/risk-overview` | — (deriva de MAGERIT) | Registro consolidado, top-10 críticos | Sin botón "Add Risk"; asignación responsabilidad no visible |
| **14** | FASE 5 — Plan de adecuación (Gantt + PDA) | admin | `/admin/projects/[id]/plan` | `PlanGantt` `[data-testid='plan-gantt-chart']`; generar PDA `[data-testid='pda-generator-button']` → `POST /api/v1/planning/pda-docx/{projectId}` | `PHASE_GUIDES.plan()` (MEDIA 8-10 sem) | Timeline 68 medidas + PDA DOCX (CCN-STIC 806) | Edición tareas Gantt poco clara; sin botón "Submit for signature" |
| **15** | FASE 6 — Bóveda de evidencias | admin | `/admin/projects/[id]/evidence` | `EvidenceVault` upload (drag-drop) · clasificador AI sugiere medida · `[data-testid='evidence-status-filter']` + `-search-input` → `POST /api/v1/evidence/upload` | `seedConformidadReady` (MEDIA=50 evidencias) · M07 WORM | Evidencias indexadas por medida Anexo II, SHA-256, WORM 7y | UI upload no mostrada (solo list/filter); enforcement WORM presumido DB-level |
| **16** | FASE 7 — Declaración conformidad E-041 (admin) | admin | `/admin/projects/[id]/conformity` | `ConformityWizard` `[data-testid='conformity-wizard']` (5 pasos valida prereqs) · `[data-testid='conformity-generate-button']` → `POST /api/v1/conformity/generate`; publicar `[data-testid='conformity-publish-ccn']` | `ConformityCloudScoreCard` · `ConformityConsole` | E-041 generado, score-card, ruta `certificacion_enac` | Wizard 5 pasos vago; firma cliente vía portal aparte |
| **17** | Categorización (read-only cliente) | cliente | `/client-portal/categorizacion` | `[data-testid='cat-view']` · `[data-testid='cat-categoria-objetivo']` · `[data-testid='cat-system-{id}']` → `GET /api/v1/client-portal/categorizacion`; SSE `m01.categorizacion.completed` | — (depende de M01 admin) | Vista read-only categorización + SSE refresh | Sin spec E2E |
| **18** | MAGERIT validación (cliente) | cliente | `/client-portal/magerit` | `heading 'MAGERIT'`; bulk `POST /api/v1/portal/magerit/assets/{id}/review` + `/risks/{id}/review`; `button 'Validar inventario MAGERIT'` → firma OTP | `seedMageritAltaData` · `magerit-validation-cliente-e2e.spec.ts` (**OTP `test.skip`**) | `magerit_signed_at` NOT NULL; cadena verificada | OTP firma marcada `test.skip` (infra email); patrón bulk API probado |
| **19** | Pentest authorization (cliente) | cliente | `/client-portal/pentest-authorization` | `PentestClienteView` read-only findings; "Autorizar divulgación" → `POST /api/v1/portal/signing/projects/{id}/intent` (`pentest_authorization`) + OTP | `seedPentestAuthData(request)` | `pentest_signed_at` NOT NULL | Sin spec que valide firma pentest cliente |
| **20** | DdA firma (cliente) | cliente | `/client-portal/dda` | `heading 'Declaración de Aplicabilidad'`; pregunta `data-testid='dda-pregunta-textarea'` + `-submit`; firmar `data-testid='dda-cliente-sign-final'` → `DdaSignFinalButton` → OTP `label /Codigo de seguridad/` → `Button /Verificar y firmar/` | `seedDdaAltaProject(request,'dda-firma')` · `waitForOtp` · **spec robusto** `dda-firma-cliente-e2e.spec.ts` | `BasicDdaRow.signed_at` NOT NULL, Ed25519, `chain_valid=true` | `DdaSummaryCard` sin `data-testid`; measure cards sin testid |
| **21** | Policies review + bulk sign (cliente) | cliente | `/client-portal/policies` | `PolicyClientViewOut` cards · `POST /api/v1/portal/policies/documents/{id}/review` · firma bulk → `POST .../finalize-signoff` (CCN-STIC 805) | MEDIA=18 (`_TIER_MIN_POLICIES`) o 8+ seedeadas vía `seedConformidadReady` | Todas las políticas → 1 signing intent, `bulk_signed=true` | **Sin spec E2E de policies**; UI per-policy no mapeada |
| **22** | Evidencias upload (cliente) | cliente | `/client-portal/evidencias` | `EvidenciasUploadPage` · file input/drag-drop → `POST /client-portal/evidencias/upload` (multipart) | seed 50 placeholders (MEDIA) | Evidencia subida + linkada; auditor puede validar | Sin spec E2E; restricciones tipo fichero poco claras |
| **23** | **Conformidad ENS (cliente) — CORE** | cliente | `/client-portal/conformidad` | `ReadinessSection` (5+ checks MEDIA) → banner `/Todos los pasos previos/`; `button 'Marcar como revisado'`; `button 'Firmar compromiso conformidad'` → `POST /api/v1/portal/signing/projects/{id}/intent` (`conformidad`) → OTP `label /Codigo de seguridad/` → `Button /Verificar y firmar/` | `seedConformidadReady(request,'MEDIA','conformidad-media')` (50 evid + políticas, `declaration_type='commitment_pre_certification'`) · **spec `conformidad-commitment-cliente-e2e.spec.ts`** | `BasicDeclarationRow.signed_at` NOT NULL; `TierAwareNextStepSection` "auditor ENAC" + ETA `+7d` / `+30-60d`; `PostSignSection` "Compromiso firmado" | MEDIA cubierto por `conformidad-commitment` (no por `conformidad-media`); tier-gate de políticas no testeado explícito |
| **24** | Firmas-Hub (cliente) | cliente | `/client-portal/firmas-hub` | `heading 'Mis firmas'`; cards `[data-signable-type='dda'|'magerit_validation'|'pentest_authorization'|'conformidad_ens']`; `heading 'Cadena criptográfica'`; `ChainVisualizer` `text /de \d+ firmas completadas/` → `GET /api/v1/portal/firmas-hub/projects/{id}` | `seedDdaAltaProject(request,'firmas-hub')` + `seedConformidadReady(request,'MEDIA','firmas-hub')` · **spec robusto** | Progreso 4/4, banner integridad, cadena Ed25519 visualizada | Cards `dpc_anual`/`actas` en `pending_creation` (aún sin firmar) |
| **25** | Plan ENS read-only (cliente) | cliente | `/client-portal/plan` | `[data-testid='cliente-plan-page']`; toggle `[data-testid='cliente-plan-filter-toggle']` ("Solo mis tareas"); `[data-testid='cliente-plan-gantt']` → `GET /api/v1/client-portal/plan`; SSE `m17.plan.updated` | — (depende seed admin tasks) | Gantt read-only filtrable; SSE auto-update | Sin spec E2E; predicado `isClienteTask` no testeado |
| **26** | Mint token auditor ENAC | system/admin | (dev API) | `POST /api/v1/_dev/auditor-portal-token?project_id={uuid}` → `{project_id, token, otp, portal_path}` | `MagicLinkPurpose.AUDITOR_PORTAL_ENAC` (ttl 336h, `max_uses=9999`, `requires_otp=True`, recipient `auditor.enac@test.fulkro.es`) | JWT magic-link + OTP plaintext (1 vez) | Email auditor hardcoded; no soporta identidades per-spec |
| **27** | Entrada portal auditor + sesión | auditor | `/auditor-portal/[token]/summary` | `GET /api/v1/public/auditor-portal/{token}` (peek, 403/410 si inválido); OTP step-up (`requires_otp`); `POST /public/auditor-portal/{token}/session` (consume 1 uso) · `data-testid='auditor-summary-view'` | env `AUDITOR_PORTAL_TOKEN` + `FULKRO_TEST_PROJECT_ID` | `AuditorPortalChrome` 11-sección sidebar; emite `auditor.session.start` (R6 hash chain) | OTP consume implícito vía `MagicLinkService.consume_magic_link` (no endpoint separado) |
| **28** | Read-only views auditor (9 secciones) | auditor | `/auditor-portal/[token]/{summary\|dda\|magerit\|plan\|evidence\|e041\|audit-log\|pentest\|documents}` | nav `data-testid='auditor-nav-{slug}'`; counts `data-testid='auditor-summary-count-{dda\|evidence\|magerit\|pentest}'`; medida `data-testid='auditor-dda-medida-{codigo}'` → `GET /public/auditor-portal/{token}/{section}` (peek-only, NO consume) | token compartido 9 views | JSON read-only por sección; `audit_log` emit `auditor.view.{section}` | — |
| **29** | Anotaciones auditor (4 severidades) | auditor | secciones con `AnnotationPanel` | `data-testid='auditor-annotate-{targetType}-{targetId}'` · `auditor-annotation-severity` (info/warning/concern/critical) · `-textarea` · `-submit` → `POST /public/auditor-portal/{token}/annotations` | `AnnotationPanel` (`evidence`/`medida`/`magerit_*`/`plan_task`/`audit_log_entry`) | `AuditorAnnotation` row, `auditor.annotation.created` | Admin responde en `/admin/projects/{id}/audit/annotations/{id}` (PATCH) |
| **30** | Solicitud aclaración auditor (2 prioridades) | auditor | top-bar cross-views | `data-testid='auditor-clarification-button-general'` · `-priority` (urgent/normal) · `-textarea` · `-submit` → `POST /public/auditor-portal/{token}/clarifications` | `ClarificationButton` | `AuditorClarificationRequest`, `auditor.clarification.requested`, SSE `project:{id}` + email a admin | — |
| **31** | DdA-Evidence gaps heatmap | auditor | `/auditor-portal/[token]/audit/dda-evidence-gaps` | `data-testid='gap-view'` · `-coverage-pct` · celda `gap-medida-cell-{code}` → drawer `gap-medida-drawer` → `GET /public/auditor-portal/{token}/audit/dda-evidence-gaps` | `dda_evidence_gap_service.compute_gap_matrix` | Matriz 68/73 medidas color-coded; emit `auditor.view.dda_evidence_gaps` | Thresholds red/yellow/green no expuestos vía endpoint |
| **32** | Generar borrador informe auditoría | auditor | `/auditor-portal/[token]/draft-report` | `data-testid='draft-auditor-name-input'` · `-period-start/-end` · `-recommendation-select` (APROBAR/APROBAR_CON_CONDICIONES/NO_APROBAR) · `-opinion-textarea`; preview `draft-preview-iframe`; `draft-generate-button` → `POST /public/auditor-portal/{token}/audit/draft-report` | `DraftReportGenerator` (reportlab platypus) | PDF firmado Ed25519 `borrador_auditoria_{project_id}.pdf` + headers `X-Pdf-Sha256`/`X-Signature-Algorithm`; emit `auditor.draft_report.generated` | weasyprint NO instalado (reportlab fallback empírico) |
| **33** | Export CSV audit-log auditor | auditor | `/auditor-portal/[token]/audit-log` | `data-testid='auditor-audit-log-export-csv'` → `GET /public/auditor-portal/{token}/audit-log.csv?limit=500[&accion=]` | nombres canónicos `AUDITOR_EVENT_TYPES` | CSV `audit_log_{project_id}.csv`; emit `auditor.download.audit_log_csv` | CSV NO incluye `hash_current`/`hash_previous` (solo raw SQL) |
| **34** | Admin responde aclaración | admin | `/admin/projects/{project_id}/audit/clarifications` | `data-testid='admin-clarifications-inbox'` · card `admin-clarification-card-{id}` · `admin-clarification-response-{id}` · `-status-{id}` · `-submit-{id}` → `PATCH /admin/projects/{project_id}/audit/clarifications/{id}` | inbox SSE realtime | `admin_response` + `admin.clarification.responded`; status `open→in_progress→responded→closed` | Estructura `AdminClarificationsInbox` no totalmente mapeada |
| **35** | **Admin marca audit-passed (M25 Paso 4)** | admin | `/admin/projects/[id]/audit` · `MarkAuditPassedDialog` | `data-testid='audit-result-option-{passed\|observed\|correction_required\|failed}'` · `id='audit-report-ref'` · toggle `cascade_certify` · submit → **`POST /api/v1/projects/{project_id}/audit/mark-passed`** | `MarkAuditPassedBody` (`cascade_certify`+`cascade_retainer_offer` flags) | `audit_passed_at`, `audit_result`; si `passed`+`cascade_certify`: `lifecycle_state=CERTIFIED` + evento `certified` | Submit/checkbox no localizados explícitos al final del componente; **NO existe `_dev` lever** (requiere auth Marcos real) |
| **36** | Cascada certificación + oferta retainer (system) | system | `POST /api/v1/projects/{id}/mark-certified` (interno) → `offer-retainer` | Cascada en `mark_audit_passed`: auto-deriva `recipient_email` (último ClientUser) → `emit_client_notification(type='retainer_offer', target_url='/client-portal/retainer')` | `cascade_retainer_offer=True` · `VALID_RETAINER_TIERS` (default `R_STD`) | `certified_at`, `ClientNotification` retainer, evento `retainer_offered` | best-effort (no-fatal si falta ClientUser) |
| **37** | Audit Accompaniment timeline (admin) | admin | `/admin/projects/[id]/audit` · `AuditAccompanimentTimeline` | `data-testid='audit-accompaniment-timeline'` · advance → `POST /api/v1/admin/projects/{id}/accompaniment/advance` (MEDIO/ALTO 11 estados, no skip/back); artifacts → `POST .../accompaniment/artifacts` | `resolve_category_branch()` MEDIA→`MEDIO_ALTO` (11 estados) | Recorre `preparation → ... → enac_audit_passed → certificate_issued → biannual_renewal_scheduled` | `STATE_TUTOR_HINTS` UI tooltip no localizado |
| **38** | Certificación read-only (cliente) | cliente | `/client-portal/certificacion` · `AuditAccompanimentClienteView` | `data-testid='cliente-audit-accompaniment-view'`; SSE `audit.milestone.updated` → `GET /api/v1/client-portal/accompaniment/timeline` | `MEDIO_ALTO_FRIENDLY_LABELS` · `useClientProjectEvents` | Timeline friendly read-only + SSE auto-update (R29) | Lifecycle init post-MEDIA conformidad poco claro |
| **39** | E-049 Distintivo + cert externo (MEDIA) | system | `/admin/projects/[id]/compliance` + Document | `build_distintivo_context` → `generate_declaration_docx` → `issue_distintivo_document` (`E-049`); cert externo ENAC `attach_external_certificate` (`E-049-EXT`) | `ConformityRouteRow.route_type='certificacion_enac'`+`status=CONFORMANT` | DOCX distintivo (texto MEDIA "no sustituye certificado entidad acreditada") + PDF cert externo CCN-STIC 808 | `cert_id` estable pero `expiry_date=today+2y` (regen cambia expiry) |
| **40** | Cliente acepta retainer | cliente | **`/client-portal/retainer` (RUTA AUSENTE)** | (UI no existe) → `POST /api/v1/projects/{project_id}/lifecycle/decision` (`decision='accept'`+`tier`+`precio_mensual`) | `RetainerDecisionBody` · M23 `RetainerService.create_retainer()` | `lifecycle_state=RETAINER`, `RetainerContract` `perfil=tier`; o `ENDED_CHURN`+`start_grace_period(240d)` si decline | **GAP REAL CONFIRMADO**: `/client-portal/retainer` NO existe (solo `/client-portal/retainer-checkin`). Endpoint backend SÍ existe |
| **41** | Retainer dashboard (admin) | admin | `/admin/projects/[id]/retainer` · `RetainerProjectDashboard` | `useRetainerProject` / `useRetainerActivities` / `useRetainerDrifts` / `useRenewalStatus` → `GET /api/v1/projects/{id}/retainer` (+ activities/drifts/renewal-status) | `CADENCES_BY_PROFILE` (5 tiers) · R_STD=40h/mes | Dashboard actividades, drift, renewal, capacidad/SLA | — (M23 dashboard completo) |

**Total: 42 fases (0–41).** Núcleo MEDIO mínimo para captura: fases 0, 1, 7, 8, 10–16, 20, 23, 24, 26–32, 35, 37, 38, 41.

---

## 2. Toolbox dev/seed

Todos bajo prefijo `/api/v1/_dev/*` salvo lifecycle (producción `/api/v1/projects/...`). Gate global: `not get_settings().is_production` (doble defensa: router include + `_require_non_production()` per-endpoint). Bypass RLS: `SET LOCAL ROLE fulkro_app_bypassrls`. Verificado en `backend/app/dev/router.py`.

| Lever | Método + Path | Params | Output clave |
|-------|---------------|--------|--------------|
| Seed info Marcos | `GET /api/v1/_dev/seed-info` | — | `marcos_user_id`, `marcos_email` |
| Crear cliente+proyecto test | `POST /api/v1/_dev/create-test-client` | `?secondary=false\|true` | `user_id`, `email=test-client-e2e@example.com`, `password=TestP@ssw0rd123!`, `client_id`, `project_id` (MEDIA) |
| Fijar categoría proyecto | `POST /api/v1/_dev/set-test-project-category` | `?tier=BASICA\|MEDIA\|ALTA` | `previous`, `current` |
| Login como Marcos (sesión real) | `POST /api/v1/_dev/login-as-marcos` | — | cookies `fulkro_session`+`fulkro_csrf`, `jti`, `expires_at` (bypassa TOTP/WebAuthn) |
| Listar emails capturados | `GET /api/v1/_dev/captured-emails` | `?to=...&subject_pattern=...` | `captured[]` (to/from/subject/html_body/sent_at), `count` |
| Esperar OTP (polling) | `GET /api/v1/_dev/captured-emails/wait-for-otp` | `?to=...&timeout_seconds=10` (1-60) | `otp_code` (6 díg), `elapsed_seconds`; 408 si timeout |
| Reset emails | `DELETE /api/v1/_dev/captured-emails` | — | 204 |
| Seed DdA ALTA (73) + aplicabilidad | `POST /api/v1/_dev/seed-dda-alta-project` | `?key=None\|dda-firma\|conformidad-{basica\|media\|alta}\|firmas-hub` | `project_id`, `dda_entries_count=73`, freeze + clears firmas |
| Seed MAGERIT ALTA | `POST /api/v1/_dev/seed-magerit-alta-data` | — | `analysis_id`, `assets_count=8`, `risks_count=12` |
| Seed pentest auth | `POST /api/v1/_dev/seed-pentest-auth-data` | — | `verification_run_id` (admin pre-firmado, cliente pending) |
| **Seed conformidad ready** | `POST /api/v1/_dev/seed-conformidad-ready` | `?tier=BASICA\|MEDIA\|ALTA&key=...` | `declaration_id`, `chain_signed`, `evidence_count` (25/**50**/73), `policies_signed_count`, draft `BasicDeclarationRow` |
| **Mint token auditor ENAC** | `POST /api/v1/_dev/auditor-portal-token` | `?project_id={uuid}` (opt) | `{project_id, token, otp, portal_path=/auditor-portal/{token}/summary}` (`requires_otp=True`) |
| Reset cycle (limpieza) | `POST /api/v1/_dev/reset-test-cycle` | `?project_id=...` | `deleted{}` por tabla |
| Seed rich demo (UUID fijo) | `POST /api/v1/_dev/seed-rich-demo-project` | — | `project_id=00000000-0000-0000-0000-000000000001` |
| **Mark audit-passed (M25)** | `POST /api/v1/projects/{project_id}/audit/mark-passed` ⚠️ NO `_dev` | body `result`, `cascade_certify`, `cascade_retainer_offer` | `audit_passed_at`, cascada `CERTIFIED` + oferta retainer |
| Mark certified (M25) | `POST /api/v1/projects/{project_id}/mark-certified` ⚠️ NO `_dev` | body `certified_on?` | `certified_at`, `lifecycle_state=CERTIFIED` |
| Offer retainer (M25) | `POST /api/v1/projects/{project_id}/lifecycle/offer-retainer` ⚠️ NO `_dev` | — | `ClientNotification` retainer, evento `retainer_offered` |
| Retainer decision (cliente) | `POST /api/v1/projects/{project_id}/lifecycle/decision` ⚠️ NO `_dev` | body `decision`, `tier`, `precio_mensual` | `RETAINER` o `ENDED_CHURN`+grace |

> ⚠️ Los 4 lifecycle (mark-passed / mark-certified / offer-retainer / decision) son endpoints de **producción** que requieren auth admin Marcos real (vía `login-as-marcos`) — NO existe lever `_dev` dedicado. La sim los invoca con la sesión de Marcos (fase 1) usando el `project_id` real.

---

## 3. Plan del harness Playwright

**Estrategia: UN spec ordenado** `frontend/tests/e2e/sim-medio-full-cloth-e2e.spec.ts` con `test.describe.serial(...)` (un solo `test()` o pasos `test.step(...)` secuenciales que comparten un `BrowserContext` por actor). Captura por fase a `out/sim_medio_e2e/NN_<phase>.png`.

### Estructura propuesta

```
test.describe.serial('SIM MEDIO full-cloth E2E', () => {
  // contextos por actor (ADR-013 doble pool): admin, cliente, auditor
  let adminCtx, clienteCtx, auditorCtx;
  let project_id, contractToken, contractOtp, auditorToken, auditorOtp;

  const shot = async (page, n, name) =>
    page.screenshot({ path: `../out/sim_medio_e2e/${String(n).padStart(2,'0')}_${name}.png`, fullPage: true });

  test('walk all phases', async ({ browser, request }) => {
    // ── FASE 0: bootstrap ──
    await resetCapturedEmails(request);
    const tc = await createTestClient(request);            // POST /_dev/create-test-client
    await setTestProjectCategory(request, 'MEDIA');         // POST /_dev/set-test-project-category?tier=MEDIA
    project_id = tc.project_id;

    // ── FASE 1: login admin ──  (REUSE loginAsMarcos)
    adminCtx = await browser.newContext();
    await loginAsMarcos(adminCtx);
    const adminPage = await adminCtx.newPage();
    await adminPage.goto('/admin/projects'); await shot(adminPage, 1, 'admin_login');

    // ── FASES 2-6: comercial (mayoría backend-driven; capturar UI que exista) ──
    await adminPage.goto('/admin/pipeline'); await shot(adminPage, 2, 'pipeline');
    await adminPage.goto(`/admin/projects/${project_id}/contratos`);
    // REUSE data-testid='contracts-generate-button' (fase_43 chain probada para firma)
    await shot(adminPage, 4, 'contrato');

    // ── FASE 7: cliente firma contrato (canvas público) ──  (REUSE fase_43 selectors)
    // seedReadyToSignContract chain → /sign/{token}
    // data-testid='contract-signature-pad' + '-name-input' + '-surname-input' + '-submit'
    // drawSignature(page, 'contract-signature') ; await shot(..., 7, 'cliente_firma_contrato')

    // ── FASES 10-16: implantación admin (cronológica) ──
    for (const [n, slug, name] of [
      [10,'dimensiones','dimensiones'],[11,'magerit','magerit_admin'],
      [12,'dda','dda_admin'],[13,'risks','risks'],[14,'plan','plan_admin'],
      [15,'evidence','evidence_admin'],[16,'conformity','conformity_admin'],
    ]) { await adminPage.goto(`/admin/projects/${project_id}/${slug}`); await shot(adminPage, n, name); }

    // ── Seeds que habilitan firma cliente (idempotentes, key='conformidad-media') ──
    await seedDdaAltaProject(request, 'conformidad-media');
    await seedMageritAltaData(request);
    await seedPentestAuthData(request);
    await seedConformidadReady(request, 'MEDIA', 'conformidad-media');  // 50 evid + políticas

    // ── FASE 8: login cliente ──  (REUSE loginAsClient)
    clienteCtx = await browser.newContext();
    await loginAsClient(clienteCtx, { dismissTutorial: true });
    const cli = await clienteCtx.newPage();
    await cli.goto('/client-portal/dashboard'); await shot(cli, 9, 'cliente_dashboard');

    // ── FASES 18-25: firmas cliente (REUSE selectores probados) ──
    // 20 DdA: REUSE dda-firma-cliente-e2e.spec.ts → data-testid='dda-cliente-sign-final' + waitForOtp + 'Verificar y firmar'
    // 23 Conformidad: REUSE conformidad-commitment-cliente-e2e.spec.ts → 'Marcar como revisado' + 'Firmar compromiso conformidad' + OTP
    // 24 firmas-hub: REUSE firmas-hub-cliente-e2e.spec.ts → [data-signable-type='conformidad_ens'] + 'Cadena criptográfica'
    await cli.goto('/client-portal/dda'); await shot(cli, 20, 'cliente_dda');
    await cli.goto('/client-portal/conformidad'); await shot(cli, 23, 'cliente_conformidad');
    await cli.goto('/client-portal/firmas-hub'); await shot(cli, 24, 'cliente_firmas_hub');

    // ── FASE 26: mint auditor token ──
    const at = await request.post(`/api/v1/_dev/auditor-portal-token?project_id=${project_id}`);
    ({ token: auditorToken, otp: auditorOtp } = await at.json());

    // ── FASES 27-33: auditor (REUSE auditor-portal-full-flow.spec.ts selectors) ──
    auditorCtx = await browser.newContext();
    const aud = await auditorCtx.newPage();
    await aud.goto(`/auditor-portal/${auditorToken}/summary`);  // OTP step-up con auditorOtp
    // data-testid='auditor-summary-view'
    for (const [n, slug, name] of [
      [27,'summary','auditor_summary'],[28,'dda','auditor_dda'],
      [31,'audit/dda-evidence-gaps','auditor_gaps'],[32,'draft-report','auditor_draft'],
    ]) { await aud.goto(`/auditor-portal/${auditorToken}/${slug}`); await shot(aud, n, name); }
    // 29 anotación: data-testid='auditor-annotate-medida-*' + 'auditor-annotation-severity' + '-submit'
    // 30 aclaración: data-testid='auditor-clarification-button-general' + '-submit'
    // 32 draft: data-testid='draft-generate-button'

    // ── FASE 34-36: admin responde + mark-audit-passed (REUSE adminCtx sesión Marcos) ──
    await adminPage.goto(`/admin/projects/${project_id}/audit`);
    // MarkAuditPassedDialog: data-testid='audit-result-option-passed' + cascade_certify + submit
    // o directo: POST /api/v1/projects/{project_id}/audit/mark-passed (sesión Marcos + CSRF)
    await shot(adminPage, 35, 'admin_audit_passed');

    // ── FASE 37-38: accompaniment timeline ──
    await shot(adminPage, 37, 'admin_accompaniment');         // data-testid='audit-accompaniment-timeline'
    await cli.goto('/client-portal/certificacion'); await shot(cli, 38, 'cliente_certificacion');

    // ── FASE 41: retainer dashboard admin ──  (fase 40 cliente retainer: ruta ausente, capturar 404/skip)
    await adminPage.goto(`/admin/projects/${project_id}/retainer`); await shot(adminPage, 41, 'admin_retainer');
  });
});
```

### Reuso de selectores probados (área "existing specs")

- **Auth**: `loginAsMarcos(context)` + `loginAsClient(page, {dismissTutorial})` + `AUDITOR_PORTAL_TOKEN`/`auditor-portal-token` — `frontend/tests/e2e/_helpers/auth-real.ts`.
- **Seeds idempotentes** (R27 `LIMIT 1`, key por spec): `seedDdaAltaProject`, `seedConformidadReady`, `seedMageritAltaData`, `seedPentestAuthData`, `resetCapturedEmails`, `waitForOtp` — `frontend/tests/e2e/_helpers/*-seed.ts`.
- **Contrato canvas** (fase 7): `data-testid='contract-signature-pad'/-name-input/-surname-input/-submit'`, `drawSignature(page,'contract-signature')` — `fase_43_contract_canvas_sign_flow.spec.ts` (modo scaffold; necesita `_dev seed-ready-to-sign-contract`).
- **DdA cliente** (fase 20): `dda-firma-cliente-e2e.spec.ts` (E2E robusto, sin gaps).
- **Conformidad MEDIA** (fase 23): `conformidad-commitment-cliente-e2e.spec.ts` (`'Compromiso de conformidad'`, `'Categoría MEDIA'`, ETA `+7d`/`+30-60d`).
- **Firmas-hub** (fase 24): `firmas-hub-cliente-e2e.spec.ts` (`[data-signable-type=*]` + `'Cadena criptográfica'`).
- **Auditor** (fases 27-33): `auditor-portal-full-flow.spec.ts` (annotations/clarifications/gaps/draft-report).
- **Patrón SSE**: páginas cliente nunca settlean networkidle — gatear en visibilidad de elemento (`domcontentloaded` + esperar `data-testid`), no `networkidle`.

> **Nota OTP**: las firmas cliente requieren `email_backend='mock'` + `waitForOtp(request, email, 10)`. El spec `magerit-validation` marca el paso OTP como `test.skip` por infra de email frágil — para la sim usar `wait-for-otp` con `subject_pattern='codigo de seguridad'` y tolerar 408.

---

## 4. Recipe de ejecución (WSL)

Stack: backend uvicorn `:8000` (`APP_ENV=development`), frontend Next.js 14 `:3100`. Verificado en `frontend/playwright.config.ts` (`PORT=3100`, `globalSetup`, `webServer: npx next start -p 3100`, `reuseExistingServer: !CI`).

```bash
# 0) Pre-flight backend (en WSL, no Windows)
curl -s http://localhost:8000/api/v1/health        # {"status":"ok","environment":"development"}
curl -s -o /dev/null -w '%{http_code}\n' \
     http://localhost:8000/api/v1/_dev/seed-info    # 200 (si 404 → app_env=production o backend caído)

# 1) BUILD frontend OBLIGATORIO (webServer usa 'next start', requiere .next/BUILD_ID)
cd /home/usuario/fulkro/frontend
npm run build                                       # ~20-30s; OJO: frontend/.env necesita FULKRO_AUTH_PUBLIC_KEY
test -f .next/BUILD_ID && echo "BUILD OK"

# 2) Carpeta de capturas
mkdir -p /home/usuario/fulkro/out/sim_medio_e2e

# 3) Ejecutar el spec ordenado (headless, chromium)
cd /home/usuario/fulkro/frontend
PLAYWRIGHT_PORT=3100 PLAYWRIGHT_BACKEND_URL=http://localhost:8000 \
  npm run test:e2e -- tests/e2e/sim-medio-full-cloth-e2e.spec.ts --project=chromium

# 4) Capturas resultantes
ls -la /home/usuario/fulkro/out/sim_medio_e2e/*.png

# (opcional) traza en fallo
npx playwright show-trace test-results/<test>-chromium/trace.zip
```

**¿Build necesario?** SÍ — `webServer` arranca con `npx next start`, que falla con "Could not find BUILD_ID" si `.next/` está sin compilar. (Para iteración rápida se podría apuntar a un `next dev` ya levantado en `:3100` con `reuseExistingServer:true`, pero el path canónico de la sim es build + start.)

**¿LLM real?** SÍ — `ANTHROPIC_API_KEY` está en `/home/usuario/fulkro/.env`; los pasos que invocan agentes (propuesta A19, narrativa contrato A20) harán **llamadas reales a Anthropic** (coste real, latencia variable, temperatura ≤0.2 por R3). Para una sim determinista/barata, las fases comerciales 3-4 pueden seedearse por API en vez de disparar LLM, o el harness puede forzar `FULKRO_RUN_LLM_TESTS` off / key vacía (mock-by-default) según la memoria `suite-seal-llm-hang-db-contention` (la key real puede colgar la suite). **Recomendación**: para la sim de capturas, NO disparar generación LLM en vivo; seedear estado y capturar UI.

**WSL gotcha**: ejecutar `npm`/`curl` desde WSL (`/home/usuario/fulkro/...`), no desde PowerShell sobre la UNC path. Las rutas relativas en `playwright.config.ts` asumen cwd `frontend/`.

---

## 5. Defectos reales probables (ranked)

Ordenados por probabilidad de bloquear/romper la sim y por impacto en producción real (de los campos `likely_gaps` de los 9 mapas + verificación empírica):

1. **`/client-portal/retainer` NO EXISTE (gap frontend confirmado).** Fase 40. El backend emite `ClientNotification` con `target_url='/client-portal/retainer'` y el endpoint `POST /lifecycle/decision` existe, pero **el directorio de ruta no está** (`frontend/app/(client-portal)/client-portal/retainer/` ausente — solo `retainer-checkin`). El cliente recibe una notificación a una ruta 404. La sim debe `test.skip` la fase 40 cliente y aceptar el retainer vía API directa, marcándolo como defecto P0.

2. **Cadena comercial sin lever `_dev` determinista para contrato listo-firmar.** Fase 4-7. No hay `_dev/seed-ready-to-sign-contract`; `fase_43_contract_canvas_sign_flow.spec.ts` queda en **scaffold** y depende de encadenar `create-test-client → generate → sign-marcos → send-client` manualmente. Frágil; un cambio en cualquier paso rompe la firma del contrato (que además dispara la creación del ClientUser #7). P0 para el primer tramo de la sim.

3. **`mark-audit-passed` requiere auth admin real (sin `_dev`) + submit/checkbox del dialog no localizados.** Fase 35. La cascada audit→cert→retainer es el corazón del cierre MEDIO; el `MarkAuditPassedDialog` no tiene `data-testid` claro para el botón submit ni el toggle `cascade_certify` en las lecturas. Riesgo de que la sim no pueda avanzar el lifecycle vía UI → fallback a `POST /api/v1/projects/{id}/audit/mark-passed` con sesión Marcos + CSRF. P1.

4. **Firmas cliente con OTP frágiles (mock email).** Fases 18, 20, 23. `magerit-validation` ya marca el OTP como `test.skip`; `waitForOtp` con `subject_pattern='codigo de seguridad'` hardcoded se rompe si cambia el asunto del email. Cualquier firma OTP que falle bloquea la readiness de conformidad. Además, la key Anthropic real puede colgar la suite (memoria `suite-seal`). P1.

5. **Firma E-012 (acta categorización) inexistente en UI + sin firma cliente en pasos admin DdA/MAGERIT/conformity.** Fases 10, 12, 16. No se encontró botón de firma E-012 en `dimensiones/page.tsx`; las firmas de DdA/conformidad viven solo en el portal cliente (magic-link), no en admin. La sim debe asumir que el estado de firma se siembra (`seedConformidadReady` congela DdA con `aprobado_por`), no se produce orgánicamente desde la UI admin. P2.

**Menores (no bloquean la sim, pero son deuda real):** sin spec E2E para policies/evidencias/categorización/plan cliente (fases 17, 21, 22, 25); `DdaSummaryCard`/measure-cards/Gantt task-bars sin `data-testid`; grace-period cliente (decline retainer) sin UI; CSV audit-log auditor sin columnas hash; thresholds heatmap gaps no expuestos; lead/proposal sin UI de creación (backend-driven).
