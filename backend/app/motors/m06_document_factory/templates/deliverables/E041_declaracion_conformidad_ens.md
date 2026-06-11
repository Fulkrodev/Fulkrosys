---
codigo_documento: "E-041"
titulo: "Declaración de Conformidad con el Esquema Nacional de Seguridad"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "PÚBLICA"
norma_aplicable: "RD 311/2022 Art. 33 + Anexo III + IV · CCN-STIC 809"
---

# DECLARACIÓN DE CONFORMIDAD CON EL ESQUEMA NACIONAL DE SEGURIDAD · {{ cliente.razon_social | upper }}

**Documento E-041 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set cat = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}
{% set requiere_certif = cat in ['MEDIA', 'ALTA'] %}
{% set basica = cat == 'BÁSICA' or cat == 'BASICA' %}

## 1. DATOS IDENTIFICATIVOS

| Campo | Valor |
|-------|-------|
| Entidad | **{{ cliente.razon_social }}** |
| NIF | **{{ cliente.nif }}** |
| Domicilio social | {{ cliente.domicilio if cliente.domicilio else '[domicilio]' }} |
| Representante legal | {{ cliente.representante.nombre if cliente.representante else '[Representante]' }} |
| Categoría ENS del sistema | **{{ cat }}** |
| Fecha de la declaración | **{{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha]' }}** |

## 2. MARCO NORMATIVO

La presente declaración se formula al amparo de:

- **Real Decreto 311/2022, de 3 de mayo**, por el que se regula el Esquema Nacional de Seguridad (en adelante, "ENS"), particularmente su **artículo 33** sobre conformidad y los **Anexos III y IV**.
- **Guía CCN-STIC 809** sobre Declaración y Certificación de Conformidad con el ENS.
- Sus normas de desarrollo y resoluciones del Centro Criptológico Nacional (CCN).

## 3. RÉGIMEN DE CONFORMIDAD APLICABLE

{% if basica %}
Dado que la **categoría del sistema es BÁSICA**, el régimen aplicable conforme al artículo 33.2 del RD 311/2022 es la **Declaración de Conformidad** mediante este documento, suscrita por el órgano competente de la Entidad, sin necesidad de certificación por entidad acreditada.

La presente Declaración tiene efectos a partir de su firma y se publica en la sede electrónica corporativa conforme al Anexo III del RD 311/2022.
{% else %}
Dado que la **categoría del sistema es {{ cat }}**, el régimen aplicable conforme al artículo 33.3 del RD 311/2022 es la **Certificación de Conformidad** por entidad de certificación acreditada por ENAC para el alcance ENS.

La presente Declaración se acompaña del **certificado emitido por la entidad acreditada** correspondiente, que constituye anexo permanente del expediente SGSI.
{% endif %}

## 4. ÁMBITO DE LA DECLARACIÓN

El alcance del Sistema cubierto por la presente Declaración se documenta en la **Declaración de Aplicabilidad (E-040)**, que constituye anexo del presente documento.

A modo de resumen ejecutivo, el alcance incluye:

a) Los sistemas de información operados por **{{ cliente.razon_social }}** para la prestación de los servicios objeto del SGSI.

b) Las medidas del Anexo II del RD 311/2022 aplicables a la categoría **{{ cat }}** del sistema (52 en categoría BÁSICA, 68 en MEDIA y 73 en ALTA), cuya aplicabilidad y estado se documenta en la Declaración de Aplicabilidad (E-040).

c) Los activos identificados en el Análisis de Riesgos (E-400) según metodología MAGERIT v3.

## 5. DECLARACIÓN FORMAL

**{{ cliente.razon_social }}**, con NIF **{{ cliente.nif }}**, representada por **{{ cliente.representante.nombre if cliente.representante else '[Representante legal]' }}**, **DECLARA**:

a) Que el Sistema de Información descrito en la sección 4 cumple con los requisitos exigidos por el RD 311/2022 para la categoría **{{ cat }}**.

b) Que las medidas del Anexo II aplicables han sido **implantadas conforme al Plan de Adecuación (E-150)** y se mantienen operativas.

c) Que el sistema ha sido sometido a la auditoría interna prevista (E-050 cuando proceda) y, {% if requiere_certif %}adicionalmente, a la auditoría de certificación por entidad acreditada{% else %}a las verificaciones operativas internas{% endif %}.

d) Que el sistema dispone de los procesos documentados de **gestión de incidentes (E-204)**, **gestión de cambios (E-203)** y **continuidad (E-401)** necesarios para mantener el nivel de seguridad declarado.

e) Que la Entidad se compromete a comunicar al Centro Criptológico Nacional (CCN) cualquier **cambio material** del sistema mediante el documento E-042.

f) Que la presente Declaración se renovará periódicamente conforme al ciclo de revisión y auditoría periódica previsto en el Anexo III del RD 311/2022, mediante el documento E-043 (cada **{{ '2 años' if basica else '3 años' }}**).

## 6. PUBLICACIÓN Y REMISIÓN

a) La presente Declaración se publica en la sede electrónica corporativa de **{{ cliente.razon_social }}** conforme al Anexo III del RD 311/2022.

b) Se remite al **CCN-CERT** para constancia en el Inventario Nacional de Servicios certificados.

c) Se incorpora al expediente SGSI con carácter permanente.

## 7. VIGENCIA

La presente Declaración tiene vigencia hasta:

a) Renovación ordinaria conforme al ciclo periódico (E-043).

b) Cambio material que altere las condiciones del sistema (E-042).

c) Cese o suspensión expresa por el órgano competente de la Entidad.

## 8. ANEXOS

- **Anexo I:** Declaración de Aplicabilidad (E-040).
- **Anexo II:** Plan de Adecuación (E-150).
- **Anexo III:** Última auditoría interna o {% if requiere_certif %}certificado emitido por entidad acreditada{% else %}verificaciones operativas internas{% endif %}.
- **Anexo IV:** Acta de Constitución del Comité de Seguridad (E-003) y Acta de Nombramiento de Roles (E-002).

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha]' }}.**

**{{ cliente.representante.nombre if cliente.representante else '[Representante legal]' }}**
{{ cliente.representante.cargo if cliente.representante else '[Cargo]' }}
{{ cliente.razon_social }} · NIF {{ cliente.nif }}

---

**Documento E-041 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: PÚBLICA**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo*
