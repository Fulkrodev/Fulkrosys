# DOCUMENTO E-050 — INFORME DE AUDITORÍA INTERNA DEL SGSI

**Es la plantilla del informe que produce el procedimiento E-234.** Es el documento que el auditor interno (sea Marcos como consultor independiente o un auditor designado por el cliente) entrega tras realizar la auditoría interna anual del SGSI.

```jinja
---
codigo_documento: "E-050"
titulo: "Informe de Auditoría Interna del SGSI"
version: "{{ auditoria.version | default('1.0') }}"
fecha: "{{ auditoria.fecha_informe }}"
clasificacion: "CONFIDENCIAL — Cliente"
auditor_jefe: "{{ auditoria.auditor_jefe }}"
---

# INFORME DE AUDITORÍA INTERNA DEL SGSI

## {{ cliente.razon_social }}

**Documento E-050 · Versión {{ auditoria.version | default('1.0') }} · {{ auditoria.fecha_informe }}**

---

## 1. RESUMEN EJECUTIVO

| Concepto | Detalle |
|---|---|
| Cliente auditado | {{ cliente.razon_social }} |
| Categoría ENS del sistema | {{ proyecto.categoria_ens }} |
| Periodo de auditoría | {{ auditoria.fecha_inicio }} a {{ auditoria.fecha_fin }} |
| Auditor jefe | {{ auditoria.auditor_jefe }} |
| Auditor técnico | {{ auditoria.auditor_tecnico | default('—') }} |
| Norma de referencia | RD 311/2022 + UNE-EN ISO/IEC 27001:2022 |
| Tipo de auditoría | {{ auditoria.tipo }} |
| Resultado global | {% if auditoria.resultado == "favorable" %}🟢 **FAVORABLE**{% elif auditoria.resultado == "favorable_observaciones" %}🟡 **FAVORABLE CON OBSERVACIONES**{% else %}🔴 **CON HALLAZGOS RELEVANTES**{% endif %} |

### 1.1 Conclusión

{{ auditoria.conclusion_resumen }}

---

## 2. ALCANCE DE LA AUDITORÍA

### 2.1 Sistema auditado

El alcance del SGSI auditado coincide con el alcance certificado de {{ cliente.razon_social }}:

> {{ proyecto.alcance.descripcion_completa }}

### 2.2 Áreas y procesos auditados

{% for area in auditoria.areas_auditadas %}
- **{{ area.nombre }}** — {{ area.descripcion }}
{% endfor %}

### 2.3 Documentos revisados

Se han revisado todos los documentos vigentes del SGSI, incluyendo las **9 políticas** del bloque POL-100 a POL-108 y los **12 procedimientos** del bloque POL-200 a POL-234.

---

## 3. CRITERIOS DE AUDITORÍA

La auditoría se ha realizado conforme a los siguientes criterios:

a) **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad, en particular su Anexo II (Medidas de seguridad).

b) **Resolución de 27 de marzo de 2018** (BOE-A-2018-4573), Instrucción Técnica de Seguridad de Auditoría de la Seguridad de los Sistemas de Información.

c) **Norma UNE-EN ISO/IEC 27001:2022** — Sistemas de Gestión de la Seguridad de la Información — Requisitos.

d) **Guía CCN-STIC 802** — Guía de auditoría del ENS.

e) **Guía CCN-STIC 808** — Verificación del cumplimiento del ENS.

f) **Documentación interna del SGSI** de {{ cliente.razon_social }}.

---

## 4. EQUIPO AUDITOR

| Rol | Nombre | Cualificación |
|---|---|---|
| Auditor jefe | {{ auditoria.auditor_jefe }} | {{ auditoria.cualificacion_jefe }} |
{% if auditoria.auditor_tecnico %}
| Auditor técnico | {{ auditoria.auditor_tecnico }} | {{ auditoria.cualificacion_tecnico }} |
{% endif %}

**Declaración de independencia:** {{ auditoria.declaracion_independencia }}

---

## 5. METODOLOGÍA EMPLEADA

La auditoría se ha desarrollado aplicando una combinación de las siguientes técnicas, conforme al procedimiento E-234 implantado:

a) **Revisión documental** — análisis de las políticas, procedimientos, instrucciones, registros y evidencias del SGSI.

b) **Entrevistas estructuradas** con los responsables y operadores de los procesos auditados, basadas en cuestionarios estándar por área (Anexo II del E-234).

c) **Observación directa** de la ejecución de procesos operativos clave.

d) **Pruebas de cumplimiento** mediante verificación práctica sobre muestras representativas de cuentas, accesos, configuraciones, copias de seguridad y demás controles.

e) **Pruebas técnicas** sobre configuraciones de sistemas, controles de acceso, registros de logs, ejecución de copias de seguridad y otros elementos técnicos del SGSI.

### 5.1 Cronograma de la auditoría

| Día | Actividad |
|---|---|
{% for dia in auditoria.cronograma %}
| {{ dia.fecha }} | {{ dia.actividad }} |
{% endfor %}

---

## 6. HALLAZGOS DE LA AUDITORÍA

### 6.1 Resumen de hallazgos

| Tipo | Cantidad |
|---|---|
| **No conformidades mayores** | {{ auditoria.nc_mayores | length }} |
| **No conformidades menores** | {{ auditoria.nc_menores | length }} |
| **Observaciones** | {{ auditoria.observaciones | length }} |
| **Oportunidades de mejora** | {{ auditoria.oportunidades | length }} |
| **TOTAL** | {{ auditoria.total_hallazgos }} |

### 6.2 No conformidades mayores

{% if auditoria.nc_mayores %}
{% for nc in auditoria.nc_mayores %}
**NCM-{{ '%03d' % loop.index }}** — {{ nc.titulo }}

- **Criterio incumplido:** {{ nc.criterio }}
- **Evidencia:** {{ nc.evidencia }}
- **Descripción:** {{ nc.descripcion }}
- **Impacto:** {{ nc.impacto }}
- **Acción correctiva requerida:** {{ nc.accion_correctiva }}
- **Plazo máximo:** 90 días naturales

{% endfor %}
{% else %}
_No se han detectado no conformidades mayores en la presente auditoría._
{% endif %}

### 6.3 No conformidades menores

{% if auditoria.nc_menores %}
{% for nc in auditoria.nc_menores %}
**NCm-{{ '%03d' % loop.index }}** — {{ nc.titulo }}

- **Criterio incumplido:** {{ nc.criterio }}
- **Evidencia:** {{ nc.evidencia }}
- **Descripción:** {{ nc.descripcion }}
- **Acción correctiva propuesta:** {{ nc.accion_correctiva }}
- **Plazo máximo:** 180 días naturales

{% endfor %}
{% else %}
_No se han detectado no conformidades menores en la presente auditoría._
{% endif %}

### 6.4 Observaciones

{% if auditoria.observaciones %}
{% for obs in auditoria.observaciones %}
**OBS-{{ '%03d' % loop.index }}** — {{ obs.titulo }}

{{ obs.descripcion }}

{% endfor %}
{% else %}
_No se han registrado observaciones en la presente auditoría._
{% endif %}

### 6.5 Oportunidades de mejora

{% if auditoria.oportunidades %}
{% for op in auditoria.oportunidades %}
**OM-{{ '%03d' % loop.index }}** — {{ op.titulo }}

{{ op.descripcion }}

{% endfor %}
{% else %}
_No se han identificado oportunidades de mejora específicas en la presente auditoría._
{% endif %}

---

## 7. EVALUACIÓN POR FAMILIA DE MEDIDAS DEL ANEXO II DEL ENS

| Familia | Conformidad | Hallazgos |
|---|---|---|
{% for familia in auditoria.evaluacion_por_familia %}
| {{ familia.codigo }} — {{ familia.nombre }} | {{ familia.conformidad }} | {{ familia.hallazgos }} |
{% endfor %}

---

## 8. EVALUACIÓN POR DIMENSIÓN DE SEGURIDAD

| Dimensión | Estado de los controles | Comentario |
|---|---|---|
| Confidencialidad | {{ auditoria.dimensiones.confidencialidad.estado }} | {{ auditoria.dimensiones.confidencialidad.comentario }} |
| Integridad | {{ auditoria.dimensiones.integridad.estado }} | {{ auditoria.dimensiones.integridad.comentario }} |
| Disponibilidad | {{ auditoria.dimensiones.disponibilidad.estado }} | {{ auditoria.dimensiones.disponibilidad.comentario }} |
| Autenticidad | {{ auditoria.dimensiones.autenticidad.estado }} | {{ auditoria.dimensiones.autenticidad.comentario }} |
| Trazabilidad | {{ auditoria.dimensiones.trazabilidad.estado }} | {{ auditoria.dimensiones.trazabilidad.comentario }} |

---

## 9. CONCLUSIÓN GENERAL

{{ auditoria.conclusion_completa }}

### 9.1 Valoración global del SGSI

Tras la auditoría realizada, el equipo auditor concluye que el SGSI implantado en {{ cliente.razon_social }} presenta el siguiente nivel de madurez global:

| Dimensión de evaluación | Nivel |
|---|---|
| Documentación | {{ auditoria.madurez.documentacion }} |
| Implantación operativa | {{ auditoria.madurez.implantacion }} |
| Eficacia de los controles | {{ auditoria.madurez.eficacia }} |
| Mejora continua | {{ auditoria.madurez.mejora_continua }} |
| **Valoración global** | **{{ auditoria.madurez.global }}** |

### 9.2 Recomendaciones generales

{% for rec in auditoria.recomendaciones %}
{{ loop.index }}. {{ rec }}
{% endfor %}

---

## 10. SEGUIMIENTO PROPUESTO

El equipo auditor propone el siguiente calendario de seguimiento de los hallazgos:

| Hito | Plazo desde el presente informe |
|---|---|
| Entrega de los planes de acción correctiva por parte del cliente | 15 días naturales |
| Aprobación de los planes por el Responsable de la Seguridad | 30 días naturales |
| Verificación del cierre de no conformidades menores | 6 meses |
| Verificación del cierre de no conformidades mayores | 90 días |
| Próxima auditoría interna ordinaria | {{ auditoria.proxima_auditoria }} |

---

## 11. ANEXOS

- **Anexo I:** Listado completo de documentos del SGSI revisados
- **Anexo II:** Personas entrevistadas y áreas implicadas
- **Anexo III:** Detalle técnico de las pruebas realizadas
- **Anexo IV:** Evidencias fotográficas o capturas relevantes
- **Anexo V:** Cuestionarios de auditoría empleados

---

**Auditor jefe:** {{ auditoria.auditor_jefe }}
**Fecha del informe:** {{ auditoria.fecha_informe }}
**Firma:** _____________

**Documento E-050 · {{ cliente.razon_social }} · Versión {{ auditoria.version | default('1.0') }}**

```

---
