---
codigo_documento: "E-155"
titulo: "Documento de Alcance del SGSI"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 (ENS) + CCN-STIC 805 (Política de Seguridad) + CCN-STIC 809 (Declaración y distintivo de conformidad)"
---

{# ===================================================================== #}
{# E-155 DOCUMENTO DE ALCANCE DEL SGSI · Estructura CCN-STIC 805/809.     #}
{# Datos per-proyecto inyectados por build_e155_alcance_context (R05):    #}
{# servicios (con tipo finalista/instrumental) + sistemas + sedes        #}
{# (físicas/cloud) + exclusiones + dimensiones DICAT reales (regla del    #}
{# máximo Anexo I). El gate E155ScopeEmptyError impide emitir sin alcance.#}
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

## 2. OBJETO Y FINALIDAD

El presente documento define el **alcance del Sistema de Gestión de Seguridad de la Información (SGSI)** de **{{ cliente.razon_social }}** en el marco de su adecuación al **Esquema Nacional de Seguridad (RD 311/2022)**.

Su finalidad es delimitar de forma inequívoca qué sistemas, servicios, información, sedes y activos quedan **dentro** del alcance de la certificación ENS, así como las **exclusiones** debidamente justificadas, sirviendo de base para la categorización (Anexo I), la Declaración de Aplicabilidad (Anexo II) y la posterior declaración/certificación de conformidad (CCN-STIC 809).

## 3. ALCANCE DEL SGSI

### 3.1. Servicios incluidos

Los servicios se clasifican en **finalistas** (los que constituyen el fin del sistema y se prestan a la Administración) e **instrumentales** (los que dan soporte a los anteriores), conforme a la guía CCN-STIC 803.

{% if alcance and alcance.servicios %}
{% for s in alcance.servicios %}
- **{{ s.nombre if s.nombre else s }}**{% if s.tipo %} _(servicio {{ s.tipo }})_{% endif %}{% if s.descripcion %} — {{ s.descripcion }}{% endif %}
{% endfor %}
{% else %}
- {{ proyecto.servicio_principal if proyecto.servicio_principal else 'Servicio prestado a la Administración Pública objeto de la adecuación ENS' }}
{% endif %}

### 3.2. Sistemas de información y plataformas

{% if alcance and alcance.sistemas %}
{% for sis in alcance.sistemas %}
- **{{ sis.nombre if sis.nombre else sis }}**{% if sis.descripcion %} — {{ sis.descripcion }}{% endif %}
{% endfor %}
{% else %}
- {{ sistema.nombre if sistema and sistema.nombre else 'Sistema de información del ámbito SGSI' }}
{% endif %}

### 3.3. Sedes y ubicaciones

{% if alcance and alcance.sedes %}
{% for sede in alcance.sedes %}
- **{{ sede.nombre if sede.nombre else sede }}**{% if sede.tipo %} — _{{ 'sede física' if sede.tipo == 'sede_fisica' else ('región cloud' if sede.tipo == 'region_cloud' else sede.tipo) }}_{% endif %}{% if sede.direccion %} · {{ sede.direccion }}{% endif %}{% if sede.pais %} ({{ sede.pais }}){% endif %}
{% endfor %}
{% else %}
- {{ cliente.domicilio_social if cliente.domicilio_social else 'Sede principal' }}
{% endif %}

### 3.4. Activos esenciales

{% if alcance and alcance.activos_esenciales %}
{% for a in alcance.activos_esenciales %}
- **{{ a.nombre if a.nombre else a }}**{% if a.tipo %} — {{ a.tipo }}{% endif %}
{% endfor %}
{% else %}
_Los activos esenciales se determinan en el inventario de activos del sistema (metodología MAGERIT) y se vinculan a este alcance._
{% endif %}

## 4. EXCLUSIONES DEL ALCANCE

{% if alcance and alcance.exclusiones %}
{% for ex in alcance.exclusiones %}
- **{{ ex.elemento if ex.elemento else ex }}**{% if ex.justificacion %} — _Justificación:_ {{ ex.justificacion }}{% endif %}
{% endfor %}
{% else %}
_No se declaran exclusiones al alcance del SGSI._
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

La categoría se determina conforme al **Anexo I del RD 311/2022** (regla del máximo sobre las dimensiones de los activos esenciales) y se formaliza en el acta de categorización (E-012).

## 6. ESTRUCTURA DE GOBIERNO Y ROLES (FASE 0)

En categoría ALTA/MEDIA debe respetarse la **separación funcional** entre el Responsable de Seguridad (RSeg) y el Responsable del Sistema (RSis), conforme a la guía CCN-STIC 801. Los nombramientos se formalizan en el acta de designación de roles (E-002).

| Rol ENS | Nombre | Cargo |
|---------|--------|-------|
| Responsable de la Información (RInfo) | {{ responsables.responsable_informacion.nombre if responsables and responsables.responsable_informacion else '—' }} | {{ responsables.responsable_informacion.cargo if responsables and responsables.responsable_informacion else '—' }} |
| Responsable del Servicio (RServ) | {{ responsables.responsable_servicio.nombre if responsables and responsables.responsable_servicio else '—' }} | {{ responsables.responsable_servicio.cargo if responsables and responsables.responsable_servicio else '—' }} |
| Responsable de Seguridad (RSeg) | {{ responsables.responsable_seguridad.nombre if responsables and responsables.responsable_seguridad else '—' }} | {{ responsables.responsable_seguridad.cargo if responsables and responsables.responsable_seguridad else 'Responsable de Seguridad de la Información' }} |
| Responsable del Sistema (RSis) | {{ responsables.responsable_sistema.nombre if responsables and responsables.responsable_sistema else '—' }} | {{ responsables.responsable_sistema.cargo if responsables and responsables.responsable_sistema else '—' }} |

## 7. MARCO NORMATIVO DE REFERENCIA

- **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad.
- **CCN-STIC 805** — Política de Seguridad de la Información.
- **CCN-STIC 803** — Valoración de sistemas en el ENS (servicios finalistas e instrumentales).
- **CCN-STIC 809** — Declaración y distintivo de conformidad con el ENS.
- **CCN-STIC 801** — Responsabilidades y funciones en el ENS.

## 8. APROBACIÓN

Este documento de alcance es elaborado por el equipo de Fulkro, revisado por el Responsable de Seguridad y aprobado por la Dirección de **{{ cliente.razon_social }}**.

| Función | Nombre | Cargo | Fecha |
|---------|--------|-------|-------|
| Elaborado | {{ firmas.elaborado.nombre if firmas and firmas.elaborado else '—' }} | {{ firmas.elaborado.cargo if firmas and firmas.elaborado else '—' }} | {{ firmas.elaborado.fecha if firmas and firmas.elaborado else '—' }} |
| Revisado (RSeg) | {{ firmas.revisado.nombre if firmas and firmas.revisado else '—' }} | {{ firmas.revisado.cargo if firmas and firmas.revisado else 'Responsable de Seguridad' }} | {{ firmas.revisado.fecha if firmas and firmas.revisado else '—' }} |
| Aprobado (Dirección) | {{ firmas.aprobado.nombre if firmas and firmas.aprobado else '—' }} | {{ firmas.aprobado.cargo if firmas and firmas.aprobado else 'Órgano de gobierno superior' }} | {{ firmas.aprobado.fecha if firmas and firmas.aprobado else '—' }} |

La aprobación del alcance corresponde a la Dirección con la revisión del Responsable de Seguridad (firmable mediante E-signature TIER 1 · m05_signing).

---

_Documento generado por Fulkro · {{ consultor.footer_text if consultor and consultor.footer_text else 'Fulkro' }}_
