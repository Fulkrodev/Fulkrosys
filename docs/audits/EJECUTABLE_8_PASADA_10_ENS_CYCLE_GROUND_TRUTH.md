# Ejecutable 8 · Pasada 10 · ENS Cycle 0-100% contra 3 Manuales Ground-Truth

> **CORAZÓN DEL EJECUTABLE 8.** Verificación empírica de que el sistema FULKRO permite implementar ENS ÍNTEGRAMENTE 0-100% según los 3 manuales (RD 311/2022, edición mayo 2026). GAP de cobertura = corrección OBLIGATORIA (NO defer).
> **Fecha**: 2026-05-30 · **Método**: 5 agentes paralelos (1 lifecycle 8 fases + 4 slices marco) file-by-file contra `docs/ens-manuales/` + catálogo `docs/catalogs/ens_measures_catalog_v1.yaml`.
> **Granularidad**: matriz completa 73 medidas × 3 categorías + 8 fases × 3 categorías (directiva Marcos).

---

## 0. VEREDICTO EJECUTIVO

El sistema **PERMITE ejecutar el ciclo ENS 0-100% en sus líneas maestras**: el PATH de implementación/evidencia **EXISTE para las 8 fases y las 73 medidas** (m03_dda genera entry per medida con applicability + estado/justificación; m07/`seed_ens_evidence_catalog` garantiza requisito de evidencia por familia; m06 genera docs E-codes PSI/normativa/POS CCN-STIC 805; m08_verification mapea medidas técnicas a runners MCP Anexo II; m05_signing firma; m09 dossier per marco). **Fases 1-6 y 8 ✅; FASE 0 gobierno ⚠️/❌; FASE 7 cierre BÁSICA ⚠️.**

Pero la Pasada 10 revela **2 clases de gap serias** (corrección OBLIGATORIA Pasada 16):

### A) CATÁLOGO `ens_measures_catalog_v1.yaml` con errores sistemáticos — el hallazgo ENS más grave

- **Mismatch de numeración**: el YAML está numerado per **CCN-STIC 804 v2017 (RD 3/2010)**, NO **RD 311/2022 Anexo II**. Esto **desplaza toda la familia `mp.info`**: catálogo tiene mp.info.3=Cifrado / 4=Firma / 5=Sellos / 6=Limpieza / 9=Backup, mientras RD 311/2022 (y el fichero hermano `ens_measure_guias_ccn_v1.yaml`) usa mp.info.3=Firma / 4=Sellos / 5=Limpieza / 6=Copias. **Los dos ficheros de catálogo son INCONSISTENTES entre sí en `mp.info`.**
- **~16 errores de aplicabilidad booleana** (`aplica_basica/media/alta`) que **SÍ propagan al DdA** (m03 los carga del catálogo→DB): `op.pl.2/op.pl.3/op.pl.4` excluidas de BÁSICA erróneamente (op.pl.4 grave ALTA-only); `op.pl.5` MEDIA falta; `op.acc.3` BÁSICA errónea; `op.exp.5` BÁSICA errónea; `op.exp.8`/`op.mon.1`/`op.mon.2` BÁSICA falta (logging/monitor); `op.ext.3`/`op.cont.4` MEDIA errónea (son SOLO ALTA); `op.ext.4` MEDIA falta; `mp.if.6`/`mp.per.1`/`mp.eq.2`/`mp.si.1` BÁSICA errónea; `mp.eq.4` ALTA-only errónea; `mp.s.3` (divergencia manual).
- **~20 `refuerzos{}` vacíos o incorrectos** en el YAML. **MITIGANTE CLAVE (verificado por 3 agentes)**: el DdA **NO usa el dict `refuerzos{}` del YAML** — usa la tabla `ens_measure_refuerzos` parseada determinísticamente de BOE-A-2022-7191 Anexo II (`seed_ens_measure_refuerzos.py`, trazable `source_chunk_id`). Por tanto los refuerzos del YAML son **artefacto secundario engañoso (deuda metadata)** que NO rompe el DdA; las **aplicabilidades booleanas SÍ** impactan.
- `seed_ens_evidence_catalog` asigna `applicable_categories=[BASICA,MEDIA,ALTA]` a TODAS las medidas — la distinción NO-APLICA recae 100% en m03_dda (que funciona correctamente).

### B) FASE 0 GOBIERNO incompleta (confirma Pasadas 2/7 con especificidad)

- `ENS_REQUIRED_ROLES` (m21_diagnosis) solo 5 roles `{sponsor, ri, rs, rseg, rsis}` — **FALTAN ASS** (Administrador Seguridad Sistema) **y POC** (Punto de Contacto, DA 3ª, obligatorio proveedores).
- E002 acta nombramiento solo nombra 3 roles + RSA condicional, **sin RInf ni POC**, conflactando ASS con "Responsable Seguridad Alta".
- **SIN validación de separación jerárquica RSeg≠RSis** (estricta en MEDIA+ALTA; el auditor la comprueba).
- m05_signing solo `acta_comite` firmable de 1ª clase; `acta_nombramiento`/`documento_alcance`/`plan_adecuacion`/`acta_decision_adecuacion` → escape hatch `document_generic`. **Falta documento de alcance dedicado.**
- **SIN control de periodicidad de comité** (semestral BÁSICA / trimestral MEDIA+ALTA).
- **SIN motor orquestador de gobierno FASE 0**.

### Otros gaps reales de cobertura

- **FASE 7 BÁSICA**: el distintivo usa colores por categoría (verde/azul/violeta, `distintivo_generator.py:213`) **NO el oficial Pantone Orange 021C** (CCN-STIC 809).
- **mp.info.3 ALTA R4 firma CUALIFICADA NO cubierta** (m05 es eIDAS simple TIER1 explícito; qualified diferido `Future-1.F+.tier-2-eidas`). **Gap real para categoría ALTA.**
- **FASE 8**: m23 no codifica explícitamente la regla de auditoría interna **≥50%/año + 100% bienal** (MEDIA+ALTA, obligatoria).

### Caveat metodológico (honestidad empírica)

El ground-truth **INLINE del briefing** diverge de los manuales en algunas medidas (`op.exp.3`, `op.exp.8`, `op.exp.10`, `mp.s.3`). Los agentes priorizaron correctamente los **3 MANUALES + RD 311/2022 Anexo II** como criterio designado. **Las correcciones de catálogo en Pasada 16 DEBEN validarse contra RD 311/2022 Anexo II oficial** (no contra el slice inline del briefing), por la ambigüedad en unas pocas medidas de planificación/explotación.

## Conclusión de cobertura

| Dimensión | Veredicto |
|-----------|-----------|
| Path lifecycle 8 fases | ✅ existe 0-100% (fases 1-6/8); ⚠️/❌ FASE 0 gobierno; ⚠️ FASE 7 BÁSICA distintivo |
| Path 73 medidas (DdA+evidencia+docs+verificación) | ✅ existe para las 73 |
| Calidad catálogo (numeración + applicability + refuerzos) | ❌ requiere saneamiento (numeración RD 311/2022 + ~16 applicabilidades + ~20 refuerzos) |
| Cobertura real ALTA firma cualificada (mp.info.3 R4) | ❌ gap (eIDAS simple, qualified diferido) |

**El sistema es funcionalmente capaz de llevar BÁSICA/MEDIA/ALTA**, pero (1) el saneamiento del catálogo ENS, (2) el cierre de FASE 0 gobierno y (3) el distintivo Pantone son **bloqueantes de calidad ENS** antes del dogfooding Bloque 7. La firma cualificada ALTA (mp.info.3 R4) es gap de cobertura ALTA conocido (diferido contractual).


---

## MATRICES POR SLICE (evidencia file-by-file)

### Slice 1 · 8 FASES ENS lifecycle × 3 categorías

## PASADA 10 · SLICE: 8 FASES ENS LIFECYCLE × 3 CATEGORÍAS + ENTREGABLES FIRMABLES

Ground-truth: `docs/ens-manuales/ENS_{BASICA,MEDIA,ALTA}_Manual_Implantacion_Completo.md`. Motores verificados: m01, m02, m03/m04, m06, m05_obligations, m05_signing, m07/m09, m10_audit_sim, m_audit_accompaniment, m27_conformity, m18, m23, m21_diagnosis.

### MATRIZ FASE × CATEGORÍA (✅ full / ⚠️ partial / ❌ gap)

| FASE | BÁSICA | MEDIA | ALTA | Entregables firmables verificados |
|------|--------|-------|------|-----------------------------------|
| **0 · Arranque/Alcance/Gobierno** | ⚠️ | ❌ | ❌ | Plantillas existen (E001 acta arranque, E002 acta nombramiento, E003 acta comité, E150 plan adecuación CCN-STIC 806) pero **solo `acta_comite` es signable de 1ª clase** en `m05_signing/signable_types.py:16`. acta_nombramiento / documento_alcance / plan_adecuacion → escape hatch `document_generic`. **Falta documento de alcance dedicado**. BÁSICA roles acumulables ⚠️ parcial (E002 nombra 3 roles). MEDIA/ALTA ❌: sin validación separación jerárquica RSeg≠RSis (estricta, auditor la comprueba per manual MEDIA §0.3), ASS/POC ausentes del nombramiento. Comité semestral BÁSICA / trimestral MEDIA+ALTA → NO hay control de periodicidad de comité por categoría. |
| **1 · Categorización (5 dims C/I/T/A/D)** | ✅ | ✅ | ✅ | m01 wizard 5 dimensiones + regla mayor dimensión + herencia cliente público. Documento E012 acta aprobación categorización + DdA. Firmable vía `acta_comite`/`policy_approval`. BÁSICA todas BAJO / MEDIA ≥1 MEDIO / ALTA ≥1 ALTO. |
| **2 · Análisis de riesgos** | ✅ | ✅ | ✅ | m02 MAGERIT. informal BÁSICA / semi-formal MEDIA op.pl.1 R1 / formal cuantitativo ALTA op.pl.1 R2. E400 BIA. `magerit_validation` signable. Acta aceptación riesgo residual Dirección vía firma. |
| **3 · SoA / DdA (73 medidas)** | ✅ | ✅ | ✅ | m03_dda holds 73 medidas applicability + estado/justificación + refuerzos Rn + compensatorias CCN-STIC 819. m04_gap. `dda` signable (E-040) con step-up OTP. Firmable RSeg. |
| **4 · Marco documental** | ✅ | ✅ | ✅ | m06 `documentation_levels.py` CCN-STIC 805: PSI [org.1]=E100 nivel 1, Normativas [org.2]=E101-E126 nivel 2, POS [org.3]=E200-E2xx nivel 3. BÁSICA esencial vs MEDIA+ALTA 10 docs vs ALTA +continuidad/cadena/sellos. `policy_approval` signable. |
| **5 · Implantación 73 medidas** | ✅ | ✅ | ✅ | m05_obligations instanciación + estado per medida (`api.py:200 VALID_ESTADOS_OBLIGATION`) + m08_verification runners MCP mapeados Anexo II. Distingue no-aplica vía DdA. |
| **6 · Evidencias / registros** | ✅ | ✅ | ✅ | m07 evidence (seed_ens_evidence_catalog) + m09 dossier per marco org/op/mp + m_live_records. |
| **7 · Cierre** | ⚠️ | ✅ | ✅ | **BÁSICA**: m_audit_accompaniment state machine BÁSICO 6 estados (drafted→signed→published→review→completed); m10_audit_sim CMM L2/L3/L4 + criterios 808; m27 `distintivo_generator.py` + `declaration_docx` (809 Anexo A) + `ines_generator` + LUCIA/AMPARO; `conformidad_ens` signable Dirección. **GAP**: distintivo usa colores por categoría (verde/azul/violeta `distintivo_generator.py:213`) NO el oficial **Pantone Orange 021C** (manual BÁSICA §7.6). **MEDIA/ALTA** ✅: 11-state machine (prep→docs→internal_audit→ENAC scheduled→in_progress→findings_resolution→passed→cert_issued→biannual). Fase 1 documental + Fase 2 campo + NC Mayor/Menor/Observación + PAC modelados. ALTA pentester externo mp.s.2 R2+R3 (slice medidas otra pasada). |
| **8 · Mantenimiento** | ✅ | ✅ | ✅ | m27 `renewal_scheduler.py` T-90 (ALERT_3M_BEFORE_DAYS=90, 730d biennial); m27 `lucia_federation.py` CCN-CERT/CCN-STIC 845 incidentes; m18 art.33 (AEPD RGPD + escalation); m23 retainer auditoría interna anual; m28 change governance. ⚠️ menor: m23 NO codifica explícitamente regla ≥50%/año + 100% bienal de auditoría interna MEDIA+ALTA. |

**Diferenciador CMM** (m10_audit_sim `audit_simulator.py:361-368`): L2 / L3 / L4 derivados por suficiencia evidencia — base presente para BÁSICA L2 / MEDIA L3 / ALTA L4, pero NO hay gate por categoría que exija CMM mínimo distinto.

### Nota de catálogo (aplicabilidad vs ground-truth)
Mi slice es el lifecycle de fases, no medidas individuales. Aplicabilidad de medidas (aplica_basica/media/alta + refuerzos) cubierta por otras pasadas. Confirmo que la regla de categoría (FASE 1) y el branch BÁSICA→autodeclaración vs MEDIA/ALTA→ENAC están correctamente codificados en `m_audit_accompaniment/state_machine.py` (`resolve_category_branch`).

### Path de evidencia por fase
- FASE 0: m06 templates E001/E002/E003/E150 → m05_signing (solo acta_comite 1ª clase) → m21_diagnosis `validate_ens_required_roles_assigned`. **Gap path firmable + roles ASS/POC + separación.**
- FASE 1-6: m01/m02/m03/m06/m05_obligations/m07/m09 → DdA + evidencias + dossier. Path completo.
- FASE 7: m_audit_accompaniment + m10_audit_sim + m27 (distintivo/declaración 809/INES/LUCIA). Path completo salvo color distintivo.
- FASE 8: m27 renewal + LUCIA + m18 + m23 + m28. Path completo salvo regla 50%/100% auditoría interna.

### Slice 2 · ORG + OP Planificación + OP Control acceso (15 medidas)

## PASADA 10 — Slice: MARCO ORGANIZATIVO (org.1-4) + OP Planificación (op.pl.1-5) + OP Control acceso (op.acc.1-6)

### Cobertura del PATH de implementación (verificado empírico)

| Etapa | Motor | Evidencia |
|-------|-------|-----------|
| DdA / aplicabilidad | m03_dda | `service.py:466 _measure_applies` lee `ens_measures.aplica_basica/media/alta` (seed catálogo YAML) |
| Refuerzos DdA | m03_dda + corpus BOE | `service.py:484 _applicable_reinforcements` lee tabla `ens_measure_refuerzos` (seed `seed_ens_measure_refuerzos.py` — parser determinista BOE-A-2022-7191 Anexo II, NO catálogo YAML) |
| Evidencia por medida | m07_evidence | `seed_ens_evidence_catalog.py:265 main` itera TODAS las ens_measures (≥73) + `_family_for` template por familia (org/op.pl/op.acc todas presentes :207-214) |
| Documentos (org) | m06_document_factory | `templates/policies/E100…` (PSI=org.1), `E101_politica_de_control_de_acceso` (op.acc), normativas/procedimientos (`api.py:371`) |
| Verificación técnica | m08_verification | `ens_mapper.py` + `scoutsuite_cloud_ens_mapper.py:22` (iam-user-no-mfa→op.acc.5) + `openvas_ens_mapper.py:36` (op.acc.5/6) + `heatmap_generator.py:30` (op.acc.1-6) |
| Loader test | tests | `test_load_ens_measures_catalog.py:26` 73 medidas + `test_marco_counts` org=4 |

### MATRIZ (filas = medidas · columnas = categoría · ✅ full / ⚠️ partial / ❌ gap)

| Medida | BÁSICA | MEDIA | ALTA | Refuerzos verificados |
|--------|--------|-------|------|------------------------|
| org.1 Política | ✅ | ✅ | ✅ | sin refuerzos (catálogo `refuerzos:{}` ✅) · path doc E-100 PSI |
| org.2 Normativa | ✅ | ✅ | ✅ | sin refuerzos ✅ · doc normativas m06 |
| org.3 Procedimientos | ✅ | ✅ | ✅ | sin refuerzos ✅ · doc procedimientos/POS m06 |
| org.4 Proceso autorización | ✅ | ✅ | ✅ | sin refuerzos ✅ |
| op.pl.1 Análisis riesgos | ✅ | ⚠️ R1 | ⚠️ R1+R2 | DdA refuerzo desde tabla BOE OK; catálogo YAML `M:[R1] A:[R1,R2]` coincide ✅ |
| op.pl.2 Arquitectura | ❌ catálogo `aplica_basica:false` vs manual BÁSICA L182 "Aplica base" | ✅ R1 (YAML `A:[R1]` solo declara ALTA) | ⚠️ R1+R2+R3 falta R2/R3 en YAML | catálogo YAML solo `A:[R1]`; ground-truth ALTA R1+R2+R3 |
| op.pl.3 Adquisición | ❌ catálogo `aplica_basica:false` vs manual BÁSICA L183 "Aplica" | ✅ | ✅ | sin refuerzos ✅ |
| op.pl.4 Dimensionamiento | ❌ catálogo `aplica_basica:false` vs manual BÁSICA L184 "Aplica base (por D=BAJO)" | ❌ catálogo `aplica_media:false` vs manual MEDIA aplica | ⚠️ R1 ausente en YAML `refuerzos:{}` (manual ALTA L157 +R1) | GAP grave applicability ALTA-only |
| op.pl.5 Componentes certif. | ✅ NO BÁSICA (`aplica_basica:false` correcto) | ❌ catálogo `aplica_media:false` vs ground-truth MEDIA aplica (guías L94 CPSTIC MEDIA+) | ⚠️ R1+R2 ausentes en YAML | GAP applicability MEDIA |
| op.acc.1 Identificación | ✅ | ⚠️ R1 | ⚠️ R1 | YAML `refuerzos:{}` vacío; ground-truth MEDIA+ALTA R1 (tabla BOE cubre) |
| op.acc.2 Requisitos acceso | ✅ | ✅ | ⚠️ R1+R2 | YAML vacío; ground-truth ALTA R1+R2 (tabla BOE) |
| op.acc.3 Segregación | ❌ catálogo `aplica_basica:true` vs ground-truth "NO BÁSICA" (manual BÁSICA L190) | ✅ | ⚠️ R1+R2+R3 | catálogo dice aplica_basica:true — INCORRECTO (no aplica BÁSICA) |
| op.acc.4 Gestión derechos | ✅ | ✅ | ✅ | sin refuerzos ✅ |
| op.acc.5 Autenticación externos | ⚠️ R1 contraseña (YAML `M:[R1] A:[R1,R2]` INCORRECTO) | ⚠️ MFA R2/R3+R5 (catálogo solo R1) | ⚠️ R4 cert HW (catálogo R1+R2) | DdA usa tabla BOE; YAML refuerzo erróneo. MFA soportado auth layer |
| op.acc.6 Autenticación org. | ⚠️ R1 (YAML `M:[R1] A:[R1,R2]` INCORRECTO) | ⚠️ R5+R8+R9 MFA admins (catálogo solo R1) | ⚠️ R5-R9 MFA todos (catálogo R1+R2) | DdA usa tabla BOE; YAML refuerzo erróneo. MCP op.acc.6 mapeado |

### Nota de catálogo (aplicabilidad vs ground-truth)
El catálogo YAML tiene errores de aplicabilidad que SÍ propagan al DdA (m03 lee columnas `ens_measures` derivadas del YAML):
- **op.pl.2/op.pl.3/op.pl.4**: marcadas `aplica_basica:false` pero los manuales BÁSICA (L182-184) dicen que aplican base en Básica. op.pl.4 además marcada ALTA-only (excluye MEDIA, contra ground-truth).
- **op.pl.5**: `aplica_media:false` pero MEDIA aplica.
- **op.acc.3**: `aplica_basica:true` pero NO aplica en BÁSICA (manual BÁSICA L190 "NO aplica en Básica").

Los **refuerzos del catálogo YAML** (`refuerzos:{}`) son un artefacto secundario incompleto/erróneo (op.acc.5/6 declaran `M:[R1]` en vez de los R2/R3/R5/R8/R9 reales). El DdA en runtime usa la tabla `ens_measure_refuerzos` parseada del corpus oficial BOE-A-2022-7191 (correcta), por lo que el riesgo funcional de refuerzos es bajo, pero el YAML debe alinearse para coherencia y para cualquier consumidor que lo lea directo (portal_api.py:198 computa tier desde columnas, no desde YAML refuerzos).

### Path de evidencia por medida
Todas las 15 medidas reciben requisito de evidencia genérico vía `seed_ens_evidence_catalog.py` (`_generic_type_for`), con template por familia: org → `documental_organizativa`, op.pl → `documental_planificacion`, op.acc → `registro_accesos`. ⚠️ El seed hardcodea `applicable_categories:["BASICA","MEDIA","ALTA"]` para todas, sin reflejar la aplicabilidad real (no es gate, el DdA filtra). MFA (op.acc.5/6) tiene además verificación técnica automatizable vía MCP cloud (scoutsuite/prowler/openvas).

### Slice 3 · OP Explotación + Ext + Nube + Continuidad + Monitorización (22 medidas)

## PASADA 10 — Slice OP: Explotación + Externos + Nube + Continuidad + Monitorización (22 medidas)

**Ground-truth**: 3 manuales `docs/ens-manuales/ENS_{BASICA,MEDIA,ALTA}_Manual_Implantacion_Completo.md`. **Catálogo**: `docs/catalogs/ens_measures_catalog_v1.yaml`. **Path**: m03_dda + m06 + m07 + m08 + m26.

Leyenda celda: ✅ catálogo applicability correcto + path implementación/evidencia existe · ⚠️ path existe pero catálogo refuerzo/applicability incompleto · ❌ catálogo applicability incorrecta vs manual o sin path.

### MATRIZ (medida × categoría)

| Medida | BÁSICA | MEDIA | ALTA | Refuerzos verificados (catálogo vs manual) |
|--------|--------|-------|------|--------------------------------------------|
| op.exp.1 Inventario | ✅ base | ✅ | ✅ | catálogo refuerzos {} ✓ (sin Rn) |
| op.exp.2 Config seguridad | ✅ base | ✅ | ✅ | {} ✓ |
| op.exp.3 Gestión config | ✅ base (manual BÁSICA L198 "Aplica base") | ⚠️ +R1 | ⚠️ +R1+R2+R3 | catálogo refuerzos **{} VACÍO** ❌; manual MEDIA R1 / ALTA R1-R3 (refuerzos vía tabla `ens_measure_refuerzos`, NO YAML) |
| op.exp.4 Mantenimiento | ✅ base | ✅ +R1 | ✅ +R1+R2 | catálogo refuerzos M:R1 / A:R1,R2 ✓ CORRECTO (YAML L412-417) |
| op.exp.5 Gestión cambios | ❌→✅ NO BÁSICA (manual BÁSICA L200 "NO aplica") catálogo aplica_basica=true ⚠️ | ✅ | ✅ | catálogo refuerzos {} ; **aplica_basica=true contradice manual** |
| op.exp.6 Código dañino | ✅ antivirus base | ⚠️ R1+R2 | ⚠️ R1+R2+R3+R4 (EDR) | catálogo refuerzos **{} VACÍO** ❌; manual MEDIA R1+R2 / ALTA R1-R4 |
| op.exp.7 Gestión incidentes | ✅ base | ✅ R1+R2 | ✅ R1+R2+R3 | catálogo refuerzos {} (refuerzos vía tabla externa) |
| op.exp.8 Registro actividad | ❌ catálogo aplica_basica=false vs manual BÁSICA L203 "Aplica base" | ⚠️ R1-R4 | ⚠️ R1-R5 | catálogo refuerzos solo **A:R1** ❌; manual MEDIA R1+R2+R3+R4 (NTP+retención≥12m+acceso) |
| op.exp.9 Registro gest. incidentes | (NO BÁSICA) | ✅ | ✅ | {} ✓ |
| op.exp.10 Protección claves | (NO BÁSICA, catálogo OK; manual BÁSICA L205 dice "Aplica base" ⚠️ divergencia manual) | ⚠️ R1 | ✅ R1 | catálogo refuerzos solo **A:R1** ; manual MEDIA R1 (CCN-STIC 807) falta clave M |
| op.ext.1 Contratación/SLA | ✅ NO BÁSICA | ✅ | ✅ | {} ✓ |
| op.ext.2 Gestión diaria | ✅ NO BÁSICA | ✅ | ✅ | {} ✓ |
| op.ext.3 Cadena suministro | ✅ NO BÁSICA | ❌ catálogo aplica_media=true vs manuales "SOLO ALTA" | ⚠️ R1+R2+R3 | catálogo refuerzos **{} VACÍO** ❌; ALTA manual L183 R1-R3 |
| op.ext.4 Interconexión | ✅ NO BÁSICA | ❌ catálogo aplica_media=false vs prompt "MEDIA aplica" (manual ALTA L184 solo cita ALTA R1; manual BÁSICA L211 NO aplica) | ⚠️ R1 | catálogo refuerzos {} ; ALTA R1 (coordinación) |
| op.nub.1 Protección cloud | ✅ base | ✅ R1 | ⚠️ R1+R2 | catálogo refuerzos **{} VACÍO** ; manual ALTA L187 R1+R2 (CCN-STIC 884/885) |
| op.cont.1 BIA | ✅ NO BÁSICA | ✅ | ✅ | {} ✓ (doc E-400 BIA) |
| op.cont.2 Plan continuidad | ✅ SOLO ALTA | ✅ NO MEDIA | ⚠️ R1+R2 | catálogo refuerzos **{} VACÍO** ; ALTA manual L191 R1+R2 |
| op.cont.3 Pruebas | ✅ SOLO ALTA | ✅ | ✅ | {} ✓ (doc E405/E406) |
| op.cont.4 Medios alternativos | ✅ NO BÁSICA | ❌ catálogo aplica_media=true vs manuales "SOLO ALTA / NO aplica en Media" | ⚠️ R1 | catálogo refuerzos **{} VACÍO** ; ALTA manual L193 R1 |
| op.mon.1 Detección intrusión | ❌ catálogo aplica_basica=false vs manual BÁSICA L222 "Aplica base" | ⚠️ R1 | ⚠️ R1+R2 | catálogo refuerzos solo **A:R1** ❌; manual MEDIA R1 / ALTA R1+R2 falta clave M |
| op.mon.2 Métricas | ❌ catálogo aplica_basica=false vs manual BÁSICA L223 "Aplica base" | ⚠️ R1+R2 | ⚠️ R1+R2 | catálogo refuerzos **{} VACÍO** ❌; ALTA manual L197 R1+R2 |
| op.mon.3 Vigilancia | ✅ base (catálogo aplica_basica=true = manual BÁSICA L224; ⚠️ diverge del prompt "NO BÁSICA") | ⚠️ R1+R2 | ⚠️ R1-R6 (minería+inspecciones) | catálogo refuerzos **{} VACÍO** ❌; ALTA manual L198 R1-R6 |

### Nota de catálogo (aplicabilidad correcta vs ground-truth manuales)
- **Applicability INCORRECTA (❌, OBLIGATORIA Pasada 16)**: op.ext.3 `aplica_media:true` (debe false, SOLO ALTA — ambos manuales); op.cont.4 `aplica_media:true` (debe false, SOLO ALTA — manuales MEDIA L210 + ALTA L193); op.exp.8 `aplica_basica:false` vs manual BÁSICA L203 "Aplica base"; op.mon.1 `aplica_basica:false` vs manual BÁSICA L222; op.mon.2 `aplica_basica:false` vs manual BÁSICA L223.
- **Divergencia prompt-vs-manual (manual prevalece)**: prompt dice op.mon.3 "NO BÁSICA" pero manual BÁSICA L224 = "Aplica base" y catálogo aplica_basica=true coincide con manual → catálogo CORRECTO. op.exp.3 prompt "NO BÁSICA" vs manual L198 "Aplica base" (catálogo aplica_basica=true = manual). op.exp.10 manual BÁSICA L205 "Aplica base" vs prompt/catálogo "NO BÁSICA". op.exp.5 manual BÁSICA L200 "NO aplica" vs catálogo aplica_basica=true.
- **Refuerzos YAML mayormente VACÍOS** (`{}`): op.exp.3/6/8(parcial)/10(parcial), op.ext.3, op.nub.1, op.cont.2/4, op.mon.1(parcial)/2/3 carecen de las claves M/A correctas en el dict `refuerzos`. El motor m03_dda lee refuerzos de la tabla `ens_measure_refuerzos` (service.py:496-505), NO del YAML — el YAML refuerzos es metadata de catálogo que debería estar alineada para auditoría/coherencia.

### Path de evidencia por medida (verificado)
- **m03_dda** (service.py:476-481 `aplica_basica/media/alta`; :484-505 refuerzos por categoría): GATEA correctamente applicability + NO_APLICA con justificación (templates.render_no_aplica_justification). Distingue NO BÁSICA / SOLO ALTA correctamente SI las columnas son correctas (depende del catálogo → defectos arriba propagan al DdA).
- **m07 evidence** (seed_ens_evidence_catalog.py): familias op.exp(L72)/op.ext(L82)/op.nub(L92)/op.cont(L102)/op.mon(L112) con evidence_type específico (registro_operacional, prueba_continuidad RTO/RPO, monitorizacion). 1 row/medida garantizado (L274 assert ≥73). ⚠️ `applicable_categories` hardcodeado a [BASICA,MEDIA,ALTA] (L229,L256) — NO distingue por categoría (distinción recae en m03_dda).
- **m06 document_factory**: BIA E-400 (op.cont.1), E401 estrategias + E402 BCP + DRP + E405/E406 pruebas (op.cont.2/3), E109 política continuidad, E208/E209 procedimientos continuidad, E229 monitorización (op.mon.1/2/3), E216 proveedores (op.ext.1/2/3), E227 cloud (op.nub.1/op.ext.1/2), E223 logs (op.exp.8/10/op.mon.1/2), E230 bastionado (op.exp.2/3). Tagging `medidas_ens` correcto.
- **m08 verification**: op.exp.2/3/4/5/6/7/8/10 + op.cont.2 mapeados a runners prowler/scoutsuite/openvas (prowler_cis_ens_mapper, scoutsuite_cloud_ens_mapper, openvas_ens_mapper, ens_mapper). op.exp.6 código dañino mapeado (ens_mapper.py:47). op.mon.* NO tienen mapper técnico dedicado (cubierto por m_compliance_monitor + docs, aceptable: medidas org/procedimentales).
- **op.cont path ALTA**: NO existe mapping explícito op.cont.* en m26_backup (motor backup genérico 3-2-1); continuidad cubierta vía m03 (applicability) + m06 (BIA/BCP/DRP/pruebas docs) + m07 (evidence prueba_continuidad RTO/RPO). Aceptable — op.cont son medidas documentales/procedimentales, NO técnicas-MCP.
- **Loader test**: `backend/tests/scripts/test_load_ens_measures_catalog.py` PASS (6 passed, 4 skipped).

### Slice 4 · MP Instalaciones + Personal + Equipos + Comunicaciones (19 medidas)

## PASADA 10 — Slice MP Físicas/Personal/Equipos/Comunicaciones (19 medidas)

Ground-truth: `docs/ens-manuales/ENS_{BASICA,MEDIA,ALTA}_Manual_Implantacion_Completo.md`. Catálogo: `docs/catalogs/ens_measures_catalog_v1.yaml`. Path: m03_dda (`service.py` `_measure_applies` lee `EnsMeasure.aplica_basica/media/alta` cargado del YAML + `_applicable_reinforcements` lee `ens_measure_refuerzos` parseado de BOE-A-2022-7191) → m07/`seed_ens_evidence_catalog.py` (≥1 tipo evidencia por medida, generación dinámica) → m08/`ens_mapper.py`+`reports/heatmap_generator.py` (las 19 presentes) → m24_idms/`awareness_tracker.py` (mp.per.3/4) → m06 docs/POS.

### TABLA MATRIZ (celda = veredicto · refuerzos verificados vs ground-truth)

| Medida | BÁSICA | MEDIA | ALTA | Refuerzos verificados |
|--------|--------|-------|------|------------------------|
| mp.if.1 Áreas separadas | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.if.2 Identificación personas | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.if.3 Acondicionamiento | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.if.4 Energía eléctrica | ✅ base | ⚠️ +R1 (SAI) | ⚠️ +R1 | GT: M+A R1; catálogo refuerzos{}={} (R1 vive en ens_measure_refuerzos BOE — verificar Pasada 16) |
| mp.if.5 Incendios | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.if.6 Inundaciones | ❌ catálogo dice aplica_basica:true (L1028) — GT: NO BÁSICA | ✅ aplica | ✅ aplica | categoria_minima debe ser MEDIA, no BASICA |
| mp.if.7 Registro entrada/salida | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.per.1 Caracterización puesto | ❌ catálogo aplica_basica:true (L1224) — GT: NO BÁSICA | ✅ aplica | ⚠️ +R1 (habilitación) | categoria_minima debe ser MEDIA; R1 ALTA vive en BOE seed |
| mp.per.2 Deberes y obligaciones | ✅ base | ⚠️ +R1 | ⚠️ +R1 | GT M+A R1; catálogo refuerzos{}={} |
| mp.per.3 Concienciación | ✅ aplica (m24 awareness) | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.per.4 Formación | ✅ aplica (m24 awareness) | ✅ aplica | ✅ aplica | sin R (correcto) |
| mp.eq.1 Puesto despejado | ✅ base | ⚠️ +R1 | ⚠️ +R1 | GT M+A R1; catálogo refuerzos{}={} |
| mp.eq.2 Bloqueo puesto | ❌ catálogo aplica_basica:true (L883) — GT: NO BÁSICA | ✅ aplica (por A) | ⚠️ +R1 | categoria_minima debe ser MEDIA |
| mp.eq.3 Portátiles | ✅ base (cifrado recomendado) | ⚠️ esperado (cifrado muy recom.) | ⚠️ +R1+R2 (CIFRADO OBLIGATORIO) | GT ALTA R1+R2; catálogo refuerzos{}={} — crítico cifrado obligatorio |
| mp.eq.4 Otros dispositivos | ❌ catálogo aplica_basica:false/categoria_minima:ALTA (L917-920) — GT: aplica base (por C) | ❌ catálogo aplica_media:false — GT: +R1 | ✅ +R1 | catálogo ALTA-only INCORRECTO: manuales BÁSICA+MEDIA lo aplican |
| mp.com.1 Perímetro | ✅ aplica | ✅ aplica | ✅ aplica | sin R (correcto; ALTA cascada 2 fabricantes = parte de la medida base) |
| mp.com.2 Confidencialidad | ✅ base (por C, TLS) | ✅ +R1 | ⚠️ catálogo A:[R1,R2] (L787-789) — GT ALTA R1+R2+R3 | falta R3 en refuerzos{} |
| mp.com.3 Integridad/autenticidad | ✅ base | ✅ +R1+R2 | ⚠️ catálogo A:[R1,R2] (L811-813) — GT ALTA R1+R2+R3+R4 | faltan R3,R4 en refuerzos{} |
| mp.com.4 Separación flujos | ✅ aplica_basica:false (L826) correcto — NO BÁSICA | ✅ +[R1 o R2 o R3] | ✅ +[R2/R3]+R4 | aplicabilidad correcta |

### Nota de catálogo (aplicabilidad correcta vs ground-truth)
- ✅ Correctas: mp.if.1/2/3/5/7, mp.per.2/3/4, mp.eq.1/3, mp.com.1/2/3, mp.com.4 (NO BÁSICA bien marcado).
- ❌ Aplicabilidad booleana errónea (impacta DdA directamente vía `_measure_applies`): **mp.if.6**, **mp.per.1**, **mp.eq.2** (marcadas aplica_basica:true cuando son NO BÁSICA → MEDIA), y **mp.eq.4** (marcada ALTA-only cuando aplica desde BÁSICA +R1 en MEDIA/ALTA).
- ⚠️ Metadata refuerzos{} del YAML incompleta (mp.com.2 falta R3, mp.com.3 faltan R3+R4; mp.if.4/per.1/per.2/eq.1/eq.2/eq.3/eq.4 con refuerzos{}={} pese a R1/R1+R2 esperados). NO bloquea path: la DdA toma refuerzos de `ens_measure_refuerzos` (parser determinista BOE Anexo II en `seed_ens_measure_refuerzos.py`), no del dict YAML. Verificar contenido real de esa tabla en runtime es Pasada 16 (DB drift reservado).

### Path de evidencia por medida (verificado)
- Todas (19): `seed_ens_evidence_catalog.py` genera ≥1 `ens_measure_evidencia_types` por código (cobertura dinámica `_family_for`/`_generic_type_for`); DdA entry creada por `m03_dda/service.create` (1 entry/medida); visible cliente (`m03_dda/portal_api.py` 73 medidas in-portal) y auditor (heatmap `m08/reports/heatmap_generator.py` incluye las 19).
- mp.if.*: evidencia física + planos/inventario locales (m06 docs); heatmap mp.if.1-7 (`heatmap_generator.py:43`).
- mp.per.1/2: POS/cláusulas firmadas (m06); mp.per.3/4: m24_idms `awareness_tracker.py` (concienciación + formación + cobertura/evaluación).
- mp.eq.2/3: verificación técnica config bloqueo + cifrado disco (m08 ens_mapper `cifrad` L171/175); mp.eq.3 ALTA evidencia cifrado obligatorio (ALTA manual L222/282/396).
- mp.com.1/2/3/4: m08 `ens_mapper.py` mapea mp.com.2 (L68/79/175/182/214 TLS/cripto) y mp.com.3 (L176/252 autenticidad/VPN); diagramas red + firewall + VPN (m06 docs + m08 runners nmap/openvas).

### Slice 5 · MP Soportes + Aplicaciones + Información + Servicios (17 medidas)

# PASADA 10 — Slice: MP Soportes + Aplicaciones + Información + Servicios (17 medidas)

## Veredicto matriz (filas = medidas; columnas = BÁSICA / MEDIA / ALTA)

Leyenda: ✅ full (catálogo correcto + path existe) · ⚠️ partial (catálogo ok pero path/refuerzo incompleto) · ❌ gap (medida ausente, applicability incorrecta, o sin path).

| Medida | BÁSICA | MEDIA | ALTA | Refuerzos verificados (catálogo vs ground-truth) |
|--------|--------|-------|------|--------------------------------------------------|
| **mp.si.1** Marcado/Etiquetado | ❌ N/A (cat. dice aplica_basica:true; GT=NO BÁSICA) | ✅ | ⚠️ (GT=R1 falta) | cat `refuerzos: {}` (L1427) · GT ALTA R1 → refuerzo FALTANTE; cat marca BÁSICA cuando GT dice NO |
| **mp.si.2** Criptografía | ❌ N/A (cat aplica_basica:false ✅ correcto NO BÁSICA) | ✅ | ⚠️ (GT R1+R2 falta) | cat `refuerzos: {}` (L1447) · GT ALTA R1+R2 → FALTANTE |
| **mp.si.3** Custodia | ✅ | ✅ | ✅ | sin refuerzos (correcto); aplica_basica:true ✅ |
| **mp.si.4** Transporte | ✅ | ✅ | ✅ | sin refuerzos (correcto); aplica_basica:true ✅ |
| **mp.si.5** Borrado/destrucción | ✅ | ⚠️ (R1 falta) | ⚠️ (R1 falta) | cat `refuerzos: {}` (L1503) · GT MEDIA+ALTA R1 → FALTANTE |
| **mp.sw.1** Desarrollo | ❌ N/A (cat aplica_basica:false ✅ NO BÁSICA) | ⚠️ (R1-R4 falta) | ⚠️ (R1-R4 + revisión código falta) | cat `refuerzos: {}` (L1522) · GT MEDIA/ALTA R1-R4 → FALTANTE |
| **mp.sw.2** Aceptación/servicio | ✅ | ⚠️ (R1 falta) | ⚠️ (R1 falta) | cat `refuerzos: {}` (L1540) · GT MEDIA+ALTA R1 → FALTANTE; aplica_basica:true ✅ |
| **mp.info.1** Datos personales (RGPD) | ✅ | ✅ | ✅ | sin refuerzos (correcto); aplica las 3 ✅ |
| **mp.info.2** Calificación info | ❌ N/A (cat aplica_basica:false ✅ NO BÁSICA) | ✅ | ✅ | sin refuerzos (correcto) |
| **mp.info.3** Firma electrónica | ⚠️ NUMERACIÓN (cat L1112 mp.info.3=Cifrado, NO Firma) | ⚠️ (R1-R3 + numeración) | ❌ R4 cualificada SIN PATH | **GAP DOBLE**: (1) numeración cat≠GT; (2) firma cualificada R4 NO cubierta (m05 = eIDAS simple) |
| **mp.info.4** Sellos de tiempo | ❌ N/A (GT NO BÁSICA) | ❌ N/A (GT NO MEDIA) | ⚠️ R1 (cat L1132=Firma, mp.info.5 L1155=Sellos) | **NUMERACIÓN cat≠GT**: cat mp.info.5=Sellos SOLO ALTA ✅ pero código≠RD311 |
| **mp.info.5** Limpieza documentos | ⚠️ NUMERACIÓN (cat L1155=Sellos; Limpieza=cat mp.info.6 L1174) | ⚠️ | ⚠️ | aplica las 3 (GT) ✅ pero código catálogo desplazado |
| **mp.info.6** Copias de seguridad | ⚠️ NUMERACIÓN (cat L1174=Limpieza; Backup=cat mp.info.9 L1192) | ⚠️ (R1) | ⚠️ (R1+R2) | cat mp.info.9 `refuerzos A:[R1]` (L1209) · GT R1+R2 ALTA → R2 FALTANTE + código≠RD311 |
| **mp.s.1** Correo electrónico | ✅ | ✅ | ✅ | sin refuerzos (correcto); aplica las 3 ✅ |
| **mp.s.2** Servicios web | ⚠️ (R1 sin marcar) | ⚠️ (R2 sin marcar) | ⚠️ (R2+R3 sin marcar) | cat `refuerzos: {}` (L1343) · GT BÁSICA R1 / MEDIA R2 / ALTA R2+R3 → TODOS FALTANTES. Path m08 ✅ (zap caja-negra/blanca + pentest auth) |
| **mp.s.3** Navegación web | ❌ (cat aplica_basica:false; manual BÁSICA "Aplica base") | ✅ | ⚠️ (R1 falta) | cat `refuerzos: {}` (L1357) · GT ALTA R1 → FALTANTE; applicability BÁSICA INCORRECTA vs manual |
| **mp.s.4** DoS | ❌ N/A (cat aplica_basica:false ✅ NO BÁSICA) | ✅ | ⚠️ (R1 falta) | cat `refuerzos: {}` (L1371) · GT ALTA R1 → FALTANTE |

## Nota de catálogo (aplicabilidad correcta vs ground-truth)

**Hallazgo estructural #1 (CRÍTICO)** — `docs/catalogs/ens_measures_catalog_v1.yaml` está numerado según **CCN-STIC 804 v2017** (todas las `fuente_oficial` lo declaran), que corresponde al ENS anterior (RD 3/2010), NO a **RD 311/2022 Anexo II**. Para la familia **mp.info** esto produce desplazamiento sistemático:

| Código catálogo (CCN-STIC 804) | Nombre catálogo | Código RD 311/2022 (GT) correcto |
|--------------------------------|-----------------|----------------------------------|
| mp.info.3 (L1112) | Cifrado | (en RD311 el cifrado de soporte = mp.si.2; mp.info.3 = **Firma electrónica**) |
| mp.info.4 (L1132) | Firma Electrónica | RD311 mp.info.3 |
| mp.info.5 (L1155) | Sellos De Tiempo | RD311 mp.info.4 |
| mp.info.6 (L1174) | Limpieza De Documentos | RD311 mp.info.5 |
| mp.info.9 (L1192) | Copias De Seguridad | RD311 mp.info.6 |

**Hallazgo estructural #2** — Los dos catálogos del sistema están **INCONSISTENTES entre sí**: `ens_measure_guias_ccn_v1.yaml:277` usa numeración RD 311/2022 correcta (`mp.info.1..mp.info.6`), mientras `ens_measures_catalog_v1.yaml` usa CCN-STIC 804. Cualquier join por `measure_code` entre guías y medidas fallará en mp.info.4/5/6.

**Hallazgo estructural #3** — TODA la familia **mp.s** tiene `refuerzos: {}` vacío (L1343, L1357, L1371) pese a que el ground-truth exige refuerzos por categoría: mp.s.2 BÁSICA R1 / MEDIA R2 / ALTA R2+R3; mp.s.3 ALTA R1; mp.s.4 ALTA R1. Igual para mp.si.1/2/5, mp.sw.1/2 (refuerzos vacíos vs GT R1-R4). El catálogo no captura granularidad de refuerzos per-categoría salvo casos puntuales (mp.info.9 A:[R1], mp.info.3-Cifrado A:[R1], mp.info.4-Firma A:[R1,R2]).

**Hallazgo estructural #4** — `mp.s.3` catálogo `aplica_basica: false` (L1351) pero manual BÁSICA línea 279 dice **"Protección de la navegación web | Aplica base."** → applicability BÁSICA INCORRECTA. (Nota: el brief de Pasada 10 decía "mp.s.3 NO BÁSICA", pero el ground-truth canónico = manuales, y BÁSICA L279 lo marca aplica. Diferencia brief↔manual señalada.)

**Correctos verificados**: mp.si.2 NO BÁSICA (cat aplica_basica:false ✅), mp.sw.1 NO BÁSICA ✅, mp.info.2 NO BÁSICA ✅, mp.s.4 NO BÁSICA ✅, mp.si.5/Sellos(=mp.info.5 cat) SOLO ALTA ✅, mp.s.1/si.3/si.4/info.1 aplican las 3 ✅.

## Path de implementación/evidencia por medida

Verificado que el sistema PERMITE implementar+evidenciar (path existe) para las 17:

- **m03_dda** (`service.py:78,103`, `api.py:68,244`): genera 73 entries atómicas de DdA por proyecto desde tabla `ens_measures` (cargada del catálogo YAML); applicability per categoría vía `aplica_basica/media/alta`. Path DdA existe para las 17. Portal cliente revisa las 73 (`portal_api.py`). ⚠️ La applicability heredada del catálogo arrastra los errores numéricos/applicability arriba.
- **m07 evidence / seed_ens_evidence_catalog.py**: lee `ens_measures` (≥73, assert L274), garantiza ≥1 evidencia por medida + plantillas de familia dedicadas para `mp.si` (L163), `mp.sw` (L173), `mp.info` (L183), `mp.s` (L193). 20 medidas con evidencia high-quality pre-mapeada (`evidence_types.json` incluye mp.info.1, mp.sw.1). Path evidencia existe genérico para las 17.
- **m08_verification** (path técnico mp.s.2 + mp.sw.1/2 + mp.s.1): `ens_mapper.py` mapea mp.s.2 (cabeceras HTTP L190), mp.sw.1 (sanitización/encoding/CSRF L196,203,208); `openvas_ens_mapper.py:133` mp.s.2 + mp.sw.1. Runners MCP presentes: `zap_runner.py` (DAST — **passive=caja negra BÁSICA / active=caja blanca MEDIA**, L74,100), `nuclei_runner`, `nmap_runner`, `lynis_runner`, `openvas_runner`, `prowler_runner`, `scoutsuite_runner`, `testssl_runner`. **Pentest mp.s.2 R2+R3 ALTA**: workflow autorización cliente ADR-020 v6 (`models.py:70-75` authorized_by + authorization_magic_link_id + authorization_signed_at; `kill_switch.py`; `portal_api.py` in-portal pentest authorization SAN-E). Pentester externo ALTA = proceso humano fuera de sistema (esperado).
- **m05_signing** (mp.info.3): TIER 1 canvas Ed25519 + hash chain (`api.py:549`, `pdf_signature_embed.py`). **firma electrónica SIMPLE eIDAS Art.25.1, explícitamente NO cualificada** (`pdf_signature_embed.py:21`). Cubre mp.info.3 BÁSICA base + parcialmente MEDIA R1-R3, NO cubre **ALTA R4 firma cualificada** → gap.
- **m26_backup** (mp.info.6): backup 3-2-1 (`backup_policy_3_2_1.py`), `encryption.py`, `offsite.py`, `service.py`, `tasks.py`. Cubre mp.info.6 base + R1 (pruebas recuperación) + R2 (separación offsite). Path completo.
- **mp.si.1-5, mp.sw.1-2, mp.info.1-6, mp.s.1-4** doc/POS via m06 document_factory + DdA m03 (path documental genérico existe; no inspeccionado individualmente por familia salvo evidencia/verificación).

## Findings TAGGED (gaps OBLIGATORIOS Pasada 16)

Ver array `findings`. Resumen: 1 crítico (numeración catálogo CCN-STIC 804 vs RD 311/2022 en mp.info), 1 high (refuerzos vacíos familia mp.s + mp.si + mp.sw), 1 high (catálogos inconsistentes entre sí), 1 high (mp.info.3 ALTA R4 firma cualificada sin path), 1 medium (mp.s.3 aplica_basica incorrecto vs manual), 1 medium (mp.si.1 marca BÁSICA cuando GT=NO BÁSICA).
