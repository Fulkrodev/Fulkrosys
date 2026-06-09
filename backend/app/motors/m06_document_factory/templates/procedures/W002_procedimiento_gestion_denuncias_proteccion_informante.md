---
codigo_documento: "W-002"
titulo: "Procedimiento de Gestión de Comunicaciones del SII y Protección al Informante"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
politica_madre: "W-001"
norma_aplicable: "Ley 2/2023, de 20 de febrero · Arts. 9-15 (gestión) + 36-41 (protección)"
---

# PROCEDIMIENTO DE GESTIÓN DE COMUNICACIONES DEL SII Y PROTECCIÓN AL INFORMANTE DE {{ cliente.razon_social | upper }}

**Documento W-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set responsable_sii_nombre = responsables.responsable_sii.nombre if responsables.responsable_sii and responsables.responsable_sii.nombre else '[A DESIGNAR]' %}
{% set responsable_sii_cargo = responsables.responsable_sii.cargo if responsables.responsable_sii and responsables.responsable_sii.cargo else 'Responsable del SII' %}
{% set dpo_nombre = responsables.delegado_proteccion_datos.nombre if responsables.delegado_proteccion_datos and responsables.delegado_proteccion_datos.nombre else '[DPO]' %}

## 1. OBJETO

El presente procedimiento desarrolla la Política W-001 (Sistema Interno de Información) detallando la operativa de recepción, análisis preliminar, admisión, investigación, decisión y cierre de las comunicaciones recibidas por el canal interno, así como las medidas de protección al informante exigidas por los artículos 9 a 15 y 36 a 41 de la Ley 2/2023.

## 2. ÁMBITO

Aplica a toda comunicación recibida por cualquiera de los canales habilitados en el SII de la Entidad y a las personas comprendidas en el ámbito subjetivo de la Política W-001.

## 3. ROLES

| Rol | Responsabilidad principal |
|-----|---------------------------|
| **Responsable del SII** ({{ responsable_sii_nombre }}, {{ responsable_sii_cargo }}) | Recepción, tramitación, investigación y resolución de comunicaciones |
| **Investigador delegado** (cuando proceda) | Apoyo técnico al Responsable en investigaciones complejas |
| **Delegado de Protección de Datos** ({{ dpo_nombre }}) | Asesoramiento en tratamiento de datos asociado al SII |
| **Asesor Jurídico interno o externo** | Asesoramiento legal cuando proceda |
| **Órgano de administración** | Recepción del informe anual + supervisión del SII |

## 4. FASES DEL PROCEDIMIENTO

### 4.1 Fase 1 — Recepción de la comunicación

a) Toda comunicación recibida por el canal interno (electrónico, postal o verbal) se registra en el Libro Registro Electrónico del SII con identificador único y huella de tiempo, garantizando integridad y trazabilidad.

b) El Responsable del SII acusa recibo de la comunicación al informante en un plazo máximo de **siete (7) días naturales** desde su recepción, salvo cuando la comunicación sea anónima o cuando el acuse pudiera comprometer la confidencialidad.

c) En el caso de comunicaciones verbales, se levantará acta de la sesión a la que tendrá acceso el informante para verificar su contenido y, en su caso, rectificarlo o complementarlo.

### 4.2 Fase 2 — Análisis preliminar

d) En los **siete (7) días naturales** siguientes a la recepción, el Responsable del SII realiza un análisis preliminar de la comunicación para determinar:

- Si la información recibida está comprendida en el ámbito material del SII (artículo 2 de la Ley 2/2023 + Política W-001 § 3.2).
- Si existe verosimilitud suficiente para iniciar actuaciones.
- Si la comunicación es manifiestamente infundada, repetitiva o presentada con manifiesto abuso de derecho.

### 4.3 Fase 3 — Decisión de admisión o inadmisión

e) El Responsable del SII emite **decisión motivada** sobre la admisión o inadmisión a trámite, en un plazo no superior a **diez (10) días naturales** desde la finalización del análisis preliminar.

f) La inadmisión se motivará en alguna de las siguientes causas:

- Inexistencia de indicios verosímiles de las infracciones comunicadas.
- Manifiesta falta de fundamento.
- Repetición sustancial de comunicaciones previas que no aporten información significativamente nueva.
- Manifiesto abuso de derecho.
- Comunicación referida a hechos manifiestamente fuera del ámbito material del SII.

g) La decisión se notifica al informante salvo que su identidad sea desconocida (anonimato).

### 4.4 Fase 4 — Investigación

h) Admitida la comunicación, se inicia la fase de investigación, conducida por el Responsable del SII o por persona en quien delegue. La investigación se desarrollará con respeto absoluto al principio de presunción de inocencia respecto de la persona afectada y a sus derechos de defensa.

i) Durante la investigación podrán realizarse, entre otras, las siguientes actuaciones:

- Entrevistas con el informante, con la persona afectada y, en su caso, con testigos.
- Análisis de documentación pertinente.
- Solicitud de información a las áreas funcionales de la Entidad que corresponda.
- Coordinación con servicios técnicos especializados.

j) La persona afectada será informada de la comunicación en su contra y de su derecho a ser oída, en el momento en que dicha información no pueda comprometer las actuaciones de investigación, y siempre con respeto a la confidencialidad del informante.

k) La investigación se desarrollará en un plazo no superior a **tres (3) meses** desde la admisión a trámite, prorrogable por un único período adicional de hasta **tres (3) meses más** mediante decisión motivada del Responsable del SII, conforme al artículo 9.2 de la Ley 2/2023.

### 4.5 Fase 5 — Decisión y medidas correctivas

l) Concluida la investigación, el Responsable del SII emite un **informe final** con sus conclusiones, en el que se identifican las medidas correctivas, disciplinarias, organizativas o de cualquier otra naturaleza que correspondan.

m) En su caso, el informe podrá proponer:

- La adopción de medidas correctivas operativas.
- La incoación de expediente disciplinario interno.
- La comunicación de los hechos a las autoridades judiciales o administrativas competentes.
- El cierre del expediente cuando no se acredite la existencia de infracción.

n) La decisión final corresponderá al órgano competente conforme a la normativa interna de la Entidad y, cuando proceda, al órgano de administración.

### 4.6 Fase 6 — Cierre e información al informante

o) Adoptada la decisión, se procede al cierre formal del expediente, dejándose constancia en el Libro Registro.

p) Se notifica al informante el resultado de las actuaciones, salvo cuando sea anónimo o cuando la notificación pueda comprometer derechos de terceros o el desarrollo de procedimientos administrativos o judiciales posteriores.

## 5. GARANTÍAS DURANTE TODO EL PROCEDIMIENTO

### 5.1 Confidencialidad operativa

La identidad del informante, de las personas afectadas y de cualquier tercero mencionado, así como la información manejada, se tratarán con la máxima reserva. Únicamente accederán al expediente las personas con un interés legítimo y estricta necesidad para el desempeño de sus funciones en el procedimiento.

### 5.2 Protección activa frente a represalias

a) Desde el momento de la comunicación, el Responsable del SII vela por la protección del informante frente a cualquier acto que pudiera constituir represalia, conforme a los artículos 36 a 41 de la Ley 2/2023.

b) Cualquier acto adoptado en perjuicio del informante en los **dos (2) años siguientes** a la presentación de la comunicación se presumirá represalia, correspondiendo a la Entidad o a la persona que lo adopte acreditar que se basa en motivos justificados y proporcionados independientes del hecho de la comunicación.

c) Acreditada la existencia de represalia, la Entidad adoptará las medidas correctoras necesarias y comunicará la situación al informante para que pueda hacer valer sus derechos, incluyendo la posibilidad de dirigirse a la AAI.

### 5.3 Tratamiento de datos personales

a) El tratamiento de datos personales se realiza conforme al RGPD, la LOPDGDD y los artículos 30 a 35 de la Ley 2/2023, bajo la base jurídica de cumplimiento de obligación legal (artículo 6.1.c) RGPD).

b) Únicamente se conservarán los datos estrictamente necesarios para la decisión sobre la admisión y, en su caso, para la investigación.

c) La conservación máxima en el sistema es de **diez (10) años** desde la finalización de la investigación, salvo cuando sea necesario un plazo superior por requerimiento de autoridad competente.

d) Las personas afectadas podrán ejercer sus derechos RGPD a través del DPO, sin que ello pueda comprometer la confidencialidad del informante ni el desarrollo de las actuaciones del SII.

## 6. LIBRO REGISTRO DE COMUNICACIONES DEL SII

a) La Entidad mantiene un Libro Registro electrónico de las comunicaciones recibidas, con la información mínima exigida por el artículo 26 de la Ley 2/2023:

- Identificador único del expediente.
- Fecha y modalidad de recepción.
- Descripción genérica del objeto.
- Estado del expediente.
- Fechas de las actuaciones más relevantes.
- Persona responsable del expediente.

b) El Libro Registro se mantiene con las medidas técnicas y organizativas necesarias para garantizar la confidencialidad y la trazabilidad inmutable.

c) El acceso al Libro está restringido al Responsable del SII y a las personas autorizadas por este con estricta necesidad.

## 7. INFORME ANUAL DE ACTIVIDAD

a) Anualmente, el Responsable del SII elabora un informe agregado y anonimizado de la actividad del Sistema, que se eleva al órgano de administración antes del **31 de marzo** de cada año.

b) El informe contiene, al menos:

- Número total de comunicaciones recibidas en el ejercicio anterior, desglosado por modalidad de canal.
- Número de comunicaciones admitidas y rechazadas, con indicación de las causas de rechazo en términos agregados.
- Número de comunicaciones investigadas y cerradas en el ejercicio.
- Plazos medios de las distintas fases del procedimiento.
- Tipología agregada de las cuestiones planteadas.
- Medidas correctivas adoptadas en términos agregados.
- Recomendaciones para la mejora del Sistema.

## 8. INDICADORES OPERATIVOS

| Indicador | Objetivo |
|-----------|---------:|
| Acuse de recibo al informante en plazo ≤ 7 días | 100% |
| Decisión de admisión en plazo ≤ 17 días naturales totales | ≥ 95% |
| Investigación concluida dentro del plazo legal (3+3 meses) | 100% |
| Comunicaciones gestionadas sin incidente de confidencialidad | 100% |
| Represalias documentadas adoptadas por la Entidad contra informantes | 0 |

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobado por el órgano competente de la Entidad junto con la Política W-001. Revisión bienal y siempre que se produzcan cambios normativos relevantes.

---

**Documento W-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}*
