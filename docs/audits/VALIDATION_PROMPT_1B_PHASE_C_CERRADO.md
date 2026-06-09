# VALIDATION_PROMPT_1B_PHASE_C_CERRADO · RadarLead V9 atomic refactor

**Status**: Phase C atomic refactor CERRADO empíricamente verde
**Fecha**: 2026-05-25
**Branch**: `radar-v9` (split paralelo desde `fulkro-1.0` HEAD `16964c7`)
**Directive Marcos**: C2 atomic refactor · ETA expanded ~3-4h cumulative
**Cumulative ETA actual**: ~2.5-3h (under target · ahorro ~20-25%)

---

## 0. Resumen ejecutivo

| Métrica | Pre-Phase-C | Post-Phase-C |
|---|---|---|
| radar_leads rows | 435 | **435** ✅ (Path A preserved) |
| temperatura distribution | 314/22/99 | **314/22/99** ✅ invariant |
| radar_leads.estado col | exists (varchar 50 dup) | **DROPPED** ✅ (D4) |
| radar_leads.estado_contacto CHECK | 8 legacy values | **10 spec §3.G values** ✅ (D3) |
| Criterios c1-c5 cols | NOT exist | **7 cols ADD** ✅ |
| dolor_summary col | NOT exist | **ADD text** ✅ |
| best_pliego_id FK tenders | NOT exist | **ADD FK** ✅ |
| jurisprudencia_citable JSONB | NOT exist | **ADD JSONB '{}' default** ✅ |
| feedback_score enum | NOT exist | **ADD enum** ✅ |
| timeline_json JSONB | NOT exist | **ADD JSONB '[]' default** ✅ |
| `lead.estado` refs backend | 13 across 5 files | **0** ✅ |
| `lead.estado` refs frontend | 9 across 5 files | **0** ✅ |
| 5 downstream Pydantic classes | `estado: str` | `estado_contacto: str` ✅ |
| 4 zod schemas frontend | `estado: z.string()` | `estado_contacto: z.string()` ✅ |
| ESTADO_CONFIG display labels | 4 legacy entries | **10 V9 entries** ES human-readable |
| Backend radar pytest | (baseline) | **166/166 verde** ✅ |
| Frontend TS errors radar scope | (baseline) | **0 new** ✅ (10 pre-existing OTHER) |
| Migration idempotency upgrade+downgrade | n/a | **3 phases verified** ✅ |

---

## 1. Commits cumulative Phase C (7 commits productivos)

| Sub-fase | Commit | LOC | Description |
|---|---|---|---|
| Phase C.0 audit consumers | `e880ebe` | +230 | docs/audits/AUDIT_RADAR_V9_C_ESTADO_DROP_CONSUMERS.md inventory |
| Phase C.1 migration + ORM | `70037db` | +290/-6 | drop estado + enum 10 + 12 new V9 cols + 3 new enums |
| Phase C.2 schemas.py | `d553bb5` | +8/-3 | 2 sites + 5 downstream class shapes |
| Phase C.3 service+api+cli+exporters | `3dd5639` | +64/-30 | 13 refs eliminated · 4 endpoints refactored |
| Phase C.3 fixture + regex fixes | `fe61262` | +78/-15 | 166/166 tests verde · auto-derive source_platform |
| Phase C.4 frontend zod+display | `d260c12` | +76/-34 | 9 refs across 5 files · ESTADO_CONFIG expanded |
| Phase C.5 cierre VALIDATION (this) | (next) | +n | this doc + CLAUDE.md update |

**Cumulative metrics**:
- 7 commits productivos
- ~1140 LOC cumulative (audit doc + 4 migrations + ORM + consumers + frontend + this doc)
- 0 production logic regressions (166/166 tests verde)
- 0 destructive sobre 435 leads (Path A invariant)

---

## 2. Decisiones Marcos D1-D7 materializadas

| ID | Decisión | Status |
|---|---|---|
| **D1** | Flat para queryables · JSONB para metadata | ✅ companies + tenders + radar_leads pattern aplicado · 3-5 JSONB meta cols per table |
| **D2** | ASCII sin acentos (live wins · spec doc CORRECCION) | ✅ ens_categoria_enum = `BASICO\|MEDIO\|ALTO` (NOT BÁSICA/MEDIA/ALTA) |
| **D3** | estado_contacto 10 values + renames + descartado collapse | ✅ CHECK constraint 10 spec §3.G values · backfill mapping safe (435 rows all `nuevo` empirically · no destructive) |
| **D4** | DROP radar_leads.estado duplicate AHORA | ✅ DROPPED Phase C.1 · consumers refactored C.2 (schemas) + C.3 (service+api+cli+exporters) + C.4 (frontend zod+display) |
| **D5** | decision_makers table crear ahora aunque vacía | ✅ NEW table Phase A · 12 cols + 2 enums + FK CASCADE · vacía esperando eInforma feature-prompt 2 |
| **D6** | CCAA derived backend con columna materializada | ✅ companies.ccaa + tenders.ccaa flat cols nullable · backend derive logic feature-prompt scoring rerun |
| **D7** | 4 migrations phased | ✅ A (Company) + B (Tender) + C (Lead) + D (Indexes pending) · sub-atom granular C.0-C.5 chain |

---

## 3. Spec §3.G state machine 10 valores V9 canonical

| V9 spec value | Legacy mapping | Display label (ESTADO_CONFIG) |
|---|---|---|
| `nuevo` | `nuevo` (no change · 435 rows current) | "Nuevo" |
| `contactado` | `enviado` (rename) | "Contactado / En seguimiento" |
| `respondido` | `respondio` (typo fix) | "Respondido" |
| `discovery_scheduled` | `reunion_agendada` (English spec) | "Reunión agendada" |
| `discovery_realizada` | NEW value | "Discovery realizada" |
| `propuesta_enviada` | `propuesta_enviada` (no change) | "Propuesta enviada" |
| `en_negociacion` | NEW value | "En negociación" |
| `cerrado_ganado` | `ganado` (rename) | "Ganado" |
| `cerrado_perdido` | NEW value | "Perdido" |
| `descartado` | `descartado` + `no_interesa` COLLAPSE | "Descartado" |

**Endpoint semantic mapping (api.py)**:
- `POST /leads/{id}/approve` → estado_contacto=`discovery_scheduled` (was "aprobado" free-form legacy)
- `PATCH /leads/{id}/discard` → estado_contacto=`descartado`
- `PATCH /leads/{id}/limbo` → estado_contacto=`contactado` (was "limbo" free-form legacy)
- `PATCH /leads/{id}/note` → no estado mutation (only notas_marcos)

**API query param `?estado=<value>` pattern**: ahora regex `^(nuevo|contactado|respondido|discovery_scheduled|discovery_realizada|propuesta_enviada|en_negociacion|cerrado_ganado|cerrado_perdido|descartado)$` (10 spec values · was 5 legacy).

---

## 4. Empirical verification matrix

### 4.A Backend gate cleared

```
$ python -m pytest backend/tests/motors/m10_ens_radar/ --no-header -q
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
166 passed in 13.89s
```

### 4.B Path A invariant preserved

```sql
SELECT COUNT(*) FROM radar_leads;
-- 435

SELECT temperatura, COUNT(*) FROM radar_leads GROUP BY temperatura;
-- ardiendo            314
-- caliente             99
-- ardiendo_sostenido   22
```

### 4.C Migration idempotency verified

```
$ alembic upgrade radar_v9_c_lead_001  # OK · 435 preserved · 45 cols
$ alembic downgrade -1                  # OK · estado col restored · 435 preserved
$ alembic upgrade radar_v9_c_lead_001  # OK · re-apply clean · 45 cols
```

### 4.D 0 `lead.estado` refs remaining

```
$ grep -rn "lead\.estado\b" backend/app/motors/m10_ens_radar/
$ grep -rn "lead\.estado\b" frontend/
(empty)
```

### 4.E Frontend TypeScript scope

```
$ npx tsc --noEmit | grep -E "ens-radar|radar|lead"
(empty)
# 10 pre-existing TS errors in OTHER areas (Sesión 3B-2B.2 polish · admin
# compliance/system-health · cloud-connectors · m14_contracts) · NOT caused
# by Phase C refactor · captured Future-X for cleanup en sesión separate
```

---

## 5. Honesty notes Phase C

1. **Migration revision id length constraint**: `alembic_version.version_num VARCHAR(32)` limit forced rename `company_v9_extension_radar_v9_a_001` (36 chars) → `radar_v9_a_company_001` (22 chars). Same cause prevented b35 migrations from being applied to this DB empirically · capture Future-X chore `ALTER alembic_version.version_num TYPE VARCHAR(64)`.

2. **Multi-head branching paralelo**: radar-v9 chain (golden_eval_runs → radar_v9_a → radar_v9_b → radar_v9_c) coexists con b35 chain (golden_eval_runs → cloud_remediation → remediation_enhancement) sin conflicto · radar-v9 usa `alembic upgrade <revision>` targeted execution (NOT `upgrade heads`).

3. **`source` legacy col preserved**: ORM Tender mantiene legacy `source: Mapped[str]` alongside new `source_platform: Mapped[str]` durante transición · pipeline + sources/*.py + scoring/*.py read-path consumen legacy field · Future-X capture `Future-1.E.radar.tender-source-deprecate` ~2-3h cuando pipeline migra read-path.

4. **`estado` VARCHAR(50) tenders LEFT INTACT**: 10 distinct values empirical (adjudicado/en_evaluacion/resuelto/publicado/preanuncio/anulado) vs spec 6 values · Future-X capture `Future-1.E.radar.tender-estado-enum-normalize` cuando AAPP normalize mapping reconciled.

5. **Dialog state names "limbo"/"dentro" preserved**: internal JS identifiers en LeadDetailDrawer.tsx · NOT user-facing state display labels (those use ESTADO_CONFIG V9 mapping). UX labels button verbs "Limbo"/"Dentro" preserved en Marcos vocabulary per directive "mantén labels visibles ES".

6. **source_platform Python-side default callable**: `_derive_source_platform_default` auto-maps legacy source → V9 enum value cuando INSERT omite source_platform (testing convenience · production puede setear ambos explícitamente). Pattern reusable T1/T2 cuando otras tablas necesiten paralelo coexistence.

7. **10 pre-existing TS errors orthogonal**: Sesión 3B-2B.2 + cloud-connectors + admin pages tienen 10 errores TypeScript existentes pre-Phase-C · captured Future-X cleanup en sesión separate. Radar scope 0 nuevos errores.

8. **Polish test files `.spec.ts` modificaciones inexplicadas**: 3 archivos en `frontend/tests/polish/probe/` aparecieron modificados durante mi sesión (NO los toqué) · likely Sesión 3B-2B.2 in-flight collateral · NO part de Phase C scope · leave untouched.

---

## 6. Future-X captured

| Future-X item | Scope | ETA empírico |
|---|---|---|
| `Future-1.E.radar.tender-source-deprecate` | Refactor pipeline + sources/* + scoring/* read-path source → source_platform · drop legacy `source` col | ~2-3h |
| `Future-1.E.radar.tender-estado-enum-normalize` | Reconcile 10 live values → 6 spec values · pipeline mapping + ALTER constraint | ~1-2h |
| `Future-1.E.radar.alembic-version-num-widen` | ALTER alembic_version.version_num TYPE VARCHAR(64) · unblock b35 chain + future long revisions | ~30 min |
| `Future-1.E.radar.einforma-decision-makers-populate` | eInforma sync · poblar decision_makers table | ~3-5h (sub-atom dedicated) |
| `Future-1.E.frontend.typescript-pre-existing-errors` | Clean up 10 TS errors en admin/cloud-connectors/m14_contracts pre-Phase-C | ~1-2h |

---

## 7. Cliente piloto MEDIA impact

V9-ready schema completo · feature-prompts subsequent puede poblar incrementalmente:
- Feature-prompt 2 (eInforma) → poblar decision_makers + plantilla + facturacion + capital_social
- Feature-prompt 3 (AEAT/BORME) → reduce SIN_CIF_* placeholders + grupo_empresarial
- Feature-prompt 4 (LLM ENS detector) → poblar explicit_in_pliego + inferred_by_llm + categoria_requerida
- Feature-prompt 5 (vence_pronto tier) → poblar fin_presentacion crítico + c1-c5 criterios
- Feature-prompt 6 (outbound) → poblar jurisprudencia_citable JSONB + timeline_json

Cliente piloto MEDIA verá UX coherente desde día 1 cuando Marcos opera radar dashboard (frontend ya muestra display labels V9 spec §3.G).

---

## 8. Próximo · Phase D + E pending

Per Marcos directive STOP-AND-REPORT FINAL Phase C · espera confirmación antes arrancar Phase D.

| Phase | Scope | ETA briefing | ETA empírico esperado |
|---|---|---|---|
| **Phase D** | 14 indexes performance V9 · radar_leads (5) + companies (5) + tenders (6) + decision_makers (1) | 30-45 min | ~20-30 min (low complexity · just CREATE INDEX statements) |
| **Phase E** | test_models_v9.py 12 tests + Path A preservation verify | 60-75 min | ~45-60 min |

Cumulative Prompt 1B ETA proyectado: ~3.5-4.5h cumulative (within Marcos's expanded 5-7h target).

---

*Phase C atomic refactor CERRADO empíricamente · 2026-05-25 · branch radar-v9 paralelo fulkro-1.0 · STOP-AND-REPORT FINAL pending Marcos confirmation.*
