---
codigo_documento: "E-043"
titulo: "Renovación Periódica de la Conformidad con el ENS"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "PÚBLICA"
norma_aplicable: "RD 311/2022 Art. 35 + CCN-STIC 809"
---

# RENOVACIÓN PERIÓDICA DE LA CONFORMIDAD CON EL ESQUEMA NACIONAL DE SEGURIDAD · {{ cliente.razon_social | upper }}

**Documento E-043 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set ren = renovacion if renovacion else {} %}
{% set period = ren.periodicidad_anios if ren and ren.periodicidad_anios else 3 %}
{% set period_str = period ~ ' años después de la actual' %}
{% set fecha_ant = ren.fecha_renovacion_anterior if ren and ren.fecha_renovacion_anterior else '[fecha anterior]' %}
{% set fecha_act = ren.fecha_proxima_renovacion if ren and ren.fecha_proxima_renovacion else '[fecha actual]' %}
{% set fecha_sig = ren.fecha_siguiente_renovacion if ren and ren.fecha_siguiente_renovacion else '[' ~ period_str ~ ']' %}
{% set tiene_cambios = ren.cambios_desde_anterior_revision and ren.cambios_desde_anterior_revision | length > 0 %}
{% set cat = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}
{% set basica = cat == 'BÁSICA' or cat == 'BASICA' %}

## 1. DATOS IDENTIFICATIVOS

| Campo | Valor |
|-------|-------|
| Entidad | **{{ cliente.razon_social }}** · NIF {{ cliente.nif }} |
| Categoría ENS | **{{ cat }}** |
| Periodicidad de renovación | **{{ period }} años** ({{ '2 años categoría Básica' if basica else '3 años categorías Media/Alta' }}) |
| Renovación anterior | {{ fecha_ant }} |
| Renovación actual | **{{ fecha_act }}** |
| Próxima renovación prevista | {{ fecha_sig }} |

## 2. MARCO NORMATIVO

Conforme al **artículo 35** del RD 311/2022, la conformidad con el ENS se renueva periódicamente con la siguiente cadencia:

- Categoría **Básica:** cada **2 años**, mediante autoevaluación documentada.
- Categorías **Media** y **Alta:** cada **3 años**, mediante auditoría por entidad acreditada conforme al Anexo III.

## 3. REVISIÓN DEL PERIODO ANTERIOR

Durante el periodo comprendido entre **{{ fecha_ant }}** y **{{ fecha_act }}**, la Entidad ha mantenido las medidas implantadas conforme al Plan de Adecuación (E-050) y ha gestionado los cambios materiales conforme al procedimiento E-042.

### 3.1 Principales cambios desde la revisión anterior

{% if tiene_cambios %}
{% for c in ren.cambios_desde_anterior_revision %}
- {{ c }}
{% endfor %}
{% else %}
*No se han registrado cambios materiales significativos desde la renovación anterior.*
{% endif %}

### 3.2 Incidentes de seguridad relevantes

Los incidentes registrados durante el periodo se documentan en el Libro de Incidentes del SGSI (procedimiento E-204) y han sido revisados por el Comité de Seguridad en sus reuniones ordinarias.

### 3.3 Auditorías realizadas

| Tipo | Fecha | Resultado | Observaciones |
|------|-------|-----------|---------------|
| Auditoría interna anual | {{ ren.fecha_auditoria_interna if ren and ren.fecha_auditoria_interna else '[fecha]' }} | Aprobada con observaciones menores | Plan de acción cerrado |
{% if not basica %}
| Auditoría externa de certificación | {{ ren.fecha_auditoria_externa if ren and ren.fecha_auditoria_externa else '[fecha]' }} | Conforme | Certificado vigente |
{% endif %}

## 4. VALIDACIÓN DE LA CONFORMIDAD ACTUAL

a) La **Declaración de Aplicabilidad (E-040)** ha sido revisada y actualizada para reflejar el estado actual de las medidas del Anexo II.

b) El **Plan de Adecuación (E-050)** ha sido revisado y, cuando ha procedido, actualizado.

c) El **Análisis de Riesgos (E-400)** ha sido revisado y actualizado conforme a los cambios identificados en sección 3.

d) Las **políticas, procedimientos y normativas internas** del SGSI han sido revisadas conforme a su ciclo bienal de revisión.

e) El **Comité de Seguridad de la Información** ha validado el mantenimiento de las condiciones de conformidad mediante acta de reunión.

## 5. DECLARACIÓN DE RENOVACIÓN

**{{ cliente.razon_social }}** renueva la Declaración de Conformidad con el Esquema Nacional de Seguridad, categoría **{{ cat }}**, confirmando que el sistema mantiene los requisitos exigidos por el RD 311/2022.

## 6. FIRMA Y APROBACIÓN

| Cargo | Nombre | Firma | Fecha |
|-------|--------|-------|-------|
| Representante legal | {{ cliente.representante.nombre if cliente.representante else '[Representante]' }} | _______________ | {{ fecha_act }} |
| Responsable de la Seguridad | {{ responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[RS]' }} | _______________ | {{ fecha_act }} |
| Presidente del Comité de Seguridad | {{ comite_seguridad.presidente.nombre if comite_seguridad and comite_seguridad.presidente else '[Presidente]' }} | _______________ | {{ fecha_act }} |

## 7. PUBLICACIÓN

La presente renovación se publica en la sede electrónica corporativa y se incorpora al expediente SGSI sustituyendo a la renovación anterior.

---

**Documento E-043 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: PÚBLICA**

*Documento generado por FULKRO · {{ fecha_act }}*
