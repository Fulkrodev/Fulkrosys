---
codigo_documento: "E-002"
titulo: "Acta de Nombramiento de Roles del Sistema (Esquema Nacional de Seguridad)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 Anexo II · org.1 · org.2 + CCN-STIC 801 (Responsabilidades y funciones)"
---

# ACTA DE NOMBRAMIENTO DE ROLES DEL SISTEMA · {{ cliente.razon_social | upper }}

**Documento E-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set fecha = proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha]' %}
{% set cat = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}
{% set rs_nombre = responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[A DESIGNAR]' %}
{% set rs_cargo = responsables.responsable_seguridad.cargo if responsables.responsable_seguridad else 'CISO' %}
{% set rs_dni = responsables.responsable_seguridad.dni if responsables.responsable_seguridad else '[DNI]' %}
{% set rsi_nombre = responsables.responsable_sistema_informacion.nombre if responsables.responsable_sistema_informacion else '[A DESIGNAR]' %}
{% set rsi_cargo = responsables.responsable_sistema_informacion.cargo if responsables.responsable_sistema_informacion else 'Director TI' %}
{% set rsi_dni = responsables.responsable_sistema_informacion.dni if responsables.responsable_sistema_informacion else '[DNI]' %}
{% set rserv_nombre = responsables.responsable_servicio.nombre if responsables.responsable_servicio else '[A DESIGNAR]' %}
{% set rserv_cargo = responsables.responsable_servicio.cargo if responsables.responsable_servicio else 'Responsable de Servicio' %}
{% set rserv_dni = responsables.responsable_servicio.dni if responsables.responsable_servicio else '[DNI]' %}
{# F0-2 (Ejecutable 8 Pasada 16): roles añadidos RI (art 11.a · siempre), ASS
   (art 11.e · MEDIA+), POC ante CCN-CERT (MEDIA+). Fuente: RD 311/2022 art. 11
   + CCN-STIC 801. #}
{% set ri_nombre = responsables.responsable_informacion.nombre if responsables.responsable_informacion else '[A DESIGNAR]' %}
{% set ri_cargo = responsables.responsable_informacion.cargo if responsables.responsable_informacion else 'Responsable de la Información' %}
{% set ri_dni = responsables.responsable_informacion.dni if responsables.responsable_informacion else '[DNI]' %}
{% set ass_nombre = responsables.administrador_seguridad.nombre if responsables.administrador_seguridad else '[A DESIGNAR]' %}
{% set ass_cargo = responsables.administrador_seguridad.cargo if responsables.administrador_seguridad else 'Administrador de Seguridad del Sistema' %}
{% set ass_dni = responsables.administrador_seguridad.dni if responsables.administrador_seguridad else '[DNI]' %}
{% set poc_nombre = responsables.punto_contacto_ccn.nombre if responsables.punto_contacto_ccn else '[A DESIGNAR]' %}
{% set poc_cargo = responsables.punto_contacto_ccn.cargo if responsables.punto_contacto_ccn else 'Punto de Contacto ante CCN-CERT' %}
{% set poc_dni = responsables.punto_contacto_ccn.dni if responsables.punto_contacto_ccn else '[DNI]' %}
{% set requiere_rsa = cat == 'ALTA' %}
{% set requiere_ass = cat in ['MEDIA', 'ALTA'] %}
{% set requiere_poc = cat in ['MEDIA', 'ALTA'] %}

## 1. DATOS DEL ACTA

| Campo | Valor |
|-------|-------|
| Fecha | **{{ fecha }}** |
| Lugar | Sede social de **{{ cliente.razon_social }}** |
| Convocante | Órgano de administración |
| Naturaleza | Acta de nombramiento formal · permanente en expediente SGSI |

## 2. ANTECEDENTES

En cumplimiento del Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y conforme a las medidas org.1 (Política de seguridad) y org.2 (Normativa de seguridad) del Anexo II, así como a las directrices de la **Guía CCN-STIC 801 sobre Responsabilidades y Funciones**, la Entidad procede al nombramiento formal de los roles necesarios para la gobernanza del sistema de información sujeto al ENS, con **categoría {{ cat }}**.

## 3. ACUERDOS

### Acuerdo 1 · Nombramiento del Responsable de la Información (RI)

Conforme al artículo 11.a) del RD 311/2022, se nombra **Responsable de la Información** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ ri_nombre }}** |
| Cargo | {{ ri_cargo }} |
| DNI | {{ ri_dni }} |

Funciones:

- Establecer los requisitos de la información tratada en materia de seguridad.
- Determinar los niveles de seguridad de la información en las dimensiones afectadas (confidencialidad, integridad, trazabilidad, autenticidad, disponibilidad).
- Aprobar los niveles de seguridad de la información junto con el Responsable del Servicio.

### Acuerdo 2 · Nombramiento del Responsable de la Seguridad (RS)

Se nombra **Responsable de la Seguridad** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ rs_nombre }}** |
| Cargo | {{ rs_cargo }} |
| DNI | {{ rs_dni }} |

Funciones, conforme al Anexo II RD 311/2022 y a la Política E-100:

- Mantener la seguridad de la información manejada y de los servicios prestados.
- Promover la formación y concienciación en seguridad.
- Coordinar la respuesta a incidentes y la gestión de cambios con impacto en seguridad.
- Elaborar los informes periódicos al Comité de Seguridad.
- Velar por el cumplimiento del Anexo II del ENS y por las medidas implantadas.

### Acuerdo 3 · Nombramiento del Responsable del Sistema de Información (RSI)

Se nombra **Responsable del Sistema de Información** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ rsi_nombre }}** |
| Cargo | {{ rsi_cargo }} |
| DNI | {{ rsi_dni }} |

Funciones:

- Desarrollar, operar y mantener el sistema durante todo su ciclo de vida.
- Definir las especificaciones técnicas necesarias para satisfacer los requisitos de seguridad.
- Resolver las incidencias técnicas con impacto en seguridad bajo la supervisión del Responsable de Seguridad.
- Asegurar la disponibilidad, integridad y trazabilidad de la información en el sistema.

### Acuerdo 4 · Nombramiento del Responsable del Servicio (RServ)

Se nombra **Responsable del Servicio** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ rserv_nombre }}** |
| Cargo | {{ rserv_cargo }} |
| DNI | {{ rserv_dni }} |

Funciones:

- Determinar los requisitos del servicio en materia de seguridad.
- Aceptar los riesgos residuales tras la implantación de las medidas.
- Suspender el uso de la información o de los servicios cuando exista riesgo grave.
- Garantizar la operativa adecuada del servicio en términos de seguridad.

{% if requiere_ass %}
### Acuerdo 5 · Nombramiento del Administrador de Seguridad del Sistema (ASS)

Conforme al artículo 11.e) del RD 311/2022, dado que la categoría del sistema es **{{ cat }}**, se nombra **Administrador de Seguridad del Sistema** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ ass_nombre }}** |
| Cargo | {{ ass_cargo }} |
| DNI | {{ ass_dni }} |

Funciones:

- Implantar, gestionar y mantener las medidas de seguridad operativas del sistema en el día a día.
- Gestionar, configurar y actualizar el hardware y software de seguridad.
- Aplicar los procedimientos operativos de seguridad bajo la supervisión del Responsable de la Seguridad.
{% endif %}

{% if requiere_poc %}
### Acuerdo 6 · Designación del Punto de Contacto ante CCN-CERT (POC)

Dado que la categoría del sistema es **{{ cat }}**, y conforme a las obligaciones de notificación de incidentes al CCN-CERT (RD 311/2022 + CCN-STIC 801), se designa **Punto de Contacto ante CCN-CERT** a:

| Campo | Detalle |
|-------|---------|
| Nombre | **{{ poc_nombre }}** |
| Cargo | {{ poc_cargo }} |
| DNI | {{ poc_dni }} |

Funciones:

- Actuar como interlocutor único con el CCN-CERT para la notificación y seguimiento de incidentes de seguridad.
- Coordinar con el Responsable de la Seguridad la gestión de incidentes notificables.
{% endif %}

{% if requiere_rsa %}
### Acuerdo 7 · Separación funcional reforzada (categoría ALTA)

Dado que la categoría de seguridad del sistema es **ALTA**, y conforme al artículo 11 del RD 311/2022 y a la guía **CCN-STIC 801**, se establece la **separación funcional obligatoria** entre el Responsable de la Seguridad (RS · gestión, Acuerdo 2) y el Responsable del Sistema de Información (RSI · operación, Acuerdo 3): ambos roles **NO pueden recaer en la misma persona**. Su acumulación constituye **no-conformidad mayor** en la auditoría ENAC.

El Administrador de Seguridad del Sistema (Acuerdo 5) opera las medidas bajo la supervisión del RS, manteniendo dicha separación.
{% else %}
### Sobre la separación funcional RS / RSI

Conforme al artículo 11 del RD 311/2022 y a CCN-STIC 801, la separación entre el Responsable de la Seguridad (gestión) y el Responsable del Sistema de Información (operación) es **obligatoria en categoría ALTA** y **recomendada en MEDIA**. La categoría actual del sistema es **{{ cat }}**{% if cat == 'BASICA' %}; en BÁSICA los roles pueden acumularse en pocas personas adoptando una medida compensatoria (revisión por tercero independiente){% endif %}.
{% endif %}

## 4. ACEPTACIÓN EXPRESA DE LOS CARGOS

Los nombrados en los Acuerdos anteriores aceptan expresamente los cargos y las funciones asignadas, comprometiéndose a su ejercicio diligente conforme a las exigencias del ENS y a las políticas internas de la Entidad.

## 5. VIGENCIA Y RENOVACIÓN

El presente nombramiento permanece vigente hasta:

a) Cese en el cargo orgánico que sirve de base al nombramiento.

b) Revocación expresa por el órgano de administración.

c) Sustitución por nuevo nombramiento formal mediante acta de igual rango.

La renovación se revisará coincidiendo con la revisión de la conformidad ENS (referencia E-043) o cuando se produzcan cambios materiales en la organización.

## 6. FIRMAS

| Cargo | Nombre | Firma |
|-------|--------|-------|
| Por el órgano de administración | {{ cliente.representante.nombre if cliente.representante else '[Representante legal]' }} | _______________ |
| RI · Acepta cargo | {{ ri_nombre }} | _______________ |
| RS · Acepta cargo | {{ rs_nombre }} | _______________ |
| RSI · Acepta cargo | {{ rsi_nombre }} | _______________ |
| RServ · Acepta cargo | {{ rserv_nombre }} | _______________ |
{% if requiere_ass %}| ASS · Acepta cargo | {{ ass_nombre }} | _______________ |
{% endif %}{% if requiere_poc %}| POC CCN-CERT · Acepta cargo | {{ poc_nombre }} | _______________ |
{% endif %}

---

**Documento E-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ fecha }}*
