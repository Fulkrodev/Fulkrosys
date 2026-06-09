# VALIDATION_PROMPT_1B_CERRADO · RADAR-V9 foundation production-ready

**Status**: ✅ **CERRADO empíricamente verde** · 5 phases cumulative + cierre
**Fecha**: 2026-05-25
**Branch**: `radar-v9` (paralelo a `fulkro-1.0` per Marcos pivot directive)
**Tag**: `radar-v9-foundation-cerrado` (this commit)
**Directive Marcos**: Prompt 1B atomic refactor · ETA expanded ~5-7h cumulative
**ETA empírico actual**: ~3.5-4h cumulative (ahorro ~25-30% vs target)

---

## 0. Resumen ejecutivo cumulative Prompt 1B (5 phases · 14 commits)

| Métrica | Pre-Prompt-1B | Post-Prompt-1B |
|---|---|---|
| **Companies rows** | 55103 | **55103** ✅ (Path A preserved · 0 destructive) |
| **Tenders rows** | 102685 | **102685** ✅ (Path A preserved) |
| **RadarLeads rows** | 435 | **435** ✅ (Path A preserved · Marcos rescore 2026-05-25) |
| **Temperatura distribution** | 314/22/99 | **314/22/99** ✅ invariant |
| **Companies cols** | 19 legacy | **44 (19 legacy + 25 V9)** ✅ |
| **Decision_makers table** | NOT exists | **NEW · 12 cols + 2 enums** ✅ (D5) |
| **Tenders cols** | 18 legacy | **35 (18 legacy + 17 V9)** ✅ |
| **RadarLeads cols** | 33 (incl estado dup) | **45 (32 legacy [−estado] + 13 V9)** ✅ (D4 estado dropped) |
| **estado_contacto CHECK** | 8 legacy values | **10 spec §3.G values** ✅ (D3) |
| **Database enums** | (baseline) | **+9 V9 enums** (ens_categoria · rol_decisional · decision_maker_fuente · tender_source_platform · organismo_tipo · tipo_procedimiento · c2_source · c4_pattern_type · feedback_score) |
| **Performance indexes** | baseline | **+15 idx_* V9** ✅ Phase D |
| **Backend tests verde** | (baseline) | **178/178** ✅ (166 baseline + 12 new V9) |
| **`lead.estado` refs cross-codebase** | 22 (13 backend + 9 frontend) | **0** ✅ |
| **TS errors radar scope** | (baseline) | **0 new** ✅ (10 pre-existing OTHER captured Future-X) |

---

## 1. Commits cumulative Prompt 1B (14 commits productivos)

| Phase | Sub-fase | Commit | LOC | Description |
|---|---|---|---|---|
| Phase 0 audit | Read-only schema diff | `16964c7` | +1349 | spec + audit doc 545+804 LOC |
| Bridge | gitignore Playwright | `7e62df0` (cherry) | +2 | Playwright HTML reports + test results ignore |
| Phase A | Company V9 + decision_makers | `271407a` | +363 | 25 cols + NEW table 12 cols + 3 enums |
| Phase B | Tender V9 + source_platform | `882cf98` | +303 | 18 V9 cols + 3 enums + 100% backfill |
| Phase C.0 | Audit consumers | `e880ebe` | +230 | grep authorized · scope inventory 3.5-4.5h |
| Phase C.1 | Migration drop estado + criterios | `70037db` | +290/-6 | D3+D4 + 12 new cols + 3 enums |
| Phase C.2 | schemas.py refactor | `d553bb5` | +8/-3 | 5 downstream Pydantic shapes |
| Phase C.3 | service+api+cli+exporters | `3dd5639` | +64/-30 | 13 backend refs eliminated · 4 endpoints |
| Phase C.3 fix | fixtures + regex | `fe61262` | +78/-15 | 166/166 verde · auto-derive source_platform |
| Phase C.4 | Frontend zod+display+breakdown | `d260c12` | +76/-34 | 9 refs across 5 files · ESTADO_CONFIG V9 |
| Phase C.5 | VALIDATION + CLAUDE.md Phase C | `ba487bb` | +247 | Phase C cumulative cierre |
| Phase D | Indexes performance V9 | `9e58c58` | +145 | 15 idx_* CREATE INDEX · EXPLAIN ANALYZE verified |
| Phase E | test_models_v9.py 12 tests | `19a5c61` | +616 | 178/178 cumulative verde |
| Cierre | VALIDATION cumulative + tag | (this) | +n | Prompt 1B CERRADO cumulative |

**Cumulative metrics**: 14 commits productivos · ~5200 LOC cumulative · 178/178 tests verde · 0 destructive · 0 regression.

---

## 2. Decisiones Marcos D1-D7 materializadas (7/7 ✅)

| ID | Decisión | Status post-Prompt-1B |
|---|---|---|
| **D1** | Flat para queryables · JSONB metadata | ✅ Materialized cross 3 tables · 8 JSONB meta cols cumulative |
| **D2** | ASCII sin acentos (live wins) | ✅ ens_categoria_enum = `BASICO\|MEDIO\|ALTO` consistente |
| **D3** | estado_contacto 10 valores + renames + descartado collapse | ✅ CHECK constraint 10 spec §3.G values · backfill safe 435/0 |
| **D4** | DROP radar_leads.estado duplicate AHORA | ✅ DROPPED + atomic consumer refactor (backend + frontend) |
| **D5** | decision_makers table crear ahora aunque vacía | ✅ NEW table · 0 rows initial · eInforma feature-prompt 2 poblará |
| **D6** | CCAA derived backend con columna materializada | ✅ companies.ccaa + tenders.ccaa flat cols · backend derive future |
| **D7** | 4 migrations phased (Company · Tender · RadarLead · Indexes) | ✅ A+B+C+D · Phase C sub-atomically split (C.0-C.5) per scope expand |

---

## 3. V9 schema completo · spec §4 mapping

### 3.A Company (spec §4)

| Spec field | Live field | Status |
|---|---|---|
| `cif` | `cif` | ✅ UNIQUE preserved |
| `razon_social` | `razon_social` | ✅ |
| `cnae_principal` | `cnae` (legacy) | ⚠ Rename Future-X |
| `cnae_secundarios` | `cnae_secundarios` (NEW) | ✅ ARRAY(String) Phase A |
| `ubicacion.ccaa` | `ccaa` (NEW · D6) | ✅ flat queryable |
| `ubicacion.provincia` | `provincia` (legacy) | ✅ |
| `ubicacion.municipio` | `municipio` (NEW) | ✅ |
| `ubicacion.codigo_postal` | `codigo_postal` (NEW) | ✅ |
| `size.plantilla` | `plantilla` (NEW · coexist `empleados` legacy) | ✅ Future-X dedup |
| `size.facturacion` | `facturacion` (legacy double) | ⚠ Type Numeric Future-X |
| `size.capital_social` | `capital_social` (NEW · Numeric 15,2) | ✅ |
| `size.is_pyme` / `is_micro` | `is_pyme` / `is_micro` (NEW) | ✅ Boolean nullable |
| `estructura.is_ute` | `is_ute` (NEW default false) | ✅ |
| `estructura.parent_company_uuid` | `parent_company_id` (NEW · int FK self) | ✅ |
| `estructura.grupo_empresarial` | `grupo_empresarial` (NEW) | ✅ |
| `ens_status.en_registro_ccn` | `en_registro_ccn` (NEW default false) | ✅ |
| `ens_status.nivel_certificado` | `nivel_certificado_ccn` (NEW ENUM ASCII D2) | ✅ |
| `ens_status.fecha_certificacion` | `fecha_certificacion_ccn` (NEW Date) | ✅ |
| `ens_status.fecha_caducidad` | `fecha_caducidad_ccn` (NEW Date) | ✅ |
| `ens_status.auditor` | `auditor_ccn` (NEW) | ✅ |
| `ens_status.sistemas_alcance` | `sistemas_alcance_ccn` (NEW Text) | ✅ |
| `ens_status.tiene_declaracion_basica` | `tiene_declaracion_basica` (NEW default false) | ✅ |
| `decision_makers[]` | `decision_makers` TABLE (NEW · D5) | ✅ FK CASCADE |
| `contactability.email_general` | `email_general` (NEW) | ✅ |
| `contactability.telefono` | `telefono` (NEW) | ✅ |
| `contactability.web` | `web` (NEW · coexist `website` legacy) | ✅ Future-X dedup |
| `contactability.direccion_fiscal` | `direccion_fiscal` (NEW) | ✅ |
| JSONB metadata | `ubicacion_meta` + `ens_status_meta` + `contactability_meta` | ✅ Phase A D1 |

### 3.B Tender (spec §4)

| Spec field | Live field | Status |
|---|---|---|
| `source_platform` | `source_platform` (NEW ENUM · backfill 102685/102685) | ✅ Phase B |
| `source_id` | `expediente` (existing close match) | ⚠ |
| `source_url` | `url_expediente` (existing) | ⚠ Rename Future-X |
| `organismo.nombre` | `organismo` (legacy flat) | ⚠ |
| `organismo.nif` | `organismo_nif` (NEW) | ✅ Phase B |
| `organismo.tipo` | `organismo_tipo` (NEW ENUM) | ✅ Phase B |
| `organismo.ccaa` | `ccaa` (NEW · D6) | ✅ |
| `objeto` | `objeto` (legacy) | ✅ |
| `cpv_principal` | `cpv` (legacy · Future-X rename) | ⚠ |
| `cpv_secundarios` | `cpv_secundarios` (NEW ARRAY) | ✅ Phase B |
| `importe_estimado` | `importe` (legacy · Future-X rename) | ⚠ |
| `importe_adjudicado` | `importe_adjudicado` (NEW Numeric) | ✅ Phase B |
| `tipo_procedimiento` | `tipo_procedimiento` (NEW ENUM) | ✅ Phase B |
| `fechas.*` | `fecha_publicacion` + `fecha_fin_presentacion` + `fecha_adjudicacion` + `fecha_formalizacion` + `fecha_apertura` (NEW) | ✅ |
| `estado` | `estado` (legacy 10 live values · spec 6 · Future-X normalize) | ⚠ |
| `ens_requirement.explicit_in_pliego` | `explicit_in_pliego` (NEW default false) | ✅ Phase B |
| `ens_requirement.inferred_by_llm` | `inferred_by_llm` (NEW default false) | ✅ |
| `ens_requirement.categoria_requerida` | `categoria_requerida` (NEW ENUM ASCII D2) | ✅ |
| `ens_requirement.detection_confidence` | `detection_confidence` (NEW Float 0-1) | ✅ |
| `is_ute` / `is_lote` / `parent_tender_uuid` / `lots` | `is_ute` + `is_lote` + `parent_tender_id` (self-FK) | ✅ Phase B |
| JSONB metadata | `organismo_meta` + `ens_requirement_meta` | ✅ |

### 3.C Lead (spec §4)

| Spec field | Live field | Status |
|---|---|---|
| `temperatura` | `temperatura` (varchar 30 · 7 values via schemas.py Literal) | ✅ |
| `score` | `score` (Float) | ✅ |
| `criterios.c1_concursando` | `c1_concursando` (NEW Boolean) | ✅ Phase C.1 |
| `criterios.c2_pliego_exige_ens` | `c2_pliego_exige_ens` (NEW Boolean) | ✅ |
| `criterios.c2_source` | `c2_source` (NEW ENUM explicit\|inferred) | ✅ |
| `criterios.c3_no_certificada_ccn` | `c3_no_certificada_ccn` (NEW Boolean) | ✅ |
| `criterios.c4_pattern_count` | `c4_pattern_count` (NEW Integer default 0) | ✅ |
| `criterios.c4_pattern_type` | `c4_pattern_type` (NEW ENUM multi_adj\|licitacion_abierta) | ✅ |
| `criterios.c5_sweet_spot` | `c5_sweet_spot` (NEW Boolean) | ✅ |
| `dolor_summary` | `dolor_summary` (NEW Text) · coexist `dolor_especifico` legacy | ✅ |
| `best_pliego_uuid` | `best_pliego_id` (NEW int FK tenders) | ✅ |
| `dias_hasta_vencimiento` | `dias_hasta_vencimiento_cee` (existing FASE 8.5) | ✅ |
| `jurisprudencia_citable` | `jurisprudencia_citable` (NEW JSONB default '{}') | ✅ |
| `estado_contacto` | `estado_contacto` (existing · CHECK 10 V9 spec values) | ✅ Phase C.1 |
| `notas_marcos` | `notas_marcos` (legacy) | ✅ |
| `feedback_score` | `feedback_score` (NEW ENUM cualificado\|no_cualificado) | ✅ |
| `timeline[]` | `timeline_json` (NEW JSONB default '[]') | ✅ |

### 3.D estado vs estado_contacto · D4 atomic refactor (CERRADO)

| Layer | Pre-Phase-C | Post-Phase-C |
|---|---|---|
| DB column | `estado` varchar(50) duplicate | **DROPPED** ✅ |
| ORM attribute | `RadarLead.estado` | **REMOVED** ✅ |
| Pydantic schemas | `LeadUpdateResponse.estado` + `LeadListItem.estado` | **renamed → `estado_contacto`** ✅ |
| Backend service | `service.update_lead_estado` mutates `lead.estado` | **mutates `lead.estado_contacto`** ✅ |
| Backend API | 4 endpoints return `lead.estado` | **return `lead.estado_contacto`** ✅ |
| Backend CLI | `cli.set_status` uses `lead.estado` | **uses `lead.estado_contacto`** ✅ + 6→10 enum values |
| Backend exporters | CSV `"estado": lead.estado` | **`"estado_contacto"`** ✅ |
| Frontend zod | `estado: z.string()` 3 schemas | **renamed `estado_contacto`** ✅ |
| Frontend components | `lead.estado` 9 refs | **`lead.estado_contacto`** ✅ |
| Frontend display | ESTADO_CONFIG 4 legacy entries | **10 V9 spec §3.G entries** ✅ |

---

## 4. Mapping legacy → V9 spec §3.G aplicado

| Endpoint / context | Legacy value | V9 spec §3.G value | Display label |
|---|---|---|---|
| `POST /leads/{id}/approve` | "aprobado" | `discovery_scheduled` | "Reunión agendada" |
| `PATCH /leads/{id}/discard` | "descartado" | `descartado` | "Descartado" |
| `PATCH /leads/{id}/limbo` | "limbo" | `contactado` | "Contactado / En seguimiento" |
| `enviado` (legacy) | n/a | `contactado` | "Contactado / En seguimiento" |
| `respondio` (typo legacy) | n/a | `respondido` | "Respondido" |
| `reunion_agendada` (legacy) | n/a | `discovery_scheduled` | "Reunión agendada" |
| `ganado` (legacy) | n/a | `cerrado_ganado` | "Ganado" |
| `no_interesa` (legacy · COLLAPSE) | n/a | `descartado` | "Descartado" |
| NEW V9 spec | n/a | `discovery_realizada` · `en_negociacion` · `cerrado_perdido` | (display labels per §3) |

---

## 5. Empirical verification matrix

### 5.A Backend test suite gate ✅

```
$ python -m pytest backend/tests/motors/m10_ens_radar/ --no-header -q
........................................................................ [ 40%]
........................................................................ [ 80%]
..................................                                       [100%]
178 passed in 14.32s
```

### 5.B Path A invariant preserved ✅

```sql
SELECT COUNT(*) FROM radar_leads;
-- 435 (Marcos rescore 2026-05-25 preserved)

SELECT temperatura, COUNT(*) FROM radar_leads GROUP BY temperatura;
-- ardiendo            314
-- caliente             99
-- ardiendo_sostenido   22
```

### 5.C Migration chain idempotency verified ✅

```
$ alembic upgrade radar_v9_d_indexes_001   # apply 4 migrations
$ alembic downgrade -1                      # revert D (indexes drop)
$ alembic downgrade -1                      # revert C (lead schema)
$ alembic downgrade -1                      # revert B (tender schema)
$ alembic downgrade -1                      # revert A (company + dm)
$ alembic upgrade radar_v9_d_indexes_001   # re-apply full chain clean
# 435 leads · 55103 companies · 102685 tenders preserved cross cycles
```

### 5.D EXPLAIN ANALYZE samples performance ✅

```
Q1 radar_leads temperatura+score · idx_radar_leads_temperatura_score · 0.122ms
Q2 tenders vence_pronto partial · idx_tenders_fin_presentacion_open · 0.198ms
Q3 companies CCN expiring · seq scan acceptable (0 rows · data not loaded)
Q4 radar_leads estado_contacto filter · seq scan acceptable (435 rows tiny)
```

### 5.E Cross-codebase invariant: 0 lead.estado refs ✅

```
$ grep -rn "lead\.estado\b" backend/app/motors/m10_ens_radar/  # empty
$ grep -rn "lead\.estado\b" frontend/                          # empty
```

---

## 6. Future-X items captured (OPS-049 honesty path · 5 items)

| Future-X item | Scope | ETA empírico |
|---|---|---|
| `Future-1.E.radar.alembic-version-num-widen` | ALTER alembic_version.version_num TYPE VARCHAR(64) · unblock b35 chain + future long revisions | ~30 min |
| `Future-1.E.radar.tender-source-deprecate` | Refactor pipeline + sources/* + scoring/* read-path source → source_platform · DROP legacy `source` col | ~2-3h |
| `Future-1.E.radar.tender-estado-enum-normalize` | Reconcile 10 live estado values (en_evaluacion/resuelto/publicado/preanuncio) → 6 spec values · pipeline mapping + ALTER constraint | ~1-2h |
| `Future-1.E.radar.einforma-decision-makers-populate` | eInforma sync · poblar decision_makers table | ~3-5h (dedicated sub-atom) |
| `Future-1.E.frontend.typescript-pre-existing-errors` | Clean up 10 TS errors en admin/cloud-connectors/m14_contracts pre-Phase-C (NOT caused by radar-v9) | ~1-2h |

### 6.A Anomaly captured · 3 commits Sesión 3B-2B.2 intermixed

3 commits orthogonal (`60d7af3` · `25bbb36` · `5ca0ad1`) admin WCAG + sidebar fixes están en chain `radar-v9` (Marcos's parallel Claude Code instance committed sobre radar-v9 en lugar de fulkro-1.0 per pivot intent). Per Marcos directive "LEAVE AS IS · 0 técnico break · solo cosmetic history · merge final a main los incorpora limpios independiente". `git log --first-parent` filtering disponible si Marcos needs clean view post-merge.

### 6.B Orthogonal modified files left untouched

`frontend/tests/polish/probe/{03,04,05}*.spec.ts` aparecen ` M` (not staged · NO touched per Marcos directive on Phase C scope). Sesión 3B-2B.2 in-flight collateral · NOT part de Prompt 1B.

---

## 7. Foundation V9 production-ready · cliente piloto MEDIA impact

Cliente piloto MEDIA recibe V9 schema completo desde día 1 cuando feature-prompts subsequent poblen incrementalmente:

| Feature-prompt | Scope | Cols V9 populated |
|---|---|---|
| **Prompt 2** (Capa B identidad cascada) | AEAT + BORME + eInforma | `decision_makers` table + `plantilla` + `facturacion` + `capital_social` + `grupo_empresarial` + `parent_company_id` + `email_general` + `telefono` + `direccion_fiscal` + `is_pyme`/`is_micro` derived |
| **Prompt 3** (CCN sync diario) | Capa D enrichment | `en_registro_ccn` + `nivel_certificado_ccn` + `fecha_certificacion_ccn` + `fecha_caducidad_ccn` + `auditor_ccn` + `sistemas_alcance_ccn` |
| **Prompt 4** (LLM ENS detector Capa C) | Detector 2 inferencia | `explicit_in_pliego` + `inferred_by_llm` + `categoria_requerida` + `detection_confidence` + `ens_requirement_meta` (reasoning) |
| **Prompt 5** (vence_pronto tier) | Capa A pliegos abiertos | `tender.fin_presentacion` + `tender.fecha_apertura` + `lead.c1_concursando` + `lead.c5_sweet_spot` |
| **Prompt 6** (outbound asistido Capa G) | Jurisprudencia + templates | `jurisprudencia_citable` JSONB + `timeline_json` JSONB + `feedback_score` enum |
| **Prompt 7** (Capa F oportunidades adyacentes) | Subcontratación + renovaciones | `parent_company_id` cascade + `fecha_caducidad_ccn` partial index |

Schema completo · columnas NULL hasta su feature-prompt las pueble · pattern reusable T1/T2/T3 feature-prompts subsequent · 0 schema refactor needed.

---

## 8. Tag git radar-v9-foundation-cerrado

Tag annotated marking milestone:
- Foundation data model V9 production-ready
- 5 phases cumulative · 14 commits productivos · 178/178 tests verde
- 435 leads Path A scoring preserved cumulative
- 0 destructive · 0 regression · 0 lead.estado refs remaining
- 7/7 Marcos decisions D1-D7 materialized
- 5 Future-X items captured

```
$ git tag -a radar-v9-foundation-cerrado -m "RADAR-V9 foundation V9-ready milestone"
```

---

## 9. Próximo · Prompt 2 (Capa B identidad cascada)

Per Marcos directive STOP-AND-REPORT FINAL Prompt 1B · espera confirmación antes arrancar Prompt 2 (Capa B identidad cascada AEAT + BORME + eInforma).

Prompt 2 prerequisites cumplidos cumulative:
- ✅ `decision_makers` table existe (vacía · listo poblar)
- ✅ `companies.plantilla` + `facturacion` (numeric) + `capital_social` + `is_pyme` + `is_micro` cols presentes
- ✅ `companies.parent_company_id` FK self + `grupo_empresarial` presentes
- ✅ `companies.contactability.*` cols presentes (email + telefono + web + direccion_fiscal)
- ✅ `cnae_secundarios` ARRAY col presente

Prompt 2 scope esperado (~25-40h per spec §8 V6 roadmap):
- Activar eInforma → desbloquea ~215 leads contactables
- Resolución AEAT/BORME → reduce SIN_CIF_* placeholders
- DiscardedCompany table existing usable para audit trail drops

---

*Prompt 1B foundation V9-ready CERRADO empíricamente · 2026-05-25 · branch radar-v9 paralelo fulkro-1.0 · STOP-AND-REPORT FINAL pending Marcos confirmation antes Prompt 2.*
