# PLAN MAESTRO DE REMEDIACIÓN ENS — Revisión con criterio AUDITOR ENAC

> **Fecha:** 2026-06-11 · **Rama auditada:** `main` (== `origin/main` == prod Hetzner desplegado 2026-06-11 13:16) · **Método:** 2 workflows multi-agente (39 + 23 agentes, ~8.5M tokens) con verificación adversaria. · **Estándar de raseo:** UNE-EN ISO/IEC 17065, CCN-STIC 808/122, CCN-CERT IC-01/19, RD 311/2022.

## Cómo usar este documento

Marca cada item `[x]` al cerrarlo. Orden de ejecución recomendado en la sección **Fases**. **Ejecutar este plan** (no solo tenerlo) es lo que deja el sistema certificable. Esfuerzo: **~90-130h nominal / ~50-75h empírico** (mayoría = extender patrones existentes: `rectores_generator`, `fix_docx_templates`, RLS 3-way canónico).

---

## VEREDICTOS

### Aislamiento por proyecto → ✅ AIRTIGHT en prod
**152/152 tablas con RLS ENABLE+FORCE**, `fulkro_app` NOBYPASSRLS+NOSUPERUSER. Probado funcionalmente: sin contexto → 0 filas; con contexto → exactamente 1 proyecto. **Nada se cruza entre clientes.** Los hallazgos de aislamiento son **defensa en profundidad + riesgo de regresión**, con **un único punto caliente real**: RLS fail-open en `signing_*` (OTP + firmas Ed25519). El airtight hoy depende de disciplina manual por endpoint, no de arquitectura → R06+R07 lo blindan.

### Entregables → ❌ NO certificable tal cual (Media/Alta); autodeclaración Básica no defendible si se piden evidencias
El cuerpo normativo es excelente y auditable. Pero los **documentos de SÍNTESIS que el auditor abre primero** están rotos de forma estructural y verificada:
- **E-040 (Informe Final / SoA)** renderiza **VACÍO** (no existe `build_informe_final_context`, solo `build_rectores_context`; confirmado en main y batch2). Valla ```jinja, autor hardcodeado, códigos POL-1xx inventados.
- **E-155 (Alcance)** se auto-declara **BORRADOR** con 13 placeholders "⚠ REVISIÓN CONSULTOR".
- **E-012 (Acta categorización)** firma con el **rol equivocado** (Presidente+RSI en vez de la doble firma competente RInfo+RServ del art. 11.a/d), flujo **monofirma estructural**, cita art. 28 (real: art. 40).
- Drift de citas RD 3/2010→311/2022 (mp.info, op.cont.3), entregables no generables (E-235.docx, W-002), 0/38 POS con bloque de firma.

> **Verificación adversaria** — falsos positivos descartados (NO actuar): DdA→E-040 es coherente con el catálogo; `template_catalog_v1.yaml` NO existe (el real es `template_registry.py`); firmas de continuidad SÍ se pueblan; `organo_aprobador_politicas` SÍ es required; cita 806 en E-040 es correcta.

---

## FASES (orden de ejecución)

| Fase | Contenido | Esfuerzo | Desbloquea |
|---|---|---|---|
| **F0** | Aislamiento por arquitectura (R06-R09) | ~10-16h | Cualquier piloto multi-cliente |
| **F1** | Documento estrella E-040 (R01-R02) | ~12-17h | MEDIA + ALTA |
| **F2** | Gobierno firmable (R03-R05, R24) | ~14-21h | Lo que el auditor abre primero |
| **F3** | Citas normativas y drift (R12, R21, R18, R19, R16, R17) | ~8-12h | Trazabilidad |
| **F4** | Generabilidad y firma POS (R10, R11, R13, R14, R22, R25) | ~8-13h | MEDIA + ALTA |
| **F5** | Cierre Básica y Continuidad (R15, R20, R26) | ~12-18h | BÁSICA + continuidad ALTA |
| **F6** | Enriquecimiento (R23) | ~6-8h | No bloqueante |

---

## NC MAYORES (11) — bloquean certificación

### F0 · Aislamiento

- [ ] **R06** `NC_MAYOR` · ~3-5h · **MODIFICAR** — RLS fail-OPEN en `signing_intents/signing_events/signing_otp_codes` → fail-CLOSED puro para pool cliente (quitar `OR current_project_id() IS NULL` en USING/WITH CHECK; bypass admin por rol `fulkro_app_bypassrls`). Mismo fix a `copilot_messages`, `email_log`, `oauth_state_tokens`. Migración additive + test empírico (fulkro_app sin contexto → 0 filas). **Verificado:** migración `123920e86153_san_e_mb5_signing_intents_events.py:248-291`. *Archivos:* nueva migración `signing_rls_failclosed_001`.
- [ ] **R07** `NC_MAYOR` · ~5-8h · **CREAR** dependency central `require_client_user_scoped` (resuelve proyecto activo + valida ownership + `SET LOCAL fulkro.project_id/client_id` en una transacción) + **CREAR** test de cobertura que falle si CUALQUIER ruta del pool cliente no la aplica. **BORRAR** docstrings falsos que afirman que el dep global setea contexto. Hoy duplicado en 20+ ficheros (283 hits). *Archivos:* api global dep; call-sites.

### F1 · E-040

- [x] **R01** `NC_MAYOR` · ~10-14h · **CREAR** `build_informe_final_context(db, project_id)` (patrón `rectores_generator`): agrega `dda_entries` por familia (aplicables/implantadas/%), cumplimiento global, excepciones (E-310 m_live_records), riesgos (m02 MAGERIT), auditoría interna (m09), evidencias (m07), alcance (E-155). Cablear a endpoint dedicado + **BLOQUEAR emisión si tablas críticas vacías**. **UI:** botón "Generar Informe Final/SoA". ALTA: tabla por-medida que renderice `refuerzos_aplicados (+R1..+R9)` desde `dda_entries.refuerzos_aplicados` (hoy no afloran). *Archivos:* `m06_document_factory/rectores_generator.py` (o nuevo `informe_final_generator.py`); `E040_informe_final_de_adecuacion_al_ens.py`; `m06_document_factory/api.py`.
- [x] **R02** `NC_MAYOR` · (cierre real `0146eb7d`) · **BORRAR** valla ```jinja (E040.md:5-351) + autor hardcodeado (`:12` → usar `fulkro_identity`) + códigos POL-1xx/POL-2xx inventados (usar E-codes). **MODIFICAR** cita `:111` E-200→E-AR-001; plazos ENAC `:316` "6-8 semanas"→rango honesto 8-16 sem. *Archivos:* `E040_informe_final_de_adecuacion_al_ens.md`.

### F2 · Gobierno

- [ ] **R03** `NC_MAYOR` · ~8-12h · **CREAR** tabla `acta_signatures(categorization_id, role∈{RInfo,RServ}, magic_link_id, signed_at, signature_ed25519, ip)` + flujo doble firma (acta "aprobada" solo con AMBAS; RS solo conformidad; eliminar RSI/RSistema como aprobador) + freeze + firma cripto del PDF emitido encadenado a audit_log R6. **MODIFICAR** las 3 variantes de E-012 a UNA plantilla canónica (la m06 rica). **UI:** dos solicitudes de firma (RInfo + RServ). **Verificado:** `E012...md:104-106`. *Archivos:* E012 .md; `acta_e012_provisional.docx`; `m01_categorization/service.py`; `signature_integration.py`; `m05_signing` (modelo).
- [ ] **R05** `NC_MAYOR` · ~5-8h · **MODIFICAR** E-155: resolver 13 placeholders por proyecto + eliminar estado BORRADOR + validación pre-firma anti-placeholder. **CREAR** modelo estructurado `servicios.tipo∈{finalista,instrumental}` (CCN-STIC 803) + `sedes.tipo∈{sede_fisica,region_cloud}` con dirección+país (ubicaciones reales en ALTA). **UI:** editor de alcance. *Archivos:* E155 .md; build context E-155; m01/m30.

### F4 · Generabilidad y firma POS

- [ ] **R10** `NC_MAYOR` · ~2-3h · **MODIFICAR** E-235 `mp.info.5`→**`mp.info.4`** en todas las apariciones (.md:3,17,32,45 + .py docstring) + **CREAR/compilar** `var/templates_docx/E-235.docx` (NO existe → único POS del refuerzo mp.info.4, sin él un cliente ALTA no puede emitirlo) + resolver placeholder propio (`:5`). Idéntico a W-002. *Archivos:* E235 .md/.py; `backend/var/templates_docx/E-235.docx`; `template_registry.py`.
- [ ] **R11** `NC_MAYOR` · ~3-5h · **MODIFICAR** `fix_docx_templates.py` para añadir `procedures` al conjunto que recibe `append_sigblock` (ELABORADO=consultor / APROBADO=RSEG-RSIS con `{{ firmas.* }}`). **Verificado:** `grep 'firmas.'` en templates/procedures = 0/38. *Archivos:* `backend/scripts/fix_docx_templates.py`; `templates/procedures/*.md`.
- [ ] **R13** `NC_MAYOR` · ~3-5h · **MODIFICAR** E-100/E-104: eliminar token fantasma `{{...}}-ABSORB_INTO_E100` + arreglar que `JINJA_BLOCK.search()` solo compila el PRIMER bloque ```jinja → el 2º bloque (documento de roles art.11) NO se compila a DOCX y **desaparece**. **CREAR** código real `E-100B` (o Anexo I de E-100), catalogarlo, separar a bloque que sí compile. *Archivos:* E100/E104 .md; `build_governance_templates.py`; `template_registry.py`.
- [ ] **R14** `NC_MAYOR` · ~5-8h · **CREAR** context builder server-side org.2 (deriva de m30 los 4 roles art.11 + comité + DPO con fallback "(pendiente designación)", nunca vacío; marcar required; `proxima_revision = fecha_aprobacion+12m`). **CREAR** modelo de **acuse de recibo per-empleado** (identidad+fecha+versión) para evidenciar mp.per.3 (PSI §11.b). **BORRAR** "Marcos Mata García" legacy en `m09_audit_prep/internal_auditor.py:598,602`. **UI:** acuse del personal. *Archivos:* m06 policy context builder; m30; `rendering.py`; `internal_auditor.py`.

### F5 · Cierre Básica

- [ ] **R15** `NC_MAYOR` · ~4-6h · **CREAR** generador real del cuestionario CCN-STIC 808 de cierre BÁSICA (reusar `audit_questions.py` M10 como checklist Anexo III) que produzca `Document` firmado (Dirección) y trazado; **MODIFICAR** `process_basic_declaration` para validar `self_assessment_report_id` contra esa tabla (FK + estado firmado) en el gate de publicación. Hoy es UUID opcional sin generador. **UI:** paso de cierre Básica. *Archivos:* `m27 conformity_service_paso5.py`; `m10_audit_sim/audit_questions.py`; generador 808; schema/FK.

---

## NC MENORES (13)

- [ ] **R04** `NC_MENOR` · ~1-2h · **MODIFICAR** E-012: cita art.28→art.40 + Anexo I (`:31`); cross-ref E-050→E-150 (`:78`); **registrar** `'E-012':'acta_categorizacion'` en `signable_types.py:100-104 _ECODE_TO_SIGNABLE_TYPE`. *(NO tocar la ref DdA→E-040: es correcta.)*
- [ ] **R08** `NC_MENOR` · ~2-3h · **MODIFICAR** las 3 policies `admin_all USING(true)` (`client_contacts`, `change_topologies`, `conformity_state_snapshots`) → patrón canónico context-aware con escape `FOR ROLE bypassrls`. Alinear `ai_act_transparency_events`. **Verificado:** `b2c3d4e5f6a7:100`, `a1b2c3d4e5f6:81`. *Archivos:* nueva migración `rls_admin_only_canonical_001`.
- [ ] **R09** `NC_MENOR` · ~2-3h · **MODIFICAR** `llm_interaction_log` rate-limit: `project_id` obligatorio (no Optional) en `get_rate_limit_status/enforce_rate_limit` + documentar exención RLS. **CREAR** writer central `emit_audit_log(db, tabla, registro_id, accion, project_id, client_id)` (hoy INSERT inline por motor). *Archivos:* `m_observability`; audit_log writer.
- [ ] **R12** `NC_MENOR` · ~2-3h · **MODIFICAR** citas mp.info: E-107/E-119 "mp.info.3 (Cifrado)"→Firma electrónica (cifrado = mp.si.2/mp.com.2-3); E-104 desplaza mp.info.4/5/6; E-103 "mp.s.1 (Servicios)"→Correo; E-100:247 RGPD `{{base}}-115`→E-105; E-232 frontmatter. *Archivos:* E104/E107/E119/E103/E100/E232 .md.
- [ ] **R16** `NC_MENOR` · ~2-3h · **MODIFICAR** E-041: cross-ref E-050→E-150 (`:68`); E-052 fantasma (`:70`); ciclo renovación (`:76` art.35 invertido → Art.33 + Anexo III); hardcode "Las 73 medidas" (`:58/:98`)→parametrizar por categoría (52/68/73). *Archivos:* E041 .md; parcial Jinja.
- [ ] **R17** `NC_MENOR` · ~1-2h · **MODIFICAR/renombrar** E-808 a "Revisión Anual de la DdA (art.31)" (dejar de reusarlo como 808 de cierre); parametrizar "73 medidas"; **MODIFICAR UI** `ConformityWizard.tsx:68` + `ProjectCategoryBanner.tsx:36` (**809→808**). *Archivos:* E808 .md; frontend; `dossier_generator.py`.
- [ ] **R18** `NC_MENOR` · ~1-2h · **MODIFICAR** `audit_questions.py`: fuente 802→808+824 (`:3`); retención `:55/:232` "6 meses"→**12 meses** (op.exp.8); realinear criterios mp.s.1/mp.s.2/mp.info.3/mp.info.4 a RD 311/2022. *Archivos:* `m10_audit_sim/audit_questions.py`.
- [ ] **R19** `NC_MENOR` · ~2-3h · **MODIFICAR** E-222: cita 802 (`:28/:191`)→Anexo II (org.4 + Art.27.3) + CCN-STIC 804; unificar Registro R-222 con el vivo E-310; **BORRAR** huérfano F-222/R-222 de texto; condicionar aprobadores L1-L4 por categoría. *Archivos:* E222 .md; m_live_records.
- [ ] **R20** `NC_MENOR` · ~4-6h · **MODIFICAR** continuidad: E-401/402/403 cita "CCN-STIC-808"→ISO/UNE 22301; E-405/406 op.cont.4→op.cont.3; E-400 POL-104→POL-109. **CREAR** `build_bia_context` + `build_continuity_context` (tablas RTO/RPO/ejercicios hoy vacías). **BORRAR** valla ```jinja en E-400/E-109/E-209. Gating E-109→media, E-209→alta. *Archivos:* E400-406/E109/E209 .md; builders.
- [ ] **R22** `NC_MENOR` · ~30min · **BORRAR** andamiaje editorial filtrado en E-220 (`:67` "## RESUMEN DEL BLOQUE 6A", `:99` "Si me dices seguimos…", aprox :65-99) + verificar con `grep_docx_leaks.py`. *Archivos:* E220 .md.
- [ ] **R24** `NC_MENOR` · ~3-4h · **MODIFICAR** coherencia: clave `responsable_sistema` unificada; `fecha_nombramiento` independiente (E-002 anterior a E-012/E-100); retención documental centralizada. **CREAR** "Acta de decisión de adecuación de la Dirección" firmable autónoma (org.1). **BORRAR** footer "Generado por FULKRO" del cuerpo de E-002/E-003/E-012 (marca solo en metadatos). E-003 cross-ref E-050→E-150 + periodicidad por categoría. *Archivos:* E002/E003/E012/E155 .md; `fase0_governance.py`; nueva `acta_decision_direccion`.
- [ ] **R25** `NC_MENOR` · ~2-3h · **MODIFICAR** `documentation_levels.py` (LEVEL_2 omite E-120/E-122/E-127; LEVEL_3 solo E-200..E-213, faltan E-214..E-235 + E-204-A + W-002). **CREAR** tracking POS-set acumulativo por categoría (BÁSICA⊆MEDIA⊆ALTA) con estado (esperado/generado/firmado/vigente); filtro de igualdad→inclusión. *Archivos:* `documentation_levels.py`; `policy_signoff_service.py`; `template_registry.py`.
- [ ] **R26** `NC_MENOR` · ~3-4h · **MODIFICAR** `dossier_generator` para fijar UNA identidad de E-040 (Informe Final). **CREAR** el certificado ENAC MEDIA/ALTA como `Document` descargable adjunto a `route_state REGISTERED` (PDF entidad + nº + vigencia 2 años). Promover hallazgos NC E-321/E-322 de JSONB a modelo estructurado (severidad + PAC ≤90d + APC solo MEDIA). Poblar DISTINTIVO-809 (client_domicilio, summaries). **UI:** descarga de certificado. *Archivos:* `dossier_generator.py`; `route_machine.py`; m27 schemas.

---

## OBSERVACIONES (2)

- [ ] **R21** `OBS` · ~1h · **MODIFICAR** `m22_discovery/paso6_config_detector.py:49,444,468` — control_ids "op.cont.3_*_backup" → op.cont.3 = Pruebas periódicas (backup es op.cont.4/mp.info.6).
- [ ] **R23** `OBS` · ~3-4h · **MODIFICAR** E-150/E-160/E-170 (rectores): poblar firmantes en tablas de firma; coste tareas (0€ → effort×tarifa); tabla Capex/Opex; E-codes exactos. Builders deterministas ya existen → enriquecimiento. *Archivos:* `rectores_generator.py`; `build_pda_context`.

---

## DELTA POR NIVEL

**BÁSICA:** R15 (autoevaluación 808 real — hoy NO existe, es el corazón del cierre) · R01 (SoA poblado) · R03 (doble firma E-012) · R05 (alcance emitible) · R16/R17 (etiquetas 808/809 + "73"→52) · R22 · R06-R09 (aislamiento).

**MEDIA:** todo lo de Básica + R01/R02 (matriz Anexo II de 68 medidas poblada) · R03/R04 (doble firma + art.40) · R11 (firma en 38 POS) · R13/R14 (roles art.11 + acuse mp.per.3) · R12/R18/R19/R20 (citas) · R26 (certificado + NC estructuradas).

**ALTA:** todo lo de Media + R01 (refuerzos +R1..+R9 que hoy no se renderizan) · R10 (E-235 sellos generable) · R05 (sedes estructuradas) · R24 (separación funcional RSeg/RSis).

---

## AISLAMIENTO — acciones (per-project airtight)

- R06 (ALTO), R07 (ALTO), R08 (MEDIO), R09 (MEDIO) — ver arriba.
- [ ] Endurecer `WITH CHECK` de INSERT en tablas tenant (hoy `WITH CHECK(true)` permite insertar fila con project_id de otro tenant) → `project_id=current_project_id()`.
- [ ] Actualizar gate `verify-deploy.sh` AL-1 al head real `unify_pricing_fiscal_rls_001` (drift de proceso) + re-aplicar `alembic upgrade head` a BD dev local (10 tablas sin RLS en Docker local = drift de BD, NO de árbol; el head real da 152/152 con ENABLE+FORCE+policy).

**Veredicto:** PROD es airtight cliente-a-cliente y proyecto-a-proyecto. Las remediaciones de aislamiento son defensa en profundidad + cierre de riesgo latente de regresión, NO fugas activas. Prioridad real: R06+R07 (convertir "ownership-check manual" en "RLS fail-closed + helper central").

---

## ESFUERZO

| Categoría | Items | Horas |
|---|---|---|
| NC_MAYOR | R01,R02,R03,R05,R06,R07,R10,R11,R13,R14,R15 | ~55-80h |
| NC_MENOR | R04,R08,R09,R12,R16,R17,R18,R19,R20,R22,R24,R25,R26 | ~28-40h |
| Observación | R21,R23 | ~7-10h |
| **TOTAL nominal** | **26** | **~90-130h** |
| **TOTAL empírico probable** | | **~50-75h** (extend de patrones existentes) |

---

*Generado a partir de los workflows `wf_f8fe8748-543` (cobertura ENS) y `wf_a6bb7407-5e0` (entregables ENAC + aislamiento), con verificación adversaria. Outputs completos en `tasks/`.*
