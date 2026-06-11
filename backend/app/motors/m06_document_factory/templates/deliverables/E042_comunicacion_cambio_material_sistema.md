---
codigo_documento: "E-042"
titulo: "Comunicación de Cambio Material en el Sistema"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA · COMUNICACIÓN CCN"
norma_aplicable: "RD 311/2022 Art. 30 + CCN-STIC 809"
---

# COMUNICACIÓN DE CAMBIO MATERIAL EN EL SISTEMA · {{ cliente.razon_social | upper }}

**Documento E-042 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set cm = cambio_material if cambio_material else {} %}
{% set fecha = cm.fecha_deteccion if cm and cm.fecha_deteccion else '[fecha]' %}
{% set descripcion = cm.descripcion if cm and cm.descripcion else '[descripción del cambio]' %}
{% set motivacion = cm.motivacion if cm and cm.motivacion else '[motivación]' %}
{% set riesgo = cm.riesgo_residual_estimado if cm and cm.riesgo_residual_estimado else 'POR DETERMINAR' %}
{% set recat = cm.requiere_recategorizacion if cm and cm.requiere_recategorizacion is defined else False %}
{% set tiene_medidas = cm.impacto_medidas_afectadas and cm.impacto_medidas_afectadas | length > 0 %}

## 1. DATOS IDENTIFICATIVOS

| Campo | Valor |
|-------|-------|
| Entidad | **{{ cliente.razon_social }}** · NIF {{ cliente.nif }} |
| Sistema afectado | Sistema certificado bajo categoría **{{ proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' }}** |
| Fecha detección del cambio | **{{ fecha }}** |
| Tipo de comunicación | Notificación de cambio material · Art. 30 RD 311/2022 |

## 2. MARCO NORMATIVO

Conforme al **artículo 30** del RD 311/2022 y a la Guía CCN-STIC 809, la Entidad está obligada a comunicar al CCN los **cambios materiales** que afecten al sistema certificado y que puedan alterar las condiciones bajo las cuales se otorgó la conformidad ENS.

## 3. DESCRIPCIÓN DEL CAMBIO

**Naturaleza del cambio:** {{ descripcion }}

**Motivación:** {{ motivacion }}

**Fecha prevista de implantación efectiva:** {{ cm.fecha_implantacion_prevista if cm and cm.fecha_implantacion_prevista else 'Inmediata' }}

## 4. EVALUACIÓN DE IMPACTO

### 4.1 Medidas del Anexo II afectadas

{% if tiene_medidas %}
| Código de medida | Tipo de afectación |
|------------------|---------------------|
{% for m in cm.impacto_medidas_afectadas %}
| **{{ m }}** | Revisión / actualización requerida |
{% endfor %}
{% else %}
*No se identifican medidas afectadas significativamente por el cambio. La verificación operativa se mantiene conforme al estado actual.*
{% endif %}

### 4.2 Riesgo residual estimado

> **Riesgo residual estimado tras el cambio: {{ riesgo }}**

### 4.3 Evaluación de la necesidad de recategorización

{% if recat %}
El cambio implica una **alteración significativa** de las dimensiones del sistema. Se procede a **recategorización** mediante la convocatoria del Comité de Seguridad y la emisión de nueva acta E-012.
{% else %}
El cambio **no altera significativamente** las dimensiones del sistema. Se mantiene la categoría **{{ proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' }}** sin necesidad de recategorización formal.
{% endif %}

## 5. ACTUACIONES PREVISTAS

a) **Actualización de la Declaración de Aplicabilidad (E-040)** para reflejar las medidas afectadas.

b) **Actualización del Plan de Adecuación (E-150)** si procede.

c) **Actualización del Análisis de Riesgos (E-400)** para incorporar el cambio en el modelo de amenazas.

d) **Notificación a las partes interesadas** afectadas, incluyendo en su caso clientes con contratos vigentes que exijan ENS.

e) {{ "Reapertura del expediente de **certificación** para emisión de nuevo certificado por la entidad acreditada." if proyecto.categoria_ens != 'BÁSICA' else "Actualización de la Declaración de Conformidad (E-041) y republicación en sede electrónica." }}

## 6. APROBACIÓN

| Cargo | Nombre | Firma | Fecha |
|-------|--------|-------|-------|
| Responsable de la Seguridad | {{ responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[RS]' }} | _______________ | {{ fecha }} |
| Responsable del Sistema | {{ responsables.responsable_sistema.nombre if responsables.responsable_sistema else '[RSI]' }} | _______________ | {{ fecha }} |
| Presidente del Comité de Seguridad | {{ comite_seguridad.presidente.nombre if comite_seguridad and comite_seguridad.presidente else '[Presidente]' }} | _______________ | {{ fecha }} |

## 7. REMISIÓN AL CCN-CERT

La presente comunicación se remite al CCN-CERT a los efectos del artículo 30 del RD 311/2022, junto con la documentación complementaria detallada en sección 5.

---

**Documento E-042 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA · COMUNICACIÓN CCN**

*Documento generado por FULKRO · {{ fecha }}*
