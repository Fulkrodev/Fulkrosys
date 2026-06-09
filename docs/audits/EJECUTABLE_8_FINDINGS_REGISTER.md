# Ejecutable 8 · Findings Register (cumulative → Pasada 16)

> Registro único de hallazgos TAGGED para corrección/implementación en Pasada 16.
> Se alimenta por sección. Secciones A (discovery) + B (analysis) cargadas. Pendiente C (Pasadas 10-15).
> Fecha corte: 2026-05-30 (post-Checkpoint 2).

---

## 🔴 CRITICAL / BLOQUEANTE

| # | ID | Hallazgo | Pasada | Acción Pasada 16 (criterio aceptación) |
|---|----|----------|--------|------------------------------------------|
| 1 | **DB-DRIFT-01** | BD live stampeada en **3 revisiones pre-merge** vs árbol Alembic **1 head**; `radar_widen` aplicado por **DDL directo**. Causa **~110+ fallos pytest** (`cloud_gaps.approval_status does not exist`, `ck_project_lifecycle_events_event_type` sin `phase_changed`). 248 tablas / 3645 cols live. | 4, 6, 9 | **BLOQUEANTE #1** (directiva Marcos, en memoria `ejecutable-8-db-drift-pasada-16-acceptance`). Backup → migración propia widen `version_num` VARCHAR(32)→64/TEXT → capturar `radar_widen` DDL en migración real → **criterio: `upgrade head` sobre BD vacía = 248 tablas/3645 cols + `alembic check` SIN diff. PROHIBIDO `stamp`.** Antes de Bloque 7. |

## 🟠 HIGH

| # | ID | Hallazgo | Pasada | Acción Pasada 16 |
|---|----|----------|--------|------------------|
| 2 | **F-PASADA9-02** | Drift ORM/test: `ClientUser(role=...)` keyword inválido neutraliza **~56 tests** (notifications + m29_client_messaging). Fixture pasa `role`, modelo ORM no lo tiene. | 9 | Reconciliar fixture vs modelo: re-añadir attr `role` al ORM **o** actualizar factories notifications+m29. Determinar fuente de verdad (¿role movido a otra tabla en merge?). |
| 3 | **P7-F1** | **4 de 6 `workflow_gates`** definidos pero **SIN call site** (`require_magerit_analysis`, `require_some_evidence`, `require_pentest_authorisation`, `require_complete_audit_prep`). Handoffs ENS H3/H4/H6 NO enforced; gate pentest (ADR-014/020) no aplicado. | 7 | Cablear: `require_magerit_analysis` en m05_obligations, `require_some_evidence` en m09, `require_pentest_authorisation` en m08, `require_complete_audit_prep` en m31/m25. Si M09 `checklist_service.py:639` cubre H5, dedupe + eliminar gate huérfano. |
| 4 | **F-08-01** | Coach cliente `/coach` + `/coach/next-step` **rotos en runtime**: `ActionHint` no tiene `cliente_description`/`template_id` → `AttributeError` silencioso (except bare) → cliente siempre ve "Todo al día". Admin `/copilot/hint` SÍ funciona. | 8 | `portal_api.py:330-332` usar `top.description_cliente`; eliminar/mapear `template_id`; quitar except bare; test fase IMPLANTACIÓN devuelve acción. |
| 5 | **F-08-02** | SSE realtime cliente falla para `signing.*` + `m_audit_accompaniment` (NO en `CLIENTE_EVENT_TYPES`) → certificación + firmas degradan a polling 30s. | 8 | Añadir `signing.requested/signed/declined` + eventos accompaniment a `CLIENTE_EVENT_TYPES` + `event_matches_audience` en `core/sse_dispatcher.py`. |
| 6 | **F-PASADA9-03** | LLM prompt-injection guard: **2 fallos behavioral reales** (no bloquea "show me your system prompt"; falso-positivo context_bleed). | 9 | Tuning regex `security/llm_prompt_injection_guard.py` (`_SYSTEM_EXTRACTION_PATTERNS` permitir tokens intermedios; context_bleed dampening). Re-correr `test_llm_prompt_injection.py`. |
| 7 | **F-PASADA9-04** | Tests `test_pentest_admin_escalation` neutralizados: sin `pytestmark = real_auth` el stub autouse inyecta auth → `/dashboard/*` 200 sin auth. **NO es bypass de producción** (middleware verificado wired); es gap del test de regresión. | 9 | Añadir `pytestmark = pytest.mark.real_auth` a `backend/tests/security/test_pentest_admin_escalation.py`; esperar 401/403. |

## 🟡 MEDIUM

| # | ID | Hallazgo | Pasada | Acción Pasada 16 |
|---|----|----------|--------|------------------|
| 8 | **P7-F2** | Drift enum `WorkflowPhase` frontend (`dashboard.ts`: magerit/dda/auditoria/retainer_activo) vs backend canonical 10 fases. | 7 | Alinear type FE con enum BE (10 fases); generar tipos desde fuente única o test de coherencia enum FE↔BE. |
| 9 | **P7-F3** | Avance de fase **no atómico**: `projects.fase` UPDATE directo (auto_billing) desacoplado de gates y de `advance_step` (ClientTask). | 7 | Servicio único `transition_to_phase(project_id, target)` que valide gate + UPDATE + emita evento en una transacción. Reemplazar UPDATE de `auto_billing.py:250`. |
| 10 | **F-08-03** | `m07 check_expiring_evidence` STUB: no consulta `fecha_caducidad` ni alerta M18. | 8 | Query Evidence `fecha_caducidad < now+30d` + push M18 EscalationService. |
| 11 | **P6-F08** | Drift documental ADR: solo **9 ficheros físicos** (ADR-046..054) pese a citarse ADR-001..054 en CLAUDE.md. | 5, 6 | Anotar en CLAUDE.md que pre-046 viven en docs/doctrine/histórico, o crear stubs. Confirmar con Marcos. |
| 12 | **F-PASADA9-05** | CSP estricta frontend diferida (`TODO-SEC-CSP-001`) + CORS prod sin middleware explícito (same-origin vía Caddy). | 9 | Documentar/planificar FASE 13: CSP estricta con nonces Next.js; confirmar CORS prod intencional. (Solo documentar en P9.) |
| 13 | **F-PASADA9-07** | Clusters menores con fallos (m12 purposes count, paso7, m13 celery import, mcp_servers fallback, m10 recert, m14 adendas) — varios arrastran drift. | 9 | Triage post-drift: re-correr tras DB-DRIFT-01; corregir reales caso por caso (m10 recert wording, m12 policy_enforcer count ADR-020). |

## 🟢 LOW / INFO

| # | ID | Hallazgo | Pasada | Acción |
|---|----|----------|--------|--------|
| 14 | **P6-F03** | Naming `copilot` (EN) vs `copiloto`/`copiloto-cliente` (ES) en frontend — NO dead code, 3 dirs usados. | 6 | Documentar; considerar consolidación naming (low prio). |
| 15 | **P6-F05** | 10 scripts demo/load-test one-off no referenciados (demo_s8_*, run_all_demos.sh, load_test_*). | 6 | Archive → `backend/scripts/_archive/`. |
| 16 | **P6-F06** | DOS migraciones `radar_widen` mismo concepto (sector_text_001 tracked + llm_freetext_text_001 untracked). | 6 | Reservado a DB-DRIFT-01 (Pasada 16). |
| 17 | **P6-F07** | Rama git `fulkro-1.0` obsoleta (230 detrás de main, 1 adelante). | 6 | Confirmar con Marcos y borrar rama (radar-v9 NO borrar). |
| 18 | **F-08-04** | Drift ruta `retainer-offer` inexistente (real `retainer-checkin`). | 8 | `adaptive_dashboard_service.py:339` corregir href. |
| 19 | **F-08-05** | No hay trigger event-driven on-phase-change proactivo (cron diario). | 8 | Suscribir consumidor a `phase_changed` → nudge inmediato. NO crítico pre-piloto. |
| 20 | **P7-F4** | FASE 0 gobierno sin fase/motor dedicado (RSI/comité/política). | 2, 7 | Documentar deuda; evaluar fase `gobierno` en enum o gate `require_rsi_designated`. **Verificar a fondo en Pasada 10 contra los 3 manuales.** |
| 21 | **F-PASADA9-06** | audit_log 3-way OR: tagging existe en código pero 1260 filas live todas NULL/NULL (cláusula legacy). | 9 | Documentar; re-verificar poblado project_id/client_id tras resolver drift + ejercitar flows auditor. |

---

## Notas de Sección A (discovery) — actualizaciones de documentación (NO findings de código)

- README.md stale (Sesión 10.5) → refresh Pasada 16/20.
- Cifras CLAUDE.md stale (subestiman): 43 motores, 163 pages, 408 componentes, 210 migraciones, 248 tablas, 484 test files, 297 specs → refresh Pasada 20.
- `.Zone.Identifier` ADS junto a manuales → limpieza menor Pasada 16.

## Suite pytest baseline (Pasada 9 · REAL)

`5737 passed · 143 failed · 49 skipped · 42 deselected(@llm) · 20 errors · 547s`. Ratio behavior-vs-mock: **~88% behavior** (Postgres real vía fixture `db` transaccional + RLS + ASGI `async_client`) / **≤12% mock**. Tras resolver DB-DRIFT-01 (#1) + ClientUser role (#2), se espera recuperar ~110+~56 ≈ **~166 tests** (objetivo: failures → ~4-10 reales tuning).

---

# SECCIÓN C · Pasada 10 · ENS Coverage (corrección OBLIGATORIA, NO defer · doctrina #10)

> Detalle completo + matrices en `EJECUTABLE_8_PASADA_10_ENS_CYCLE_GROUND_TRUTH.md`.
> **Caveat**: validar TODA corrección de catálogo contra **RD 311/2022 Anexo II oficial** (el GT inline del briefing diverge de los manuales en op.exp.3/8/10 y mp.s.3). El path de implementación/evidencia EXISTE para las 73 medidas; lo que falla es la CALIDAD del catálogo + FASE 0 gobierno + 1 gap real ALTA.

## 🔴 CRITICAL

| # | ID | Hallazgo | Acción Pasada 16 |
|---|----|----------|------------------|
| 22 | **P10-CAT-NUM** (P10-F1/F3) | Catálogo `ens_measures_catalog_v1.yaml` numerado per **CCN-STIC 804 v2017 (RD 3/2010)** NO RD 311/2022 → familia **mp.info desplazada** (cat info.3=Cifrado/4=Firma/5=Sellos/6=Limpieza/9=Backup vs RD311 info.3=Firma/4=Sellos/5=Limpieza/6=Copias). **Inconsistente con `ens_measure_guias_ccn_v1.yaml`** (que ya usa RD311) → joins por measure_code fallan en mp.info.4/5/6. | Re-mapear códigos mp.info del catálogo a RD 311/2022; unificar con `ens_measure_guias_ccn_v1.yaml` (canon RD311); actualizar `fuente_oficial`. **COORDINAR con DB-DRIFT-01**: re-numerar puede requerir migración `ens_measures` → hacerlo dentro del trabajo de migraciones de Pasada 16. Tras fix, join 1:1 measure_code guías↔ens_measures. |

## 🟠 HIGH

### Cluster catálogo — aplicabilidad booleana (propaga al DdA, impacto real)
| # | ID | Corrección (validar vs Anexo II oficial) |
|---|----|-------------------------------------------|
| 23 | **P10-001** | `op.pl.4` Dimensionamiento ALTA-only → `aplica_basica:true, aplica_media:true` (+R1 ALTA). Excluía del DdA BÁSICA/MEDIA. |
| 24 | **P10-002** | `op.pl.2` + `op.pl.3` `aplica_basica:false` → `true`. |
| 25 | **P10-003** | `op.pl.5` `aplica_media:false` → `true` (+ R1+R2 ALTA). |
| 26 | **P10-004** | `op.acc.3` `aplica_basica:true` → `false` (categoria_minima MEDIA). |
| 27 | **P10-OPEXT3** | `op.ext.3` `aplica_media:true` → `false` (SOLO ALTA). |
| 28 | **P10-OPCONT4** | `op.cont.4` `aplica_media:true` → `false` (SOLO ALTA, +R1). |
| 29 | **P10-OPEXP8** | `op.exp.8` `aplica_basica:false` → revisar (manual: base); refuerzos MEDIA R1-R4. **Logging — relevante seguridad.** |
| 30 | **P10-OPEXP6** | `op.exp.6` refuerzos `{}` → MEDIA R1+R2 / ALTA R1-R4 (EDR). |
| 31 | **P10-MPIF6** | `mp.if.6` `aplica_basica:true` → `false` (NO BÁSICA). |
| 32 | **P10-MPPER1** | `mp.per.1` `aplica_basica:true` → `false` (NO BÁSICA; +R1 ALTA habilitación). |
| 33 | **P10-MPEQ2** | `mp.eq.2` `aplica_basica:true` → `false` (NO BÁSICA). |
| 34 | **P10-MPEQ4** | `mp.eq.4` ALTA-only → `aplica_basica:true, aplica_media:true` (+R1 M/A). |
| 35 | **P10-F2** | Refuerzos `{}` vacíos familia mp.s/mp.si/mp.sw → poblar per categoría vs manuales (mp.s.2 B:R1/M:R2/A:R2+R3; mp.si.2 A:R1+R2; mp.sw.1 M/A:R1-R4; etc). |

### Cluster FASE 0 gobierno (gap funcional real)
| # | ID | Hallazgo | Acción Pasada 16 |
|---|----|----------|------------------|
| 36 | **P10-F01** | `ENS_REQUIRED_ROLES` (m21 stakeholder_service.py:9-15) solo 5 roles — faltan **ASS** + **POC** (DA 3ª proveedores). | Añadir `ass` (cond. ≥MEDIA) + `poc`; actualizar `validate_ens_required_roles_assigned` + coverage. |
| 37 | **P10-F02** | E002 acta nombramiento solo 3 roles + RSA condicional, sin RInf/POC/ASS. | Extender E002 con RInf, POC, ASS; separar ASS (MEDIA+) de RSA (solo ALTA). |
| 38 | **P10-F03** | **SIN validación separación RSeg≠RSis** (estricta MEDIA+ALTA). | stakeholder_service: si MEDIA/ALTA y rseg==rsis → finding critical; BÁSICA → warning + medida compensatoria. |
| 39 | **P10-F04** | m05_signing solo `acta_comite` firmable 1ª clase. | Añadir SignableTypes: `acta_nombramiento_roles`, `documento_alcance`, `plan_adecuacion`, `acta_decision_adecuacion` (firma Dirección/RSeg + email templates). |
| 40 | **P10-F09** | SIN motor orquestador FASE 0 (m16 Role enum es destinatarios, no roles ENS). | Orquestación FASE 0 (thin wrapper m21+m06+m05_signing): kickoff→alcance→roles→comité→plan, distinguiendo BÁSICA (acumulables) vs MEDIA/ALTA (separación + ASS). |

### Gap de cobertura real
| # | ID | Hallazgo | Acción Pasada 16 |
|---|----|----------|------------------|
| 41 | **P10-F4** | `mp.info.3` ALTA **R4 firma CUALIFICADA NO cubierta** (m05 es eIDAS simple TIER1). Gap real categoría ALTA. | Documentar en DdA que mp.info.3 R4 requiere proveedor externo cualificado (`Future-1.F+.tier-2-eidas`); m05 TIER1 cubre BÁSICA + parcial MEDIA. Decidir con Marcos si ALTA es scope pre-piloto. |

## 🟡 MEDIUM
| # | ID | Hallazgo | Acción |
|---|----|----------|--------|
| 42 | **P10-F05** | Sin plantilla dedicada **Documento de Alcance del Sistema** (entregable FASE 0 §0.2). | Crear E-code Documento de Alcance firmable Dirección+RSeg. |
| 43 | **P10-F06** | Distintivo FASE 7 usa colores por categoría NO **Pantone Orange 021C** (CCN-STIC 809). | `distintivo_generator.py:213` color oficial #FE5000 (Pantone Orange 021C). |
| 44 | **P10-F07** | Sin control periodicidad **Comité** (semestral BÁSICA / trimestral MEDIA+ALTA). | Scheduler/validación cadencia comité + conteo actas firmadas + alerta pre-auditoría. |
| 45 | **P10-OPEXP5** | `op.exp.5` `aplica_basica:true` → `false` (manual: NO BÁSICA). | Corregir + re-seed. |
| 46 | **P10-OPMON** | `op.mon.1`/`op.mon.2` `aplica_basica:false` → revisar (manual: base) + refuerzos. | Alinear con manual o documentar excepción dimensional. |
| 47 | **P10-MPCOM** | refuerzos ALTA sub-spec: mp.com.2 → R1+R2+R3; mp.com.3 → R1+R2+R3+R4. | Actualizar YAML + verificar `ens_measure_refuerzos`. |
| 48 | **P10-F5/F6** | `mp.s.3` aplica_basica (divergencia manual L279) + `mp.si.1` aplica_basica:true → false. | Confirmar con Marcos vs Anexo II oficial. |

## 🟢 LOW / INFO
| # | ID | Hallazgo | Acción |
|---|----|----------|--------|
| 49 | **P10-F08** | m23 no codifica auditoría interna ≥50%/año + 100% bienal (MEDIA+ALTA). | Modelar plan auditoría interna por cobertura + gate pre-renovación. |
| 50 | **P10-F10** | m10_audit_sim deriva CMM L2/L3/L4 pero sin gate por categoría. | Gate cierre: bloquear firma Declaración si CMM medio < umbral (L2/L3/L4). |
| 51 | **P10-EVID-CAT** | `seed_ens_evidence_catalog` hardcodea applicable_categories=[B,M,A] a todas. | Derivar de `aplica_basica/media/alta` (bajo impacto; DdA filtra). |
| 52 | **P10-REFUERZOS-META** | refuerzos `{}` YAML vacíos/incompletos en ~12 medidas más (artefacto no-canónico; DdA usa tabla BOE). | Poblar YAML para coherencia documental o anotar no-autoritativo. |

## Veredicto Pasada 10
**Path lifecycle + 73 medidas: ✅ existe 0-100%.** Bloqueantes de CALIDAD ENS pre-Bloque 7: (1) saneamiento catálogo (numeración RD311 + ~16 aplicabilidades + refuerzos), acoplado a DB-DRIFT-01; (2) FASE 0 gobierno (roles ASS/POC + separación + firmables + orquestación); (3) distintivo Pantone. Gap cobertura ALTA: firma cualificada mp.info.3 R4 (diferido contractual).

---

# SECCIÓN C · Pasadas 11-15 · Deep Verification (cloud/onboarding/copilots/documents/frontend)

> Detalle en `EJECUTABLE_8_PASADA_{11,12,13,14,15}_*.md`.
> **CORRECCIÓN a P10-F04/P10-F1.04**: m05_signing tiene **11 SignableTypes** (acta_comite, policy_approval, dda, conformidad_ens, magerit_validation...). Actas de comité, políticas, DdA y conformidad SÍ son firmables de 1ª clase. El gap real es **más estrecho**: solo `E002 acta_nombramiento_roles`, `E150 plan_adecuacion` y `documento_alcance` carecen de SignableType dedicado (caen a `document_generic`). Ajustar P10-F04 a este alcance.

## 🟠 HIGH (nuevos)

| # | ID | Hallazgo | Pasada | Acción Pasada 16 |
|---|----|----------|--------|------------------|
| 53 | **F-13-02** | **LLM prompt-injection guard es DEAD CODE**: `security/llm_prompt_injection_guard.py` tiene 0 callers en producción (solo docstring + tests). La defensa anti-jailbreak está IMPLEMENTADA pero INACTIVA en copiloto cliente/admin/A14. (Pasada 9 halló 2 fallos tuning del guard que ni siquiera está wired.) | 13 | Wire `sanitize_user_input` pre-LLM en `copilot_cliente_service.generate_response` + `copilot_admin_service` + `portal_api` /coach//chat. should_block → audit_log + error friendly R29 (no break). Después, los 2 fallos tuning de Pasada 9 (F-PASADA9-03). |
| 54 | **F-13-01** | Rate limiter (`copilot_rate_limit`) NO wired en `m11_copiloto/portal_api.py` (`/coach`, `/chat/stream`, `/quick-actions`) — el router que el FE `copiloto.ts` consume. Caps token/coste/mes evadibles por esa vía. | 13 | Añadir `enforce_rate_limit_or_raise(tier='cliente')` en portal_copiloto_coach + chat/stream + quick-actions (mirror `client_copilot_stub.py:152`). Endpoints deterministas (hint/next-step) pueden omitirse. |
| 55 | **F-13-03** | Root cause exacto de F-08-01: `_resolve_coach_context` (portal_api.py:330-332) accede `top.cliente_description` + `top.template_id` inexistentes en dataclass `ActionHint` (campos reales `description_cliente`/`description_admin`/`target_url`) → AttributeError silenciado. (Refina/duplica F-08-01 #4). | 13 | Igual que #4 (F-08-01): usar `top.description_cliente`, sustituir `template_id`→`target_url`, verificar `top_action_for_role` retorna ActionHint. |
| 56 | **F-14-01** | m06 document_factory quedó FUERA de Ejecutable 7.6: NO importa `fulkro_identity` → footer/teléfono/web Fulkro NO propagados a las **124 plantillas** (políticas/procedimientos/entregables/actas). | 14 | Wirear `backend.app.fulkro_identity` en m06 (`rendering._inject_brand` + contexto header/footer), igual que `proposal_context.py`. |
| 57 | **F-14-02** | Branding visual inconsistente: m06 usa `assets/brand/logo_marcos.png` mientras la propuesta usa `fulkro-logo-light.svg`. | 14 | Unificar logo consultor a `fulkro-logo-light.svg` en `m06.service._CONSULTOR_LOGO`. |
| 58 | **F-14-03** | m06.generate_document NO emite audit_log canónico `document.generated`/`document.signed` → trazabilidad ENAC de generación documental ausente. | 14 | Emit audit_log Sub-atom 5.A 3-way OR (`document.generated`/`document.signed`) en `service.generate_document`, preservando hash chain R6. |

## 🟡 MEDIUM (nuevos)

| # | ID | Hallazgo | Pasada | Acción |
|---|----|----------|--------|--------|
| 59 | **F-13-04** | 2 violaciones **R3 temp>0.2** en motores LLM: `m05_obligations/personalization.py:99` (0.3) + `m10_ens_radar/outreach/draft_generator.py:713` (0.3). | 13 | Bajar ambas a ≤0.2 (o documentar excepción justificada — R3 es global). |
| 60 | **F-11-01** | AWS/Azure connectors descubren storage pero NO pueblan `public_access`/`encrypted_at_rest`/`backup_enabled`/`logging_enabled` → `mp.s.2`/`mp.info.3`/`op.cont.3`/`op.exp.8` nunca disparan para esos providers (detección shallow MVP, degrada graceful R1). | 11 | Documentar limitación; poblar `get_bucket_encryption`/`get_public_access_block`/`get_bucket_logging` (AWS) + equiv Azure (`Future-3B-2B-7-EXPANDED.aws/azure-connector`). Confirmar que el catálogo cliente no promete detección no entregada. |
| 61 | **F-12-01** | Email primer-acceso (`m21_portal_cliente/api.py:1351-1380`) HTML pobre + identidad NO centralizada (drift vs Ejecutable 7.6; estilo inline azul ajeno al branding violeta). Primer contacto cliente. | 12 | Importar `fulkro_identity` (FOOTER/EMAIL_SIGNATURE) + branding violeta (OPS-026 DRY). |
| 62 | **F-14-04** | `consultor.header_brand` (InlineImage logo) inyectado pero ningún template `.md` lo usa → embed muerto. | 14 | Consumir `header_brand` en partial Jinja común o eliminar embed muerto. |
| 63 | **F-14-05** | Documento de Alcance del SGSI dedicado FALTA (0 plantillas) — confirma P10-F05. | 14 | Crear E-code 'Documento de Alcance del SGSI' (CCN-STIC 805/809) personalizable per-proyecto. |
| 64 | **F-15-01** | `AuditAccompanimentClienteView` se suscribe a `useClientProjectEvents` pero no existe `AccompanimentEventType`/`certificacion.*` en `ClientSseEventType` → timeline certificación no refresca realtime (reconfirma F-08-02). | 15 | Añadir `AccompanimentEventType` a `ClientSseEventType` + emitir desde backend; conectar invalidate específico. (Junto a F-08-02 #5.) |

## 🟢 LOW / INFO (nuevos)

| # | ID | Hallazgo | Pasada | Acción |
|---|----|----------|--------|--------|
| 65 | **F-11-02** | AWS/Azure/GitHub en `_PROVIDER_CATALOG` (cliente puede conectar) pero SIN entrada en `CONNECTOR_PROVIDER_ENS_GUIDANCE` → `get_provider_ens_guidance` devuelve None. | 11 | Añadir guidance mínima honesta (op.exp.1+org.1) o marcar 'coming soon' en catálogo (R29 honestidad). |
| 66 | **F-11-04** | `detect_logging_disabled` (op.exp.8) + `detect_no_backup_strategy` (op.cont.3) son dead-code efectivo: ningún connector puebla `logging_enabled`/`backup_enabled`. | 11 | Degradar a 'documental' (como org.1) para que el cliente aporte evidencia manual, en vez de silencio (falso 'implemented'). |
| 67 | **F-13-05** | Cost controls m_observability son reporting-only; agentes opus A4/A11/A19 vía `/{id}/invoke` sin cap de coste. | 13 | Deuda: enforce a nivel AgentBase/router genérico post-piloto (Future-X). |
| 68 | **F-14-06** | Distintivo sin color canónico: `fulkro_identity` no define Pantone Orange 021C ni hex (confirma P10-F06). | 14 | Añadir constante color marca a `fulkro_identity.py` + `.ts`. |
| 69 | **F-12-02..05** | Onboarding: MFA no proactivo (solo settings/mfa), greeting estático sin time-of-day, jargon 'retainer post-cert' en tutorial, tutorial localStorage-only (no server-side). | 12 | Nudge MFA en tutorial (R29 sin presión); enriquecer greeting; suavizar copy; evaluar persistir `tutorial_completed` en ClientUser. |
| 70 | **F-14-07** | `E002 acta_nombramiento` + `E150 plan_adecuacion` solo firmables como `document_generic` (alcance estrecho del gap P10-F04). | 14 | Evaluar SignableType propio o documentar que document_generic es aceptable. |
| 71 | **F-15-02/03** | Estados loading/error/empty heterogéneos en thin client-pages; FulkroFooter global incluye portal auditor/público (¿condicionar por route group?). | 15 | Spot-check thin pages + decisión producto sobre footer en auditor-portal. |

## Veredicto Pasadas 11-15
Infraestructura **muy madura** (cloud cliente-mínimo 100%, onboarding hiper-intuitivo R29 fuerte, R30 admin tutor EXCELENTE, a11y gate estricto 97 specs/102 pages, 124 plantillas doc + propuesta perfecta). Gaps acotados: **seguridad LLM (guard dead-code + rate-limit no wired)**, **m06 sin identidad 7.6 + sin audit_log generación**, cobertura cloud shallow AWS/Azure, 2 R3 temp violations, onboarding polish. Ninguno rompe operación; F-13-01/02 y F-14-01/03 merecen prioridad en Pasada 16.

---

# Pasada 16 · DB-DRIFT-01 RESUELTO (core) + item dedicado registrado

**DB-DRIFT-01 (#1) — CORE RESUELTO** (commit `936d81ca`):
- ✅ Esquema reproducible desde migraciones: `alembic upgrade head` sobre BD vacía EJECUTA y produce 250 tablas / 3672 cols (verificado scratch). version_num widen 32→128. NO stamp.
- ✅ `phase_changed` añadido al CHECK (Future-1.E.workflow-trigger-bug-fix · ambas DBs).
- ✅ 3 tablas audit_accompaniment capturadas en migración (antes DDL-only).
- ✅ `alembic check` ya CORRE (FK + metadata imports resueltos); 16 tablas catálogo/raw excluidas (documentadas).
- ✅ audit_log model: +client_id/project_id (Sub-atom 5.A) — corregido drift sustantivo.

**NUEVO item dedicado (registrado, decisión Marcos "arreglar 2 sustantivos + seguir")**:
- **MODEL-MIGRATION-ALIGNMENT** (cosmético, NO afecta runtime · proyecto ~50 items): para `alembic check` 100% cero-diff faltan: (a) declarar ~40 índices creados solo-en-migración en los modelos ORM (tenders/radar_leads/companies/cloud_*/auditor_*/decision_makers/...), (b) **ENUM→String enum-deprecation** (`tenders.source_platform/organismo_tipo/tipo_procedimiento/categoria_requerida`, `companies.nivel_certificado_ccn`, `decision_makers.rol_decisional/fuente`, `radar_leads.c2_source/c4_pattern_type/feedback_score`) — los modelos ya usan String pero las migraciones crean ENUM → migración de conversión (= Future-1.E.radar.tender-source-deprecate + tender-estado-enum-normalize), (c) ruido nullable/type(BIGINT/DATE/REAL)/comment + algunos índices con expresión DESC. Sin impacto funcional (el esquema ES reproducible). Ejecutar como hardening dedicado post-Pasada-16.

---

# Pasada 16 · LIVE dev DB forward-migrated to head (2026-05-31)

DB-DRIFT-01 aplicado a LIVE `fulkro` (con backup `out/backups/fulkro_pre_p16_20260531.dump`):
- `ALTER alembic_version.version_num VARCHAR(32)→128` (manual · migración inicial ya corrió en live).
- `alembic upgrade head` REAL (NO stamp) desde los 3 heads pre-merge → aplicó `cloud_remediation_orchestrator_b35_001` + `remediation_enhancement_b35_e_001` (→ `cloud_gaps.approval_status` + `cloud_remediation_approval_logs`) + `sub_atom_5b_magerit_child_rls_001` + merges + radar_widen (idempotente) + `add_phase_changed_event_type_001` + `create_audit_accompaniment_tables_001` (IF NOT EXISTS).
- Live ahora: head `create_audit_accompaniment_tables_001` · approval_status ✓ · phase_changed ✓ · 249 tablas.
- Suite #1 (pre-migrate): 143→84 failed (ClientUser recuperado). Post live-migrate + conftest alias: clusters cloud/m14/billing recuperados (15err→2err en muestra). Pendiente full re-run autoritativo.

**Residual conocido (no bloqueante core)**:
- 3 magerit child RLS (`sub_atom_5b`) → `InFailedSQLTransactionError` bajo rol `fulkro_app` (RLS/GRANT del migration sub_atom_5b surfaced al aplicarlo) → debug RLS dedicado.
- 1 cloud state-machine assert (`verification_pending`) · 2 billing fixture errors · 2 LLM PI tuning (F-PASADA9-03) · ~3 paso7 purposes.

---

# Pasada 16 · Clasificación de tests fallidos (directiva Marcos · fuente obligatoria)

| Test | Clasificación | Acción | Fuente |
|------|---------------|--------|--------|
| test_paso7 ::test_34_purposes_total / test_purposes_registered | (b) test desactualizado | FIX test 35→36 | AUDITOR_PORTAL_ENAC añadido Sesión 3B-2B.6 (CLAUDE.md + memoria auditor-portal-architecture.md + enum) |
| security::test_blocks_show_system_prompt + test_legitimate_client_mention_not_flagged | (a) código mal | FIX código (guard regex + \b) | Propósito documentado del guard (bloquear system_extraction) + OWASP LLM01 |
| ClientUser role= fixtures (notifications + m29) | (a)/(b) modelo correcto, fixtures stale | FIX fixtures | ADR-013 v3 + migración san_e_mb3_cleanup_m21_drop_role_columns |
| pentest_admin_escalation | (b) test mal configurado | FIX (pytestmark real_auth) | Intención del test (regresión seguridad real_auth) |
| cloud/m14/billing 'client' fixture | (b) fixture name | FIX (alias conftest) | Canónico async_client (observable) |
| **🏷️ TAG MARCOS — test_all_purposes_have_email_template** | **AMBIGUO** | **NO TOCADO** | 5 purposes sin template (aprobacion_factura, validacion_cambio_alcance, aceptacion_riesgo_residual, consentimiento_tratamiento_datos, auditor_portal_enac). ¿(a) code gap → escribir 5 templates email R29, o (b) entrega out-of-band → relajar test? Sin fuente clara de diseño. **Marcos decide.** |
| **🏷️ TAG MARCOS — 3 magerit child RLS** (test_rls_multitenancy SubAtom5B) | **A INVESTIGAR (probable código)** | pendiente debug | sub_atom_5b RLS/GRANT surfaced al aplicar a live · InFailedSQLTransaction bajo fulkro_app. Probable GRANT/policy faltante (código) pero requiere debug dedicado antes de tocar. |
| **🏷️ TAG MARCOS — cloud test_admin_full_flow_then_audit_log** (verification_pending) | **A INVESTIGAR** | pendiente | assert sobre estado verification_pending · revisar si código state-machine o test. |
| **🏷️ TAG MARCOS — 2 billing test_api fixture errors** | **A INVESTIGAR** | pendiente | fixture client_user_authed · revisar tras alias. |

---

# Pasada 16 · magerit RLS (3 tests) + DEUDA conftest-live-DB (directivas Marcos)

## 🔒 magerit child RLS — SEGURIDAD VERIFICADA CORRECTA (no es bug de código)
Ejecutado el query cross-tenant REAL (directiva Marcos, no leído):
- Cada uno de los 3 tests (`test_client_a_cannot_see_magerit_assets_of_client_b`, `test_magerit_treatment_plan_isolation_via_analysis_id`, `test_no_tenant_context_returns_empty_magerit_assets`) **PASA en aislamiento** (`exit=0`).
- Query manual `SET ROLE fulkro_app; SELECT count(*) FROM magerit_assets;` sin contexto → **0 filas** (default-deny correcto). `current_project_id()` → NULL sin error.
- ⇒ La RLS de aislamiento multi-tenant sobre las 6 tablas hijas magerit (`sub_atom_5b`) **FUNCIONA**. No hay fuga cross-tenant. **Seguridad OK.**
- `fulkro_app` tiene GRANT en magerit_* en LIVE (init-roles `GRANT ON ALL TABLES`). (En scratch falta porque no corrí init-roles → artefacto de scratch, no de prod.)

## 🏷️ TAG MARCOS — flake de aislamiento de tests (NO seguridad, NO tocado sin causa raíz)
Los 3 tests fallan SOLO en contexto de fichero/suite (tras los otros 5 RLS tests del mismo fichero), con `InFailedSQLTransactionError` (cascade · el error original no es visible, pytest muestra solo el cascade en `RESET ROLE`/setup). El `db` fixture es function-scoped con engine+conexión NUEVOS por test (no hay leak de conexión obvio). Hipótesis asyncpg statement-cache post-DDL DESCARTADA (statement_cache_size=0 no lo arregló · revertido). Mecanismo exacto NO root-caused en tiempo razonable. Candidatos: acumulación de conexiones asyncpg por engine-per-test + event-loop, o estado server-side. **Requiere debug de test-infra dedicado.** NO es regresión de mis cambios (estaban en los 143 originales).

## 🔴 DEUDA REGISTRADA (directiva Marcos #2) — conftest reusa BD LIVE
`backend/tests/conftest.py::db` hace `create_async_engine(settings.database_url)` → la BD de test ES la **BD LIVE `fulkro`**, NO una BD construida desde `alembic upgrade head`. Consecuencias:
- Los tests corren contra el esquema drifteado de dev (raíz de DB-DRIFT-01 manifestándose como fallos de schema en la suite).
- Aplicar migraciones en caliente (como en P16) puede introducir flakiness (planes/estado).
- **Recomendación**: fixture session-scoped que (a) cree BD efímera `fulkro_test`, (b) `alembic upgrade head`, (c) seed mínimo, (d) drop al final. Aísla la suite del dev DB y la hace reproducible (alinea con criterio DB-DRIFT-01). Esfuerzo ~3-5h · post-P16 dedicado.

---

# Pasada 16 · Clasificación FINAL de fallos restantes (directiva Marcos · (a)/(b)+fuente/TAG)

## ✅ ARREGLADOS este batch (con fuente)
| Cluster | Clase | Fuente |
|---------|-------|--------|
| billing auto_billing (8) + test_api (2) | (b) test | ClientUser role= sweep · ADR-013 v3 + migración san_e_mb3_cleanup |
| mcp_smoke (3) | (b) test | kwargs server/tool/args/timeout_seconds (signature mcp_client.py:62 + prod callers) |
| mcp graceful fallback (código) | (a) código | try_invoke_mcp_or_none capta FileNotFoundError/OSError (contrato or_none) |
| m23 addendum freshness (1) | (a) código | import roto módulo inexistente → cálculo inline days-based (intención test) |
| remediation_orchestrator terminal (1) | (b) test | Phase A: EXECUTED→verification_pending (orchestrator:94-103) |
| remediation_orchestrator failed_path (1) | (b) test | Phase A: mark_failed enriquece metadata (subset assert) |
| m12 policy_enforcer (2) + email_renderer (1) | (b) test | AUDITOR_PORTAL_ENAC Sesión 3B-2B.6 |
| SSE count/subset, paso7, LLM guard, coach, R3, pentest, ClientUser/m29 | (a)+(b) | (commits previos) |

## 🏷️ TAG MARCOS (ambiguo / infra / sin fuente clara — NO tocados)
| Cluster | Por qué TAG |
|---------|-------------|
| **m13 celery_auto_import (4) + crm_extensions (1)** | Fallan AISLADOS con `InFailedSQLTransactionError` (cascade · error original enmascarado). No es flake (determinista) pero la raíz no se extrae barato. Posible bug de servicio auto-import O infra conftest-live-DB. **Necesita debug per-test surfacing del error original.** |
| **notifications test_redispatch_event_not_found (1)** | Mismo patrón abort-cascade · raíz enmascarada. Debug per-test. |
| **m_cloud_connectors test_remediation_api::test_admin_full_flow_then_audit_log (1)** | assert sobre estado `verification_pending` en audit_log (DB-integration · Phase A). Probable (b) test Phase A pero requiere verificar el flujo completo en DB. |
| **m23 timesheet (2) + api test_llm_observability::test_llm_top_consumers (1)** | DATA-dependent: asertan agregados globales (top clientes por minutos · top LLM consumers) contaminados por datos de la BD LIVE. **Síntoma directo de la deuda conftest-reusa-BD-live** (test no aislado). Se resuelven con BD test desde alembic upgrade head. |
| **m10 test_m10_proposal::test_recert_garantia (1)** | assert de COPY específica ('la renovación no queda lista para reauditar') ausente del PDF generado. El clause recert existe pero con wording distinto. Decisión de PRODUCTO (¿qué copy es correcta?) → Marcos. |
| **audit_fixes test_gap5 magic_link_hook (1)** | Test BRITTLE (grep literal `MagicLinkPurpose.APORTE_EVIDENCIA` en source api.py). El hook `_trigger_cliente_aporta_magic_link` EXISTE y se invoca (api.py:284) → plumbing presente. Test necesita reescritura funcional (no grep de string). Bajo valor. |
| **magerit RLS (3)** | SEGURIDAD VERIFICADA OK (cerrado per Marcos) · flake test-infra documentado. |
| **m_workflow_engine test_cliente_event_types_subset_of_admin (1)** | Invariante CLIENTE⊆ADMIN CONTRADICE diseño audiencias (admin denies client_notification/m02). Decisión: ¿admin superset o invariante incorrecta? → Marcos. |

---

# Pasada 17 · Cluster seguridad/wiring RESUELTO (F-13-01 + P7-F1) · 2026-05-31

Tres commits atómicos de código + tests, suite verde por batch, cero regresión. Disciplina audit→plan→batches con fuente citada.

## ✅ F-13-01 · rate-limit cliente wired en `m11_copiloto/portal_api.py` — RESUELTO (commit `88640299`)
- `enforce_rate_limit_or_raise(tier='cliente')` cableado en `/chat`, `/chat/stream`, `/coach` (superficies LLM) + `/quick-actions` (defense-in-depth).
- hard-block → 429 R29 friendly; soft-warn → `rate_limit_warning` en respuesta. `/hint` + `/coach/next-step` deterministas omitidos (per finding).
- Caps derivados on-query de `llm_interaction_log` (ADR-025, sin tablas nuevas). Mirror de `client_copilot_stub.py:152`.
- **Decisión de ingeniería señalada a Marcos**: el finding listaba coach + chat/stream + quick-actions; **añadí `/chat`** (superficie LLM alcanzable que el finding omitía, cerraba evasión de coste) y **auth dep a `/quick-actions`** (carecía de ella). Aceptado.
- 4 tests nuevos (`backend/tests/motors/m11_copiloto/test_portal_copilot_rate_limit.py`) · 106 copilot-suite verde.

## ✅ P7-F1 · 4 workflow_gates huérfanos conectados (antes 2/6, ahora 6/6) — RESUELTO (commits `5f08a511` + `45a7685a`)

| Handoff | Gate | Call-site | Condición | Commit |
|---|---|---|---|---|
| H3 | `require_magerit_analysis` | `m05_obligations/instantiation_service.py::instantiate_obligations_for_multiple_gaps` | siempre | `5f08a511` |
| H4 | `require_some_evidence` | `m09_audit_prep/checklist_service.py::run_full_checklist` | siempre | `5f08a511` |
| H5 | `require_complete_audit_prep` | `m25_lifecycle/lifecycle_service.py::transition` | **sólo `to_state=="CERTIFIED"`** | `45a7685a` |
| H6 | `require_pentest_authorisation` | `m08_verification/service.py::create_run` | **sólo `mode=="external"`** | `45a7685a` |

- Todos con param `enforce_gates=True` (patrón `m03_dda/service.py:92`). conftest fija `FULKRO_SKIP_WORKFLOW_GATES=1` → cero regresión (322 m05/m09 + 99 m04 + 346 m25/m08 verde).
- **Decisión de ingeniería señalada a Marcos (H5)**: el plan inicial decía `{CERTIFIED, RETAINER, ENDED_*}`; reducido a **sólo CERTIFIED** por topología de `VALID_TRANSITIONS`: RETAINER/ENDED_RENEWAL_OK sólo alcanzables DESDE CERTIFIED (ya gateado), y gatear ENDED_CHURN rompería el registro de un abandono legítimo sin dossier. Correcto y suficiente. Aceptado.
- **H6** condición `mode=="external"` per decisión Marcos (runs internal self-scan/dogfooding exentos · ADR-014/ADR-020 step-up sólo para acción técnica sobre infra del cliente).
- 8 tests nuevos (`backend/tests/core/test_workflow_gates_wiring.py`): raise + bypass por gate, + ENDED_CHURN-no-gateado + internal-no-gateado.

**Fuente**: EJECUTABLE_8_FINDINGS_REGISTER F-13-01 (Pasada 13) · EJECUTABLE_8_PASADA_7_COHERENCE_SYSTEMIC §2.2 (P7-F1, handoffs H3-H6) · ADR-014 · ADR-020 · ADR-025.

---

# Pasada 17 · monitoring absorbed — VERIFICADO + F-08-03 RESUELTO · 2026-06-01

Audit-first del subsistema monitoring/observability/compliance. Conclusión "absorbed": ya estaba **production-ready**, no requería pasada de construcción. Un único gap de código real cerrado.

## ✅ VERIFICADO production-ready (sin tocar · ya estaba bien)
Subsistema **100% DB-backed, cero mocks en rutas de producción, cero endpoints huérfanos**:
- `m_compliance_monitor` · 19 checks + alerts + reports (tablas `compliance_checks/alerts/reports`) · 4 tareas Celery beat **registradas y vivas** (daily/weekly/monthly/quarterly).
- `m_compliance` · breach + erasure RGPD (Art. 33/34) · DB real.
- `m_observability` · coste/anomalías LLM desde `llm_interaction_log` (ADR-025).
- `admin_system_health` aggregator (19 checks + LLM anomalías + test conexión DB) · REAL.
- `admin_cross_project_compliance` · agregado multi-tenant cross-motor · REAL.
- `operations.py` overview (backups/restore/renewals) · REAL.
- SSE `sse_dispatcher` + `dashboard_events` · event-driven real (incl. `alert_new`).
- Frontend: `/admin/compliance/monitor`, `/admin/system-health`, `/admin/llm-observability`, `/admin/compliance/projects`, `/admin/operations` · todos consumen datos reales.

## ✅ F-08-03 RESUELTO (commit `c6ba02c7`)
`m07_evidence/tasks.py::check_expiring_evidence` era un **stub vivo** (en Celery beat diario 06:00 pero solo logueaba). Ahora implementación real:
- `fecha_caducidad < hoy` → escalado M18 `evidencia_critica_caducada` idempotente (no duplica · corre a diario).
- `hoy ≤ fecha_caducidad < hoy+30d` → solo recuento+log, NO escala (semántica honesta · decisión Marcos · no abusar del trigger "caducada" con evidencia vigente).
- Cross-tenant `SET LOCAL ROLE fulkro` (patrón m23_retainer/tasks). 3 tests nuevos · 162 m07+m18 verde.

## Pendientes del subsistema — etiquetados por causa honesta (NO son deuda de código propia)
| Item | Categoría | Razón |
|---|---|---|
| F-13-05 · cap coste agentes opus vía `/{id}/invoke` | **decisión-Marcos** | Diferido a post-piloto por Marcos (reporting-only suficiente pre-piloto). NO deuda. |
| `eval_runner.py` evaluators skeleton | **no-prod-path** | Golden-eval regression harness · NO ruta de producción · se rellena cuando haya evaluadores LLM. |
| Norma-reports UI (17 scorecards) | **UI-demand-driven** | Backend completo (`/admin/compliance/norma-reports/*`) · UI cuando haya demanda. |
| Operations overview UI polish | **UI-demand-driven** | Endpoint completo + spec p2/25 pasa · polish demand-driven. |
| `/admin/cross-project-compliance` redirect legacy | **intencional** | Backward-compat (Sesión 3B-1 B.2) · canónico `/admin/compliance/projects` activo. |
| Firma cualificada eIDAS (ALTA) · pentest OSCP | **trabajo-terceros** | NO se implementan · se integran con cliente ALTA real (proveedor eIDAS + pentester certificado). |

**Resultado Pasada 17**: monitoring verificado production-ready + último gap de código (F-08-03) cerrado. Cero deuda de código propia en el subsistema; cada pendiente con su causa (decisión-Marcos / no-prod-path / UI-demand-driven / trabajo-terceros).

---

# Pasada 18 · SYSTEM_KNOWLEDGE_BASE + copilots wiring · 2026-06-01

Audit-first del knowledge de copilotos + creación del auto-conocimiento de plataforma. 2 commits (Batch A doc `b9bbd87d` + Batch B código `37bfb724`), suite verde (497 agents+copilot PASS), cero regresión.

## Mapa empírico (qué consumían los copilotos)
- A14 RAG (`/chat`, `/chat/stream`, `/coach` · lo que usa el FE): corpus **normativo ENS** (RD 311/2022 + CCN-STIC 800-808 + DORA/NIS2/RGPD/eIDAS + AEPD) vía `hybrid_search` + PageContext/coach + contactos M30 + identidad Fulkro. Regla estricta: si no está en RAG → "No encontrado en el corpus oficial".
- Copilot cliente stub + admin stub: **prompt-only** (persona YAML + metadata · sin corpus).
- **Gap real**: ningún camino respondía **uso de plataforma** ("¿cómo subo evidencia?", "¿qué hago en esta fase?") de forma fundamentada. `SYSTEM_KNOWLEDGE_BASE.md` no existía (solo referenciado como futuro en los prompts y CLAUDE.md).

## Resuelto
- **Batch A** (`b9bbd87d`) — *documentación-de-lo-que-existe*: creado `docs/SYSTEM_KNOWLEDGE_BASE.md`. Estructura derivada de **código real verificado**: nav cliente real `frontend/components/layout/ClientSidebar.tsx` (`CLIENT_NAV_SECTIONS`) + 10 fases `workflow_phase.py` + `fulkro_identity.py`. Copy cliente-facing marcado **⚠ REVISIÓN CONSULTOR** (pendiente pasada Marcos · criterio E-155).
- **Batch B** (`37bfb724`) — *código*: constante compacta `backend/app/agents/system_knowledge.py` (cliente + admin) inyectada en A14 runtime+spec + cliente stub + admin stub. **Opción 1** (decisión Marcos): SIN ingestión en corpus RAG; plataforma se cita `[Fulkro Plataforma]`; R2 ENS intacto (fallback "No encontrado en corpus oficial" preservado). 7 tests deterministas + 497 agents/copilot suite verde.

## Verificado ya-resuelto (findings de Pasada 13 · NO re-tocados)
| Finding | Estado | Evidencia |
|---|---|---|
| **F-13-02** PI guard dead-code | **RESUELTO** (ejecutable previo) | `sanitize_user_input` wired en `agent_14_copiloto/service.py:384` + `:516`. |
| **F-13-03 / F-08-01** coach AttributeError | **RESUELTO** | `_resolve_coach_context` usa `description_cliente`/`motor`/`target_url` (campos reales de `ActionHint`). |

## Pendiente por causa honesta (NO deuda de código)
| Item | Categoría | Razón |
|---|---|---|
| Secciones ⚠ REVISIÓN CONSULTOR del .md | **decisión-producto** | Copy cliente-facing requiere pasada de Marcos antes de exponerse como definitivo. Plumbing + estructura factual hechos. |
| Inventario script-por-script (Pasada 5) | **doc-demand-driven** | Catalogación detallada de scripts diferida · no bloquea copilotos. |

## Nota de proceso (honestidad)
La primera tanda de Batch A/B se ejecutó en paralelo y se canceló en cascada tras un error de shell; además el `.md`/constante iniciales salieron de memoria (nav inventada · referencia errónea a `ClientPortalNav.tsx`, que no existe). **Rehecho íntegro** con la nav real de `ClientSidebar.tsx` (labels verificados por test). Causa raíz del shell: el Bash tool corre desde Windows (`C:\\Python313`) sobre rutas `//wsl.localhost/...`; los heredocs Python fallaban por encoding cp1252 → todo Python se corre vía `wsl.exe -d Ubuntu -- bash -lc` con el venv del repo.

---

# Verificación aislamiento copilotos (petición Marcos pre-Batch) · 2026-06-01

Verificación empírica de aislamiento + conexión por proyecto de los 2 copilotos (admin + cliente). Lectura de código + psql sobre `fulkro_test` + probe ASGI/SQL. NO se tocó código de producción.

## Seguridad — 4/4 puntos SAFE (confirmado psql)
Hechos base: `projects` `relrowsecurity=t`+`relforcerowsecurity=t`, política `client_isolation` (ALL) `client_id = current_client_id()`; `current_client_id()=NULLIF(current_setting('app.current_client_id',true),'')::uuid`; rol runtime `fulkro_app` `rolbypassrls=f`; sin contexto → `SELECT count(*) FROM projects`=**0** (fail-closed). NO existe `tenant_rls_middleware.py` (ls confirmó). `authenticate_request` (global_dep.py:214-216) setea SOLO `app.current_user`.

1. **Admin project-scoping**: `project_id` del payload (admin_copilot_stub.py:67-69→182-186); router `require_owner` (admin_copilot_stub.py:44+121); query `WHERE id=:pid` (copilot_persona_service.py:148-153). SAFE: owner único por diseño (R23), no hay 2º pool admin que filtrar.
2. **Cliente project-scoping**: query NO filtra por user.client_id en código (`WHERE p.id=:pid`, copilot_persona_service.py:69-78); aislamiento forzado por RLS. Aunque se mande project_id ajeno → 0 filas (fail-closed). SAFE, NO fuga cross-tenant.
3. **Selector → portal admin**: scope per-request explícito (`project_id: req.projectId`, copilot.ts:80,171); resto del portal project-scoped vía route param + `set_tenant_context` (~70 call-sites). No se pierde de forma insegura.
4. **Admin+cliente mismo proyecto**: ambos apuntan a la misma fila `projects.id` (cliente resuelto server-side m21 api.py:526; admin desde selector); `projects.fase` source of truth única (workflow_phase.py:26-27). Mismo estado. Matiz: SSE `phase_changed` admin-only → la *vista* cliente puede ir con latencia (refetch), no divergencia de estado.

## 🏷️ TAG F-18-01 (FUNCIONAL · fail-closed · NO seguridad) — copiloto cliente no setea `app.current_client_id`

**Confirmado en runtime (probe SQL · A/B sobre datos idénticos + SANITY proj_exists=True, cid_match=True):**
- A · prod-réplica (solo `app.current_user`, lo que hace el copiloto hoy): query `SELECT id FROM projects WHERE client_id=:cid` → **raw_visible=None** (RLS oculta su proyecto).
- B · control (+ `app.current_client_id`): misma query, mismos datos → **raw_visible=<project_id>**.
- Única diferencia A↔B = la llamada `set_config('app.current_client_id',...)` → es el **contexto que falta, no datos ausentes**. Esa query es idéntica a `_resolve_project_meta` (portal_api.py:99-106).
- (El wrapper HTTP del probe dio 401 al no poder saltar limpiamente el global dep que exige cookie; irrelevante para el hallazgo, que se confirma a nivel SQL/RLS — la capa donde vive el gap.)

**Causa raíz (file:line):**
- `authenticate_request` (global_dep.py:214-216) setea solo `app.current_user`; NO `app.current_client_id`. No hay tenant-RLS middleware.
- Paths copiloto cliente usan `get_db` plano y NO llaman `set_tenant_context` (grep `set_tenant_context|set_config`=0 en ambos):
  - `m11_copiloto/portal_api.py`: `_resolve_project_meta` (:89-109, query :99-106) consumido por `/chat` (:150, resol :191), `/chat/stream` (:219, resol :230), `/coach` (:342), `/coach/next-step` (:431), `/hint` (:550, resol :565).
  - `api/v1/client_copilot_stub.py`: `client_copilot_chat` (:124) → `generate_response` (:193) → `build_client_context` (copilot_persona_service.py:67-91, query :69-78).
  - NO afectado: `/quick-actions` (catálogo estático, no consulta projects).
- Síntoma: `/hint`→`has_action=False`; `/chat`+`/coach`→**404** (portal_api.py:192-194). El admin tendría portfolio/contexto a 0 por la misma razón.

**Por qué nunca saltó en tests**: el `db` fixture del conftest SÍ setea `app.current_client_id` (conftest.py:160,216) — contexto que producción no pone → tests verdes, runtime ciego.

**Patrón de fix (NO hoy · batch dedicado · entorno estable + suite verificable):**
- Espejar `m17_planning/portal_api.py:141` (`set_tenant_context(db, client_id=user.client_id, project_id=...)`). Poner `set_tenant_context(client_id=user.client_id)` antes de `_resolve_project_meta` (RLS projects es por client_id) y `project_id` tras resolver para lecturas project-scoped (`compute_workflow_state`).

**Sutileza CRÍTICA (por la que NO es one-liner):**
- `set_tenant_context` usa `is_local=true` (auto-reset fin de transacción · evita bleed de GUC entre peticiones que reúsen conexión del pool).
- `/chat/stream` hace `await db.commit()` (portal_api.py:250) ANTES de que el generador ejecute `answer_question` → un GUC `is_local=true` puesto antes se PIERDE tras ese commit. Fix correcto: re-setear tras cada commit intermedio.
- `is_local=false` PROHIBIDO: el GUC persistiría en la conexión del pool y podría filtrarse a la siguiente petición de OTRO cliente → eso SÍ sería fuga cross-tenant (fallo de seguridad real). Por eso el fix debe ser per-commit con is_local=true.

**Test del fix (prod-fiel · OBLIGATORIO):** NO usar el atajo del conftest (su `db` setea `app.current_client_id`→falso verde). Replicar prod: sesión `get_db` sin client_id + override `get_current_client_user`; assert A(sin ctx)=ciego/404 vs B(con ctx)=ve-proyecto sobre datos idénticos (probe ya validó la diferencia a nivel SQL).

**Clasificación**: gap de CÓDIGO real (no doc, no producto). Severidad funcional alta (copiloto cliente inoperante sobre su proyecto en prod) pero **fail-closed** (NO fuga).

**Estado: ✅ RESUELTO (Batch 1 · 2026-06-01).**
- **commit 1 `2f95803c`** — `_resolve_project_meta_scoped` (única puerta correcta · `set_tenant_context(client_id)` ANTES de resolver, `project_id` tras resolver) wired en los 5 paths deterministas + stub (`/chat`, `/coach`, `/coach/next-step`, `/hint`, `client_copilot_chat`→`build_client_context`). Tests prod-fieles: A/B helper inequívoco + `/coach/next-step` + `/hint` + `build_client_context` (sin ctx genérico / con ctx real · path 6 cubre la rama LLM que el stub NO ejercita sin `llm_enabled()`, comentado en código).
- **commit 2 `2be0b4fa`** — `/chat/stream`: resolución vía `_resolve_project_meta_scoped` + **re-set del contexto DENTRO del generador SSE** tras el `db.commit()` pre-stream que tira el GUC `is_local` (sin el re-set, las lecturas project-scoped del generador serían ciegas). Test DEMUESTRA (no assert 200 ciego): lectura project-scoped DENTRO del stream, con commit REAL, ve el proyecto (`client_id` setting == cid AND `seen_project` == pid) + brazo-mecanismo A(ciego tras commit)/B(re-set restaura).
- **Suite copiloto+agents: 490 passed, 0 failed, 0 skipped, 1 rerun** (flake LLM conocido `agents/test_agent_20.py` `*_real_llm` · A20 contract narrative · NO relacionado con F-18-01 · falló una vez y pasó al reintento vía pytest-rerunfailures). `grep TEMP-NEUTER` en `backend/` = 0 antes de cada commit.
- `is_local=false` sigue PROHIBIDO (bleed cross-tenant): el fix re-setea per-commit con `is_local=true`.

---

## 🏷️ TAG F-18-01b (FUNCIONAL · fail-closed · NO seguridad) — m17 comparte el bug latente (resolver-antes-de-setear)

> **Distinto de F-18-01** (pese al prefijo): F-18-01 es el copiloto cliente `m11` (✅ RESUELTO Batch 1). **F-18-01b es `m17_planning`** → **✅ RESUELTO (Batch m17 · commit `d84e2bfc`)**.

**Hallazgo (mismo patrón fail-closed que F-18-01):** `m17_planning/portal_api.py` resuelve el proyecto ANTES de setear el contexto RLS, el orden mal:
- `:135` `project_id = await _resolve_project_id(db, user.client_id)` ← query `SELECT id FROM projects WHERE client_id=:cid` corre **sin** `app.current_client_id` → en prod (fulkro_app, RLS activa, sin middleware tenant) es **ciega** → `project_id=None` → **404** en `get_cliente_plan_timeline`.
- `:141` `await set_tenant_context(db, client_id=user.client_id, project_id=project_id)` ← setea el contexto DESPUÉS de resolver · demasiado tarde para la propia resolución (solo sirve para las lecturas project-scoped posteriores).

**Por qué nunca saltó:** mismo enmascaramiento que F-18-01 — el `db` fixture del conftest setea `app.current_client_id` → verde en tests, ciego en runtime.

**Nota Batch 1:** este es exactamente el "inline que deja escapar el orden mal" que motivó centralizar `_resolve_project_meta_scoped` en `m11` (puerta única que hace imposible olvidar el orden). m17 **no** se tocó en Batch 1 (scope = copiloto cliente).

**Clasificación**: gap de CÓDIGO real · severidad funcional alta (timeline cliente 404 en prod) · **fail-closed** (NO fuga).

**Estado: ✅ RESUELTO (Batch m17 · 2026-06-01 · commit `d84e2bfc`).**
- **Auditoría previa (PARA antes de tocar código):** 1 solo endpoint afectado (`get_cliente_plan_timeline`). Admin `m17_planning/api.py` **NO afectado** — resuelve `client_id` vía `get_project_owner()` **`SECURITY DEFINER`** (bypassa RLS por diseño · migración `7c63d18af556`), así que su resolver-antes-de-setear es seguro. **Sin commit-boundary intermedio**: el único `db.commit()` del endpoint (`:249`) es **terminal** (no hay lecturas project-scoped después) → **NO** requiere re-set tras commit (a diferencia de `/chat/stream` en F-18-01).
- **Fix (Opción B · replicar espejando m11, decisión Marcos):** NEW `_resolve_project_id_scoped` — `set_tenant_context(client_id)` ANTES de `_resolve_project_id`, `project_id` tras resolver. Usado en `:135`; eliminado el `set_tenant_context` redundante de `:141`. `is_local=true` SIEMPRE (`is_local=false` PROHIBIDO · bleed cross-tenant).
- **Test prod-fiel** (NO `setup_test_project`, que setea `app.current_client_id` → falso verde · `test_portal_plan_tenant_context.py`): A/B helper inequívoco (`_resolve_project_id` ciego/None vs `_resolve_project_id_scoped` ve, datos idénticos) + endpoint prod-fiel (siembra sin ctx → sin fix 404 ciego, con fix 200 que VE sus 3 tasks).
- **Suite `backend/tests/motors/m17_planning/`: 74 passed, 0 failed, 0 skipped, 0 rerun** (72 existentes + 2 nuevos · 6.08s). `grep TEMP-NEUTER backend/` = 0.

**Razón Opción B sobre A (helper compartido cross-motor):** con solo 2 consumidores (m11 + m17), A obligaría a reabrir m11 (cerrado/verificado · re-validar suite 46 min) o a aceptar **dualidad de puertas** (lo peor); B es de riesgo contenido y honra la convención vigente (m11 y m17 ya tenían cada uno su `_resolve_project_id`).

**Future-X capturado (NO ahora · cuando aparezca el 3er consumidor):** `Future-X.portal-cliente.extract-shared-scoped-resolution-gate` — extraer una **puerta única cross-motor** ("set `client_id` → resolve active project → set `project_id`", `is_local=true`) a infra neutral de portal cliente (p.ej. `m21_portal_cliente` o `core/`, sin acoplar m11↔m17 directamente) y **migrar m11 + m17 + el nuevo a la vez**, deliberadamente. Justificación: la extracción se paga sola con ≥3 consumidores; con 2 la duplicación de ~5 líneas es preferible a reabrir código cerrado o a la dualidad de puertas.
