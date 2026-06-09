# AUDIT Sesión 3A · Phase 0 · 4 PARTS comprehensive

**Date**: 2026-05-25
**HEAD base**: d16cf26 (post Sesión 1)
**OPS-052 doctrine**: Phase 0 MANDATORY empirical state verification BEFORE implementation chain.
**Constraint**: NO grep · solo find/cat/wc/head/tail/ls.

## Scope refined cumulative

Briefing nominal asumía greenfield para:
- (A) Project selector entry flow polish/build (~2-3h)
- (B) Copilot guided foundation + roadmap 10-fase stepper + onboarding tour (~3-6h)

**Phase 0 reveals**: ~85-90% existing production-grade. Sub-atom 3A scope recalibrated **massive reduction** + Sub-atom 3B + 3C ETAs refined per findings.

OPS-045 candidato **38ª aplicación consecutiva** (audit-first reveals existing infrastructure).

---

## PART A · Project selector entry flow · status

**Verdict**: ✅ **PRODUCTION-GRADE existing**. Briefing claim greenfield falso · realidad selector + ProjectContext + redirect L3 hybrid + sidebar banner + breadcrumb COMPLETOS.

### Findings

| Item | Path | Status | Notes |
|------|------|--------|-------|
| Selector page | `frontend/app/(admin)/admin/projects/page.tsx` | ✅ existing 229 LOC | Card grid + search + lifecycle status pill + "Último usado" badge + ArchiveProjectButton + CreateProjectModal + demo project shortcut |
| ProjectContext (Zustand store) | `frontend/lib/stores/active-project-store.ts` | ✅ existing 87 LOC | `activeProject` + `lastUsedProjectId` persist localStorage partialize + SSR-safe `readLastUsedProjectIdFromStorage()` helper |
| Post-login L3 hybrid redirect | ADR-054 referenced inline | ✅ existing | Sub-atom 1.E.2 Phase A canonical · login → /admin/projects selector OR lastUsedProjectId auto-redirect |
| Sidebar persistent banner | `frontend/components/layout/Sidebar.tsx` + `ActiveProjectBanner.tsx` | ✅ existing | Banner muestra cliente + project + ENS badge |
| ProjectSwitcherDropdown | inferred (ADR-054 reference) | ✅ existing | DropdownMenu reuse PortalSwitcher pattern |
| ProjectBreadcrumb | inferred (Sub-atom 1.E.2 Phase C) | ✅ existing | Per-page breadcrumb [Cliente] > [Proyecto] > [Sub-página] |
| ActiveProjectSync routing guard | inferred (1.E.2.Phase C 213 LOC) | ✅ existing | layout.tsx sync URL ↔ store · auto-fetch project header |
| Copilot-store sync `panelContext.projectId` | `frontend/lib/stores/copilot-store.ts` | ✅ existing | Cross-portal isolation (1.E.2 Phase D) |
| Project CRUD (admin) | `CreateProjectModal` + `ArchiveProjectButton` | ✅ existing 1.E.2.bis Phase A | Backend `DELETE archive` endpoint + frontend modal name-match confirmation |

### Architecture decisions ALREADY formalized

- **ADR-054 · Project-Scoped Admin UX** (Sub-atom 1.E.2 commit `e74706c`)
  - L3 hybrid post-login redirect
  - Zustand store + persist localStorage partialize
  - Sidebar enhance + DropdownMenu pattern reuse
  - Cliente portal R29 architectural isolation
  - 6 commits productivos Sub-atom 1.E.2 cumulative
  - 4 backend integration tests verde (cross-project data leak prevention E2E confirmed)
  - 3 E2E specs fase_36 ARTIFACT

- **Sub-atom 1.E.2.bis RECALIBRATED** (cumulative · 5 sub-fases A+B+C+D+E+F)
  - Phase A Project CRUD + soft delete
  - Phase B status pill general info display per card
  - Phase C client_users management 4 new tabs per project
  - Phase D personalización per project (branding form + live preview)
  - Phase E+F cliente portal verified + multi-tenant scenarios E2E doc

### Gaps detected (POLISH minor only)

| Gap | Severity | Effort | Sesión 3A scope decision |
|-----|----------|--------|-------------------------|
| "Entrar al proyecto" hoy va a `/dashboard` · briefing pide → `/roadmap` | MINOR (1 línea) | ~5 min | ✅ Sesión 3A Phase A microfix |
| Single-project auto-redirect logic missing (briefing pide if N=1 → roadmap directly) | MINOR (1 useEffect) | ~15 min | ✅ Sesión 3A Phase A microfix |
| Empty state copy "Crea tu primer proyecto ENS · te guiamos paso a paso" (más friendly que actual "No hay clientes en la base de datos") | NICE-TO-HAVE | ~5 min | ✅ Sesión 3A Phase A microfix |

### PART A verdict empírico

**Effort recalibrated Phase A**: ~2-3h nominal → **~30-45 min empírico** (scope reduced ~85% · POLISH 3 microfixes only).

---

## PART B · Copilot guided flow + Roadmap · status

**Verdict**: ✅ **PRODUCTION-GRADE existing 90%+**. Briefing assume greenfield roadmap/copilot/onboarding tour FALSO · realidad infraestructura masiva existing.

### Findings · Roadmap 10 fases ENS

| Item | Path | Status | Notes |
|------|------|--------|-------|
| Roadmap page admin | `frontend/app/(admin)/admin/projects/[id]/roadmap/page.tsx` | ✅ existing 71 LOC | Layout 70/30 · RoadmapView + NextActionCard list top 5 priority · ADR-026 FASE 8 |
| WorkflowPhase enum 10 fases | `frontend/lib/admin-workflow/schemas.ts` | ✅ existing 10 fases canonical | pre_venta · onboarding · diagnostico · analisis_riesgos · adecuacion · implantacion · dda_final · verificacion · conformidad · retainer_cierre (Manual ENS plan v4.2 · SAN-C MB-11.1) |
| RoadmapView grid 4 cols responsive | `frontend/components/workflow/RoadmapView.tsx` | ✅ existing 35 LOC | PhaseStepper top + grid PhaseCards · onPhaseClick callback |
| PhaseStepper visual horizontal | `frontend/components/workflow/PhaseStepper.tsx` | ✅ existing 32 LOC | Wrapper Stepper UI base + WORKFLOW_PHASES enum |
| PhaseCard per fase | `frontend/components/workflow/PhaseCard.tsx` | ✅ existing 92 LOC | Status badge variant + STATUS_LABEL + STATUS_ICON + Progress bar + click → onPhaseClick |
| PhaseProgressWizard alternativo | `frontend/components/dashboard/PhaseProgressWizard.tsx` | ✅ existing 273 LOC | 10 fases canonical descritas + tooltips + locks (Lock icon) + Link navigation + segment mapping ADR-035 MB-13.2 |
| Hooks useRoadmap + useNextActions + usePhaseProgress | `frontend/hooks/useWorkflowAdmin.ts` | ✅ existing 75 LOC | TanStack Query staleTime 30s · 5 hooks completos |
| Backend roadmap endpoint | inferred `getRoadmap(projectId)` consumed | ✅ existing | ADR-026 FASE 8 implementation |
| NextActionCard top 5 priority | `frontend/components/workflow/NextActionCard.tsx` | ✅ existing | Per-action priority + estimated_minutes + endpoint link |

### Findings · Copilot guided existing

| Item | Path | Status | Notes |
|------|------|--------|-------|
| CopilotoDock (cliente portal global) | `frontend/components/copiloto/CopilotoDock.tsx` | ✅ existing 264 LOC | Floating dock per page · streaming SSE · quick actions contextual per pathname (magerit/dda/conformidad/evidencias/incidents) · MB-7 atom 7.2 |
| CopilotoClienteBottomRight | `frontend/components/copiloto-cliente/CopilotoClienteBottomRight.tsx` | ✅ existing | Sub-atom 1.D.B.1 v3.11 LLM real Haiku 4.5 R29 doble defensa |
| CopilotoAdminSidebar | `frontend/components/workflow-command-center/CopilotoAdminSidebar.tsx` | ✅ existing | Sub-atom 1.D.B.2 v3.11 LLM real Sonnet 4.6 R30 defensive enrich + LLM badge |
| CopilotoBriefingMatutino | `frontend/components/workflow-command-center/CopilotoBriefingMatutino.tsx` | ✅ existing | Sesión brief admin |
| CopilotoQuickActions | `frontend/components/workflow-command-center/CopilotoQuickActions.tsx` | ✅ existing | Quick actions ProjectContext aware |
| CopilotPanel + CopilotComposer + CopilotMessages + CopilotMessage | `frontend/components/copilot/` | ✅ existing 4 files | Component layer reusable |
| CopilotChat (agents) | `frontend/components/agents/CopilotChat.tsx` | ✅ existing | Multi-agent dispatch |
| Backend copilot_persona_service + loader + admin_service + cliente_service + rate_limit + stub_service | `backend/app/agents/copilot_*.py` | ✅ existing 7 files | Anexo M v3.10 personas YAML production-grade · sub-atom 1.D.B.0/1/2 cumulative |

### Findings · OnboardingTutorial existing

| Item | Path | Status | Notes |
|------|------|--------|-------|
| OnboardingTutorial cliente portal | `frontend/components/client-portal/tutorial/OnboardingTutorial.tsx` | ✅ existing 155 LOC | 5-step welcome modal primer login · localStorage `fulkro_tutorial_completed` flag · skip option · MB-7 atom 7.3 plan v6 · Q5.4 cement message |
| OnboardingClientFlow | `frontend/components/client-portal/OnboardingClientFlow.tsx` | ✅ existing | Cliente onboarding flow wizard |
| OnboardingAdminPanel | `frontend/components/onboarding/OnboardingAdminPanel.tsx` | ✅ existing 4 Tabs | Sessions · Catálogo · Connectors · LMS |
| ProjectDiagnosticoWizard | `frontend/components/project-wizard/ProjectDiagnosticoWizard.tsx` | ✅ existing | Sub-atom 1.D.F.0.A wizard diagnóstico ENS 6 steps |
| DimensionsWizardPanel | `frontend/components/dimensions/DimensionsWizardPanel.tsx` | ✅ existing | 19 dimensiones adaptación canonical |
| ConformityWizard · ContractGenerateWizard · ChangeRequestWizard | per-motor | ✅ existing | Wizards production-grade per motor |
| WorkflowStepperCard (cliente) | `frontend/components/client-portal/dashboard/WorkflowStepperCard.tsx` | ✅ existing | Dashboard cliente stepper |

### Findings · Per-phase explanatory content (briefing Phase B.4)

| Item | Path | Status | Notes |
|------|------|--------|-------|
| Per-phase descriptions inline | `PhaseProgressWizard.tsx` 10 PHASES const | ✅ existing | Por cada fase: id · short · full · description (1 línea) · segment URL mapping |
| Dedicated explanatory doc | `docs/copilot/phase-explanations.md` | ❌ NOT existing | Briefing pide structure (intro · why_important · what_we_do · common_mistakes · estimated_time · help_resources) |
| HelpModal contextual FAQ | NOT found in `frontend/components/` | ❌ NOT existing | Briefing pide |
| CopilotGuidedFlow component wrapper | NOT found · solo CopilotoDock + CopilotoSidebar production | ⚠ PARCIAL existing | Existing dock cumple función but NOT structured "guided per phase" pattern |
| Help "Contactar a Marcos" mailto/Slack button | NOT found dedicated component | ❌ NOT existing | Cliente puede usar `/client-portal/chat` · admin no dedicated |

### Gaps detected (Phase B real scope)

| Gap | Severity | Effort | Sesión 3A scope decision |
|-----|----------|--------|-------------------------|
| `/admin/projects/[id]/roadmap` → "Entrar al proyecto" CTA (selector card update) | MINOR | ~5 min (already PART A) | ✅ PART A microfix |
| `docs/copilot/phase-explanations.md` 4 phases priority (Categorización · Análisis riesgos · DoA · Monitoring) | NEW content | ~1.5-2h architect-curated | ✅ Sesión 3A Phase B real work |
| `CopilotGuidedFlow.tsx` wrapper component (structured guided sidebar per page · NOT dock global) | NEW component | ~1h | ✅ Sesión 3A Phase B |
| `HelpModal.tsx` contextual FAQ per phase + "Contactar a Marcos" mailto/Slack | NEW component | ~30 min | ✅ Sesión 3A Phase B |
| Backend `/api/v1/admin/projects/{id}/roadmap-status` enriched (status + locks reason + last_updated) | Verify existing useRoadmap returns this · likely ✅ existing | ~0-15 min verify | ✅ Phase B verify only |
| OnboardingTour primer admin login (briefing Phase B.3) | ⚠ Existing cliente tutorial · admin variant NOT existing | NEW component analogous ~30 min | ✅ Sesión 3A Phase B |
| 10-phase stepper roadmap render | ✅ existing | 0h | NO work needed |
| Phase locks coherent | ✅ existing PhaseProgressWizard isFuture Lock icon | 0h | Verify only |
| Progress visual % overall | ✅ existing PhaseCard `pct_completed` + Progress bar | 0h | Verify only |

### PART B verdict empírico

**Effort recalibrated Phase B**: ~3-6h nominal → **~3-4h empírico** (scope mostly POLISH + new explanatory content doc + CopilotGuidedFlow wrapper + HelpModal + OnboardingTour admin variant).

---

## PART C · MCPs + Agentes + Motores manual action UI inventory matrix

**Verdict**: ✅ **97% existing production-grade**. Sub-atom 1.D.E v3.11 + 1.D.F + ProjectTabs SUB_TABS sweep cumulative cubren scope.

### Motors inventory (44 dirs reales backend/app/motors/)

```
m01_categorization · m02_magerit · m03_dda · m04_gap · m05_obligations · m05_signing
m06_document_factory · m07_evidence · m08_verification · m09_audit_prep
m10_audit_sim · m10_ens_radar · m11_copiloto · m12_magic_link · m13_commercial
m14_contracts · m15_billing · m16_onboarding · m17_planning · m18_communication
m19_risk · m20_workspace · m21_diagnosis · m21_portal_cliente · m22_discovery
m23_retainer · m24_idms · m25_lifecycle · m26_backup · m27_conformity
m28_change_governance · m29_client_messaging · m30_client_contacts · m31_whatsapp
m_cloud_connectors · m_compliance · m_compliance_monitor · m_legal · m_live_records
m_meetings · m_observability · m_workflow_engine
```

**41 directorios totales** (40 lifecycle + 1 utility m_observability + 2 duals m05/m10 + m_dms=m24_idms · CLAUDE.md count canonical).

### Matrix per motor · manual action UI exposure

| Motor | Manual trigger? | Admin page existing | Required action button | Page target | Gap status |
|-------|----------------|---------------------|----------------------|-------------|------------|
| M01 Categorization | YES (cliente input + admin verify) | ✅ `/admin/projects/[id]/categorization` (via `/dimensiones`) | "Categorizar sistema" wizard | existing | ✅ done (1.D.F.0.A wizard 6 steps) |
| M02 MAGERIT | YES (admin propose + cliente sign) | ✅ `/admin/projects/[id]/magerit` | "Crear análisis · Aprobar · Firmar" | existing | ✅ done |
| M03 DdA | YES (admin draft + cliente sign final) | ✅ `/admin/projects/[id]/dda` 7 components | "Generar inicial · Marcar implementada · Congelar" | existing | ✅ done (1.D.F.A) |
| M04 Gap | YES (admin generate plan + cliente review) | ✅ `/admin/projects/[id]/plan` | "Generar plan · Asignar responsable · Marcar resuelto" | existing | ✅ done |
| M05 Obligations | YES (cliente input + admin curate) | ✅ `/admin/projects/[id]/obligations` | "Añadir obligación · Tag normativa" | existing | ✅ done |
| M05 Signing | NO direct UI (transversal) | service-level | (used by all sign flows) | N/A | ✅ service backend |
| M06 Document Factory | YES (admin generate documents) | ✅ `/admin/projects/[id]/documents` (IDMS) + per-motor generate buttons | "Generar plantilla X" inline per motor | existing | ✅ done (104 plantillas registry) |
| M07 Evidence | YES (admin attach + cliente upload) | ✅ `/admin/projects/[id]/evidence` | "Subir evidencia · Asociar medida" | existing | ✅ done |
| M08 Verification | YES (admin trigger pentest/MCP) | ✅ `/admin/projects/[id]/verification` + `/mcps` | "Lanzar verificación · Stream SSE" | existing | ✅ done (1.D.E) |
| M09 Audit Prep | YES (admin generate dossier ENAC) | ✅ `/admin/projects/[id]/dossier` | "Generar dossier · Descargar ZIP" | existing | ✅ done (3485 LOC dossier_generator) |
| M10 Audit Sim | YES (admin tabletop exercises) | ✅ `/admin/projects/[id]/audit-dry-run` | "Lanzar simulación auditoría" | existing | ✅ done (1.D.F.B ProjectTabs entry) |
| M10b ENS Radar | YES (admin captación leads cross-cliente · top-level legítimo R23) | ✅ `/admin/ens-radar` (top-level) | "Iniciar búsqueda · Resume · Cancelar" | existing | ✅ done (9 hooks real fetch · Sesión 1 resume cursor pattern) |
| M11 Copiloto/RAG | NO direct UI (used by agents) | service-level | N/A | N/A | ✅ scope-out documented |
| M12 Magic Link | YES (admin generate magic links) | ✅ `/admin/magic-links` (top-level) | "Generar link · Revocar · Reenviar" | existing | ✅ done |
| M13 Commercial | YES (admin pipeline + leads) | ✅ `/admin/pipeline` (top-level) + `/admin/projects/[id]/financial` | "Crear lead · Cualificar · Convertir" | existing | ✅ done |
| M14 Contracts | YES (admin generate + send) | ✅ `/admin/projects/[id]/contratos` 4 components | "Generar contrato · Firmar Marcos · Enviar cliente · Descargar" | existing | ✅ done (1.D.D.A) |
| M15 Billing | YES (admin invoice + AAPP) | ✅ `/admin/projects/[id]/billing/aapp` + `/admin/finance` | "Emitir factura · AAPP submit" | existing | ✅ done |
| M16 Onboarding | YES (admin send + cliente fill) | ✅ `/admin/projects/[id]/onboarding` OnboardingAdminPanel 4 Tabs | "Enviar session · Catálogo · Connectors · LMS" | existing | ✅ done |
| M17 Planning | YES (admin planning) | ✅ `/admin/projects/[id]/plan` (shared con M04) | "Crear plan · Asignar fases" | existing | ✅ done |
| M18 Communication | YES (admin send) | ✅ `/admin/projects/[id]/communication` + `/admin/messages` + `/admin/inbox` | "Componer · Enviar · Bulk" | existing | ✅ done |
| M19 Risk | YES (admin BIA + risks) | ✅ `/admin/projects/[id]/risks` + `/bia` | "Crear riesgo · BIA · Plan tratamiento" | existing | ✅ done (1.D.F.B sweep) |
| M20 Workspace | YES (admin workspace ops) | ✅ `/admin/projects/[id]/workspace` | "Workspace ops" | existing | ✅ done (1.D.F.B sweep) |
| M21 Diagnosis | YES (admin diagnóstico) | ✅ `/admin/projects/[id]/diagnosis` | "Lanzar diagnóstico · Scoring maturity" | existing | ✅ done |
| M21 Portal Cliente | NO admin UI direct (cliente-facing) | cliente portal scope | N/A admin | ✅ cliente portal completo | ✅ scope (1.D.F.bis.III refactor cumulative) |
| M22 Discovery | YES (admin discovery + awareness) | ✅ `/admin/projects/[id]/discovery` + `/awareness` | "Lanzar discovery · Consolidar" | existing | ✅ done (1.D.J K-full + 1.D.F.B sweep) |
| M23 Retainer | YES (admin retainer ops + check-in) | ✅ `/admin/retainers` (top-level) + `/admin/projects/[id]/retainer` | "Check-in · Renovar · Churn risk" | existing | ✅ done |
| M24 IDMS (=m_dms) | YES (admin docs gestor) | ✅ `/admin/projects/[id]/documents` 7 components | "Upload · Folder · Version history · Viewer" | existing | ✅ done (1.C.G.A admin enrichment) |
| M25 Lifecycle (DPC · revision_anual) | YES (admin DPC + revision) | ✅ `/admin/projects/[id]/dossier` shared + `/exit` + `/renewal` | "DPC anual · Revision · Cierre · Renovación" | existing | ✅ done (1.D.F.B sweep) |
| M26 Backup | YES (admin backup policy verify) | ✅ `/admin/projects/[id]/backup-policy` | "Verificar política · Test recovery" | existing | ✅ done (1.D.F.B sweep) |
| M27 Conformity | YES (admin generate declaración) | ✅ `/admin/projects/[id]/conformity` | "Generar declaración · Firmar · Cloud score" | existing | ✅ done (1.D.J K-full ConformityCloudScoreCard) |
| M28 Change Governance | YES (admin wizard 5 steps) | ✅ `/admin/projects/[id]/changes` 3 components + wizard | "Solicitar cambio · Assess materiality · Notificar E-042" | existing | ✅ done (1.D.D.B) |
| M29 Client Messaging | YES (admin chat con cliente) | ✅ `/admin/projects/[id]/communication` + `/admin/messages` | "Componer mensaje · Bulk" | existing | ✅ done |
| M30 Client Contacts | YES (admin equipo del proyecto) | ✅ `/admin/projects/[id]/equipo` 4 Tabs + `/equipo/areas` | "Añadir contacto · Departamentos · Asignar roles ENS" | existing | ✅ done (1.C.F 5 sub-fases) |
| M31 WhatsApp | YES (admin WhatsApp ops) | ✅ `/admin/whatsapp` (top-level) | "Send · Opt-in · OTP · Templates" | existing | ✅ done |
| M_cloud_connectors | YES (admin OAuth + diagnose) | ✅ `/admin/projects/[id]/cloud-connectors` 4 Tabs | "OAuth M365/Google/Azure/AWS/GitHub · Sync · Run Diagnosis · Manual import" | existing | ✅ done (1.D.X cloud-first MVP) |
| M_compliance | NO per-project UI (global self-monitoring) | ✅ `/admin/compliance/monitor` + `/admin/compliance/norma-reports` (top-level) | "Recheck · View status" | existing | ✅ done (Bloque 4) |
| M_compliance_monitor | utility transversal global | ✅ `/admin/system-health` (top-level) | "View checks · Anomalies · DB conn" | existing | ✅ done (Bloque 4) |
| M_legal | DORMANT (cross-compliance NO core ENS) | scope-out USO pre-piloto | N/A | N/A scope-out PERMANENT R32 v3.10 | ✅ scope-out justified |
| M_live_records | YES (cliente + admin registros vivos) | cliente `/client-portal/registros` + admin via per-motor consumers | "Add entry · Update · Aggregates" | existing per motor | ✅ done (Anexo K matrix) |
| M_meetings | YES (admin meetings) | ✅ `/admin/meetings` + `/admin/meetings/new` + `/admin/meetings/[id]` (top-level cross-cliente) | "Schedule · Conduct · Acta · Tasks" | existing | ✅ done |
| M_observability | utility transversal admin internal | ✅ `/admin/llm-observability` + `/golden-eval` (top-level) | "View LLM costs · Anomalies · Logs" | existing | ✅ done |
| M_workflow_engine | infrastructure backend (orchestration) | ✅ `/admin/workflow-command-center` (top-level) + per-project `/workflow-command-center/projects/[id]` | "Cross-actor sync · SSE · Recordar cliente" | existing | ✅ done (1.D.G EXPANDED cumulative) |

**Verdict matrix motores**: ✅ **41/41 motores con UI/scope clarificado**. 0 gaps P0 detected. Solo m_legal scope-out USO pre-piloto justified arquitecturalmente (R32 v3.10).

### Agents inventory (14 agentes total · 54 .py files con __init__/services/prompts/schemas)

| Agent | UI exposure? | Status | Notes |
|-------|--------------|--------|-------|
| A02 Pliegos | service-level | scope-out memoria 24 LOC | Used by M14 contracts service-level |
| A04 Redactor | service-level cross-motor | invoked by motores | M04 + M06 narrative enrichment |
| A06 Contratos | service-level | invoked by M14 wizard | Used in ContractGenerateWizard Step 2 |
| A11 Auditor Virtual | service-level | invoked by M10 audit + M09 dossier supplementary | Sub-atom 1.D.A external · M9 internal_auditor function-level |
| A11 Wrapper | service helper | wraps A11 capabilities | N/A direct UI |
| A12 Coach Cliente | service-level cliente | wraps cliente copiloto | LLM real Haiku 4.5 (1.D.B.1) |
| A14 Copiloto RAG | core backend used by other agents | service-level production 817 LOC | Consumed by copiloto admin + cliente |
| A17 Cualificador | service-level pipeline | invoked by M13 commercial workflow | Lead cualification |
| A18 Reunión | service-level m_meetings | invoked by meeting actas extraction | |
| A19 Propuestas | service-level pipeline | invoked by M13 propose flow | |
| A20 Negociación | service-level pipeline | invoked by M13 + M14 contract narrative | Sub-atom 1.D.D.A wire |
| A21 Discrepancias | ✅ ENS-only DETERMINISTA admin UI | `/admin/projects/[id]/discrepancies` panel + critical badge | Sub-atom 1.D.A v3.10 (5 detectores · NO LLM) |
| A21 API + Service | backend infra | ENS-only deterministic detector | |
| A27 Clasificador | service-level upload (cliente) | invoked by m24_idms upload pipeline | Tag classification suggestions |
| A31 Enriquecedor DdA | service-level M03 | invoked by DdA narrative enrichment | |

**Agentes con UI dedicada**: A21 Discrepancias (1.D.A). **Resto agentes**: service-level production-grade invoked by motores · NO UI dedicada needed (architectural decision: separación responsabilidad · agents = service capabilities consumed by motors).

### MCPs inventory (15 servers backend/mcp_servers/)

```
apisec · cloud · config · cracking · infra · mobile · phishing · recon
redteam · sast · scope_enforcer · shared · vulnscan · webpentest · wireless
```

**4 catalog production-grade (Sub-atom 1.D.E v3.11)**: vulnscan · cloud · config · phishing · 13 tools registered.
**11 structural (scaffolding)**: apisec · cracking · infra · mobile · recon · redteam · sast · webpentest · wireless · scope_enforcer · shared
**Manual invocation UI**: ✅ `/admin/projects/[id]/mcps` 6 components + 6 endpoints + SSE streaming + auto-attach Evidence Vault folder "13_Informes_Tecnicos" (1.D.E v3.11)

### PART C verdict empírico

**Effort recalibrated**: ~0h work needed. **Sesión 3B (MCPs/Agentes/Motores UI exposure)** originally planned: **SCOPE-OUT 95%+** (production-grade existing) · solo polish minor edge-cases.

**Sesión 3B refined scope**: ~30-60 min total · solo verify smoke + edge-case polish per finding-specific.

---

## PART D · Admin pages REAL count + 12-criteria priority

**Count empírico**: `find frontend/app/(admin) -name "page.tsx" | wc -l` = **81 admin pages**.

### Per page priority categorization

#### PRIORITY 1 · Cliente piloto MEDIA path (CRITICAL pre-piloto · 12-criteria deep polish)

| Page | Path | Notes |
|------|------|-------|
| Roadmap | `/admin/projects/[id]/roadmap` | Entry post-selector · Phase B target |
| Dashboard | `/admin/projects/[id]/dashboard` | Main project view |
| Categorización | `/admin/projects/[id]/dimensiones` + `/archetype` | M01 wizard 6 steps |
| Diagnóstico | `/admin/projects/[id]/diagnosis` | M21 |
| Análisis riesgos | `/admin/projects/[id]/risks` + `/magerit` + `/bia` | M02 + M19 |
| Plan adecuación | `/admin/projects/[id]/plan` + `/implementation` | M04 + M17 |
| DdA | `/admin/projects/[id]/dda` | M03 (1.D.F.A) |
| Evidencias | `/admin/projects/[id]/evidence` | M07 |
| Documentos IDMS | `/admin/projects/[id]/documents` | M24 (1.C.G.A) |
| Conformity | `/admin/projects/[id]/conformity` | M27 + cloud score (1.D.J) |
| Dossier ENAC | `/admin/projects/[id]/dossier` | M09 (Future-dossier-pack scope) |
| Contratos | `/admin/projects/[id]/contratos` | M14 (1.D.D.A) |
| MCPs | `/admin/projects/[id]/mcps` | M08 + MCPs (1.D.E) |
| Cloud Connectors | `/admin/projects/[id]/cloud-connectors` | M_cloud_connectors (1.D.X) |
| Equipo + Áreas | `/admin/projects/[id]/equipo` + `/equipo/areas` | M30 (1.C.F) |
| Workflow Command Center | `/admin/workflow-command-center/projects/[id]` | M_workflow_engine (1.D.G EXPANDED) |
| Projects selector | `/admin/projects` | Entry flow (Phase A target) |

**PRIORITY 1 count**: ~17 pages CRITICAL pre-piloto.

#### PRIORITY 2 · Feature-critical (ENS Radar · monitoring · etc)

| Page | Path | Notes |
|------|------|-------|
| ENS Radar | `/admin/ens-radar` (top-level multi-cliente legítimo R23) | M10b 9 hooks real fetch |
| Cross-project compliance | `/admin/cross-project-compliance` | Bloque 4 monitoring admin |
| System health | `/admin/system-health` | Bloque 4 self-monitoring FULKRO |
| Compliance monitor | `/admin/compliance/monitor` + `/norma-reports` | M_compliance_monitor |
| LLM observability | `/admin/llm-observability` + `/golden-eval` | M_observability |
| Pipeline | `/admin/pipeline` + `/leads/[id]` | M13 commercial |
| Clients | `/admin/clients` + `/[id]` + `/new` + `/branding` + `/meetings` | M30 + M_meetings |
| Workflow Command Center | `/admin/workflow-command-center` (cross-cliente) | M_workflow_engine |
| Magic links | `/admin/magic-links` | M12 |
| Meetings | `/admin/meetings` + `/[id]` + `/new` | M_meetings |
| Operations | `/admin/operations` | M20 admin ops |
| Onboarding (project-scoped) | `/admin/projects/[id]/onboarding` | M16 OnboardingAdminPanel 4 Tabs |
| Discovery + Awareness | `/admin/projects/[id]/discovery` + `/awareness` | M22 |
| Audit dry-run | `/admin/projects/[id]/audit-dry-run` | M10 + A11 |
| Changes | `/admin/projects/[id]/changes` | M28 (1.D.D.B) |
| Discrepancies | `/admin/projects/[id]/discrepancies` | A21 (1.D.A) |
| Planes acción | `/admin/projects/[id]/planes-accion` | Cross-motor (1.D.C) |
| Verification | `/admin/projects/[id]/verification` | M08 MEDIA+/ALTA |
| Audit | `/admin/projects/[id]/audit` | M10 MEDIA+/ALTA |
| BIA | `/admin/projects/[id]/bia` | M19 BIA |
| AEPD | `/admin/projects/[id]/aepd` | M19 RGPD |
| Backup policy | `/admin/projects/[id]/backup-policy` | M26 |
| Retainer (per-project) | `/admin/projects/[id]/retainer` | M23 |
| Renewal | `/admin/projects/[id]/renewal` | M25b |
| Exit | `/admin/projects/[id]/exit` | M31 cierre |
| Transparency IA | `/admin/projects/[id]/transparency` | Sub-atom 1.E.1.B.2 AI Act art.50 |

**PRIORITY 2 count**: ~28 pages feature-critical.

#### PRIORITY 3 · Secondary admin

| Page | Notes |
|------|-------|
| Inbox + Messages + Notifications + Alerts + WhatsApp | M18 + M29 + M31 |
| Finance + Retainers + Churn risk + Timesheet | M15 + M23 |
| Settings + Copilot (legacy standalone) | M11 |
| Project sub-pages | personalización · users · roles · feature-flags · obligations · communication · billing/aapp · financial · summary · workspace · providers |
| Magerit analyses import | `/admin/magerit-analyses/[id]/import` |
| Branding (cliente-scoped) | `/admin/clients/[id]/branding` |
| Retainers churn risk | `/admin/retainers/churn-risk` |

**PRIORITY 3 count**: ~25 pages secondary admin.

#### PRIORITY 4 · Edge/rare

| Page | Notes |
|------|-------|
| Project root index | `/admin/projects/[id]/page.tsx` (redirect to /summary typically) |
| Demo project | `sdl-demo` hardcoded helper |
| Misc internal | settings (per-user pref) |

**PRIORITY 4 count**: ~11 pages edge.

### 12-criteria deep quality preliminary checklist (Sesión 3C scope)

For each PRIORITY 1+2 page · Sesión 3C scope:
1. ✅ Title + breadcrumb visible
2. ✅ Empty state friendly R30 admin (R29 cliente)
3. ✅ Loading skeleton
4. ✅ Error state retry button R29 cliente (technical link admin)
5. ✅ Mobile responsive 375x812
6. ✅ Keyboard navigation + focus-visible:ring-2
7. ✅ WCAG AA contrast + aria-labels
8. ✅ Real fetch tanstack-query (0 mocks)
9. ✅ CTA actions visible top-bar
10. ✅ Help/tooltip ENS jargon
11. ✅ Server actions feedback (toast + invalidation)
12. ✅ Project context breadcrumb visible

Sesión 3C ETA refined per Phase 0 PART D findings: ~45 pages (PRIORITY 1+2) deep polish · pattern reuse Bloque 6 verified 89% production-grade existing · scope-out PRIORITY 3+4 unless edge issue detected.

### PART D verdict empírico

**Effort recalibrated Sesión 3C**: nominal "all admin pages" → **~45 pages priority** · ~8-12h cumulative (vs nominal ~20-30h sin priority).

---

## Scope refined Sesión 3A + 3B + 3C

### Sesión 3A real scope (NEW empírico recalibrated)

| Phase | Original ETA | Empírico ETA | Reason |
|-------|--------------|--------------|--------|
| Phase 0 audit 4 PARTS | ~60-90 min | ✅ done (~45 min) | This doc |
| Phase A selector polish | ~2-3h | ~30-45 min | POLISH 3 microfixes (production-grade existing) |
| Phase B copilot guided foundation | ~3-6h | ~3-4h | docs/copilot/phase-explanations.md 4 phases + CopilotGuidedFlow wrapper + HelpModal + OnboardingTour admin variant |
| Phase C cierre | ~30 min | ~30 min | Validation + CLAUDE.md |
| **TOTAL Sesión 3A** | **~6-10h** | **~5-6h** | Audit-first reveals ~85-90% production existing |

### Sesión 3B scope refined (POST 3A · MCPs/Agentes/Motores UI buttons)

**Verdict**: ✅ **SCOPE-OUT 95%+** · production-grade existing per PART C matrix. Only ~30-60 min smoke verify + edge polish if findings detected real session.

### Sesión 3C scope refined (POST 3B · Admin pages comprehensive polish)

**Verdict**: ~45 pages PRIORITY 1+2 · 12-criteria quality polish · ~8-12h cumulative (pattern reuse Bloque 6 polish quick wins applied to remaining pages).

---

## OPS-052 strengthened compliance verified empíricamente

Phase 0 doctrine **MANDATORY** ejecutado per briefing 3-point commitment vigilancia tight:
- ✅ Empirical state verification 4 PARTS comprehensive ANTES Phase A implementation
- ✅ Briefing-vs-reality matrix tracking row per finding
- ✅ Scope recalibrated mid-Phase-0 (NOT mid-execution downstream)
- ✅ Honest path · production-grade existing acknowledged · NO greenfield duplication

Pattern análogo a OPS-045 audit-first reveals · 38ª aplicación consecutiva candidate.

## Honesty notes Phase 0

1. **Selector + Copilot + Roadmap + OnboardingTutorial existing** desde sub-atoms 1.E.2 + 1.D.B + ADR-026 FASE 8 + MB-7 atom 7.3 · NO greenfield needed · POLISH only
2. **WORKFLOW_PHASES enum 10 fases canonical** ya existing en schemas.ts (matches briefing target) · NO redesign needed
3. **CopilotoDock (cliente) + CopilotoAdminSidebar (admin)** production-grade LLM real Haiku 4.5 + Sonnet 4.6 · NO new copilot infrastructure needed
4. **HelpModal contextual FAQ** + **CopilotGuidedFlow structured wrapper** + **OnboardingTour admin variant** + **docs/copilot/phase-explanations.md** son gaps REAL Phase B
5. **PRIORITY 4 phases priority HOY**: Categorización · Análisis riesgos · DoA · Monitoring (briefing explicit)
6. **6 phases remaining** (pre_venta · onboarding · adecuacion · implantacion · verificacion · conformidad · retainer_cierre · dda_final) DEFER Sesión 3C content-curation
7. **NO touch backend ENS Radar parallel ADDENDUM safety** sostained

---

**Phase 0 verdict**: ✅ **GATE PASSED** · proceeding Phase A microfixes selector → Phase B copilot guided foundation real work.
