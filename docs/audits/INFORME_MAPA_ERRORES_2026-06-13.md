# MAPA DE ERRORES — Simulacro ENS-MEDIA cliente real + auditoría de sistema (2026-06-13)

> Registro de TODOS los fallos encontrados ejecutando el ciclo ENS completo de un cliente MEDIA
> (lead → implantación → auditoría → retainer + cloud) **y** auditando el sistema entero. Cada bug:
> causa raíz · impacto · fix · guarda de regresión ("para que no se repitan"). Estado: ✅ arreglado.
> Verificación: empírica, sin falsos positivos (cada bug confirmado leyendo la fuente o reproducido live).
> Proyecto de prueba: `fbab7e62-…` (Proyecto ENS Test E2E · CIF B00000000 · MEDIA).

## Resumen ejecutivo
- **~30 bugs reales corregidos** en 6 clases sistémicas. Patrón dominante: comparaciones contra
  literales/claves que **no existen** (enum drift) y endpoints admin **sin contexto RLS**, ambos
  invisibles porque la suite usa rol bypassrls y los specs no ejercían esas rutas.
- **0 regresiones**: suites afectadas verdes (1801+ tests). Fixes con guardas de regresión.
- Tras los fixes, el cliente MEDIA simulado queda genuinamente implantado y el portal auditor da APROBAR.

---

## CLASE 1 · Deriva del enum DdA `EstadoImplementacion` (SISTÉMICO) ✅
Enum canónico (`m03_dda/enums.py`): `no_valorado|no_implantada|parcial|implantada|no_aplica`. 8 ficheros comparaban contra `implementado`/`implantado`/`en_proceso` (inexistentes) → ramas muertas con datos reales.
| ID | Fichero | Impacto | Fix |
|----|---------|---------|-----|
| BUG-01 | core/workflow_state/{phase,items,signals}.py | derivación de fase + % progreso rotos (proyecto certificado mostraba `fase=pre_venta`) | `implementado→implantada`, `en_proceso→parcial` |
| BUG-01 | m10_audit_sim/audit_simulator.py | detección de contradicciones DdA↔evidencia/pentest muerta (`contradicciones_count` siempre 0) | idem |
| BUG-01 | m09_audit_prep/checklist_service.py | contradicciones del dossier muertas | idem |
| BUG-01 | m08_verification/integrations/m3_dda_updater.py | contradicción verificación↔DdA muerta | idem |
| BUG-01 | agents/copilot_project_state.py + m11_copiloto/api.py | stats DdA leían clave `implantado` inexistente | `.get("implantada")` |
**Cómplices**: 4 ficheros de test sembraban el literal incorrecto → verde falso. Corregidos a enum canónico (= guarda de regresión).

## CLASE 2 · Atributo/clave equivocada (drift ES/EN tras dead code) ✅
| ID | Fichero | Impacto | Fix |
|----|---------|---------|-----|
| BUG-03 | m10_audit_sim/audit_simulator.py:176 | `pentest_finding.severidad` (campo es `.severity`) → **500** en audit-sim+simulacro al activarse la rama tras BUG-01 | `.severity` |
| BUG-14 | m09_audit_prep/dossier_generator.py:493 | `f.get("severidad")` sobre dict con clave `"severity"` → resumen ejecutivo del **dossier ENAC** decía siempre "(0 críticos)" | `.get("severity")` |

## CLASE 3 · Más deriva de literal (query devuelve SIEMPRE 0) ✅
| ID | Fichero | Literal malo | Impacto | Fix |
|----|---------|--------------|---------|-----|
| BUG-09 | agents/agent_21_service.py (×3) | `aplicabilidad='aplicable'` | contaba 0 aplicables → **NC CRÍTICA falsa** en proyectos con riesgos MAGERIT | `<> 'no_aplica'` |
| BUG-10 | api/v1/projects.py:235 | `aplicabilidad=="aplicable"` | `dda_aplicables` siempre 0, pendientes sobrecontado | `!= "no_aplica"` |
| BUG-11 | m27_conformity/distintivo_generator.py:132 | `estado_implementacion='implementada'` | **Distintivo de Conformidad CCN-STIC 809** (doc oficial cliente) mostraba SIEMPRE 0% conformidad | `'implantada'` |
| BUG-12 | services/adaptive_dashboard_service.py:141 | `IN ('pendiente','en_curso')` | KPI "medidas pendientes" siempre 0 | `IN ('no_valorado','no_implantada','parcial')` |
| BUG-13 | services/adaptive_dashboard_service.py:167 | `status IN ('open','in_progress',...)` | KPI "riesgos abiertos" siempre 0 (enum es español) | `IN ('identificado','monitorizado','materializado')` |

## CLASE 4 · Default nunca recomputado / rama muerta ✅
| ID | Fichero | Impacto | Fix |
|----|---------|---------|-----|
| BUG-04 | m10_audit_sim/audit_simulator.py `_scores_by_family` | nivel de madurez POR FAMILIA siempre `L0` (global daba L3) | nivel = media de niveles de la familia |
| BUG-05 | m_cloud_connectors/diagnostic_gap_engine.py `_render_explanation` | `str.format(**raw_evidence, n_privileged=…)` kwarg DUPLICADO → **500 en todo `/cloud-diagnosis/run`** con exceso de privilegiados (op.acc.5) | dict único + capturar TypeError |
| BUG-15 | m09_audit_prep/dda_evidence_gap_service.py:71/305 | `family in {"op","mp"}` vs código 2º nivel (`op.acc`) → siempre False → severidad infravalorada → **no se abren bucles correctivos y GATE-7 ve menos NC** | comparar sobre el marco `split(".")[0]` |
| BUG-16 | agents/services/audit_dry_run_service.py + agents/agent_11_wrapper.py | histograma de madurez leía claves `_total_LX` inexistentes → **auditor virtual A11 (LLM) veía siempre L5..L0=0** | computar histograma de findings reales |

## CLASE 5 · Claim vs implementación ✅
| ID | Fichero | Impacto | Fix |
|----|---------|---------|-----|
| BUG-17 | core/workflow_state/items.py:334 | "DdA congelada" leía `dda_project_signatures` (solo lo escribe el flujo opcional E-040), no `aprobado_por` → progreso IMPLANTACIÓN topado 5/6 | leer `dda_entries.aprobado_por` |
| BUG-18 | m23_retainer/report_service.py:320 | `medidas_implementadas_pct=85.0` HARDCODED en informe de retainer al cliente (KPI falso + RAG fabricado) | computar de `dda_entries` reales |

## CLASE 6 · Integridad de catálogo (códigos sin plantilla → NC/missing falsos) ✅
| ID | Fichero | Impacto | Fix |
|----|---------|---------|-----|
| BUG-19 | m10_audit_sim/audit_questions.py | `documento_esperado` E-005/E-300/E-301/E-302 sin plantilla (E-300-302 son register-types m_live_records) → 4 NC de documento falsas | → None |
| BUG-20 | m09_audit_prep/internal_auditor.py:85 | Q-002 `code_required="E-005"` (sin plantilla, weight 3) → fallaba SIEMPRE, deprimía score E-701 | → `E-002` |
| BUG-21 | m09_audit_prep/checklist_service.py | `REQUIRED_DELIVERABLES` exigía 13-14 códigos sin plantilla (E-005,E-006,E-020..E-030,E-605) → errores incerrables → **readiness_score deprimido** (explica readiness ~60) | eliminados los huérfanos |

## CLASE 7 · RLS tenant-context ausente (latente bajo `fulkro_app` prod · 13) ✅
Mismo patrón que el simulacro 404. Endpoints admin que consultan tablas RLS vía `get_db` sin `set_tenant_context` → bajo `fulkro_app` (RLS) devuelven **404/vacío**. Tests pasaban por usar rol bypassrls. Fix canónico: `get_project_owner` (SECURITY DEFINER) + `set_tenant_context`. **EMPÍRICAMENTE confirmados live** (404→200 tras fix).
| ID | F | Fichero | Tabla RLS / Impacto |
|----|---|---------|---------------------|
| BUG-02 | — | m09_audit_prep/simulacro_pre_enac_api.py | simulacro pre-ENAC daba 404 "Project not found" (gate inoperativo) |
| BUG-22 | F1 | api/v1/action_plans.py | findings/incidents → dashboard K.3 vacío/404 |
| BUG-23 | F2 | m_workflow_engine/api.py (`_ensure_project_access`) | projects/client_tasks → 404/0% en TODA la superficie del motor |
| BUG-24 | F3 | agents/services/audit_dry_run_service.py | audit_dry_run_results → vacío |
| BUG-25 | F4 | m23_retainer/retainer_checkin_admin_api.py | quarterly reports invisibles a Marcos |
| BUG-26 | F5 | m18_communication/alerts_api.py | feed de alertas por proyecto vacío |
| BUG-27 | F6 | m19_risk/incident_admin_api.py | reportar incidente daba 404 siempre |
| BUG-28 | F7 | m19_risk/bia_api.py (`_ensure_project_exists`) | BIA CRUD 404 |
| BUG-29 | F8 | m21_portal_cliente/audit_api.py | client_user_audit vacío + **verify_chain_integrity sobre 0 filas = chain_valid=True (falso pase, SEGURIDAD)** |
| BUG-30 | F9 | m08_verification/pentest_auto_trigger_api.py | auto-trigger nunca creaba engagement |
| BUG-31 | F10 | m02_magerit/threat_auto_mapper_api.py | auto-map de amenazas siempre no-op |
| BUG-32 | F11 | core/workflow_blocking_api.py | "Proyecto no existe" → TODA transición de fase bloqueada |
| BUG-33 | F12 | m19_risk/continuidad_admin_api.py | lookup directo de projects antes de contexto → 404 |
| BUG-34 | F13 | m05_signing/api.py | cliente no veía sus propias firmas pendientes (404) |

---

## REVISADOS Y RESUELTOS (semánticos · verificados contra el catálogo, no-FP)
- **REV-1 ✅ RESUELTO** `m_cloud_connectors/gap_rules.py` + `integrations.py`: re-mapeo a canónico RD 311/2022 — cifrado-at-rest `mp.info.3`→**`mp.si.2`** (MEDIA/ALTA, ya no BÁSICA), backup `op.cont.3`→**`mp.info.6`**, privilegios `op.acc.5`→**`op.acc.2`**. 11 tests cómplices actualizados + mapa de recursos sincronizado. Cada re-mapeo contrastado contra `anexo2_rd311_2022.py`.
- **REV-2 ✅ RESUELTO** `audit_questions.py`: org.1→**E-100** (Política de Seguridad · E-001 era "Ficha Resumen Ejecutivo", doc equivocado · verificado en `template_catalog_v1.yaml`). Test seed corregido.
- **REV-3 ✅ RESUELTO** `documents.estado`: predicado canónico de "aprobado" = `approved_at IS NOT NULL AND estado IN ('approved','firmado','entregado')`.
- **REV-4 ✅ RESUELTO** Simulacro Pre-ENAC: `check_audit_log_integrity` acotado a ventana (`since_seq = max_seq − 2000`) → ya no recorre la cadena global.

## AFLORADOS POR EL ROLE-PLAY EN VIVO (navegador real · 2026-06-13 · 43/43 fases OK)
| Bug | Archivo | Síntoma | Fix |
|-----|---------|---------|-----|
| **BUG-35** | `frontend/tests/e2e/_helpers/sim-medio.ts` (`drawSignature`) | el trazo de canvas no registraba (lienzo vacío → "firma con tu dedo/ratón") porque `signature_pad` ignora `dispatchEvent(new PointerEvent)` sintético | usar el ratón REAL de Playwright (`page.mouse.*`) → 1414px de trazo · firma 200 `signed` |
| **BUG-36** | `m_cloud_connectors/integrations.py` `get_measure_cloud_status` | **500 `MultipleResultsFound`** en `/cloud-conformity-score` (una medida con ≥2 gaps abiertos · p.ej. `op.exp.8`) | `scalar_one_or_none()` → ordenar por severidad + `.first()` (más severo); bulk determinista |
| **BUG-37** | `m13_commercial/services/contract_signing_flow.py` `_resolve_or_create_signer` | **400 "Firmante sin email"** al firmar si el `Client` no tenía `contacto_email` y la conversión #7 no devolvía `client_user_id` → bloqueaba onboarding | fallback al email del magic-link (`scope.recipient_email`) · firmante autoritativo |

## GUARDAS DE REGRESIÓN AÑADIDAS
| Test | Cubre |
|------|-------|
| `m10_audit_sim/test_family_maturity_regression.py` | BUG-04 (nivel familia ≠ L0) |
| `m_cloud_connectors/test_render_explanation_regression.py` | BUG-05 (op.acc.2 sin crash) |
| `m09_audit_prep/test_simulacro_api_regression.py` | BUG-02 (endpoint scopea, no 404) |
| `m09_audit_prep/test_catalog_integrity_regression.py` | BUG-19/20/21 (códigos con plantilla) |
| `m_cloud_connectors/test_integrations_m03_m04_m07.py::test_measure_status_multiple_open_gaps_returns_most_severe` | **BUG-36** (multi-gap → más severo, sin 500) |
| `m13_commercial/test_contract_signing_flow.py::test_resolve_signer_falls_back_to_scope_recipient_email` (+ raises) | **BUG-37** (firmante sin contacto_email · fallback magic-link) |
| 4 tests de contradicción corregidos a enum canónico | BUG-01/03 |
| `test_m09_paso4` + `test_checkin_admin_api` + 11 tests cloud REV-1 actualizados | catálogo real + RLS 404 + códigos canónicos |

## NOTA DE COMPLETITUD (seed `seed-full-implantation`)
El lever de dev decía "DdA + FREEZE" pero no firmaba la DdA (E-040), no creaba acta de categorización, dejaba MAGERIT sin cálculo de riesgo y ~1/79 entregables → readiness ~60 aunque registraba `passed`. Para este cliente se completó vía motores reales (acta E-012 + firma E-040 + 43 risk-calcs MAGERIT + entregables); pendiente dejarlo permanente en el seed.
