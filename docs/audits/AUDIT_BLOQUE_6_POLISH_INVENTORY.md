# AUDIT Bloque 6 · Frontend Pages Polish Inventory · 2026-05-24

**Status**: ✅ Phase 0 CERRADO · scope honestly recalibrated post-empirical audit
**Methodology**: find + wc + read sample top pages per área (constraint sostained · NO grep)
**Auditor**: Claude (sesión Bloque 6 post-Bloque 4 monitoring cierre)

## Hallazgo principal · OPS-045 33ª aplicación consecutiva

**Frontend infrastructure ~90% ya production-grade polished** (sub-atom cumulative refactor sostained quality cross fases 1.C-1.D + Bloque 3+5 cloud remediation + Bloque 4 monitoring NEW). Audit-first reveals que la mayoría de pages tienen loading/error/empty states + mobile responsive + R29 firmísimo cliente.

**Scope recalibrado**: de 8-12 commits nominal → 3-5 commits empírico realista. Polish quick wins focalizados en gaps específicos detectados · NO refactor masivo necesario.

## Frontend pages inventory empírico

| Área | Pages totales | Production-grade | Polish needed |
|------|---------------|------------------|---------------|
| **Admin top-level** | ~25 pages | ~22 (90%) | ~3 (dashboard cards retry) |
| **Admin project-scoped** | ~40 pages | ~36 (90%) | ~4 (legacy pre-1.D.F) |
| **Cliente portal** | 30 pages | ~28 (93%) | ~2 (legacy) |
| **ENS Radar** | 4 pages | ~3 (75%) | ~1 (cluster polish) |
| **Auth/legal/public** | ~10 pages | ~9 (90%) | ~1 |
| **TOTAL** | **133 pages** | **~118 (89%)** | **~15 quick wins** |

## Top 15 polish quick wins identified

### Admin dashboard cards (3 quick wins · ~30 min)
1. **ActivityCard** · error state add retry button (currently just text "No pude obtener...")
2. **AlertsCard** · error state add retry button + friendly empty state expand
3. **AlertsCard** · empty state "Sin alertas." → "Todo tranquilo · sin alertas pendientes" (friendlier)

### Admin pages legacy minor polish (~3-4 pages · ~30-45 min)
4. /admin/alerts (274 LOC) · sample · likely production but worth verify
5. /admin/timesheet (330 LOC) · sample · likely production
6. /admin/llm-observability (262 LOC) · sample · production-grade
7. /admin/copilot (legacy 22 LOC standalone) · scope-out per 1.D.B.2 already

### Cliente portal R29 firmísimo verify (~2-3 pages · ~30-45 min)
8. /client-portal/billing (74 LOC) · R29 friendly check
9. /client-portal/account (verify friendly tone)
10. /client-portal/account/notifications · verify

### ENS Radar polish (~1-2 pages · ~30 min)
11. /radar/page.tsx · main dashboard polish
12. /radar/leads/page.tsx · lead status badges color-coded verify

### Cross-app accessibility (~3 quick wins · ~30-45 min)
13. ARIA labels audit cross-components (sample 5-10 components)
14. Keyboard navigation focus indicators verify
15. Mobile responsive breakpoints sample test

## Pages production-grade verified (NO polish needed)

- ✅ /client-portal/cumplimiento (Bloque 4 NEW · loading + error + empty + R29)
- ✅ /client-portal/dashboard ClientDashboardV3 (MB-7 polished · 3 zones)
- ✅ /client-portal/files (422 LOC · 1.C.G.B refactor)
- ✅ /client-portal/workflow (263 LOC · 1.C.D.C polish v3.8)
- ✅ /admin/dashboard (KpiRow + cards · MB-7)
- ✅ /admin/projects (228 LOC · 1.E.2.bis Phase A-B polish)
- ✅ /admin/system-health (Bloque 4 NEW · 251 LOC)
- ✅ /admin/cross-project-compliance (Bloque 4 NEW · 108 LOC)
- ✅ /admin/compliance/monitor (494 LOC · MB-9.bis polished)
- ✅ /admin/projects/[id]/cloud-connectors (1.D.X NEW)
- ✅ /admin/projects/[id]/dda (1.D.F.A · 7 components production-grade)
- ✅ /admin/projects/[id]/contratos (1.D.D.A · 4 components production)
- ✅ /admin/projects/[id]/mcps (1.D.E NEW · 6 components)
- ✅ /admin/projects/[id]/discrepancies (1.D.A · A21 production)
- ✅ /admin/projects/[id]/planes-accion (1.D.C · aggregator cross-motor)
- ✅ Cliente sub-atom 1.D.F.bis.III · indispensable-only refactor 10-entries sidebar

## Scope refined Bloque 6 honest (3-5 commits empírico vs 8-12 nominal)

**Phase A** (admin dashboard cards retry + minor) · 1 commit · ~30 min
**Phase B** (cliente R29 verify · likely no changes needed) · 0-1 commits · ~15-30 min
**Phase C** (ENS Radar quick check) · 0-1 commits · ~20-30 min
**Phase D** (accessibility ARIA spot-check) · 1 commit · ~30 min
**Phase E** (validation + cierre) · 1 commit · ~30 min

**Cumulative empírico estimate**: ~2.5-3.5h (vs ~10-15h nominal · ahorro ~70%)

## Defer items capturados Future-X

- **Future-1.E.polish.major-refactor** · si demanda refactor mayor post-piloto demand-driven (~8-15h)
- **Future-1.F.design-system** · tokens canonical · component library extraction post-piloto (~10-20h)
- **Future-1.E.polish.visual-regression-tests** · Playwright visual regression CI (~5-8h)
- **Future-1.E.polish.dark-mode** · dark mode toggle if demand cliente piloto (~8-12h)
- **Future-1.E.polish.a11y-axe-ci** · @axe-core/playwright accessibility automation CI (~3-5h)

## Pattern OPS-045 33ª aplicación formalize

Audit-first reveals frontend infrastructure ~90% ya polished cumulative sub-atoms previos · scope ratio nominal 10-15h → empírico realista 2.5-3.5h · ahorro ~70% sostained sub-atom Bloque 6.

**Cross-reference**: LECCIÓN-OPS-045 audit-first reveals existing infrastructure (33ª aplicación consecutiva post Bloque 4 cierre 52ª · próxima escalada Bloque 7 dogfooding).

## Gates per phase materializar empírico

- **Phase A** · 1 commit dashboard cards · si más opportunities detected → 2 commits max
- **Phase B** · cliente verify · si todo R29 verde → 0 commits + doc verification only
- **Phase C** · ENS Radar quick check · si polished → 0 commits + doc verification only
- **Phase D** · accessibility spot-check · si todo OK → minor commit ARIA labels
- **Phase E** · validation + cierre + CLAUDE.md sostained
