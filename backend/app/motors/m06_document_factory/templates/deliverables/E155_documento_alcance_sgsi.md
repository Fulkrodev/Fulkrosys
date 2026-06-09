---
codigo_documento: "E-155"
titulo: "Documento de Alcance del SGSI"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 (ENS) + CCN-STIC 805 (Política de Seguridad) + CCN-STIC 809 (Declaración y distintivo de conformidad)"
estado_revision: "BORRADOR — wording normativo genérico · PENDIENTE REVISIÓN CONSULTOR antes de uso con cliente real"
---

{# ===================================================================== #}
{# E-155 DOCUMENTO DE ALCANCE DEL SGSI · Ejecutable 8 Pasada 16 (F-14-05) #}
{# Estructura CCN-STIC 805/809. Los datos per-proyecto van por placeholders #}
{# Jinja2. El WORDING NORMATIVO marcado con `⚠ REVISIÓN CONSULTOR` es        #}
{# genérico/borrador y DEBE validarlo Marcos antes de emitirlo a un cliente. #}
{# ===================================================================== #}

# DOCUMENTO DE ALCANCE DEL SISTEMA DE GESTIÓN DE SEGURIDAD DE LA INFORMACIÓN (SGSI) · {{ cliente.razon_social | upper }}

**Documento E-155 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

---

## 1. IDENTIFICACIÓN DEL SISTEMA

| Campo | Valor |
|-------|-------|
| Entidad titular | **{{ cliente.razon_social }}** |
| NIF | {{ cliente.nif }} |
| Domicilio social | {{ cliente.domicilio_social if cliente.domicilio_social else cliente.domicilio if cliente.domicilio else '—' }} |
| Sistema de información | {{ sistema.nombre if sistema and sistema.nombre else proyecto.nombre_sistema if proyecto.nombre_sistema else 'Sistema de información del ámbito SGSI' }} |
| Responsable del documento | {{ responsables.responsable_seguridad.nombre if responsables and responsables.responsable_seguridad else '—' }} |
| Fecha de emisión | {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else proyecto.fecha_fin if proyecto.fecha_fin else '—' }} |

{# ⚠ REVISIÓN CONSULTOR: confirmar identificación exacta del/los sistema(s) de información objeto del ENS (nombre formal, código interno, si aplica a un único sistema o a varios). #}

## 2. OBJETO Y FINALIDAD

El presente documento define el **alcance del Sistema de Gestión de Seguridad de la Información (SGSI)** de **{{ cliente.razon_social }}** en el marco de su adecuación al **Esquema Nacional de Seguridad (RD 311/2022)**.

{# ⚠ REVISIÓN CONSULTOR: wording de objeto/finalidad GENÉRICO. Ajustar al contexto real del cliente (servicio que presta a la AAPP, motivación de la adecuación, sistema concreto). #}

Su finalidad es delimitar de forma inequívoca qué sistemas, servicios, información, sedes y activos quedan **dentro** del alcance de la certificación ENS, así como las **exclusiones** debidamente justificadas, sirviendo de base para la categorización (Anexo I), la Declaración de Aplicabilidad (Anexo II) y la posterior declaración/certificación de conformidad (CCN-STIC 809).

## 3. ALCANCE DEL SGSI

### 3.1. Servicios incluidos

{% if alcance and alcance.servicios %}
{% for s in alcance.servicios %}
- **{{ s.nombre if s.nombre else s }}**{% if s.descripcion %} — {{ s.descripcion }}{% endif %}
{% endfor %}
{% else %}
- {{ proyecto.servicio_principal if proyecto.servicio_principal else 'Servicio prestado a la Administración Pública objeto de la adecuación ENS' }}
{# ⚠ REVISIÓN CONSULTOR: listado de servicios PLACEHOLDER. Enumerar los servicios reales en alcance. #}
{% endif %}

### 3.2. Sistemas de información y plataformas

{% if alcance and alcance.sistemas %}
{% for sis in alcance.sistemas %}
- {{ sis.nombre if sis.nombre else sis }}
{% endfor %}
{% else %}
- {# ⚠ REVISIÓN CONSULTOR: enumerar sistemas/plataformas (on-premise, cloud, SaaS) en alcance. #} Por determinar en el inventario de activos.
{% endif %}

### 3.3. Sedes y ubicaciones

{% if alcance and alcance.sedes %}
{% for sede in alcance.sedes %}
- {{ sede.nombre if sede.nombre else sede }}{% if sede.direccion %} ({{ sede.direccion }}){% endif %}
{% endfor %}
{% else %}
- {{ cliente.domicilio_social if cliente.domicilio_social else 'Sede principal' }}
{# ⚠ REVISIÓN CONSULTOR: confirmar sedes físicas y ubicaciones cloud (regiones) en alcance. #}
{% endif %}

### 3.4. Activos esenciales

{% if alcance and alcance.activos_esenciales %}
| Activo esencial | Tipo |
|-----------------|------|
{% for a in alcance.activos_esenciales %}
| {{ a.nombre if a.nombre else a }} | {{ a.tipo if a.tipo else '—' }} |
{% endfor %}
{% else %}
{# ⚠ REVISIÓN CONSULTOR: los activos esenciales se materializan tras el inventario (M-MAGERIT). Vincular aquí los activos esenciales identificados. #}
_Los activos esenciales se determinan en el inventario de activos del sistema (metodología MAGERIT) y se vinculan a este alcance._
{% endif %}

## 4. EXCLUSIONES DEL ALCANCE

{% if alcance and alcance.exclusiones %}
{% for ex in alcance.exclusiones %}
- **{{ ex.elemento if ex.elemento else ex }}**{% if ex.justificacion %} — _Justificación:_ {{ ex.justificacion }}{% endif %}
{% endfor %}
{% else %}
{# ⚠ REVISIÓN CONSULTOR: toda exclusión del alcance debe justificarse (CCN-STIC 805). Si no hay exclusiones, indicarlo expresamente. #}
_No se declaran exclusiones, o bien las exclusiones serán detalladas y justificadas por el Responsable de Seguridad._
{% endif %}

## 5. CATEGORÍA DEL SISTEMA (DIMENSIONES C-I-D-A-T)

{% set dims = categorizacion.dimensiones if categorizacion and categorizacion.dimensiones else {} %}

| Dimensión | Nivel |
|-----------|-------|
| Confidencialidad (C) | **{{ dims.confidencialidad if dims.confidencialidad else '—' }}** |
| Integridad (I) | **{{ dims.integridad if dims.integridad else '—' }}** |
| Disponibilidad (D) | **{{ dims.disponibilidad if dims.disponibilidad else '—' }}** |
| Autenticidad (A) | **{{ dims.autenticidad if dims.autenticidad else '—' }}** |
| Trazabilidad (T) | **{{ dims.trazabilidad if dims.trazabilidad else '—' }}** |
| **Categoría global** | **{{ proyecto.categoria_ens if proyecto.categoria_ens else categorizacion.nivel_global if categorizacion and categorizacion.nivel_global else '—' }}** |

La categoría se determina conforme al **Anexo I del RD 311/2022** y se formaliza en el acta de categorización (E-012).

{# ⚠ REVISIÓN CONSULTOR: confirmar que la categoría global aquí reflejada coincide con el acta E-012 aprobada. #}

## 6. ESTRUCTURA DE GOBIERNO Y ROLES (FASE 0)

{# ⚠ REVISIÓN CONSULTOR: roles ENS conforme a CCN-STIC 801. En categoría ALTA/MEDIA debe respetarse la SEPARACIÓN entre Responsable de Seguridad (RSeg) y Responsable del Sistema (RSis). Confirmar nombramientos reales (ver acta E-002). #}

| Rol ENS | Nombre | Cargo |
|---------|--------|-------|
| Responsable de la Información (RInfo) | {{ responsables.responsable_informacion.nombre if responsables and responsables.responsable_informacion else '—' }} | {{ responsables.responsable_informacion.cargo if responsables and responsables.responsable_informacion else '—' }} |
| Responsable del Servicio (RServ) | {{ responsables.responsable_servicio.nombre if responsables and responsables.responsable_servicio else '—' }} | {{ responsables.responsable_servicio.cargo if responsables and responsables.responsable_servicio else '—' }} |
| Responsable de Seguridad (RSeg) | {{ responsables.responsable_seguridad.nombre if responsables and responsables.responsable_seguridad else '—' }} | {{ responsables.responsable_seguridad.cargo if responsables and responsables.responsable_seguridad else 'Responsable de Seguridad de la Información' }} |
| Responsable del Sistema (RSis) | {{ responsables.responsable_sistema.nombre if responsables and responsables.responsable_sistema else '—' }} | {{ responsables.responsable_sistema.cargo if responsables and responsables.responsable_sistema else '—' }} |

## 7. MARCO NORMATIVO DE REFERENCIA

- **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad.
- **CCN-STIC 805** — Política de Seguridad de la Información.
- **CCN-STIC 809** — Declaración y distintivo de conformidad con el ENS.
- **CCN-STIC 801** — Responsabilidades y funciones en el ENS.

{# ⚠ REVISIÓN CONSULTOR: añadir/ajustar guías CCN-STIC adicionales aplicables según categoría y naturaleza del sistema. #}

## 8. APROBACIÓN

Este documento de alcance es elaborado por el equipo de Fulkro, revisado por el Responsable de Seguridad y aprobado por la Dirección de **{{ cliente.razon_social }}**.

| Función | Nombre | Cargo | Fecha |
|---------|--------|-------|-------|
| Elaborado | {{ firmas.elaborado.nombre if firmas and firmas.elaborado else '—' }} | {{ firmas.elaborado.cargo if firmas and firmas.elaborado else '—' }} | {{ firmas.elaborado.fecha if firmas and firmas.elaborado else '—' }} |
| Revisado (RSeg) | {{ firmas.revisado.nombre if firmas and firmas.revisado else '—' }} | {{ firmas.revisado.cargo if firmas and firmas.revisado else 'Responsable de Seguridad' }} | {{ firmas.revisado.fecha if firmas and firmas.revisado else '—' }} |
| Aprobado (Dirección) | {{ firmas.aprobado.nombre if firmas and firmas.aprobado else '—' }} | {{ firmas.aprobado.cargo if firmas and firmas.aprobado else 'Órgano de gobierno superior' }} | {{ firmas.aprobado.fecha if firmas and firmas.aprobado else '—' }} |

{# ⚠ REVISIÓN CONSULTOR: la aprobación del alcance corresponde a Dirección con revisión del RSeg (firmable E-signature TIER 1 · m05_signing). Confirmar firmantes. #}

---

_Documento generado por Fulkro · {{ consultor.footer_text if consultor and consultor.footer_text else 'Fulkro' }}_
