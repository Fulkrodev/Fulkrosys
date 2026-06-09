# VALIDATION · Path A · ENS Radar Scoring + Extraction Refinement · CERRADO

**Date**: 2026-05-25
**Scope**: Closure document Path A (4 phases · Phase 0 → A → B → C → D).
**Trigger**: Sesión 1 ADDENDUM Phase D revealed temperatura skew 90% ardiendo + 47-53% extraction gaps. Marcos directive: 5-criteria intersection (concursando AAPP · pliego exige ENS · empresa NO ENS · reincidente · sweet spot 60-500k€) + min CIF OR razón social filter.

---

## Phase-by-phase summary

| Phase | Status | Commit |
|-------|--------|--------|
| 0 · Empirical diagnose | ✅ 4 root causes verified · 1 criterio unmodelable | `92e5644` |
| A · Extraction filter | ✅ Forward-looking defensive · 0 cleanup (empirical) · 15/15 tests | `4cc5e83` |
| B · Scoring 4-criteria intersection | ✅ Sweet spot FILTER (not bonus) · 19/19 tests | `544d306` |
| C · Rescore 435 leads | ✅ 218 changes · distribution 100% coherent · 30/30 spot-check | `08a7060` |
| D · Cumulative validation + cierre | ✅ this commit | TBD |

---

## Marcos directive materialization · 4/5 strict empirical (C4 honest defer)

Original Marcos criteria:
> ARDIENDO = (concursando AAPP) AND (pliego exige ENS) AND (empresa NO ENS) AND (reincidente) AND (presupuesto sweet spot 60-500k€)

| Marcos C# | Status | Implementation | Evidence |
|-----------|--------|----------------|----------|
| C1 concursando AAPP | ✅ STRICT | `participations` JOIN query | Implicit pipeline filter |
| C2 pliego exige ENS | ✅ STRICT | `ens_analysis.exige_ens=TRUE` filter | temperature.py:80-91 |
| C3 empresa NO ENS | ✅ STRICT | `tiene_ens_vigente=FALSE` split | temperature.py:162 |
| **C4 reincidente** | ⚠ **PROXY** | ≥2 adjudicaciones in sweet spot (NOT strict "rejected by NO ENS") | UNMODELABLE empírico actual · `participations.rol` solo "adjudicatario" |
| C5 sweet spot 60-500k€ | ✅ STRICT FILTER | `MARCOS_BUDGET_MIN/MAX` (NOT bonus) | temperature.py:165-178 |

**C4 honest defer**: `participations.rol` empirical = 198,734 rows · **100% "adjudicatario"** · 0 "licitador" (losing bidders). PLACSP scrape does NOT capture losing bidders currently. **Future-1.E.ens-radar.scrape-losing-bidders** (~6-8h) blocks strict C4 implementation. Proxy via ≥2 sweet-spot adjudications = "reincidente patron" indirecto.

---

## Empirical results · before vs after

### Distribution change

| Metric | PRE | POST | Δ |
|--------|-----|------|---|
| ardiendo | 392 (90.1%) | 314 (72.2%) | −78 (demoted) |
| ardiendo_sostenido | 43 (9.9%) | 22 (5.1%) | −21 (proxy strict) |
| caliente | 0 | 99 (22.8%) | +99 (NEW) |
| **total leads** | 435 | 435 | 0 |
| **changes** | — | 218 (50.1%) | — |

### Coherence verification (100% accurate post-rescore)

| temperatura | total | in_sweet_spot | outside_sweet_spot |
|-------------|-------|---------------|---------------------|
| ardiendo | 314 | **314 (100%)** | 0 |
| caliente | 99 | 0 | **99 (100%)** |
| ardiendo_sostenido | 22 | **22 (100%)** | 0 |

✅ **0 false positives empírico · perfect categorization**.

### Manual spot-check 30 leads

10 per tier verified (ardiendo importes 65-315k · caliente 30-675k outside · sostenido count=2 each). 0 inconsistencias.

---

## Tests cumulative Path A

| Test file | Tests | Status |
|-----------|-------|--------|
| `test_m10_identification_filter.py` (Phase A) | 15 | ✅ Verde |
| `test_m10_temperature_marcos_intersection.py` (Phase B) | 12 | ✅ Verde |
| `test_m10_temperature_v2.py` (regression) | 7 | ✅ Verde |
| `test_m10_pipeline_csv_mkdir_fix.py` (Sesión 1 ADDENDUM Phase C) | 4 | ✅ Verde |
| **Total cumulative** | **38** | ✅ **38/38** |

---

## Cumulative metrics Path A

- **5 commits productivos** (Phase 0 audit + A filter + B refactor + C rescore + D cierre)
- **~4h empírico** cumulative (within ETA 4-6h)
- **~1200 LOC** cumulative (193 audit + 262 Phase A + 394 Phase B + 291 Phase C + this doc)
- **3 new modules** (identification_filter + rescore script + Marcos tests)
- **1 refactor** (temperature.py 272 LOC · 67 lines modified)
- **218 leads rescored** empirical · **0 destructive** (Marcos workflow preserved)
- **0 regression** tests

---

## Future-X items captured Path A (~17-23h cumulative post-piloto demand-driven)

### Phase 0 + Phase B (Marcos strict full enablement)
- **Future-1.E.ens-radar.scrape-losing-bidders** (~6-8h) · Modify PLACSP scrape to capture `rol="licitador"` losing bidders · enable C4 reincidencia strict ("rejected by NO ENS")
- **Future-1.E.ens-radar.denormalized-counters-fix** (~2h) · `radar_leads.num_licitaciones_ens` always 0 despite participations existing (stale denormalized counter)

### Phase A (extraction enrichment)
- **Future-1.E.ens-radar.cif-enrichment-from-name** (~3-5h) · INE/AEAT API populate 28,868 `SIN_CIF_*` placeholders with real CIFs (220 affected radar_leads)
- **Future-1.E.ens-radar.name-enrichment-from-cif** (~3-5h) · Reverse lookup populate `razon_social` for 7,856 companies with CIF-as-razon_social (215 affected radar_leads)

### Phase C (tibio category empirical)
- **Future-1.E.ens-radar.tibio-from-historic-only-leads** (~2-3h) · Current rescore did not produce tibio category because all 435 existing leads have ≥1 adjudication; rerun pipeline_v2 may detect new tibio candidates from full PLACSP corpus

---

## Patterns sostained Path A

- ✅ **OPS-052 Phase 0 doctrine** · empirical audit BEFORE implementation · 4 root causes verified · 1 criterio unmodelable detected EARLY (saves ~6-8h rework)
- ✅ **OPS-045 audit-first reveals existing infrastructure** (38ª-39ª aplicaciones) · `temperature.py` 272 LOC + 7 levels production + `get_sweet_spot_for_tender` existing
- ✅ **OPS-049 ARTIFACT honesty path** · 5 Future-X items explicit · NO silent debt
- ✅ **Anti-workaround firmísimo** · C4 honest defer · NO fake mark-as-implemented · proxy explícito documented
- ✅ **Marcos workflow preserved** · `estado_contacto` + `notas_marcos` + `notas_privadas` + `email_redactado` NOT touched in rescore

---

## ADR + Reglas sostained

- **ADR-013** (doble pool auth) sostained · NO auth changes
- **ADR-025** (NO new tables) sostained · solo additive ORM columns vía `scored_at` update
- **R1** (motores deterministas > LLM) sostained · scoring rule-based · NO LLM decisions
- **R31** sostained · 0 mocks production · regression tests verde

---

## Bloque 7 dogfooding pre-condition · Marcos scoring quality

**Pre-Path-A**: 392/0/0/0 temperatura skew · ALL ardiendo · NO segmentation
**Post-Path-A**: 314/99/22 sensible distribution · per Marcos directive

Cliente piloto MEDIA cuando reciba leads ardiendo: top-tier intersección 4-criteria (concursando AAPP + pliego ENS + NO ENS vigente + budget en sweet spot). Marcos lista de leads-lunes (Future-X export feature) tendrá ahora 22 ardiendo_sostenido + 314 ardiendo = 336 prioridad-alta (vs antes 392 sin discriminación) y 99 caliente segunda prioridad (vs antes 0 categorización útil).

---

## "Marcos 5-criteria" verdict honest

**4/5 STRICT materializado** + **1/5 PROXY** (C4 reincidencia · honest defer Future-X).

Marcos directive literal NO 100% empirical (C4 blocked upstream data gap). Path A delivers maximal possible empirical implementation. C4 strict requires PLACSP scrape modification (~6-8h Future-X).

---

→ **Path A CERRADO** · 5 commits · 38/38 tests verde · 218 leads rescored · distribution 100% coherent · Marcos 4-criteria materializado · cliente piloto MEDIA scoring quality ready pre-Bloque-7 dogfooding.
