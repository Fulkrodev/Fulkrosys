---
codigo_documento: "E-090"
titulo: "Informe de Diagnóstico Inicial · GAP Analysis frente al ENS"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 Anexo II (73 medidas) + CCN-STIC 808 (verificación)"
documento_destino: "Base para Plan de Adecuación (E-150) y Declaración de Aplicabilidad (E-040)"
---

# INFORME DE DIAGNÓSTICO INICIAL · GAP ANALYSIS FRENTE AL ESQUEMA NACIONAL DE SEGURIDAD · {{ cliente.razon_social | upper }}

**Documento E-090 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set diag = diagnostico if diagnostico else {} %}
{% set fecha = diag.fecha_realizacion if diag and diag.fecha_realizacion else '[fecha]' %}
{% set metodologia = diag.metodologia if diag and diag.metodologia else 'Auto-evaluación RD 311/2022 Anexo II · 73 medidas' %}
{% set madurez = diag.nivel_madurez_actual if diag and diag.nivel_madurez_actual else 'L2 · Definido parcialmente' %}
{% set tiene_hallazgos = diag.hallazgos_gap and diag.hallazgos_gap | length > 0 %}
{% set tiene_recom = diag.recomendaciones and diag.recomendaciones | length > 0 %}

## 1. OBJETO

El presente informe documenta el **diagnóstico inicial** del estado de cumplimiento de **{{ cliente.razon_social }}** frente al Esquema Nacional de Seguridad (ENS), realizado como paso previo a la elaboración del Plan de Adecuación (E-150) y de la Declaración de Aplicabilidad (E-040).

El diagnóstico identifica los **gaps de cumplimiento** entre el estado actual y el estado objetivo definido por el Anexo II del RD 311/2022, atendiendo a la categoría **{{ proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' }}** previamente aprobada (E-012).

## 2. ALCANCE

| Campo | Detalle |
|-------|---------|
| Entidad evaluada | **{{ cliente.razon_social }}** · NIF {{ cliente.nif }} |
| Categoría ENS objetivo | **{{ proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' }}** |
| Fecha de realización | **{{ fecha }}** |
| Metodología | {{ metodologia }} |
| Marco evaluativo | RD 311/2022 Anexo II + CCN-STIC 808 |
| Estado documental | Anterior a Plan de Adecuación (E-150) |

## 3. METODOLOGÍA

El diagnóstico se ha realizado mediante revisión sistemática de las **73 medidas** del Anexo II del RD 311/2022, distribuidas en:

| Familia | Nº de medidas | Códigos |
|---------|--------------:|---------|
| Marco organizativo | 4 | org.* |
| Marco operacional | 33 | op.* |
| Medidas de protección | 36 | mp.* |
| **TOTAL** | **73** | |

Para cada medida se ha aplicado el siguiente criterio de valoración:

- **L0 · No implantado:** medida ausente o desconocida en la organización.
- **L1 · Inicial:** medida implantada de forma informal o reactiva.
- **L2 · Definido parcialmente:** medida documentada parcialmente · ejecución no consistente.
- **L3 · Definido:** medida documentada y aplicada consistentemente.
- **L4 · Gestionado:** medida medida y revisada periódicamente.
- **L5 · Optimizado:** medida revisada con mejora continua basada en métricas.

## 4. NIVEL DE MADUREZ ACTUAL ESTIMADO

> **Nivel de madurez global: {{ madurez }}**

Este nivel representa la media ponderada de las 73 medidas evaluadas, asumiendo el peso doble de las medidas operacionales y de protección con respecto a las organizativas.

## 5. HALLAZGOS GAP CRÍTICOS POR FAMILIA

{% if tiene_hallazgos %}
| Familia | Nivel del hallazgo | Descripción del gap |
|---------|--------------------|---------------------|
{% for h in diag.hallazgos_gap %}
| {{ h.familia }} | **{{ h.nivel }}** | {{ h.descripcion }} |
{% endfor %}
{% else %}
*No se han registrado hallazgos significativos en la presente revisión.*
{% endif %}

## 6. ANÁLISIS POR FAMILIA

### 6.1 Marco organizativo (4 medidas org.*)

Cobertura aparente: medidas relativas a política de seguridad, normativa interna, procedimientos de seguridad y procesos de autorización. Estas medidas requieren formalización documental y aprobación por órgano competente (Comité de Seguridad de la Información, ya constituido conforme a E-003).

### 6.2 Marco operacional (33 medidas op.*)

Cobertura aparente: medidas relativas a planificación de la seguridad, control de acceso, explotación, recursos externos, continuidad y monitorización. Las áreas con mayor gap se concentran típicamente en monitorización proactiva, segregación de funciones y gestión de cambios.

### 6.3 Medidas de protección (36 medidas mp.*)

Cobertura aparente: medidas técnicas para proteger instalaciones, personal, equipamiento, comunicaciones, soportes, aplicaciones, información y servicios. Las áreas con mayor gap se concentran típicamente en cifrado homogéneo, gestión del ciclo de vida de la información y resiliencia de servicios.

## 7. RECOMENDACIONES PRIORIZADAS

{% if tiene_recom %}
A continuación se relacionan las recomendaciones de máxima prioridad para la elaboración del Plan de Adecuación (E-150):

{% for r in diag.recomendaciones %}
- {{ r }}
{% endfor %}
{% else %}
*Las recomendaciones se desarrollarán en el documento Plan de Adecuación (E-150).*
{% endif %}

## 8. CONCLUSIONES Y SIGUIENTES PASOS

a) Las medidas del Anexo II del RD 311/2022 presentan **gaps documentables** que requieren intervención formalizada mediante un **Plan de Adecuación** (E-150).

b) La aprobación de la Declaración de Aplicabilidad (E-040) y del Plan de Adecuación (E-150) procederá conforme al cronograma definido en el acta de aprobación de la categorización (E-012, sección 7.b).

c) Se recomienda al **Responsable de la Seguridad** elevar al Comité de Seguridad de la Información los siguientes documentos en orden:

1. **Declaración de Aplicabilidad (E-040)** – plazo orientativo: 30 días.
2. **Plan de Adecuación (E-150)** – plazo orientativo: 90 días.
3. **Análisis de Riesgos (E-400)** – plazo orientativo: 120 días.
4. **Auditoría interna previa** – plazo orientativo: 180 días.

d) El presente diagnóstico será **revisado** cuando se hayan implantado las medidas correctivas planificadas, y como mínimo **anualmente** coincidiendo con la revisión ordinaria del SGSI.

---

**Elaborado por:** {{ responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[Responsable de Seguridad]' }} · {{ responsables.responsable_seguridad.cargo if responsables.responsable_seguridad else 'CISO' }}
**Validado por:** Comité de Seguridad de la Información
**Fecha:** {{ fecha }}

---

**Documento E-090 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

*Documento generado por FULKRO · {{ fecha }}*
