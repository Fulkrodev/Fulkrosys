---
codigo_documento: "E-012"
titulo: "Acta de Aprobación de la Categorización del Sistema y de la Declaración de Aplicabilidad"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 Anexo I (categorización) + Anexo II (DA) + CCN-STIC 803"
---

# ACTA DE APROBACIÓN DE LA CATEGORIZACIÓN DEL SISTEMA Y DE LA DECLARACIÓN DE APLICABILIDAD · {{ cliente.razon_social | upper }}

**Documento E-012 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set dec = decision_categorizacion if decision_categorizacion else {} %}
{% set nivel = dec.nivel_global if dec and dec.nivel_global else proyecto.categoria_ens %}
{% set fecha = dec.fecha_decision if dec and dec.fecha_decision else proyecto.fecha_aprobacion_inicial %}
{% set dims = dec.dimensiones if dec and dec.dimensiones else {} %}

## 1. DATOS DEL ACTA

| Campo | Valor |
|-------|-------|
| Fecha de aprobación | **{{ fecha }}** |
| Sistema objeto | Sistemas de información del ámbito SGSI de **{{ cliente.razon_social }}** |
| Órgano aprobador | Comité de Seguridad de la Información |
| Metodología | {{ dec.metodologia if dec and dec.metodologia else 'RD 311/2022 Anexo I + CCN-STIC 803' }} |

## 2. ANTECEDENTES

Conforme al **artículo 40** del RD 311/2022 y a su **Anexo I**, la categorización del sistema debe formalizarse mediante acta del órgano competente, sirviendo de base para la determinación de las medidas aplicables del **Anexo II** y para la elaboración de la **Declaración de Aplicabilidad (DA)**, esta última conforme al **artículo 28** del mismo Real Decreto.

El presente acta documenta la decisión adoptada tras el proceso de análisis de las cinco dimensiones de la seguridad (Confidencialidad, Integridad, Disponibilidad, Autenticidad, Trazabilidad) y el cálculo del nivel global del sistema.

## 3. VALORACIÓN DE DIMENSIONES

| Dimensión | Nivel asignado |
|-----------|---------------|
| Confidencialidad (C) | **{{ dims.confidencialidad if dims.confidencialidad else '—' }}** |
| Integridad (I) | **{{ dims.integridad if dims.integridad else '—' }}** |
| Disponibilidad (D) | **{{ dims.disponibilidad if dims.disponibilidad else '—' }}** |
| Autenticidad (A) | **{{ dims.autenticidad if dims.autenticidad else '—' }}** |
| Trazabilidad (T) | **{{ dims.trazabilidad if dims.trazabilidad else '—' }}** |

## 4. CATEGORÍA GLOBAL DEL SISTEMA

Conforme al criterio del Anexo I del RD 311/2022 (la categoría global es la máxima de las dimensiones), se aprueba:

> **CATEGORÍA GLOBAL DEL SISTEMA: {{ nivel | upper }}**

## 5. JUSTIFICACIÓN DE LA VALORACIÓN

La valoración de cada dimensión se ha realizado conforme a los criterios del Anexo I del RD 311/2022 y a la guía complementaria CCN-STIC 803, atendiendo a:

a) Naturaleza de la información tratada y de los servicios prestados.

b) Impacto previsto en caso de fallo en cada dimensión, considerando dimensiones operativa, económica, reputacional y legal.

c) Marco regulatorio sectorial aplicable a **{{ cliente.razon_social }}**.

d) Compromisos contractuales con terceros, particularmente con el sector público en procedimientos de licitación.

## 6. DECLARACIÓN DE APLICABILIDAD (DA)

En aplicación del nivel global aprobado, **{{ nivel }}**, se determina la aplicabilidad de las medidas del Anexo II del RD 311/2022 (73 medidas: 4 organizativas + 33 operacionales + 36 de protección).

La Declaración de Aplicabilidad detallada se documenta en el documento **E-040**, que constituye anexo del presente acta y que recoge para cada medida:

- Aplicabilidad (sí / no / no aplica con justificación).
- Estado de implantación (planificada / parcial / completa).
- Responsable funcional.
- Plazo de implantación cuando proceda.

## 7. DECISIONES COMPLEMENTARIAS

a) Se aprueba la versión inicial de la Declaración de Aplicabilidad (DA, E-040).

b) Se encomienda al Responsable de Seguridad la elaboración del Plan de Adecuación (E-150) en plazo de noventa (90) días naturales.

c) Se establece el ciclo de revisión periódica de la categorización: **anual ordinaria** + extraordinaria ante cambios materiales en el sistema (E-042).

## 8. VIGENCIA Y REVISIÓN

La presente categorización tiene vigencia hasta:

a) Revisión ordinaria anual prevista en sección 7.c.

b) Decisión expresa de recategorización tras cambio material (E-042).

c) Cambio normativo que altere los criterios del Anexo I del RD 311/2022.

## 9. ANEXOS AL ACTA

- **Anexo I:** Declaración de Aplicabilidad (documento E-040).
- **Anexo II:** Análisis dimensional detallado por activos representativos.
- **Anexo III:** Acta de la sesión del Comité de Seguridad en la que se adoptó la decisión.

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ fecha }}.**

Conforme al **artículo 40.2 del RD 311/2022**, la categorización del sistema se aprueba mediante la **doble firma competente**: el **Responsable de la Información** determina y aprueba los niveles de las dimensiones que afectan a la información, y el **Responsable del Servicio** los de las dimensiones que afectan a los servicios. El **Responsable de la Seguridad** suscribe su conformidad sin carácter aprobatorio. El acta solo se considera **aprobada cuando constan las firmas del Responsable de la Información y del Responsable del Servicio**.

| Rol ENS (art. 11) | Nombre | Carácter de la firma | Firma |
|-------------------|--------|----------------------|-------|
| Responsable de la Información | {{ responsables.responsable_informacion.nombre if responsables.responsable_informacion else '[A DESIGNAR]' }} | **Aprueba** (dimensiones de la información) | _______________ |
| Responsable del Servicio | {{ responsables.responsable_servicio.nombre if responsables.responsable_servicio else '[A DESIGNAR]' }} | **Aprueba** (dimensiones de los servicios) | _______________ |
| Responsable de la Seguridad | {{ responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[A DESIGNAR]' }} | Conforme (no aprobador) | _______________ |

---

**Documento E-012 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**
