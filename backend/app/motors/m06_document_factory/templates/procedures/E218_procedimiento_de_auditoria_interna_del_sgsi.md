# DOCUMENTO E-218 — PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI

**Materializa el artículo 31 del RD 311/2022 y la ITS de Auditoría de la Seguridad** (Resolución BOE-A-2018-4573), así como el control A.9.2 (Internal audit) de ISO/IEC 27001:2022. Es el procedimiento que el auditor externo ENAC pide consultar antes de empezar su propia auditoría: si la auditoría interna está bien hecha, la externa fluye.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-218"
titulo: "Procedimiento de Auditoría Interna del SGSI"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-218 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} planifica, ejecuta, comunica y realiza el seguimiento de las auditorías internas del SGSI, con el doble objetivo de:

a) Verificar el cumplimiento del SGSI con los requisitos del Real Decreto 311/2022 y de las normas y procedimientos internos de la Entidad.

b) Identificar oportunidades de mejora del SGSI y de la postura general de seguridad.

Este procedimiento da cumplimiento al **artículo 31 del Real Decreto 311/2022** (Auditoría) y a la **Instrucción Técnica de Seguridad de Auditoría de la Seguridad** publicada por Resolución de 27 de marzo de 2018 (BOE-A-2018-4573), y complementa, sin sustituirla, a la auditoría externa de certificación realizada por una entidad acreditada por ENAC conforme a la norma UNE-EN ISO/IEC 17065:2012.

## 2. ALCANCE

La auditoría interna abarca la totalidad del SGSI implantado en {{ cliente.razon_social }}, incluyendo:

a) Cumplimiento documental: verificación de la existencia, vigencia y aprobación de las políticas, procedimientos e instrucciones técnicas.

b) Cumplimiento operativo: verificación de que las medidas declaradas en la Declaración de Aplicabilidad están realmente implantadas y son eficaces.

c) Cumplimiento técnico: verificación mediante pruebas de la robustez técnica de los controles desplegados.

d) Cumplimiento de obligaciones legales: verificación del cumplimiento del marco normativo aplicable (RD 311/2022, RGPD, LOPDGDD y normativa sectorial cuando proceda).

## 3. PRINCIPIOS DE LA AUDITORÍA INTERNA

### 3.1 Independencia

El equipo auditor será **funcionalmente independiente** de las áreas auditadas. En particular, el Responsable del Sistema no podrá auditar los aspectos técnicos cuya operación tenga encomendada.

Cuando, por la dimensión de la Entidad, no sea posible garantizar plenamente la independencia interna, se recurrirá a un **auditor externo independiente** específicamente contratado para esta función, distinto en cualquier caso de la entidad de certificación.

### 3.2 Objetividad

Los hallazgos de auditoría se basarán exclusivamente en **evidencias objetivas** documentadas, no en opiniones o impresiones del auditor.

### 3.3 Profesionalidad

El equipo auditor contará con la **formación y experiencia** adecuadas en materia de seguridad de la información, ENS y técnicas de auditoría.

### 3.4 Confidencialidad

La información a la que el equipo auditor acceda en el ejercicio de sus funciones estará sujeta a estricto deber de confidencialidad, formalizándose mediante el correspondiente acuerdo cuando intervengan auditores externos.

### 3.5 Carácter constructivo

La auditoría interna tiene **carácter constructivo y de mejora**, no sancionador. Su objetivo es identificar oportunidades de mejora y no buscar culpables.

## 4. FRECUENCIA

### 4.1 Auditoría completa ordinaria

Se realizará una **auditoría interna completa anual** del SGSI, conforme exige el artículo 31 del RD 311/2022. La auditoría se programará idealmente para los **3-6 meses anteriores** a la auditoría externa de certificación, de modo que sus hallazgos puedan ser corregidos antes del paso del auditor ENAC.

### 4.2 Auditorías parciales

Adicionalmente, podrán realizarse **auditorías parciales** centradas en aspectos específicos cuando:

- Se introduzcan cambios significativos en el sistema.
- Se materialice un incidente relevante.
- Se identifiquen áreas de riesgo elevado en el análisis de riesgos.
- Lo decida el Comité de Seguridad.

### 4.3 Auditorías de seguimiento

Tras una auditoría que detecte no conformidades, se realizarán **auditorías de seguimiento** para verificar la efectividad de las acciones correctivas.

## 5. EQUIPO AUDITOR

### 5.1 Composición

El equipo auditor estará integrado por al menos:

- **Auditor jefe:** persona con experiencia acreditada en auditoría de SGSI conforme al ENS o a ISO 27001, formación específica en técnicas de auditoría y conocimiento del marco normativo aplicable.

- **Auditor técnico:** persona con conocimientos técnicos suficientes para evaluar los controles tecnológicos.

- **Auditor de procesos:** cuando proceda, persona especializada en procesos organizativos.

### 5.2 Cualificación

El equipo auditor acreditará formación en, al menos, una de las siguientes vías:

- Curso oficial de auditoría ENS impartido por el CCN o por entidad reconocida.
- Certificación ISO 27001 Lead Auditor.
- Certificación CISA (Certified Information Systems Auditor).
- Experiencia demostrable de al menos 3 auditorías SGSI ENS previas.

### 5.3 Designación

El equipo auditor será propuesto por el Responsable de la Seguridad y aprobado por el Comité de Seguridad, garantizando los principios de independencia y objetividad del apartado 3.

## 6. PROCESO DE AUDITORÍA

### 6.1 Planificación

**Paso 1.** Con al menos 30 días naturales de antelación al inicio de la auditoría, el Responsable de la Seguridad elabora el **Plan de Auditoría Interna** que incluirá:

- Alcance específico de la auditoría.
- Criterios de auditoría (RD 311/2022, normativa interna, normas ISO aplicables).
- Calendario detallado.
- Composición del equipo auditor.
- Áreas y procesos a auditar.
- Métodos a emplear (entrevistas, revisión documental, observación, pruebas técnicas).
- Recursos necesarios.

**Paso 2.** El Plan se comunica a las áreas auditadas con la antelación suficiente.

### 6.2 Reunión de apertura

**Paso 3.** La auditoría se inicia con una **reunión de apertura** en la que:

- Se presenta el equipo auditor.
- Se confirma el alcance, los criterios y el calendario.
- Se acuerdan los canales de comunicación y los enlaces operativos.
- Se aclaran las dudas previas.

### 6.3 Trabajo de campo

**Paso 4.** El equipo auditor realiza el trabajo de campo aplicando una combinación de las siguientes técnicas:

a) **Revisión documental:** revisión de las políticas, procedimientos, registros, actas, informes y demás documentación del SGSI.

b) **Entrevistas:** entrevistas estructuradas con los responsables y operadores de los procesos, basadas en preguntas estándar (Anexo II).

c) **Observación:** observación directa de la ejecución de los procesos.

d) **Pruebas de cumplimiento:** verificación práctica del cumplimiento de los controles mediante muestras representativas.

e) **Pruebas técnicas:** ejecución de pruebas técnicas concretas (revisión de configuraciones, escaneos, pruebas de control de acceso, verificación de logs).

**Paso 5.** Cada hallazgo se documenta indicando:

- Criterio de auditoría aplicado.
- Evidencia objetiva observada.
- Conformidad o no conformidad.
- En caso de no conformidad, su tipificación (ver apartado 7).

### 6.4 Reunión de cierre

**Paso 6.** Al finalizar el trabajo de campo se celebra una **reunión de cierre** en la que el equipo auditor presenta los principales hallazgos a las áreas auditadas, recoge sus comentarios y aclara posibles malentendidos.

### 6.5 Informe de auditoría

**Paso 7.** En el plazo máximo de **15 días naturales** desde la reunión de cierre, el equipo auditor elabora el **Informe de Auditoría Interna** que incluirá:

- Resumen ejecutivo.
- Alcance, objetivos y criterios de la auditoría.
- Equipo auditor y áreas auditadas.
- Metodología empleada.
- Resumen de hallazgos.
- Detalle de cada no conformidad y observación.
- Recomendaciones de mejora.
- Conclusiones generales y valoración global del SGSI.

**Paso 8.** El Informe se eleva al Comité de Seguridad y, en su caso, a {{ cliente.organo_aprobador_politicas }}.

## 7. TIPIFICACIÓN DE HALLAZGOS

Los hallazgos de auditoría se tipifican conforme a la siguiente escala:

| Tipo | Definición | Acción requerida |
|---|---|---|
| **No conformidad mayor** | Incumplimiento sistemático de un requisito esencial, ausencia total de un control crítico, o conjunto de no conformidades menores que en agregado evidencian un fallo sistémico | Plan de acción correctivo en 15 días, ejecución máxima en 90 días, verificación obligatoria |
| **No conformidad menor** | Incumplimiento puntual o aislado, fallo en un control no crítico o ineficacia parcial de una medida implantada | Plan de acción correctivo en 30 días, ejecución máxima en 180 días |
| **Observación** | Cumplimiento formal pero con potencial mejora, hallazgo que sin ser incumplimiento merece atención | Análisis y, en su caso, plan de mejora voluntario |
| **Oportunidad de mejora** | Recomendación del auditor para optimizar el SGSI, sin que exista incumplimiento | Análisis del Comité de Seguridad |

## 8. PLAN DE ACCIÓN CORRECTIVA

**Paso 9.** Para cada no conformidad detectada, el responsable del área auditada elabora un **Plan de Acción Correctiva** (PAC) que incluya:

- Análisis de la causa raíz del hallazgo.
- Acciones correctivas a implantar.
- Acciones preventivas para evitar la repetición.
- Responsable de cada acción.
- Plazo de ejecución.
- Indicador para verificar el cierre.

**Paso 10.** El PAC se eleva al Responsable de la Seguridad para su aprobación, y posteriormente al Comité de Seguridad para conocimiento.

## 9. SEGUIMIENTO Y CIERRE

**Paso 11.** El Responsable de la Seguridad realiza el seguimiento del cumplimiento de los PAC, registrando el avance en el sistema de gestión del SGSI.

**Paso 12.** Una vez completadas las acciones correctivas, se realiza una **verificación del cierre**, que puede consistir en:

- Revisión documental de las evidencias aportadas.
- Auditoría parcial de seguimiento.
- Verificación in situ por parte del auditor original.

**Paso 13.** Las no conformidades verificadas se cierran formalmente. Las no verificadas o cuya solución no resulta satisfactoria permanecen abiertas y se reportan al Comité de Seguridad.

## 10. RELACIÓN CON LA AUDITORÍA EXTERNA

**Paso 14.** Los resultados de la auditoría interna se ponen a disposición del auditor externo de certificación (entidad ENAC) cuando lo solicite. La existencia de auditoría interna eficaz se considerará por el auditor externo como evidencia de la **madurez del SGSI**.

**Paso 15.** Las no conformidades detectadas en la auditoría interna y no resueltas pueden ser detectadas también por el auditor externo, por lo que es responsabilidad del SGSI cerrarlas con anticipación a la auditoría externa.

## 11. INDICADORES

| Indicador | Objetivo |
|---|---|
| Auditoría interna anual realizada | 100% (1 al año) |
| Cumplimiento del Plan de Auditoría | ≥ 95% del alcance previsto |
| No conformidades mayores cerradas en plazo | 100% |
| No conformidades menores cerradas en plazo | ≥ 90% |
| No conformidades repetidas año a año | 0 |
| Antelación de la auditoría interna respecto a la externa | 3-6 meses |

## 12. ANEXOS

- **Anexo I:** Plantilla del Plan de Auditoría Interna
- **Anexo II:** Cuestionarios estándar de entrevista por área
- **Anexo III:** Plantilla del Informe de Auditoría Interna
- **Anexo IV:** Plantilla del Plan de Acción Correctiva
- **Anexo V:** Lista de comprobación de cumplimiento ENS basada en CCN-STIC 808 Anexo III

---

**Documento {{ proyecto.codigo_documento_base }}-218 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```
