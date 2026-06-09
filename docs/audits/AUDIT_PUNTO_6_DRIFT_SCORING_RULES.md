# Audit #6 · Drift de keys/valores: SCORING_RULES ↔ templates de onboarding

> **Estado**: ✅ **RESUELTO** (2026-06-03). Tabla de valores aprobada por Marcos (con 6 ajustes
> de criterio de consultor) e implementada como **capa de normalización (Opción A)** en el motor
> de scoring — **sin tocar los 77 templates ni la UX**. El mapa de desajustes original se conserva
> abajo como referencia.

## ✅ RESUELTO — qué se implementó

**Estrategia: Opción A (capa de normalización en el motor).** Reestructurado `SCORING_RULES` →
`SCORING_CONCEPTS` en
[`maturity_service.py`](../../backend/app/motors/m21_diagnosis/maturity_service.py): **1 entrada
por concepto** con `keys` (alias de cuestionario · QUESTION_ALIASES) + `value_points` (puntos por
valor · VALUE_ALIASES). Reflejo en
[`compliance_service.py`](../../backend/app/motors/m21_diagnosis/compliance_service.py)
(normalización ISO) y
[`pkg_ingest_service.py`](../../backend/app/motors/m16_onboarding/pkg_ingest_service.py)
(alias de node-map + DPO boolean).

**Ajustes de criterio de Marcos sobre la tabla** (todos aplicados):
1. **Backup**: `scripts_manuales` = **0** (separado de `basico/manual`=+1) — un script manual no
   es continuidad fiable en ENS.
2. **DPO** `no_obligatorio` = **neutro de verdad** (`_NEUTRAL_VALUES`): ni puntúa ni cuenta en
   `max_possible`. Verificado que el frontend (`DiagnosisPanel`) solo muestra nivel global → no se
   pinta como carencia.
3. **Identidad** `active_directory`/`on_prem_ad` = **+1** (AD on-premise bien gestionado es gestión
   de identidad válida en op.acc).
4. **MFA** `solo_empleados` = +2 en MADUREZ — **anotado**: en ENS Alta no basta para CONFORMIDAD
   (MFA universal obligatorio). Planos separados (ver principio MADUREZ≠CONFORMIDAD).
5. **Cloud** concepto renombrado a **"infraestructura conocida/identificada"** (no "cloud
   identificado": una empresa sin cloud no "tiene" cloud); `on_prem_only` = +1.
6. **SIEM** `logs_centralizados` = +1.

**Dos arreglos técnicos** (aprobados):
- **`max_possible` inflado** → arreglado: con 1 concepto = 1 entrada, `max_possible` = el máximo
  REAL del concepto (backup máx 2, no 5). Antes la madurez tenía techo artificial (≤L2 en varios
  dominios aunque el cliente lo hiciera todo bien).
- **ISO** `iso_27001`→`iso27001` normalizado en la regla cross-compliance.

**Verificación**: [`test_maturity_drift.py`](../../backend/tests/motors/m21_diagnosis/test_maturity_drift.py)
(6 tests · PASS) demuestra que `educacion_privada` (`backup=3_2_1`, `mfa=completo`, `dpo=True`,
`experiencia=iso27001`) — que **hoy puntuaba 0** — **ahora SÍ puntúa**, con guards anti-falso-verde
(respuestas malas → 0), `scripts_manuales`=0 y `no_obligatorio`=neutro. **0 regresiones nuevas**.

> **Nota honesta (OPS-049)**: 2 tests pre-existentes de `test_m21_diagnosis.py`
> (`test_mfa_boosts_op_acc`, `test_siem_boosts_op_mon`) seedean vía API con `submit(allow_partial)`
> que NO deja la sesión en `COMPLETED` → la query de madurez no ve las respuestas → 0. **Fallan
> idéntico en baseline** (verificado con `git stash`), independiente de este fix. Es un issue del
> path de seed-API/estado de onboarding, NO del scoring. Anotado para tarea aparte.

**Estado #6**: *diseño cerrado + drift arreglado; cableado cloud+copiloto → diagnóstico pendiente
de #18 + #22.*

---


## Causa raíz y por qué importa

Las `SCORING_RULES` del motor de madurez
([maturity_service.py:27-45](../../backend/app/motors/m21_diagnosis/maturity_service.py)) y la
regla cross-compliance ISO27001
([compliance_service.py:70](../../backend/app/motors/m21_diagnosis/compliance_service.py)) se
escribieron contra los templates de **`servicios_profesionales`** (y parte de `generico`). Los
otros **9 sectores** se redactaron después con **otro vocabulario**. Resultado: **casi todas las
reglas solo puntúan en 1-2 sectores**; para el resto, la respuesta existe pero la regla no la ve
→ **madurez artificialmente baja**.

El drift es **doble**:
- **Drift de KEY**: la regla espera `q-X`, el template define `q-Y` para el mismo concepto.
- **Drift de VALOR**: misma key, pero las `options` difieren y la `value`/`condition` de la regla
  no matchea (p.ej. la regla espera `cloud_automatico`, el template ofrece `3_2_1`).

Datos extraídos empíricamente de los 77 templates JSON
(`backend/app/motors/m16_onboarding/templates/*.json`).

## Tabla de desajustes (1 fila por regla)

| # | Dominio · Regla (file:line) | Key esperada · cond · value | Realidad en templates (key → nº tmpls · valores) | Tipo drift | **Canónica propuesta + reconciliación** |
|---|---|---|---|---|---|
| R1 | org · L28 | `q-sponsor_ejecutivo` · not_empty · +2 | `q-sponsor_ejecutivo`→1 (text, solo servicios_prof). Otros sponsor: `q-dedicacion_semanal_sponsor`→2 (concepto distinto: dedicación), `q-sponsors_alternativos`→5 (concepto distinto). **3 sponsor sin pregunta de identidad de sponsor.** | KEY + cobertura | **[DECIDE]** El sponsor ES el interlocutor de la sesión → derivar "sponsor identificado" de `OnboardingSession.interlocutor_nombre` (robusto, sin perfil técnico) en vez de exigir `q-sponsor_ejecutivo`. Alternativa: añadir la key a los 11 sponsor (toca UX). Recomiendo derivar de la sesión. |
| R2 | org · L29 (+ **compliance L70**) | `q-proyectos_previos_seguridad` · not_empty / contains `iso27001` · +1 | `q-proyectos_previos_seguridad`→1 (multi, valores incl `iso27001`). Dominante `q-experiencia_previa_certificacion`→**9** (single, valores incl `iso27001`). `q-certificacion_iso`→7 (industria, valor `iso_27001` con guión bajo). | KEY | **`q-experiencia_previa_certificacion`** (9 tmpls, ya trae `iso27001`). Cambiar key en regla madurez + regla compliance. Alias secundario `q-certificacion_iso` (ojo valor `iso_27001`≠`iso27001`). Confianza ALTA. |
| R3 | org · L30 | pkg_check `stakeholder_roles_coverage` · gte_60 · +2 | No es key de pregunta (sale del grafo PKG). El PKG solo se puebla de 4 keys (ver node-map) → cobertura casi siempre baja. | (no key) | Sin cambio de key. La cobertura mejora cuando #18/#22 pueblen el PKG. Anotado, no se toca ahora. |
| R4/R5 | op_acc · L31-32 | `q-mfa_universal` · equals `si_todos`(+3)/`solo_privilegiados`(+1) | `q-mfa_universal`→5 (2 sets de valores: `si_todos\|solo_privilegiados\|...` y `empleados_y_clientes\|solo_empleados\|...`). `q-mfa_implantado`→5 (`completo\|parcial\|no`). (`q-mfa_personal`/`q-mfa_proveedores` = conceptos distintos, NO tocar.) | KEY + VALOR | **`q-mfa_universal`** canónica. Aceptar alias key `q-mfa_implantado`. Alias valor: `empleados_y_clientes`→`si_todos`, `completo`→`si_todos`, `parcial`→`solo_privilegiados`. |
| R6 | op_acc · L33 | `q-email_identidad` · in [`microsoft_365`,`google_workspace`] · +1 | `q-email_identidad`→1 (servicios_prof). `q-proveedor_identidad`→1 (generico, mismos valores microsoft_365/google_workspace). 8 ti_cto **sin** pregunta de identidad (cobertura → bonus). | KEY + cobertura | **`q-proveedor_identidad`** canónica + alias `q-email_identidad` (valores ya coinciden). Cobertura de 8 ti_cto = bonus (la cubre cloud discovery #18). |
| R7/R8 | op_exp · L35-36 | `q-pentest_ultimo` · equals `ultimo_ano`(+2)/`hace_1_3_anos`(+1) | `q-pentest_ultimo`→3. `q-ultimo_pentest`→1 (`hace_1_2_anos`). `q-pentest_frecuencia`→1 (`trimestral\|semestral\|anual`). `q-soc_pentest_recientes`→7 (saas_tech, `si_sin_hallazgos_criticos\|...`). | KEY + VALOR | **`q-pentest_ultimo`** canónica. Alias key+valor: `q-ultimo_pentest`(`hace_1_2_anos`→`hace_1_3_anos`), `q-soc_pentest_recientes`(`si_*`→`ultimo_ano`), `q-pentest_frecuencia`(`trimestral/semestral/anual`→reciente). |
| R9 | op_exp · L34 | `q-endpoints_managed` · equals `si_mdm` · +2 | `q-endpoints_managed`→3 (valores `si_mdm/solo_antivirus/no`). Resto ti_cto sin pregunta endpoint. | cobertura | Sin drift de key/valor. Cobertura (3 tmpls) = bonus (la cubre cloud discovery #18). |
| R10 | op_mon · L37 | `q-siem_activo` · equals `True` · +3 | `q-siem_activo`→2 (uno **boolean**, uno **single_select** `siem_dedicado/...`). `q-siem_presente`→1 (generico, boolean). `q-siem_soc`→1 (fintech, single_select). La regla `equals True` solo matchea los **boolean**. | KEY + VALOR | **`q-siem_presente`** (boolean, semántica `True`) canónica + alias `q-siem_activo`/`q-siem_soc`. Cambiar cond a "truthy / valor ≠ `no`/`False`" para cubrir los single_select. |
| R11/R12/R13 | op_cont · L38-40 | `q-backup_estrategia` · equals `cloud_automatico`(+2)/`software_dedicado`(+2)/`scripts_manuales`(+1) | `q-backup_estrategia`→8 pero **2 sets de valores**: `3_2_1\|basico\|cloud\|ninguno`→**7** vs `cloud_automatico\|software_dedicado\|scripts_manuales\|no_formal`→1. `q-backup_strategy`→1 (fintech, `cloud_auto\|software_dedicado\|manual`). | VALOR (grave) + KEY | **`q-backup_estrategia`** canónica + alias key `q-backup_strategy`. **Reconciliar valores**: `3_2_1`→+2, `cloud`→+2, `basico`→+1, `ninguno`→0; `cloud_auto`→+2, `manual`→+1. Hoy solo puntúa 1 de 8. |
| R14 | mp_com · L41 (+ **node-map**) | `q-cloud_providers` · not_empty · +1 | `q-cloud_providers`→2. `q-cloud_provider`→4 (singular). `q-cloud_uso`→1 (industria). Cond `not_empty` (valores irrelevantes). | KEY | **`q-cloud_providers`** canónica + alias `q-cloud_provider`,`q-cloud_uso`. Actualizar también el node-map PKG. Confianza ALTA (not_empty). |
| R15 | mp_info · L42 (+ **node-map**) | `q-dpo_designado` · in [`interno`,`externo`] · +2 | `q-dpo_designado`→**10** (KEY OK) pero **3 sets de valores**: `boolean`, `interno\|externo\|no`, `interno\|externo\|no_obligatorio\|deberiamos_pero_no`. La regla `in[interno,externo]` **no matchea los boolean**. | VALOR | Key OK. **Reconciliar valor**: tratar `True`(boolean)→designado; `in[interno,externo]` ya cubre los single_select. Mismo arreglo en el node-map (`condition: answer in (interno,externo)`). |
| R16/R17 | mp_info · L43-44 | `q-contratos_encargado_firmados` · equals `todos`(+2)/`mayoria`(+1) | `q-contratos_encargado_firmados`→1 (servicios_prof). `q-contratos_art28_estado`→1 (generico, MISMOS valores). `q-contratos_proveedores_pagos`→1 (fintech, mismos valores). `q-contratos_marco`→4 (operaciones, boolean — rol/concepto distinto). | KEY | **`q-contratos_art28_estado`** canónica + alias `q-contratos_encargado_firmados`,`q-contratos_proveedores_pagos` (valores ya coinciden). `q-contratos_marco` (operaciones) NO entra (otro rol). |
| NM | node-map · [pkg_ingest_service.py:19-42](../../backend/app/motors/m16_onboarding/pkg_ingest_service.py) | `q-sponsor_ejecutivo`,`q-email_identidad`,`q-cloud_providers`,`q-dpo_designado` | Mismos desajustes que R1/R6/R14/R15. Solo 4 keys pueblan el PKG; **ninguna crea nodos `process`** → `inventory_processes` vacío sin discovery. | KEY/VALOR | Aplicar los mismos alias (sponsor→interlocutor, identidad, cloud, dpo-boolean). La ausencia de nodos `process` la resuelve #18. |

## Resumen del impacto

- **De 17 reglas, solo ~4-5 puntúan hoy fuera de `servicios_profesionales`** (dpo single_select,
  cloud not_empty parcial, mfa solo_privilegiados, backup en 1 tmpl). El resto está roto por
  drift.
- Concepto más grave: **backup** (7 de 8 templates con el valor correcto de key pero valores que
  la regla ignora) y **dpo** (10 templates con la key correcta pero los boolean nunca puntúan).

## Estrategia de fix propuesta (decisión de Marcos)

Dos opciones:

- **(A) Capa de normalización en las reglas** (RECOMENDADA · tarea acotada): añadir
  `QUESTION_ALIASES` (key→canónica) + `VALUE_ALIASES` (valor template→valor canónico) en
  `maturity_service.py`, y reflejar lo necesario en `compliance_service.py` + `pkg_ingest_service.py`.
  El evaluador normaliza key+valor antes de puntuar. **Toca 1-3 ficheros**, reversible, testable,
  **NO toca los 77 templates ni la UX del lead/cliente**. Canónica = la key más clara/dominante.
- **(B) Canonicalizar los 77 templates** a un único vocabulario. "Correcto" a largo plazo pero
  **NO es tarea acotada**: 20+ ficheros, cambia lo que ven leads/clientes, riesgo alto.

**Recomendación: (A).** El #6 hoy solo cierra el drift como bug acotado; la consistencia total de
templates puede ir a una tarea de pulido posterior (Ola 9 cosmético/coherencia).

## Verificación de cierre (cuando Marcos apruebe)

Test que, partiendo de respuestas con las keys/valores **de un sector que hoy NO puntúa** (p.ej.
`educacion_privada` con `q-backup_estrategia=3_2_1`, `q-mfa_implantado=completo`,
`q-dpo_designado=True`), demuestre que tras el alias **la madurez puntúa** (nivel > L0 en los
dominios afectados), con guard anti-falso-verde (sin alias → no puntúa).
