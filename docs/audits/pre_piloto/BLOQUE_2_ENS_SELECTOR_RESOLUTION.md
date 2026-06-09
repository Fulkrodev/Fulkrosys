# BLOQUE 2 · ENS selector ambiguity · architect resolution

**Status**: ✅ RESOLVED · architect decision SCOPE-OUT PERMANENT pre-piloto
**Date**: 2026-05-24
**Source audit**: `AUDIT_03_ENS_SELECTOR_PATTERN.md` (commit 244c0d2)
**Bloque 2 decision**: 3/3 items scope-out CERRADO post-Bloque-1

---

## Architect decision

**Option B confirmed**: NO entity requiere selector unificado similar ENS Radar pattern · scope-out PERMANENT pre-piloto.

**Decision rationale**:
- Cada selector ad-hoc per-motor actualmente sirve sin friction operacional (LeadsTable filters · ProjectSwitcherDropdown · ENS Category per-motor pickers)
- Refactor unification tendría riesgo regresión cross 363 componentes
- Conflict con 1.E.2 ADR-054 Project-Scoped Admin UX recientemente cement
- Conflict con 1.D.F.bis.III sidebar refactor 14→10 entries recient
- 3 hipótesis distintas (A/B/C) NO confirmed cuál era la real intención · scope-out es honest path NO speculation

---

## Future capture

**Future-1.E.ens-selector-pattern-unification** (post-piloto demand-driven):
- ETA empírico ~3-6h
- Pre-condición: Marcos clarifica explícito qué quiere unificar (Hipótesis A vs B vs C)
- Trigger: 2do cliente onboarding emerge real need OR Marcos comercial UX feedback specific

---

## Bloque 2 cierre · 3/3 items scope-out post-Mega-Audit

| # | Item | Decision | Future capture |
|---|------|----------|----------------|
| #4 | ENS Radar retry failed search | scope-out PERMANENT (workaround skip flags) | Future-1.E.ens-radar-retry-failed-step (~2-6h) |
| #3 | Compliance portal separated | scope-out PERMANENT (maintain nested admin) | Future-1.E.compliance-portal-separated (~4-8h) |
| #2 | ENS selector pattern | **scope-out PERMANENT THIS resolution** | Future-1.E.ens-selector-pattern-unification (~3-6h) |

**Total Bloque 2 scope-out cumulative ETA Future**: ~9-20h post-piloto demand-driven · ahorro pre-piloto 100%.

---

## Cross-ref

- Source audit: `docs/audits/pre_piloto/AUDIT_03_ENS_SELECTOR_PATTERN.md`
- Plan Macro v3: `docs/audits/pre_piloto/PLAN_MACRO_v3_PRE_PILOTO_REFINED.md` · sección scope-out 5 items
- Audit #4 ENS Radar: `docs/audits/pre_piloto/AUDIT_01_ENS_RADAR_LAST_SEARCH.md`
- Audit #3 Compliance: `docs/audits/pre_piloto/AUDIT_02_COMPLIANCE_PORTAL_SEPARATED.md`
- ADR-054 Project-Scoped Admin UX
- 1.D.F.bis.III sidebar refactor cement

---

## Honest notes

1. Architect decision en autonomous chain · NO Marcos human disponible legal-validation tipo
2. Decision align con audit recommendation cement · NO scope creep speculation
3. Future capture explicit · NO silent debt (OPS-049 honesty path sostained)
