# FASE C Phase D · BOE refs refinement · scope-out documented (honest path)

**Status**: 🟡 Scope-out PERMANENT pre-piloto · Future-1.E.contracts.boe-refs-completion captured
**Date**: 2026-05-24
**Decision rationale**: Marcos NOT en legal-critical mode (autonomous chain run) · Phase D doctrine "BOE refs CRÍTICO · requires Marcos legal-critical mode validation" NO satisfied.

---

## Decision

Per FASE C Path Hybrid briefing literal:

> ⚠️ ESTE ES EL PHASE DONDE MARCOS DEBE ENGAGE CRÍTICAMENTE para BOE refs validation.
> Per audit · 7/9 normativas core con refs · falta 2 normativas + polish refs existing.
>
> 3. STOP-AND-REPORT con Marcos · refs proposals · architect validates:
>    Claude Code lista refs missing/incomplete · Marcos provee refs correctas
>    Pattern similar to B.3.C Marcos-curated golden entries

**Honest path**: Marcos esta autonomous chain run · NO disponible para legal-critical validation per template. Speculating BOE refs sin Marcos legal review violaria **R1 INVIOLABLE** ("motores deterministas > LLM decisiones normativas · trazabilidad ENAC > flexibilidad LLM").

**Decision**: scope-out PERMANENT pre-piloto · capturar Future-1.E.contracts.boe-refs-completion para Marcos engagement asynchronous post-FASE C cierre.

---

## Gap matrix BOE refs current state (per audit cdde3c6)

| Template | RD 311/2022 | RGPD | NIS2 | DORA | LCSP | Schrems II | CCN-STIC | ISO | CP | Status pre-piloto |
|----------|:-----------:|:----:|:----:|:----:|:----:|:----------:|:--------:|:---:|:--:|-------------------|
| C-001 commercial | ✅ | — | — | — | — | — | — | ISO/IEC 17065 | — | ✅ piloto MEDIA OK |
| E-604 deliverable | ✅ art 18 + op.ext.1 | ✅ art 28 + LOPDGDD | ✅ Dir 2022/2555 art 21.2.d | ✅ Reg 2022/2554 art 30 | — | — | — | — | — | ✅ comprehensive |
| C-100 legal | implicit | — | — | — | — | — | CCN-STIC 802 | ISO/IEC 17065 | — | ✅ piloto MEDIA OK |
| C-110 NDA | — | — | — | — | — | — | — | — | — | 🟡 NO refs (legacy template) |
| C-120 RGPD Art 28 | — | ✅ art 28 + LOPDGDD + ARSULIPO | — | — | — | — | — | ISO 27001 | — | ✅ comprehensive |
| C-130 ENS terceros | ✅ implicit | — | — | — | — | — | ✅ CCN-STIC 823 | — | — | ✅ piloto MEDIA OK |
| C-140 confidencialidad | — | — | — | — | — | — | — | — | ✅ Art 197-201 CP | ✅ piloto MEDIA OK |
| C-150 DPA | — | ✅ SCC | — | — | — | ✅ Decisión 2021/914 + TIA | — | — | — | ✅ comprehensive |
| C-160 pentesting marco | — | — | — | — | — | — | — | — | — | 🟡 NO refs (legacy template) |

**Cobertura empírica**:
- ✅ 7/9 templates con refs explícitas (sufficient cliente piloto MEDIA pre-cert)
- 🟡 2/9 templates sin refs (C-110 NDA + C-160 pentesting marco) · NO bloquean piloto

**Gaps identificados sin Marcos legal validation**:
- C-110 NDA bilateral: candidate refs Marcos validate later: Ley 1/2019 secretos empresariales (BOE 21/02/2019) + Art 197-201 CP secretos
- C-160 pentesting marco: candidate refs Marcos validate later: Ley Orgánica 10/1995 CP delitos informáticos + RGPD Art 32 pentesting como medida apropiada + CCN-STIC 808 pentesting

---

## Why NOT speculate BOE refs autonomously

1. **R1 INVIOLABLE** sostiene: decisiones normativas LLM-free · Marcos legal-validated refs only
2. **Auditor ENAC trazabilidad** requires legal source documented + cross-checked
3. **Cliente piloto MEDIA pre-cert** NO bloquea con 7/9 cobertura actual · gaps son polish post-piloto
4. **Pattern OPS-049 honesty** · NO claim "BOE refs complete" sin Marcos validation explícita (avoid ARTIFACT aspirational debt risk)

---

## Future-1.E.contracts.boe-refs-completion capturado

**Scope**: Marcos engagement legal-critical mode · review C-110 + C-160 gaps + polish refs comprehensive cross all templates.

**Approach**: similar B.3.C golden curation · Claude Code presenta refs candidates · Marcos accept/reject/correct per template.

**ETA empírico**: ~1-2h una vez Marcos en legal-critical mode (NO autonomous · validation manual).

**Pre-condición**: ninguna · arrancable post-FASE C cierre cuando Marcos quiera engage.

**Cross-ref**:
- Audit cdde3c6 FASE C M14_M28 findings · sección BOE references baseline
- Phase 0 re-verify · sección BOE references baseline RE-CONFIRMED 7/9
- Cliente piloto MEDIA pre-cert ENS-ready con 7/9 actual cobertura

---

## Verification empírica · Phase 0 confirms 7/9 stable

`grep -n` punteado en `legal_templates.py` + `E604_adenda_contractual_ens.md` confirma refs persistent desde sub-lote 1.B.9 (commit historic):
- RD 311/2022 art 18 + Anexo II op.ext.1 (E-604 multiples sections)
- RGPD art 28 + LOPDGDD (E-604 + C-120)
- Dir 2022/2555 NIS2 art 21.2.d (E-604)
- Reg 2022/2554 DORA art 30 (E-604)
- CCN-STIC 802 (C-100 implícito implantador/auditor incompatibilidad)
- CCN-STIC 823 (C-130 cadena suministro)
- Art 197-201 CP secretos (C-140)
- Decisión UE 2021/914 SCC + Schrems II + TIA (C-150)
- ISO/IEC 17065 + IC-01/19 (C-001 + C-100)

**0 deuda silenciosa**: refs existen empíricamente · NO claim "complete" donde no lo está.

---

## OPS-052 + OPS-049 sostained

- **OPS-052**: NO inflar scope Phase D para satisfacer ETA briefing nominal · scope-out honest cuando precondiciones (Marcos legal-critical mode) no cumplen.
- **OPS-049**: NO claim "BOE refs FASE C complete" en commit message o CLAUDE.md sin Marcos validation real · capturar Future-1.E.contracts.boe-refs-completion explícito · DEFER explicit prevents aspirational debt.
