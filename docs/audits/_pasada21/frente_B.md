# FRENTE B — Entregables por fase (0→7) · auditoría READ-ONLY

**Método:** clasificación 1/2/3 justificada leyendo el CUERPO del código/template, citando `file:line` real. 1 = real con datos cliente · 2 = parcial / placeholders / hardcode · 3 = stub / ausente.

Sub-preguntas por entregable: **a** artefacto real con datos cliente o placeholder · **b** evidencia IDMS por medida · **c** audit_log R6 · **d** escala por nivel · **e** frontend accionable.

---

## Tabla de hallazgos

| Fase / entregable | Clase | file:line del cuerpo | a | b | c | d | e | Qué falta |
|---|---|---|---|---|---|---|---|---|
| **F0 · Acta nombramiento 5 roles (E-002)** | 1 | `m06_document_factory/templates/policies/E002_acta_nombramiento_roles_ens.md:57-198` (Jinja2 real con `responsables.*.nombre/cargo/dni` + `cliente.razon_social`) · render `m06/service.py:349` | datos cliente | sí (m24 folder 01_Gobierno) | parcial | **sí** (`requiere_ass`/`requiere_poc`/`requiere_rsa` BÁSICA/MEDIA/ALTA L38-40,125-170) | sí | RInf/RSeg/RSis/RServ + ASS/POC condicionales; firma manual (no e-sign cableada) |
| **F0 · Acta constitución Comité (E-003)** | 1 | `templates/policies/E003_acta_constitucion_comite_seguridad.md:9-122` (presidente/secretario/miembros desde `comite_seguridad.*`) | datos cliente | sí | parcial | parcial (solo MEDIA/ALTA generan F0; `fase0_governance.py:40-41`) | sí | — |
| **F0 · Documento de Alcance SGSI (E-155)** | 1 | template `templates/deliverables/E155_documento_alcance_sgsi.md` + builder rectores `rectores_generator.py:58-150` | datos cliente | sí | parcial | sí (catálogo `aplica_desde`) | sí | — |
| **F0 · Plan de Adecuación CCN-STIC 806 (E-150)** | 2 | `m17_planning/pda_generator.py:69-228` (aglutina M01+M02+M03+M04+M17 reales) | datos cliente (mayoría) | sí | sí (m06 emite en generación) | sí | sí | hardcodes: `conformes=0` placeholder `:173`, `cost_eur=0` TODO `:208`, `information_types=[]`/`services=[]` `:219-220` |
| **F0 · Acta de DECISIÓN de adoptar ENS** | 3 | NO existe template dedicado; `fase0_governance.py:33-44` solo trackea kickoff/alcance/roles/comité/plan | n/a | n/a | n/a | n/a | parcial | falta el "Acta de decisión/compromiso de la Dirección" como artefacto propio (cubierto indirectamente por E-100 PSI + E-003) |
| **F0 · Estado FASE 0 (composer)** | 1 | `m17_planning/fase0_governance.py:49-133` (puro, category-aware, separación RSeg≠RSis, cadencia comité) | n/a | n/a | n/a | sí | sí | composer de estado, NO generador; depende de que m06 genere los docs |
| **F1 · Categorización 5 dims + regla Anexo I** | 1 | `m01_categorization/service.py:137-215` (regla del máximo determinista) + `:224-298` (max por dimensión desde InformationType/Service reales) + snapshot inmutable `:266-296` | datos cliente | n/a | **no** (m01 NO emite audit_log; solo m12 en firma) | n/a (regla idéntica, categoría es el output) | sí | herencia del cliente público NO implementada |
| **F1 · Acta categorización (E-012)** | 1 | `m01_categorization/service.py:331-395` (genera MD con tabla DICAT + justificación + cita CCN-STIC 803) | datos cliente | sí | no | n/a | sí | — |
| **F1 · Herencia del cliente público (AAPP)** | 3 | NO existe; grep `m01/` solo halla `is_aapp_developer` (arquetipo comercial `pyme_archetypes.py:130`), `m02/` ninguna `herencia` | n/a | n/a | n/a | n/a | no | medida org.* de herencia de la AAPP contratante ausente |
| **F1 · Firma RInf + RSer del RInf/RSer** | 2 | `m01_categorization/signature_integration.py:75-141` (magic link eIDAS, hash acta) | real | n/a | sí (m12) | n/a | sí | firma **un solo** `recipient_role` (docstring "Responsable de la Informacion" `:5`); NO se exige doble firma RInf+RSer concurrente |
| **F2 · Riesgos MAGERIT v3 (E-400)** | 1 | `m02_magerit/service.py` completo: propagación `:434-602`, riesgo intrínseco `:608-872`, efectivo `:914-1098`, residual `:1195-1278`, snapshot freeze `:1393-1414` | datos cliente | sí | parcial | **NO** (sin informal/semiformal/formal por nivel) | sí | escala por nivel ausente (siempre full quali/quanti); ver prosa |
| **F2 · Aceptación riesgo residual por Dirección** | 2 | treatment plan `m02_magerit/service.py:1100-1192` (accept/mitigate/transfer/eliminate, umbral "A") | parcial | n/a | parcial | no | parcial | la "aceptación formal por la Dirección" solo aparece como texto en plantillas (E-150 §5, E-002 Acuerdo 4); NO hay artefacto firmado de aceptación de riesgo residual |
| **F3 · SoA / DdA (medida→aplicab→justif)** | 1 | `m03_dda/service.py:71-168` (73 medidas, `aplica_basica/media/alta`, refuerzos, justif NO_APLICA template, responsable, aprobado) + `list_entries:174-224` | datos cliente | sí (tag `measure_ens` m24) | parcial | **sí** (per medida por categoría) | sí | — |
| **F3 · Firma DdA por RSeg (E-040)** | 1 | `m03_dda/signature_integration.py:110-195` (gate freeze obligatorio `:135`, snapshot hash `:35-54`, magic link RSEG) | real | n/a | sí (m12) | n/a | sí | — |
| **F3 · Artefacto/PDF DdA firmado** | 1 | informe E-040 `templates/deliverables/E040_*.md` (m06 render+firma Ed25519 `m06/service.py:358-403`) + dossier ZIP `m09/dossier_generator.py` | datos cliente | sí | sí (m06) | sí | sí | — |
| **F4 · PSI + Normativa + POS (marco documental)** | 1 | catálogo `docs/catalogs/template_catalog_v1.yaml` (84 plantillas, 4 niveles `documentation_levels.py:46-145`) + render real `m06/service.py:267-436` | datos cliente | sí | sí (m06 `:409`) | **sí** (`aplica_desde`: 42 basica / 23 media / 9 alta / 10 null) | sí | scaling por nivel existe a nivel catálogo (`list_templates(aplica_desde=)`); NO hay un orquestador que "ligero vs completo" auto-seleccione el set por proyecto (selección manual) |
| **F4 · Variantes per-arquetipo (no per-nivel)** | 1 | `template_resolver.py:45-71` (resuelve `_sector_salud`/`_saas_only`/`_desarrollador_aapp`…) | datos cliente | n/a | n/a | n/a (per arquetipo, no nivel) | sí | resolver elige por arquetipo, no por categoría |
| **F6 · Organización evidencias por marco/medida** | 1 | `m24_idms/idms_service.py`: 15 carpetas estándar `:30-46` (incl 09_Evidencias), intake SHA-256+dedupe `:258-347`, tag `measure_ens` `:440-450`, búsqueda por medida `search_by_measure` | datos cliente | **sí** (tag por medida + folder por marco) | parcial | n/a | sí | clasificación marco/medida es heurística por nombre `:48-64` + tag manual; no auto-mapeo medida→evidencia exigida |
| **F6 · Dossier exportable para auditor** | 1 | `m09/dossier_generator.py:1-40+` (ZIP, 14 carpetas + Matriz 99 + MANIFEST con hashes) | datos cliente | sí | sí (m09) | sí | sí | — |
| **F7 · Máquina de estados (ciclo cierre)** | 1 | `m_audit_accompaniment/state_machine.py:25-134` (BÁSICO 6 estados, MEDIO/ALTO 11 estados, branch `resolve_category_branch:97-109`) + service `service.py:191-298` (audit_log 3-way OR `:108-130`, SSE, advisory lock) | n/a (tracker) | n/a | **sí** (`audit_accompaniment` events `:118-130`) | **sí** (branch por categoría) | sí | máquina genérica: avanza estados + sube artifacts pero NO valida QUIÉN firma ni genera distintivo/AMPARO |
| **F7 BÁSICA · pentest gate EXCLUIDO** | 1 | `state_machine.py:34-41` (BÁSICO transitions: drafted→signed→published→review→completed · SIN estado de auditoría/pentest) | n/a | n/a | sí | sí | sí | **correcto**: pentest no aparece en branch BÁSICO ✓ |
| **F7 BÁSICA · Declaración Anexo A 809 firmada por DIRECCIÓN** | 2 | **E-041** correcto `templates/deliverables/E041_declaracion_conformidad_ens.md:41,64,105-108` (firma "representante legal / órgano competente", art. 33.2) · **PERO E-180** `m27_conformity/distintivo_generator.py:369-382` + `templates/policies/E180_declaracion_conformidad.md:81-88` firma **RSEG** ✗ | datos cliente | n/a | parcial | sí | sí | **incoherencia normativa**: dos artefactos de declaración BÁSICA; el de cierre m27 (E-180) lo firma RSEG, no Dirección (CCN-STIC 809 Anexo A exige órgano superior) |
| **F7 BÁSICA · Distintivo Pantone Orange** | 1 | `m27_conformity/distintivo_generator.py:223-256` (SVG, `FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C` #FE5000 único todas categorías `:217-235`) + Ed25519 verificable | datos cliente | n/a | parcial | sí (color único correcto) | sí | — (color canónico correcto CCN-STIC 809) |
| **F7 BÁSICA · Comunicación CCN vía AMPARO** | 3 | NO existe flujo; grep "amparo": solo mención en lista de herramientas CCN `E203_*.md:386` y usos jurídicos "al amparo de" (sin relación) | n/a | n/a | n/a | n/a | no | submission a AMPARO/CCN ausente por completo |
| **F7 MEDIA/ALTA · Flujo ENAC real** | 1 | `state_machine.py:60-86` (preparation→docs_collected→internal_audit→ENAC scheduled→in_progress→findings_resolution(PAC)→passed→certificate→biannual) | n/a | n/a | sí | sí | sí | flujo documental→campo→informe→PAC→verificación→decisión→certificado→renovación bienal presente |
| **F7 MEDIA/ALTA · Portal auditor sirve el flujo** | 1 | dossier `m09/dossier_generator.py` + auditor APIs `m09/{auditor_annotations_api,auditor_clarifications_api,draft_report_api}.py` + frontend `frontend/components/audit/AuditAccompanimentTimeline.tsx` | n/a | sí | sí | sí | sí | portal auditor (magic-link AUDITOR_PORTAL_ENAC) + anotaciones + draft report reales |
| **F7 · Frontend cierre cliente** | 1 | `frontend/app/(client-portal)/client-portal/certificacion/page.tsx` + `components/client-portal/AuditAccompanimentClienteView.tsx` | n/a | n/a | n/a | sí | sí | cliente VE timeline (cliente-mínimo); admin avanza |

---

## Prosa — hueco normativo-real vs hueco de producto

### Huecos NORMATIVOS reales (bloquean / degradan certificabilidad)

1. **Firmante de la Declaración BÁSICA inconsistente (PRIORIDAD ALTA).**
   Existen DOS artefactos de declaración de conformidad para BÁSICA con firmantes distintos:
   - `E-041` (m06) lo firma el **representante legal / órgano competente** invocando art. 33.2 RD 311/2022 → **correcto** (`E041_*.md:41,64,107-108`).
   - `E-180` (m27 `distintivo_generator.py:369-382` y `E180_*.md:81-88`) lo firma el **RSEG** → **incorrecto**: la Declaración modelo Anexo A de CCN-STIC 809 debe suscribirla la **DIRECCIÓN** (órgano superior), no el Responsable de Seguridad ni el consultor.
   El camino de cierre real de producto pasa por m27 (distintivo + E-180), que es el firmante equivocado. Esto es un hueco normativo que un auditor/CCN podría rechazar. **Bloquea certificar BÁSICA correctamente** salvo que se use solo E-041.

2. **Comunicación a CCN vía AMPARO ausente (PRIORIDAD ALTA para BÁSICA).**
   No hay ningún flujo de envío/registro a AMPARO. La autodeclaración BÁSICA contempla publicar distintivo en sede (sí implementado) pero NO la comunicación al CCN. Hueco normativo de cierre del ciclo BÁSICA.

3. **MAGERIT no escala informal/semiformal/formal por nivel (PRIORIDAD MEDIA).**
   `m02_magerit/service.py` siempre ejecuta análisis completo cualitativo/cuantitativo. No hay rama "análisis informal/simplificado" para BÁSICA vs formal para ALTA (CCN-STIC 803/MAGERIT prevén proporcionalidad). No bloquea (un análisis completo cumple de sobra), pero es sobre-ingeniería para BÁSICA y desalineado con la doctrina de proporcionalidad ENS.

4. **Herencia de categorización del cliente público ausente (PRIORIDAD MEDIA).**
   m01 no modela la herencia de niveles/medidas que el sistema del proveedor recibe del organismo AAPP contratante. `is_aapp_developer` es un flag de arquetipo comercial (`pyme_archetypes.py:130`), no herencia ENS. Para proveedores que prestan a la AAPP (target FULKRO) esto puede ser materialmente relevante.

5. **Aceptación formal de riesgo residual por la Dirección no es artefacto firmado (PRIORIDAD MEDIA).**
   m02 calcula residual y treatment plan, pero la "aceptación por la Dirección" (RD 311/2022 art. 11 RServ / MAGERIT Libro I p.46) solo existe como texto en plantillas (E-150 §5, E-002 Acuerdo 4). No hay un acto de aceptación de riesgo residual firmable independiente.

6. **Firma de categorización: un solo firmante.** `m01/signature_integration.py:75-141` solicita firma a un único `recipient_role`. La práctica ENS aprueba niveles con RInf (información) + RServ (servicio) conjuntamente. No se fuerza la doble firma.

### Huecos de PRODUCTO (no bloquean certificar, mejoran la entrega)

- **PdA con placeholders parciales:** `pda_generator.py` deja `conformes=0` (`:173`), `cost_eur=0` (`:208`), `information_types/services` vacíos (`:219-220`). El documento sale, pero con métricas de conformidad y coste sin poblar → necesita que M04 gap real esté evaluado antes de emitir el PdA definitivo.
- **"Acta de decisión" de adoptar ENS** no tiene template propio; queda absorbida por la PSI (E-100) + Acta constitución comité (E-003). Coherente, pero si Marcos quiere el acta formal de decisión/compromiso de la Dirección como entregable separado, falta.
- **Selección de set documental por nivel es manual:** el catálogo tiene `aplica_desde` (basica/media/alta) pero no hay orquestador que auto-genere "el paquete ligero BÁSICA" vs "completo MEDIA/ALTA" en un click. La capacidad existe (`list_templates(aplica_desde=)`), la automatización no.
- **audit_log no se emite en m01 (categorización) ni en la generación core de m03 (DdA):** la trazabilidad ENAC del acto de categorizar/generar DdA se apoya solo en el evento de firma (m12) y en m06 (cuando se materializa el documento). m02, m_audit_accompaniment, m06 sí emiten audit_log 3-way OR. Hueco de trazabilidad menor (R6 hash chain intacta donde se emite).
- **Clasificación de evidencias por medida es heurística + tag manual** (`idms_service.py:48-64`); no hay motor que mapee "esta medida exige estas evidencias" automáticamente (sí lo hay en m09 `dda_evidence_gap_service` para el gap, pero el archivado en IDMS es manual).

---

## Veredicto por fase

| Fase | Veredicto | Bloquea certificar a nivel |
|---|---|---|
| **F0 Gobierno** | Sólido (1). E-002/E-003/E-155 reales con datos cliente, category-aware, firma manual. E-150 real pero con 3 placeholders. | No bloquea. Falta acta de decisión formal (producto). |
| **F1 Categorización** | Núcleo determinista real (1). Anexo I correcto. **Falta herencia AAPP** (normativo) y doble firma RInf+RSer (degradado). | Degrada en escenarios de herencia AAPP; no bloquea categoría per se. |
| **F2 Riesgos** | Motor MAGERIT v3 completo y citado (1). **No escala por nivel** + aceptación residual no firmada. | No bloquea (cumple de más). Normativo: proporcionalidad. |
| **F3 SoA/DdA** | Real, category-aware, firmado por RSeg con gate freeze (1). | No bloquea. Bien. |
| **F4 Marco documental** | PSI/Normativas/Procedimientos reales (1), scaling por catálogo `aplica_desde` existe; auto-selección por nivel manual (producto). | No bloquea. |
| **F6 Evidencias** | IDMS real (carpetas+tag por medida+dossier ZIP MANIFEST) (1). | No bloquea. |
| **F7 Cierre BÁSICA** | Máquina de estados correcta (pentest excluido ✓), distintivo Pantone Orange correcto ✓. **Firmante E-180 = RSEG (debe ser DIRECCIÓN)** + **AMPARO ausente**. | **BLOQUEA cierre BÁSICA conforme** hasta corregir firmante (usar E-041 órgano competente) y añadir comunicación CCN/AMPARO. |
| **F7 Cierre MEDIA/ALTA** | Flujo ENAC completo (documental→campo→PAC→verificación→certificado→bienal) + portal auditor real (1). | No bloquea. Sólido. |

**Prioridad de remediación (bloqueantes de certificación):**
1. Corregir firmante Declaración BÁSICA → DIRECCIÓN (unificar en E-041, deprecar firma RSEG de E-180).
2. Implementar comunicación/registro CCN vía AMPARO para cierre BÁSICA.
3. (Media) Herencia AAPP en m01 · proporcionalidad MAGERIT por nivel · aceptación residual firmada.
