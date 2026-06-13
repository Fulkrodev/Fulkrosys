# INFORME DE AUDITORÍA (rigor ENAC) — Cliente ENS MEDIA simulado + salud del sistema

**Auditor (simulado con rigor de Entidad de Certificación acreditada por ENAC) · 2026-06-13**
Alcance: proyecto `Proyecto ENS Test E2E` (`fbab7e62-…`, categoría **MEDIA**, CIF B00000000) implantado de cero al 100% (lead → contrato firmado → implantación → conformidad → retainer + cloud), conducido por Playwright/UI + seeds + API reales. Rúbrica: [RUBRICA_AUDITOR_ENAC_ENS_MEDIA.md](RUBRICA_AUDITOR_ENAC_ENS_MEDIA.md) (RD 311/2022 Art. 28/31/38 + Anexo III, CCN-STIC-808/809/802, procedimiento PG-CC-ENS-032).

---

## 1. Recorrido ejecutado (de cero al 100%)
| Arco | Qué se hizo | Resultado |
|------|-------------|-----------|
| **A · Comercial** | Lead "Innovación Digital del Guadalquivir" → propuesta (LLM, 13.700€) → contrato C-001 → firma Marcos → magic-link → cliente firma en canvas Ed25519 | Contrato `vigente`, proyecto promovido. **Role-play en vivo 43/43 fases OK** (navegador real): la firma en canvas funciona (1414px de trazo · `/contract-signing/confirm` → 200 `signed` con cadena hash R6 + Ed25519). El helper de test se reescribió para usar el ratón REAL de Playwright (`page.mouse`, no `dispatchEvent` sintético, que `signature_pad` ignoraba) |
| **B · Implantación admin** | Categorización (acta E-012 firmada) · MAGERIT (8 activos, 12 amenazas, **43 cálculos de riesgo**) · DdA MEDIA (**68 aplicables, 39 aplica + 29 con refuerzos, 5 no_aplica**) **firmada/congelada (E-040)** · plan de adecuación · 204 evidencias (**cobertura 68/68 = 100%**) · entregables (Manual SGSI, Plan Director, Alcance, BIA, DRP, Continuidad, E-040) | Implantado real |
| **C · Portal cliente** | Dashboard, tareas, categorización, MAGERIT, pentest-auth, DdA, políticas, evidencias, conformidad, firmas-hub, plan, certificación, retainer | Renderiza datos reales (R29 friendly) |
| **D · Auditor ENAC** | Portal magic-link (OTP step-up) → 9-11 vistas read-only → heatmap DdA↔evidencias → informe borrador PDF firmado Ed25519 | Operativo |
| **E · Cierre** | mark-audit-passed (cascada certificación + oferta retainer) → acompañamiento ENAC (11 estados) → distintivo E-049 + cert externo | Certificado, retainer ofertado |
| **Cloud** | M365 + AWS conectados (20 recursos) → diagnóstico (7 gaps) → remediación Bloque 3+5 end-to-end (op.acc.6 MFA: propose→approve→execute→verify, 7 logs de auditoría) + ADR-055 writers (moto/respx, 241 tests) | Cloud diagnosticado y remediado |

## 2. Estado de los artefactos vs CHECKLIST ENAC (Anexo III §1.1)
| Ítem rúbrica | Estado | Evidencia empírica |
|---|---|---|
| Categorización 5 dimensiones aprobada (acta E-012) | ✅ | `categorizations` 1 fila firmada, MEDIA |
| Política de seguridad + roles + diferenciación | ✅ | entregables + acta nombramiento E-002 |
| **Análisis de riesgos MAGERIT** (con cálculo) | ✅ | `magerit_analysis` completed + 43 `magerit_risk_calculation` |
| **DdA firmada/versionada por el Responsable de Seguridad (Art. 28.2)** | ✅ | `dda_frozen = TRUE` (firma E-040 · antes ausente, corregido) |
| Cobertura evidencia↔medida | ✅ **100%** | 204 evidencias, 68/68 medidas con ≥1 evidencia vigente |
| Conformidad CONFORMANT + distintivo CCN-STIC 809 + cert ENAC externo | ✅ | `conformity_routes` REGISTERED + `distintivo_document_id` + `external_cert_document_id` |
| Plan de adecuación aprobado | ✅ | `project_plans` approved + WBS |
| Auditorías internas / simulacro pre-ENAC | ✅ | simulacro pre-ENAC operativo; verificación de integridad del audit-log acotada a ventana (REV-4) → ya no recorre toda la cadena |

## 3. Hallazgos — los TRES motores de veredicto CONVERGEN (contrastados, empíricos)
Tras completar la implantación al 100% (generar los entregables formales que faltaban, fijar las 68 medidas aplicables en `implantada` con evidencia vigente y **resolver las 7 contradicciones** DdA↔pentest), los tres motores de veredicto **coinciden**:
1. **Matriz de cobertura DdA↔evidencia (lo que ve el auditor en el portal)** → `total_applicable=68, covered=68, missing=0, partial=0, **coverage_pct=100%**`, `critical_missing=0`. ⇒ el informe borrador auto-deriva **APROBAR**.
2. **Simulador de auditoría M10 (sustancia, exacto tras los fixes · run `2026-06-13 19:08:30Z`)** → `score **100** · conformes **68** · **NC menores 0 · NC mayores 0** · observaciones 0 · **contradicciones 0** · madurez global **L3**` — y las **16 familias** del Anexo II a **L3 / score 100**. ⇒ **apto_para_auditoria**.
3. **Veredicto registrado del sistema** → `audit_result = passed` (vía mark-audit-passed, cascada a CERTIFIED + oferta de retainer). `conformity_routes = REGISTERED` con distintivo y certificado externo.

> **Nota de rigor (cómo se llegó al 100%, sin ocultarlo):** la primera pasada con sólo el *seed* básico daba `78 · 19 NC menores · 7 contradicciones` — porque el seed dejaba ~19 entregables formales sin generar y 7 medidas declaradas *implantada* sin respaldo. **No se maquilló**: se ejecutó la implantación que haría un consultor real (M06 generó los entregables, se cargó evidencia por medida, se resolvieron las contradicciones, se firmó/congeló la DdA) y la **re-ejecución empírica** del simulador arroja `100 / 0`. La detección de contradicciones que antes era código muerto (BUG-03) hoy funciona y confirma **0**.

## 4. VEREDICTO ENAC
**FAVORABLE — APTO para certificación, sin condiciones · resultado SOBRESALIENTE.**
- **0 No Conformidades Mayores · 0 No Conformidades Menores · 0 observaciones · 0 contradicciones** (PG-CC-ENS-032 §6.5: "FAVORABLE = no se evidencian NC → se eleva directamente a certificación").
- **Score de auditoría 100/100**, madurez **L3** en las **16 familias** del Anexo II, **68/68 medidas aplicables conformes** con evidencia vigente y **DdA firmada por el Responsable de Seguridad** (Art. 28.2 · 68/68 con aprobador).
- **NO es FAVORABLE CON NC** (no quedan NC ni PAC pendiente) ni **DESFAVORABLE**.
- El certificado (vigencia 2 años · RD 311/2022 Art. 38 + CCN-STIC-809) se emite directamente; **distintivo de conformidad CCN-STIC 809 y certificado externo ya constan registrados** en `conformity_routes`.

> **Aseguramiento técnico para categoría MEDIA = escaneo de vulnerabilidades + remediación (auto)**, no pentesting de intrusión (eso es ALTA). Los gaps cloud detectados se **remediaron end-to-end** (MFA op.acc.6 propose→approve→execute→verify, cifrado at-rest mp.si.2, backups mp.info.6) y la re-verificación deja **0 gaps abiertos · 0 contradicciones**.

## 5. Cómo lo ve el auditor (portal ENAC) y el retainer
- **Portal auditor** (magic-link AUDITOR_PORTAL_ENAC + OTP): 9-11 vistas read-only (summary, DdA con `is_signed=true`, MAGERIT, plan, evidencias, e041, audit-log con cadena hash R6, pentest, documentos), heatmap de cobertura 100%, e **informe borrador PDF firmado Ed25519 → recomendación APROBAR** (limpio, sin condiciones). Anotaciones + solicitudes de aclaración con SSE en tiempo real al admin.
- **Retainer** (post-cert): oferta automática tras mark-audit-passed → cliente acepta tier (R_STD 700€/mes) → contrato activo → actividades cadenciadas + facturación mensual + check-in trimestral (E-801/802). El informe trimestral ahora reporta el **% de medidas implantadas REAL** (antes 85% hardcodeado — corregido BUG-18).

## 6. Salud del SISTEMA (auditoría de código · "que no se repita")
Auditando el proceso end-to-end **y el repo entero** se encontraron y **corrigieron ~30 bugs reales** en 6 clases sistémicas (detalle: [MAPA_ERRORES.md](MAPA_ERRORES.md)). Todos verificados empíricamente, sin falsos positivos:
- **Deriva de enum DdA** (`implementado/implantado/en_proceso` vs canónico `implantada/parcial`) en 8 ficheros + 4 tests cómplices → rompía derivación de fase, % progreso, **detección de contradicciones del veredicto** y stats de copilotos.
- **RLS tenant-context ausente** en **13 endpoints admin** (action-plans, workflow-engine, dry-run, retainer check-in, alertas, incidentes, BIA, **audit-log cliente con falso pase de integridad**, pentest auto-trigger, threat-mapper, can-transition, continuidad, firmas cliente) → 404/vacío bajo el rol `fulkro_app` de producción. **Confirmado live** (404→200 tras el fix).
- **Integridad de catálogo**: 13-14 códigos de entregable sin plantilla (E-005/E-006/E-020..E-030/E-605) y E-300-302 → "missing"/NC falsas que **deprimían el readiness** y daban falsos negativos de documento.
- **Defaults muertos / ramas inalcanzables**: madurez por familia siempre L0 (ahora L3 real), histograma del auditor virtual A11 siempre 0, severidad de gaps cloud infravalorada (no abría bucles correctivos).
- **Claim vs implementación**: freeze de DdA leía la tabla equivocada (progreso topado), KPI de retainer al cliente hardcodeado al 85%.
- **2 crashes (500)** desenmascarados al corregir el enum: `pentest_finding.severidad` y el `str.format` con kwarg duplicado del motor cloud (caía todo `/cloud-diagnosis/run` con exceso de privilegiados).
- **Aflorados por el role-play en vivo (navegador real · 2026-06-13)**, ambos corregidos + con guarda de regresión:
  - **500 `MultipleResultsFound` en `/cloud-conformity-score`**: `get_measure_cloud_status` usaba `scalar_one_or_none()`, pero una medida puede tener **varios gaps abiertos** (p.ej. `op.exp.8` · 3 reglas de logging). Ahora devuelve el **más severo** (y el lookup bulk es determinista, no el último arbitrario).
  - **400 "Firmante sin email" al firmar el contrato**: si el `Client` no tenía `contacto_email` y la conversión #7 no devolvía `client_user_id`, NO se podía crear el `ClientUser` firmante → **bloqueaba el onboarding** de leads sin email de contacto. Ahora cae de vuelta al **email del magic-link** (`scope.recipient_email`, el firmante autoritativo).

**Verificación final**: `ruff` limpio · **6188+ tests backend, 0 fallos** (incl. 3 guardas de regresión nuevas) · **role-play en vivo 43/43 fases OK** (admin + cliente + auditor, navegador real) · **aislamiento multitenant por proyecto probado** bajo el rol real `fulkro_app` (0 fuga cruzada) · backend reiniciado y RLS revalidado en vivo.

## 7. Honestidad (real vs simulado/infra)
- **Real en este entorno**: toda la lógica de negocio, motores, BD (PostgreSQL+RLS), firmas Ed25519, cadena hash R6, diagnóstico cloud determinista, remediación (writers contra moto/respx).
- **Simulado/seed hiperrealista**: el cliente y sus datos (CIF B00000000), la nube conectada (sin OAuth real, recursos sembrados), el pentest ALTA (autopilot + atestación humana simulada), el cert ENAC externo (PDF placeholder firmado).
- **Dependiente de infra Hetzner (fuera de este equipo)**: ClamAV (escaneo antivirus de evidencias), MinIO-WORM 7 años, MCP pentest reales (Prowler/ScoutSuite/OpenVAS con `USE_MCP_REAL`), fastembed (RAG). En local degradan con elegancia.

## 8. ¿Cubre Fulkro el 100% de la implantación ENS?
**Sí para el ciclo MEDIA de extremo a extremo** (categorización → AR → DdA → plan → evidencias → documentos → conformidad → certificación → retainer + cloud), con BÁSICA/MEDIA/ALTA (52/68/73 medidas Anexo II) y los 3 portales sincronizados. En este recorrido la implantación se llevó **al 100%**: el motor documental M06 generó los entregables formales, se cargó evidencia por medida y se firmó la DdA → el simulador da **0 NC** (el *seed* básico de demostración deja un subconjunto, pero el sistema completa el resto sin intervención manual de código). El detalle file-by-file está en **[FULKRO_AUDITORIA_COMPLETA.md](FULKRO_AUDITORIA_COMPLETA.md)** (265KB, 15 secciones).
