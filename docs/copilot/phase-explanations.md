# Phase Explanations · Copilot Guided Content

**Source**: Sesión 3A Phase B.1 · briefing-curated content production-grade.
**Scope**: 4 phases priority HOY (Categorización · Análisis riesgos · DoA · Monitoring). 6 phases remaining DEFER Sesión 3C content curation.
**Audience**: Marcos (admin tutor "hasta un mono") · cliente piloto MEDIA pre-cert ENS.
**Style**: R30 admin tutor primer principios · R29 cliente sin jerga · plain Spanish · NO presión.

Map per phase (WORKFLOW_PHASES enum canonical 10 fases):
- `categorizacion_dimensiones` (M01 + dimensiones 19) → Phase 1 priority
- `analisis_riesgos` (M02 MAGERIT + M19 risk) → Phase 2 priority
- `dda_final` (M03 DdA + Anexo II 73 medidas) → Phase 3 priority
- `monitoring_retainer_cierre` (Bloque 4 + M23 retainer) → Phase 4 priority

---

## Phase 1 · Categorización del sistema ENS

**phase_id**: `categorizacion_dimensiones`
**motor_principal**: M01 categorization (+ dimensiones 19 canonical Sub-atom 1.D.F.0.A)
**target_url_admin**: `/admin/projects/[id]/dimensiones`
**target_url_cliente**: `/client-portal/onboarding` Tab dimensiones

### intro

Antes de implantar el ENS necesitamos saber **cuánto riesgo asume tu sistema** si pasa algo malo. Categorizar = poner una etiqueta (BÁSICA · MEDIA · ALTA) que define qué medidas del Anexo II tienes que cumplir.

### why_important

La categoría determina TODO el alcance del proyecto: qué medidas obligatorias · si necesitas auditoría externa ENAC (MEDIA/ALTA) o autoevaluación (BÁSICA · CCN-STIC 809) · cuántos meses dura la implantación · cuánto cuesta. Equivocarse aquí significa o sobre-invertir en medidas innecesarias o quedarte corto y suspender la auditoría.

### what_we_do

1. **Cliente rellena** las 5 dimensiones de seguridad ENS (Confidencialidad · Integridad · Trazabilidad · Autenticidad · Disponibilidad) marcando BAJO/MEDIO/ALTO por dimensión. Cada dimensión tiene preguntas concretas en lenguaje plain (NO jerga normativa).
2. **Marcos revisa** las respuestas en `/admin/projects/[id]/dimensiones` · puede ajustar si hay incoherencias (e.g. "marcaste disponibilidad ALTO pero no tienes contrato de SLA con proveedor").
3. **Motor M01 calcula** la categoría agregando las dimensiones según RD 311/2022 Anexo I: max(D1..D5) determina BÁSICA si todas ≤BAJO · MEDIA si ≥1 MEDIO · ALTA si ≥1 ALTO.
4. **Marcos firma** la decisión + cliente firma la **Acta de Aprobación Categorización (E-012)** vía m_signing Ed25519. Queda inmutable en audit log.
5. **Sistema desbloquea** las siguientes fases (Análisis riesgos · DoA · etc) con el conjunto de medidas Anexo II aplicables a tu categoría.

### common_mistakes

- **Subestimar la disponibilidad**: sistemas accesibles desde Internet o usados por terceros suelen ser MEDIA mínimo · BÁSICA es realmente solo intranet/pyme pequeña.
- **Confundir BÁSICA con "es fácil"**: BÁSICA tiene 49 medidas obligatorias · NO es trivial pero NO requiere auditoría ENAC externa.
- **Marcar todo ALTO "por si acaso"**: triplica el coste y los plazos · solo justificado si tratas datos sensibles RGPD art.9 o eres sector crítico (sanidad · energía · infraestructura).
- **Saltarse esta fase y empezar por MAGERIT**: el análisis de riesgos depende de la categoría · sin categoría firmada las salvaguardas escogidas pueden ser insuficientes O excesivas.

### estimated_time

**~2-4 horas reales de cliente** (rellenar 19 dimensiones · 1 reunión revisión con Marcos · firma) · **calendar 3-5 días** desde envío hasta firma final.

### help_resources

- Glosario ENS plain Spanish: tooltip "Categoría ENS" en `/dimensiones` (75 términos cubiertos `glosario-ens.ts`)
- Guía CCN-STIC 803 v3.0 (categorización · ya citada inline en system prompt copiloto)
- Pregunta al copiloto: "¿Por qué Marcos me dice MEDIA?" → respuesta con cita Anexo I + dimensiones marcadas
- Contactar Marcos: `mailto:marcosmata@fulkro.es` o canal Slack interno

---

## Phase 2 · Análisis de riesgos (MAGERIT)

**phase_id**: `analisis_riesgos`
**motor_principal**: M02 MAGERIT v3 (+ M19 risk catalog)
**target_url_admin**: `/admin/projects/[id]/magerit`
**target_url_cliente**: `/client-portal/magerit`

### intro

Una vez sabemos la categoría, identificamos **qué cosas valiosas tienes** (activos: servidores · datos · personas · contratos) y **qué cosas malas pueden pasarles** (amenazas: ataques · fallos · errores humanos · desastres). Para cada combinación calculamos el riesgo y decidimos qué medidas aplicar.

### why_important

ENS Anexo II te dice QUÉ medidas debes cumplir según categoría · MAGERIT te dice POR QUÉ las necesitas y CUÁNTO esfuerzo poner en cada una. Sin análisis de riesgos las medidas son arbitrarias · con MAGERIT son trazables al riesgo real de TU sistema. Auditor ENAC lo pide explícitamente (op.pl.1).

### what_we_do

1. **Cliente lista activos** (servidores · BBDD · aplicaciones · personas clave · contratos) con valoración por dimensión heredada de Phase 1.
2. **Motor M02 genera matriz amenazas** automática usando catálogo MAGERIT (E.1 Errores de los usuarios · A.5 Suplantación de identidad · I.5 Avería de origen físico o lógico · etc · ~40 amenazas core).
3. **Marcos calcula riesgo** por activo+amenaza = Impacto × Probabilidad. Filtra por umbral aceptable (típico ~MEDIA o superior).
4. **Sistema sugiere salvaguardas** del catálogo MAGERIT mapeadas a medidas ENS Anexo II (e.g. "Riesgo I.5 sobre BBDD → safe.SW.A.2 backups → ENS op.cont.3 Pruebas periódicas").
5. **Marcos refina** salvaguardas (acepta · rechaza con justificación · añade ad-hoc) en `/admin/projects/[id]/magerit`.
6. **Cliente firma** el documento MAGERIT final (PDF + hash SHA-256 inmutable) vía Ed25519.

### common_mistakes

- **Listar TODOS los activos físicos**: te pierdes en el detalle · MAGERIT pide solo activos que aportan VALOR al servicio en alcance.
- **Inventar amenazas exóticas**: el catálogo MAGERIT cubre 90% de casos · solo añade ad-hoc si tu sector tiene amenazas específicas (e.g. sabotaje político en defensa).
- **Aceptar TODO el riesgo "para ahorrar"**: si auditor ENAC ve riesgos críticos sin tratar y sin justificación documentada, FAIL audit. Acepta solo riesgos BAJO con argumento por escrito.
- **Olvidar el análisis al firmar la DoA**: la DoA debe trazar cada medida implantada a un riesgo MAGERIT específico · NO basta con "cumplimos porque toca".

### estimated_time

**~8-15 horas reales de Marcos** (modelado activos · matriz amenazas · refinamiento salvaguardas · documento final) · **calendar 1-2 semanas** desde firma categorización hasta firma MAGERIT.

### help_resources

- Catálogo MAGERIT v3 amenazas: tooltips inline en `/magerit` con código E/A/I/N + descripción plain
- Guía CCN-STIC 470/471/472 (MAGERIT applied to ENS)
- Pregunta al copiloto: "¿Cómo mapea esta amenaza a medida ENS?" → respuesta con tabla cross-reference
- Plantilla MAGERIT canonical: ver dossier ENAC `/dossier` → folder `06_Analisis_Riesgos`

---

## Phase 3 · Declaración de Aplicabilidad (DdA) final

**phase_id**: `dda_final`
**motor_principal**: M03 DdA (73 medidas Anexo II + cross-mappings ENS-RGPD-NIS2-DORA-AIAct via m_legal dormant)
**target_url_admin**: `/admin/projects/[id]/dda`
**target_url_cliente**: `/client-portal/dda`

### intro

La DoA es el documento estrella del ENS: lista las **73 medidas del Anexo II** y dice por cada una si la aplicas (SÍ/NO/PARCIAL), por qué, dónde está la evidencia, y quién es responsable. Es el documento que el auditor ENAC mira primero · si la DoA está mal el resto no importa.

### why_important

Sin DoA firmada NO hay certificación ENS. Es prueba ante auditor de que **conoces TODO el Anexo II** (incluso las medidas que NO aplicas, justificando por qué) y de que **tienes evidencias trazables** para cada SÍ. Es también la base del **Plan de Adecuación** (gaps a cerrar) y del **Dossier ENAC** (entrega de auditoría).

### what_we_do

1. **Motor M03 genera DoA inicial** con las 73 medidas Anexo II filtradas por categoría (BÁSICA 49 · MEDIA 73 · ALTA 73 con reforzados) + sub-medidas R/M/A intensity.
2. **Marcos rellena por cada medida**: estado (implementada · pendiente · no_aplicable) + justificación + responsable (rol cargo del cliente desde M30 client_contacts) + observaciones técnicas. M03 genera narrativa enriquecida via A31 (asistido NO generativo · R1 INVIOLABLE).
3. **Sistema valida cobertura ≥80%** antes de permitir congelar la DoA (gate empírico · NO LLM decision).
4. **Cliente revisa la DoA en `/client-portal/dda`** ve solo las medidas con justificación friendly (R29 sostener · NO "evidencia ENS op.acc.6") sino "control de acceso multi-factor implantado · evidencia en folder seguridad").
5. **Marcos congela la DoA** (estado IMMUTABLE · aprobado_por requirement + hash SHA-256 + audit log entry).
6. **Cliente firma la DoA final** vía Ed25519 (DoA es uno de los **4 firmas Chain Integrity** junto con MAGERIT · Pentest · Conformidad).

### common_mistakes

- **Saltarse las "no aplicables"**: cada medida del Anexo II requiere justificación · NO basta con dejar en blanco · auditor pide "¿por qué no aplica esta medida en tu sistema?".
- **Reusar DoA de otro proyecto**: cada sistema tiene su propio alcance · medidas idénticas en texto pero con responsables y evidencias específicas.
- **Congelar la DoA con gaps abiertos**: si una medida está PENDIENTE en DoA congelada, el auditor lo verá · mejor congelar SOLO cuando todas implantadas O justificadas como "diferida en Plan de Adecuación".
- **No vincular medidas a evidencias en m24_idms**: la DoA dice "implementada" pero el auditor pide la prueba · sin link evidencia → finding minor en audit dry-run.

### estimated_time

**~15-30 horas Marcos** (relleno 73 medidas · narrativa A31 asistida · revisión cobertura · congelar) · **calendar 2-4 semanas** post-firma MAGERIT.

### help_resources

- Tooltips por medida en `/dda` con cita CCN-STIC 803/804/805/806/807 + Anexo II RD 311/2022 (12 guías mapeadas via `ens_measure_guias_ccn_v1.yaml` 73/73 coverage 100%)
- Pregunta al copiloto: "¿Esta medida aplica a mi sistema cloud?" → respuesta con cita Anexo II + análisis empírico
- Catálogo cross-compliance: si tienes RGPD/NIS2/DORA en scope, motor `m_legal` (dormant pre-piloto · activable T2) muestra mappings 250 obligaciones legales con ENS Anexo II
- Plantilla DoA canonical: ver `/admin/projects/[id]/dda` Tab "Catálogo" · 73 medidas filtrable marco+estado

---

## Phase 4 · Monitoring + Retainer post-cert

**phase_id**: `monitoring_retainer_cierre`
**motor_principal**: M23 retainer (+ Bloque 4 monitoring dashboards · m_compliance + m_compliance_monitor)
**target_url_admin_global**: `/admin/cross-project-compliance` + `/admin/system-health`
**target_url_admin_proyecto**: `/admin/projects/[id]/retainer`
**target_url_cliente**: `/client-portal/cumplimiento` + `/client-portal/retainer-checkin`

### intro

Una vez certificado el ENS, la implantación NO acaba: hay que **mantener el cumplimiento vivo**. El retainer es el contrato mensual post-cert (R_BÁSICO 700€ · R_MEDIO 1.500-2.500€ · R_ALTO 3.000-5.000€) que cubre vigilancia continua + revisión anual + auditoría bienal interna + cualquier cambio material que requiera adenda.

### why_important

El ENS exige **revisión anual** (CCN-STIC 802 §4.6) y **auditoría externa cada 2 años** (MEDIA/ALTA). Sin retainer activo el cliente "se duerme" · cuando llega la re-auditoría bienal aparecen findings que se podrían haber prevenido. El retainer también activa **alertas cloud-first auto-detect** (M_cloud_connectors diagnose daily · gap detection deterministic · NO LLM) y **propuestas de remediación** (Bloque 3+5 cumulative cumplimiento) que cliente aprueba inline.

### what_we_do

1. **Dashboard `/client-portal/cumplimiento`** muestra al cliente 5 áreas aggregadas friendly R29: conformity status · remediations pendientes · tasks indispensables · evidencias por subir · gaps M04 críticos. NO técnico · "Sin temas críticos abiertos" · "Faltan N documentos por subir cuando puedas".
2. **Dashboard `/admin/cross-project-compliance`** muestra a Marcos TODOS los proyectos retainer en single pane of glass · 5 KPI cards + filter chips + sortable table + drill-down per proyecto.
3. **Auto-detect cloud gaps** (M_cloud_connectors diagnose · Celery daily 04:00 ES) · si aparece gap ENS measure → CloudGap row + propose RemediationProposal admin (Bloque 3+5) → cliente aprueba/rechaza vía `/client-portal/mejoras-propuestas` → Marcos ejecuta admin manual + marca verified → audit trail inmutable ENAC.
4. **Revisión anual** (M25b revision_anual) · Marcos consolida cambios materiales (M28) · evalúa adendas (M14 cascade event-driven · 1.D.G EXPANDED + FASE C Path Hybrid) · genera informe revisión + cliente firma E-043 Renovación Conformidad anual.
5. **Check-in retainer mensual** (`/client-portal/retainer-checkin`) · cliente responde 3-5 preguntas core (¿incidentes? · ¿cambios sistema? · ¿personal nuevo?) · queda como evidencia continua.
6. **Auditoría externa cada 2 años** (MEDIA/ALTA · ENAC) → dossier auto-generado via M09 audit_prep (3485 LOC + 14-folder structure + 21 endpoints production · Future-1.E.dossier-pack-10docs scope) → cliente firma Declaración Conformidad renovada (E-041).

### common_mistakes

- **Cancelar retainer post-cert para "ahorrar"**: cuando llega la re-auditoría bienal, ramping up desde cero cuesta 3-5x el retainer ahorrado · y si hay gaps acumulados, FAIL audit.
- **Ignorar alertas cloud-first auto-detect**: aparecen en `/admin/cross-project-compliance` filtradas por severidad · si no se atienden gaps críticos en 72h, RemediationProposal escala a Marcos via inbox + WhatsApp.
- **Considerar el monitoring "post-trabajo"**: NO es post-trabajo · es operativa continua · 30-60 min/semana Marcos por cliente retainer + check-in mensual cliente.
- **Saltarse la revisión anual formal**: ENS exige documento revisado anualmente firmado · sin él, auditor ENAC suspende auditoría bienal hasta presentarlo.

### estimated_time

**Recurring mensual**: Marcos ~30-60 min/semana per cliente retainer · cliente ~5-10 min check-in mensual + 30 min revisión anual.
**Eventos puntuales**: revisión anual ~4-8h Marcos + cliente firma 30 min · auditoría bienal externa ~12-20h Marcos (dossier + acompañamiento auditor) + cliente disponibilidad sesiones.

### help_resources

- Dashboard cliente friendly: `/client-portal/cumplimiento` (aggregator R29 · NO técnico)
- Dashboard admin Marcos: `/admin/cross-project-compliance` (cross-cliente single pane of glass)
- Self-monitoring FULKRO platform: `/admin/system-health` (19 compliance checks + LLM anomalies + DB conn · MB-9.bis)
- Pregunta al copiloto: "¿Qué pasa si suspendo el retainer?" → respuesta con desglose económico + impacto re-auditoría
- Contractual: ver `/admin/projects/[id]/contratos` plantillas E-614 Trimestral + E-615 Anual retainer reports

---

## Remaining 6 phases · DEFER Sesión 3C content curation

DEFER Sesión 3C content curation (pattern reuse 4 phases above):
- **pre_venta** · M13 commercial pipeline (cualificación · propuesta · contrato firma)
- **onboarding** · M16 onboarding + dimensiones (post-categoría · roles ENS m30 + áreas + portal user)
- **adecuacion** · M04 Plan adecuación (gaps detected · acciones correctivas · fechas objetivo)
- **implantacion** · M06 Document Factory + M07 Evidence + M_live_records (documentos generables · evidencias subidas · registros vivos)
- **verificacion** · M08 verification + MCPs pentest (MEDIA/ALTA · pentest CPSTIC · findings)
- **conformidad** · M27 conformity + audit ENAC (declaración firma final · auditoría externa)

Each remaining phase will follow same structure: intro · why_important · what_we_do · common_mistakes · estimated_time · help_resources.

Cross-reference por phase enumerado en `frontend/components/dashboard/PhaseProgressWizard.tsx` 10 PHASES const + segment mapping URL.

---

## Style guide (R30 admin tutor + R29 cliente sostener firmísimo)

**R30 admin tutor primer principios**:
- Asume cero ENS · explica "por qué" antes "qué"
- Plain Spanish · jerga normativa explained inline
- Bullets ≤4 puntos · steps numbered si secuenciales
- "Auditor ENAC pide..." prefijo cuando aplique justification

**R29 cliente sin presión coercitiva**:
- "Cuando puedas" · "Sin prisa por tu parte"
- NO "urgente" · NO "preocupante" · NO "crítico" tono alarmista
- "Marcos te avisa cuando hay algo nuevo" tono empático
- Empty states celebratory: "✨ Todo al día"

**Cross-cutting**:
- Cita normativa explícita (RD 311/2022 · CCN-STIC · Anexo II · ISO) cuando aplique
- Links internal target_url_admin/cliente per phase
- Pregunta al copiloto: pattern reusable per phase (admin Sonnet 4.6 + cliente Haiku 4.5 · 1.D.B cumulative)
