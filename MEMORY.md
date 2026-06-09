# FULKRO · Memoria operativa de sprint

> Anchor persistent del estado del proyecto a través de Sprint Polish Máximo (9 blocks consecutivos).
> Actualizado al cierre de cada block. Recogemos solo lo no derivable del código/git.

---

## Estado actual

**Fecha**: 2026-05-13
**Branch HEAD**: `71fba1f` (Atom 10.6.C beat schedule) · closure + tag próximo commit
**Sprint en curso**: Sprint Polish Máximo · 9 blocks
**Blocks cerrados**: 1 (`e496b55`) + 2 ajustado (`659c633` + `d14579d` + `aa6ee7e`) + 3 minimal (`811c404`) + 4 Aplus-final (`0022ddb`) + 5 Fix2 (`939d0e6`) + 6 PATH 2 audit-driven (`eca2e1a`)
**MB-10 ENTERO CERRADO** (tag `s14-mb10-cerrada` aplicado este closure):
- ✅ Atom 10.0 ADR-046 + Q5.3 cement (`05b2ec9` · capability vs feature_flag · OPS-026 28ª · M32 LOGICAL preserved ISMS docs · renamed post-audit B1.2 · was ADR-037 MB-10)
- ✅ Atom 10.1 m_compliance_monitor polish (`94c3e52` + `0fd12a8` · 17 → 19 checks)
- ✅ Atom 10.2 feature_flag_overrides materialization (5 sub-atoms · ADR-036 deferred materializado · ~3-4h · 40% savings · 46 tests pass)
- ✅ Atom 10.3 admin UI overrides management (4 sub-atoms · OPS-026 29ª · 5/5 E2E PASS · ~1.5-2h)
- ⛔ Atom 10.4 SKIP (Q5.3 cement INVISIBLE cliente applied per ADR-046)
- ⛔ Atom 10.5 DEFER ADR-047 (`d63d579` · Intelligence cross-motor distributed pattern · 22 agents + 8+ dashboards + LLM router existing · OPS-026 30ª · OPS-061 3ª vez · OPS-062 NEW · renamed post-audit B1.2 · was ADR-042 MB-10)
- ✅ Atom 10.6 Backups encrypted + offsite (`52dc46f` ADR-048 + `8566b0a` + `99cdeb5` + `71fba1f` · 4 sub-atoms + ADR · Fernet encryption + MinIO offsite bucket-vault-fulkro + beat verify/restore · ISMS commitments honored literal · MB-11 Hetzner cutover DEFER · OPS-026 31ª · OPS-062 2da vez · 19/19 tests PASS · ~2.5h efectivo · renamed post-audit B1.2 · was ADR-043 MB-10)

**MB-10 cumulative**: ~8-10h efectivo vs 19-29h original · **~55-65% savings audit-driven** · 3 ADRs new (046 · 047 · 048 · renamed post-B1.2) · 19+ OPS validated · 2 NEW (OPS-061 + OPS-062)

**FASE 2 cumulative en curso** (post FASE 1 BLOQUEANTES cerrados):
- H2 CANCEL audit-driven · ADR-049 NEW (3 surfaces architectural intent · NO duplicate) + ADR-050 NEW (Copilot guided mode visión Marcos DEFER MB-14 polish bloque mayor · ~25-45h cumulative dedicated post FASE 2 + Blocks 7-9) · OPS-061 5ª aplicación cumulative
- H1 · workflow_state.py 52K refactor (~2-3h MAJOR cabeza fresca) ⏸
- H3 CANCEL audit-driven · ADR-051 NEW (2 surfaces architectural intent · NO duplicate · `firma/` página explicativa legal ADR-010 + C-001 URL literal contractual · `firmas-hub/` hub operativo MB-6 atom 0.2 backend API) · OPS-061 6ª aplicación cumulative · OPS-026 36ª aplicación
- H7 COMPLETE · 37 READMEs cumulative (H7.A 9 + H7.B 12 + H7.C 12 + H7.D 4) · 113.981 LOC institutional documented · 7 HUBS topology empirical descubierta · OPS-026 38ª/39ª/40ª/41ª
- H1 workflow_state refactor · 52K monolith → 5 modular files (phase + items + signals + views + __init__) · 58/58 tests PASS · backward compat 100% via __init__.py re-export · OPS-026 42ª
- H4 dashboard wire-up real + refinement · 4 endpoints REST cross-motor aggregator + M19/M21 sources · OPS-026 43ª/44ª · 8/8 tests PASS
- H5 CANCEL audit-driven · ADR-052 NEW (Copilot SSE streaming wire-up YA implementado 100% · audit cita endpoint path `/agents/14/invoke` que NUNCA fue real · path empírico `/api/v1/copilot/chat/stream` M11 wrapper per ADR-049 3 surfaces architectural · DevHint stale removed) · OPS-061 7ª aplicación cumulative · OPS-026 45ª aplicación
- H4 · Dashboard backend wire-up simple (~2-3h · NOT guided) ⏸
- H5 · Copilot streaming SSE wire-up simple (~2-3h · NOT guided) ⏸
- H6 · litellm cleanup deps (~30 min) ⏸
- H7 · per-motor READMEs 37 motors (~2-3h) ⏸
Tag forward · `s14-mb10-high-priority-cerrada` (post H1-H7 cumulative)

**Próximo paso**: Blocks 7-9 sprint closure POST-MB-10 (~4-6h · cement Marcos literal sequence sostained):
- Block 7 Documentation gaps (~1-2h)
- Block 8 Production-readiness docs (~2-3h)
- Block 9 V-CHECK FINAL + tag `s14-polish-maximo-cerrada` (~1h)

## Tags acumulados de sesión 14 (s14)

| Tag | Cierre | Descripción |
|-----|--------|-------------|
| s14-mb1-auth-cerrada | — | MB-1 Auth |
| s14-mb2-tooltips-cerrada | — | MB-2 Tooltips |
| s14-mb3-placeholders-cerrada | — | MB-3 Placeholders |
| s14-mb3-m21-single-user-rw-cerrada | — | MB-3 M21 single user |
| s14-mb4-motors-ui-cerrada | — | MB-4 Motors UI |
| s14-mb5-core-ens-cerrada | — | MB-5 Core ENS |
| s14-mb6-truly-zero-debt-final | — | MB-6 truly zero debt final |
| s14-mb6-truly-complete-perfect | — | MB-6 truly complete |
| s14-mb6-operativo-continuo-production-validated | — | MB-6 operativo continuo |
| s14-mb7-0-drift-cleanup-partial | — | MB-7.0 drift cleanup partial |
| s14-mb7-0-drift-cleanup-extended | — | MB-7.0 drift cleanup extended |
| s14-mb7-truly-complete-perfect | — | MB-7 truly complete |
| s14-mb7-bis-retainer-ops-cerrada | — | MB-7.bis Retainer OPS |
| s14-mb7-dashboard-copiloto-cerrada | — | MB-7 Dashboard CopilotoDock |
| s14-mb8-whatsapp-email-cerrada | — | MB-8 WhatsApp + Email |
| s14-mb9-per-cliente-cerrada | — | MB-9 Per-cliente branding |
| **s14-mb9-bis-multi-norma-cerrada** | **2026-05-12 (Block 1)** | **MB-9.bis CIERRE · 14 docs production-grade + Inventory.xlsx** |
| **s14-polish-admin-microfixes-cerrada** | **2026-05-12 (Block 2 ajustado)** | **QuickActions refactor + SSE hook DRY · 2 commits · 2 diferidos** |
| **s14-magic-links-migration-cerrada** | **2026-05-12 (Block 3 minimal)** | **96 % cumplido previamente (ADR-042 + ADR-020 v3) · cleanup minimal 4 email configs deleted** |
| **s14-rls-hardening-cerrada** | **2026-05-12 (Block 4 Aplus-final)** | **1 table RLS apply (email_log defense-in-depth) · MB-9 atom 9.3 HONORED · OPS-054 cement table owner membership fix · 61.1 % coverage** |
| **s14-validation-infra-cerrada** | **2026-05-12 (Block 5 Fix2)** | **E2E SMOKE 94.4% + Full 188/266 · Fix1 tutorial + Fix2 context.request + OPS-056 freshness + OPS-057 proactive cement** |
| **s14-redis-caching-cerrada** | **2026-05-12 (Block 6 PATH 2)** | **No-op audit-driven · Redis service YA exists docker-compose + 18 LRU vs 5 asumido · MB-12 batch coherent · OPS-058 NEW cement** |
| _MB-10 atoms intra (NO tag intra)_ | _2026-05-13_ | _10.0-10.6 progress · tag final s14-mb10-cerrada cumulative_ |
| **s14-mb10-cerrada** | **2026-05-13 (MB-10 entero)** | **MB-10 perfecto entero cerrado cement Marcos literal honored · 5 atoms BUILT (10.0 ADR-046 + 10.1 monitor 17→19 + 10.2 ff_overrides 5 sub + 10.3 admin UI + 10.6 backups encrypted) + 2 cement decisions (10.4 SKIP Q5.3 · 10.5 DEFER ADR-047) · 3 ADRs new (046 capability vs feature_flag · 047 Intelligence distributed · 048 backup encryption strategy · all renamed post-audit B1.2 · were 037/042/043 MB-10 originally) · ~8-10h efectivo vs 19-29h original = ~55-65% savings audit-driven · 19+ OPS validated cumulative · 2 NEW (OPS-061 vaporware detection · OPS-062 DEFER architectural with ADR explicit)** |
| **s14-mb10-bloqueantes-cerrada** | **2026-05-13 (FASE 1 post-audit)** | **B1.1 _dev/ env-gated CASE A production-safe empirical confirmed (doble defensa Layer 1 main.py + Layer 2 per-endpoint 10/10 coverage) · B1.2 ADR collisions resolved (037→046 · 042→047 · 043→048) · OPS-063 NEW cement (pre-audit ADR grep mandatory 3 paths)** |
| _FASE 2 H2 atom intra (NO tag intra)_ | _2026-05-13_ | _H2 CANCEL audit-driven · ADR-049 + ADR-050 NEW · OPS-061 5ª aplicación · tag final s14-mb10-high-priority-cerrada post H1-H7 cumulative_ |
| _FASE 2 H3 atom intra (NO tag intra)_ | _2026-05-13_ | _H3 CANCEL audit-driven · ADR-051 NEW (firma/ legal disclosure + firmas-hub/ operativo MB-6 · 2 surfaces distinct intent) · OPS-061 6ª aplicación cumulative (7 instancias) · OPS-026 36ª aplicación · tag final s14-mb10-high-priority-cerrada post H1-H7 cumulative_ |
| _FASE 2 H7+H1+H4+H5 atoms intra (NO tag intra)_ | _2026-05-13_ | _H7 COMPLETE 37 READMEs (4 sub-atoms cumulative) · H1 workflow_state 52K modular refactor · H4 dashboard wire-up + refinement (2 commits) · H5 CANCEL audit-driven ADR-052 NEW (Copilot SSE wire-up YA real existing · OPS-061 7ª aplicación 8 instancias) · OPS-026 38ª-45ª (8 aplicaciones cumulative) · tag final s14-mb10-high-priority-cerrada FASE 2 CERRADA_ |

## LECCIONES-OPS acumuladas

| ID | Lección | Origen |
|----|---------|--------|
| OPS-024 | Atomic commits per concern (1 commit = 1 concepto) | MB-6 cleanup |
| OPS-026 | Audit-first antes de cambios con riesgo (investigación → reporte → decisión → ejecución) | MB-6 RLS |
| OPS-034 | Atom-per-motor pacing en refactors cross-cutting | MB-7 magic links |
| OPS-046 | NO-blocker pattern para compliance sidebar (passive badge slate · no modal popup) | MB-9 sidebar compliance |
| OPS-047 | Sprint Polish Máximo bloque-por-bloque con V-CHECK + tag entre blocks · NO continuous blind | Sprint plan v1 |
| OPS-048 | Honest effort estimation cement: Write tool parallel batching ~2-3h vs serial 3-4h | Block 1 cement |
| OPS-049 | UNC path WSL Write tool validated: `\\wsl.localhost\Ubuntu\...` sin heredocs nested | Block 1 cement |
| OPS-050 | Audit-driven scope adjustment: defer sub-atoms con gap mayor en lugar de inflar block. Cementación cumulativa 4ª vez en Block 3 (audit revela 96% trabajo cumplido por ADR-042 + ADR-020 v3) · regla forward: SIEMPRE audit pre-ejecución antes de comprometer effort para cualquier block del plan v6 | Block 2 + Block 3 (cement 4ª vez) |
| OPS-051 | Duplicate inline pattern (2x literal) signals hook extraction opportunity (DRY) | Block 2 cement (SSE hook) |
| OPS-052 | Test invariante post-cleanup: cuando se elimina código que un test iteraba, el test debe documentar el contrato post-cleanup (e.g. `pytest.raises(ValueError)` en lieu of removing the iteration). Preserve test count · evolve contract. | Block 3 cement (test_all_purposes_render_without_error update) |
| OPS-053 | Honest target metrics: plan v6 70% RLS target inflated · empirical ceiling sin user-scoped + cross-cutting auth setting = ~61%. Honest metrics > inflated plan v6 systematic. | Block 4 cement 2ª vez |
| OPS-054 | Table owner membership inheritance bypass RLS: si role A es miembro de role B (table owner), inherits RLS bypass. Fix: ALTER TABLE OWNER TO fulkro_migrate (no-superuser, no-member-of-fulkro_app). Verificar owner antes de cada ENABLE RLS forward. | Block 4 cement NEW (email_log fix) |
| OPS-056 | Backend freshness check OBLIGATORIO step 0 pre-smoke/E2E: verificar `ps -o lstart= -p <pid>` + `find code -newer /proc/<pid>`. NO accept HTTP 200 health como freshness proof. Stale uvicorn 20h sirve código antiguo sin routers actuales (falsos negativos masivos). | Block 5 cement NEW (1.5h debug perdido por regla `feedback_smoke_dev_freshness` ignorada) |
| OPS-057 | Proactive surface cemented memoria rules pre-action step 0. NO accept "recall post-error". Memoria value = 0 si NO actuada proactivamente. Cada audit/smoke arrancar con check de memoria relevant rules + state. | Block 5 cement NEW (self-inflicted lesson) |
| OPS-058 | Product-perfect vs spec-perfect distinción: cuando audit reveal scope mismatch (asumido vs real >2×), defer al batch coherent y document refined plan. NO force literal plan adherence si el atom no es scope-coherent con work natural. Aplicación: Block 6 Redis → MB-12 production infra batch. | Block 6 cement NEW (Redis MB-12 deferral) |
| OPS-061 | Vaporware path/component/concept detection cumulative pattern: pre-audit revela que conceptos cementados en memoria/cumulative docs (umbrella terms · sprint cement Block N · MEMORY drift) NO tienen spec literal en master plan empirical · NO existen filesystem · NO tienen scope concreto. Pattern detectable 8 instancias cumulative cement: M32 Capabilities (Atom 10.2) · features panel path (Atom 10.3) · Intelligence cross-motor (Atom 10.5) · backup encryption-as-stub (Atom 10.6) · ADR-037/042/043 self-collisions (B1.2 audit-blind numbering) · copilot/copiloto "duplicate" (FASE 2 H2 audit O2 superficial · 3 surfaces distinct intent ADR-049) · firma/firmas-hub "duplicate" (FASE 2 H3 audit O3 superficial · 2 surfaces distinct intent ADR-051 · legal disclosure + operativo MB-6) · copilot streaming wire-up "pendiente" (FASE 2 H5 audit O2/O15 superficial · audit cita path inventado `/agents/14/invoke` que NUNCA fue real · wire-up real `/copilot/chat/stream` M11 wrapper per ADR-049 · ADR-052 cement). Forward rule: SIEMPRE pre-audit empirical filesystem + spec literal verify + semantic distinction check ANTES de comprometer effort para concepto cumulative-memorial. | MB-10 + FASE 1 + FASE 2 cement 7ª aplicación cumulative (8 instancias detected) |
| OPS-062 | DEFER architectural con ADR explicit ≠ silent debt. Cement "0 deuda perfecto" honors:  - DEFER architectural con ADR documenting decision (Intelligence Atom 10.5 ADR-047 · backup infra Atom 10.6.0 ADR-048 = MB-11 Hetzner cutover + MB-12 secrets externalization · ADRs renamed post-audit B1.2 · were 042/043 MB-10 originally) · NO silent.  - NOT BUILD redundant duplication existing infrastructure (anti-pattern).  Forward: cualquier scope DEFER honrar via ADR cement architectural · evita future drift "we deferred this somewhere". | MB-10 Atom 10.5 + 10.6 cement 2 instancias |
| OPS-063 | Pre-audit ADR numbering SIEMPRE grep 3 paths antes de crear `docs/architecture/ADR-NN_*.md` nuevo: (1) `docs/spec/DECISIONS.md` inline ADR-NN entries · 12+ pre-MB-10 incluyendo conflicts ADR-037/042/043 (2) `docs/architecture/ADR-NN_*.md` standalone files · 3 pre-MB-10 con collisions (3) `docs/decisions/*.md` name-descriptive ADRs · 4 files convention 3rd. Empirical lesson MB-10 (3 instances collision detected post-audit O12 · OPS-061 vaporware-detection extension hacia dominio "existing artifact detection" · convention archivística fragmentada en 3 patterns concurrent · forward consolidation candidate MB-14). | FASE 1 B1.2 cement NEW (3 ADRs renamed 037/042/043 → 046/047/048) |

## Sub-procesadores cementados (5)

1. **Hetzner Online GmbH** · Falkenstein DE · DPA · IaaS
2. **Postmark (ActiveCampaign)** · EU Fráncfort · DPA + SCC 2021 · email transaccional
3. **Anthropic PBC** · US primario · DPA + SCC 2021 + TADPF + seudonimización · LLM Claude API
4. **360dialog GmbH** · Alemania · DPA · WhatsApp Business BSP
5. **MinIO** · Hetzner DE autoalojado · sin tercero · object storage

## Identificadores fijos (no comerciales)

- **DPO interim**: Marcos Mata García · dpo@fulkro.es
- **Security**: security@fulkro.es
- **Personal**: marcosmataga@fulkro.es
- **Dominio**: fulkro.es
- **CIF**: pendiente alta autónomo (placeholder explícito en docs)
- **Domicilio social**: Madrid, España (dirección específica TBD post-alta)

## Estructura compliance docs (post-Block 1)

```
docs/compliance/
├── 01-RGPD/
│   ├── Privacy_by_Design_FULKRO.md
│   └── Data_Retention_Policy_FULKRO.md
├── 02-LOPDGDD/
│   ├── DPO_Designation_FULKRO.md
│   ├── AEPD_Procedure_FULKRO.md
│   └── DPO_Contact_Channel_FULKRO.md
├── 04-ISMS_ISO27001/
│   ├── Information_Security_Policy_FULKRO.md
│   ├── ISMS_Risk_Assessment_FULKRO.md
│   ├── Asset_Register_FULKRO.md
│   ├── Access_Control_Policy_FULKRO.md
│   └── Incident_Response_BCP_FULKRO.md
├── 05-NIS2/
│   ├── NIS2_Classification_FULKRO.md
│   ├── Incident_Notification_Procedure_NIS2.md
│   ├── Supply_Chain_Security_NIS2.md
│   └── Vulnerability_Disclosure_security_txt.md
├── 06-Sub_Processors/
│   ├── Sub_Processors_List_FULKRO.md
│   └── Sub_Processors_Inventory.xlsx (auto-generado vía scripts/generate_sub_processors_inventory.py)
└── 07-Trust_Center/
    └── Security_Whitepaper_FULKRO.md
```

Auto-export Desktop: `/mnt/c/Users/Usuario/Desktop/Fulkro compliance/` (6 subdirs sincronizados al cierre cada block).

## Métricas baseline (post-Block 1)

- pytest m_compliance + m_compliance_monitor: 75 PASS · 0 fail
- Alembic: clean · head `sane_mb9bis_norma_rep_001`
- TSC frontend: 0 errors
- Compliance docs: 14 MD + 1 xlsx production-grade Spanish formal jurídico

## Working tree drift heredado pre-sprint (Block 1 NO toca)

- 1 modified: `progress/jaymon_comparative_analysis.md`
- 58 untracked: principalmente `progress/AUDIT_PRE_MB6_*.md`, `progress/MB*_FINAL_REPORT_*.md`, scripts audit ad-hoc, `progress/session_11/`, `backend/tests/security/__init__.py`

Decisión: drift se preserva como carryover · cada block solo `git add` archivos específicos generados en ese block.

## Plan blocks restantes (8 pendientes)

| Block | Descripción | Effort estimado | Estado |
|-------|-------------|-----------------|--------|
| 2 | Micro-polish admin ajustado (QuickActions + SSE hook DRY) | ~1.5h real | ✅ CERRADO `d14579d` |
| 3 | Magic links migration cleanup minimal (Opción α: 4 email configs deleted · 96% pre-cumplido ADR-042 + ADR-020 v3) | ~20 min real | ✅ CERRADO `811c404` |
| 4 | RLS hardening Aplus-final (1 table apply email_log + 3 skip honest · MB-9 honored · OPS-054 owner fix) | ~1h real | ✅ CERRADO `0022ddb` |
| 5 | External constraints resolution (E2E SMOKE 94.4% post-Fix2 · Full 188/266 70.7% · OPS-056+057 cement · Lighthouse defer MB-15) | ~95 min real | ✅ CERRADO `939d0e6` |
| 6 | Redis caching PATH 2 audit-driven · MB-12 batch coherent (Redis service YA exists + 18 LRU vs 5 · OPS-058 NEW · 0 material apply) | ~15 min real | ✅ CERRADO (próximo commit) |
| 7 | Documentation gaps + roadmap | ~1-2h | pendiente |
| 8 | Production-readiness docs (Postmark+360dialog+Hetzner+Bedrock+Secrets) | ~2-3h | pendiente |
| 9 | V-CHECK FINAL + Plan v6 progress closure | ~1-2h | pendiente |

## Diferidos Block 2 ajustado (a documentar en MB-14 polish o post-deploy)

- **CopilotoDock admin layout wire** (~1-1.5h cuando se retome): componente actual cliente-only · requiere refactor structure (interfaz + inferContext + endpoint admin paralelo). Trigger: demanda real validada por Marcos.
- **WhatsApp digest infrastructure BASICA + MEDIA** (~3-4h cuando se retome): tabla `client_whatsapp_preferences` + `digest_service.py` + cron Celery NO existen · build from zero. Trigger: cliente piloto activo con opt-in WA + demanda explícita.

Cap soft: 30h · hard: 36h · pacing real bloque-por-bloque con confirmación Marcos.
