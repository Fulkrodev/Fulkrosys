# PLAN MACRO v3 PRE-PILOTO REFINED · Post 11-Audit Mega-Baseline

**Status**: ✅ Plan v3 refined consolidando 11 audits empíricos
**Date**: 2026-05-24
**Methodology**: 11 audits Phase 0 cumulative + OPS-045 audit-first scope reductions + dependency sequencing
**HEAD base post-Bloque 1**: 217250e (after 11 audits committed)
**Bloque 1 commits cumulative**: 11 audits + this plan = 12 commits docs-only

---

## Verdict ejecutivo

**Scope refined empírico cumulative**: **~30-55h pre-piloto MEDIA (vs ~89-162h nominal · ahorro ~55-70%)**.

Cumulative pattern OPS-045 49ª+ aplicaciones consecutivas confirmed: **infrastructure existing 70-95% production-grade** across todos 11 items audited. Scope-out PERMANENT defaults para items críticos donde audit reveals workaround sufficient OR feature scope-creep.

**Cliente piloto MEDIA pre-cert ENS ready**: ~5-8 weeks calendar realistic empírico (vs ~3.5-7 weeks nominal · pero scope items diferentes priorizables).

---

## Per-item scope refined post-audit

| # | Item | Nominal ETA | Empírico refined | Status post-audit | Bloque assign |
|---|------|-------------|------------------|--------------------|----------------|
| #1 | Frontend polish | ~20-30h | **~10-15h iterative** (defer major) | iterative quick wins | Bloque 7 (parallel) |
| #2 | ENS selector pattern | ~5-8h | **0h scope-out** (interpretación ambigua) | Future-1.E demand-driven | scope-out |
| #3 | Compliance portal separated | ~5-10h | **0h scope-out** (maintain nested admin) | Future-1.E post-piloto | scope-out |
| #4 | ENS Radar last failed search retry | ~5-8h | **0h scope-out** (workaround skip flags) | Future-1.E post-piloto | scope-out |
| #5 | Cliente access features | ~10-20h | **~8-13h** (depends Audit #9 cloud remed) | Bloque 4+5 | Bloque 4+5 |
| #6 | LLM fallback chain | ~6-10h | **0h scope-out** (Anthropic SLA OK) + ~30min metric opcional | Future-1.E post-piloto | scope-out |
| #7 | Backups encryption + DR | ~10-15h | **0h independent** (absorbido FASE 1.F deploy) | Bloque 8 FASE 1.F | Bloque 8 |
| #8 | Monitoring multi-tenant | ~10-15h | **~5-8h** wire cliente compliance feed | Bloque 6 | Bloque 6 |
| #9 | Cloud remediation propuesta CRÍTICO | ~10-15h | **~6-10h** (orchestrator + frontend) | Bloque 2 (HIGH priority) | Bloque 2 |
| #10 | Admin↔cliente sync bidireccional | ~5-8h | **0h independent** (absorbido Audit #9) | absorbido #9 | absorbido |
| #11 | MCPs 16 servers verification | ~10-15h | **0h scope-out** (4 reales sufficient) | Future-1.E post-piloto | scope-out |
| **TOTAL** | **~89-162h nominal** | **~29-46h empírico HIGH priority** | | |

### Items en Plan v3 con ETA real
- **HIGH priority** (~29-46h cumulative): #9 cloud remediation + #5 cliente features + #8 monitoring + #1 frontend polish + #7 backups (incl FASE 1.F)
- **SCOPE-OUT 5 items** Future-1.E demand-driven: #2 · #3 · #4 · #6 · #11
- **Absorbido en otros items**: #10 sync (within #9) · #7 backups (within FASE 1.F deploy)

---

## Dependency graph

```
            ┌──────────────────────────┐
            │ #9 Cloud Remediation     │
            │ (~6-10h CRÍTICO)         │
            └────────┬─────────────────┘
                     │
                     │ depends-on
                     ▼
        ┌───────────────────────────────┐
        │ #10 Admin↔Cliente Sync        │
        │ (infrastructure existing)     │
        └────────┬──────────────────────┘
                 │
                 │ enables
                 ▼
    ┌──────────────────────────────────┐
    │ #5 Cliente Access Features       │
    │ - Remediations approval UI ~4-6h │
    │ - Compliance alerts feed ~2-4h   │
    │ - Settings polish ~2-3h          │
    └──────────────────────────────────┘
                 │
                 │ parallel
                 ▼
    ┌──────────────────────────────────┐
    │ #8 Monitoring Multi-Tenant       │
    │ ~5-8h (depende verify per-proj)  │
    └──────────────────────────────────┘
                 │
                 │ then
                 ▼
    ┌──────────────────────────────────┐
    │ #1 Frontend Polish iterative     │
    │ ~10-15h sweep + quick wins       │
    └────────┬─────────────────────────┘
             │
             │ then
             ▼
    ┌──────────────────────────────────┐
    │ #7 Backups (within FASE 1.F)     │
    │ ~3-5h Hetzner cutover            │
    └──────────────────────────────────┘
```

---

## Sequencing recommendation · 8 Bloques

### Bloque 2 · Cloud remediation orchestrator (HIGH · CRÍTICO)
- **Duration**: 6-10h · ~1-2 sessions
- **Scope**: backend orchestrator service + notification template + frontend cliente UI
- **Items**: #9 (CRÍTICO) + #10 (absorbido sync infrastructure existing)
- **Output**: cliente piloto MEDIA tiene cloud remediation flow end-to-end production-ready

### Bloque 3 · Cliente access features (HIGH · dependent Bloque 2)
- **Duration**: 4-7h · ~1 session
- **Scope**: cliente settings polish + compliance alerts feed + remediation page wire
- **Items**: #5 (HIGH+MEDIUM only · LOW MFA defer)
- **Output**: cliente piloto MEDIA portal-ready 100% pre-cert ENS

### Bloque 4 · Monitoring multi-tenant + per-project (MEDIUM)
- **Duration**: 5-8h · ~1 session
- **Scope**: backend audit per-project scope CHECK_REGISTRY + frontend cliente compliance feed
- **Items**: #8
- **Output**: cliente piloto MEDIA compliance posture visible

### Bloque 5 · Frontend polish iterative (LOW-MEDIUM)
- **Duration**: 10-15h · ~2-3 sessions parallel
- **Scope**: empty states + skeleton + error boundary + WCAG AA
- **Items**: #1 (iterative quick wins only · defer major refactor)
- **Output**: design consistency + accessibility cliente piloto MEDIA

### Bloque 6 · Optional polish (DEMAND-DRIVEN Marcos approve)
- **Duration**: 0-3h · audit-driven
- **Scope**: ENS selector clarification + LLM router metric opcional
- **Items**: #2 + #6 quick win
- **Output**: nice-to-have polish · ONLY if Marcos quiere

### Bloque 7 · Dogfooding sintético + integración E2E (1.E)
- **Duration**: ~15-25h · ~3-5 sessions
- **Scope**: sintético personas BÁSICA + MEDIA · 2 clientes dogfooding end-to-end · Playwright cross-blocks · SSE
- **Items**: 1.E original scope
- **Output**: validación REAL dogfooding ENS-only · gaps capturados last-mile

### Bloque 8 · FASE 1.F producción Hetzner (CRÍTICO)
- **Duration**: ~35-55h · ~5-8 sessions
- **Scope**: Hetzner deploy + auth hardening + Backups cutover (#7 absorbido) + branding multi-tenant + onboarding 4 semanas soporte
- **Items**: 1.F original + #7 absorbido
- **Output**: producción live · cliente piloto MEDIA recibe FULKRO ready

### Bloque 9 · Cliente piloto MEDIA onboarding REAL (HITO FINAL)
- **Duration**: ~4 semanas calendar · soporte cumulative
- **Scope**: Marcos onboard cliente piloto MEDIA real · 4 semanas hand-holding
- **Output**: **🎯 PRIMER CLIENTE PILOTO PAGADOR 9.500€ + R_STD 700€/mes**

---

## Critical path identification

**Critical path pre-piloto MEDIA**: Bloque 2 (cloud remediation) → Bloque 3 (cliente features) → Bloque 7 (dogfooding) → Bloque 8 (FASE 1.F producción) → Bloque 9 (onboarding cliente piloto).

**Non-critical parallel**: Bloque 4 (monitoring) · Bloque 5 (frontend polish) ejecutables paralelos durante Bloques 2-3 idle periods.

**Bloque 6 opcional**: solo si Marcos explicit approve.

---

## Calendar realistic empírico

**Total cumulative**: ~30-55h pre-piloto técnico + ~35-55h producción + ~4 weeks onboarding calendar = ~13-15 weeks calendar realistic empírico (vs ~3.5-7 weeks nominal pre-piloto + 4 semanas onboarding).

**Breakdown**:
- Bloques 2-6 técnico: ~30-55h cumulative · ~1-3 weeks calendar (sessions 6-10h/week realistic)
- Bloque 7 dogfooding: ~15-25h · ~1-2 weeks calendar
- Bloque 8 FASE 1.F producción: ~35-55h · ~3-5 weeks calendar
- Bloque 9 onboarding: 4 weeks soporte cliente piloto

**Calendar realistic empírico final**: **~9-15 weeks** desde HEAD actual hasta cliente piloto live.

---

## Risk identification

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Audit #9 cloud remediation scope creep | MEDIUM | HIGH | Bloque 2 Phase 0 pre-implementation re-verify · scope-cap 10h max |
| FASE 1.F Hetzner deployment complexity | MEDIUM-HIGH | HIGH | Bloque 8 dedicated planning sub-bloques (deploy + auth + backups + branding distinct) |
| Cliente piloto MEDIA dogfooding gaps surprise | MEDIUM | MEDIUM | Bloque 7 buffer 5-10h captura iterativa |
| Frontend polish iterative scope creep | LOW | LOW | Bloque 5 strict time-cap 15h iterative ONLY |
| Marcos disponibilidad legal-critical mode (#9 contracts BOE) | LOW | MEDIUM | Future-1.E.contracts.boe-refs-completion post-piloto OK |
| Hetzner Object Storage latency cliente experience | LOW | MEDIUM | Bloque 8 verify performance baseline pre-piloto onboarding |

---

## Dogfooding readiness criteria

Criterios para pasar Bloque 7 verde y dar luz verde Bloque 8 producción:
- ✅ Cloud remediation flow end-to-end production-grade
- ✅ Cliente portal access features completas (HIGH+MEDIUM gaps closed)
- ✅ Monitoring multi-tenant per-project verde
- ✅ Frontend polish iterative quick wins applied
- ✅ Dogfooding sintético BÁSICA + MEDIA end-to-end PASS sin gaps P0
- ✅ Backend tests verde cumulative (audit-first reveal critical path coverage)
- ✅ TS + ESLint scope 0 errors

---

## OPS-045 49ª+ aplicación consecutiva CONFIRMED

Pattern OPS-045 audit-first sostained empíricamente 11 audits Bloque 1:
- Item #4 ENS Radar: scope-out workaround existing
- Item #3 Compliance: scope-out portal nested existing
- Item #2 ENS selector: scope-out interpretación ambigua
- Item #5 Cliente: ~8-13h vs 10-20h nominal (~30% reduction)
- Item #6 LLM fallback: scope-out Anthropic SLA OK
- Item #7 Backups: 0h independent absorbido FASE 1.F
- Item #8 Monitoring: ~5-8h vs 10-15h (~50% reduction)
- Item #9 Cloud remediation: ~6-10h vs 10-15h (~30% reduction · audit reveals 70% existing)
- Item #10 Sync: 0h independent absorbido
- Item #11 MCPs: scope-out 4 reales sufficient
- Item #1 Frontend: ~10-15h iterative vs 25-30h major refactor

**Cumulative ahorro empírico**: **~55-70% vs nominal** sostained pattern OPS-045 49ª aplicación consecutiva confirmed.

---

## OPS-052 9ª manifestation NOT TRIGGERED

Per Bloque 1 11 audits empíricos · NO briefing-vs-reality mismatch significant detected:
- Audits reveal infrastructure existing 70-95% per item
- Scope reductions HONEST sostained (NOT inflation)
- ETAs refined empírico grounded
- 9ª OPS-052 manifestation NOT triggered ✅

---

## Cross-ref · 11 audits Bloque 1

- `docs/audits/pre_piloto/AUDIT_01_ENS_RADAR_LAST_SEARCH.md` · commit 12d9078
- `docs/audits/pre_piloto/AUDIT_02_COMPLIANCE_PORTAL_SEPARATED.md` · commit b97cc55
- `docs/audits/pre_piloto/AUDIT_03_ENS_SELECTOR_PATTERN.md` · commit 244c0d2
- `docs/audits/pre_piloto/AUDIT_04_CLIENTE_ACCESS_FEATURES.md` · commit 1a9fe00
- `docs/audits/pre_piloto/AUDIT_05_LLM_FALLBACK_CHAIN.md` · commit 8720f79
- `docs/audits/pre_piloto/AUDIT_06_BACKUPS_DR.md` · commit 486f388
- `docs/audits/pre_piloto/AUDIT_07_MONITORING_MULTI_TENANT.md` · commit 063d4ad
- `docs/audits/pre_piloto/AUDIT_08_CLOUD_REMEDIATION.md` · commit 74ffb3d (CRÍTICO)
- `docs/audits/pre_piloto/AUDIT_09_ADMIN_CLIENTE_SYNC.md` · commit 5c21514
- `docs/audits/pre_piloto/AUDIT_10_MCPS_16_SERVERS.md` · commit e5fcacf
- `docs/audits/pre_piloto/AUDIT_11_FRONTEND_POLISH.md` · commit 217250e

---

## Future captures consolidated (5 scope-out items + 2 polish defer)

1. **Future-1.E.ens-radar-retry-failed-step** (~2-6h post-piloto demand-driven · Audit #4)
2. **Future-1.E.compliance-portal-separated** (~4-8h post-piloto · Audit #3)
3. **Future-1.E.ens-selector-pattern-unification** (~3-6h post-piloto · Audit #2 Marcos clarify required)
4. **Future-1.E.llm-multi-provider** (~8-15h post-piloto demand-driven · Audit #6)
5. **Future-1.E.mcps-9-scaffolding-promote** (~10-20h cumulative post-piloto · Audit #11)
6. **Future-1.F.cliente-mfa-real** (~6-10h post-piloto · Audit #5)
7. **Future-MB-11.dr-drill-real** (~6-10h post-piloto · Audit #7)
8. **Future-1.F.major-design-system-refactor** (~25-35h post-piloto · Audit #11)
9. **Future-1.F.hetzner-monitoring-prometheus-grafana** (~4-6h FASE 1.F natural · Audit #7)

---

## Recomendación final ejecutiva Marcos

**Plan v3 GO**: ~30-55h pre-piloto técnico empírico realista · NO scope inflation · 9 Future items capturados.

**Próximo paso recomendado**: **Bloque 2 · Cloud remediation orchestrator** (HIGH · CRÍTICO · ~6-10h)
- Pre-condición: architect approve scope cumulative
- Pre-implementation Phase 0 (~30 min) verify before propagate

**STOP-AND-REPORT FINAL** · architect approve Plan v3 antes Bloque 2 execution.

---

## Honest notes

1. Target path `/mnt/c/Users/Usuario/Desktop/FULKRO_AUDIT_PRE_1E_22052026/` NO accessible WSL UNC environment · Plan v3 escrito en `docs/audits/pre_piloto/` repo root (Marcos puede sync manual a Desktop si quiere)
2. ETAs empíricos asumen sesiones productivas sin context-switch · realidad ~10-20% buffer recomendado
3. Calendar ~9-15 weeks asumes Marcos disponibilidad full-time technical work · variable per business priorities
4. Bloque 8 FASE 1.F producción es **HIGHEST risk** scope significant + Hetzner unknowns
5. OPS-052 9ª manifestation NOT triggered confirmed · Plan v3 grounded empírico Bloque 1 11 audits
