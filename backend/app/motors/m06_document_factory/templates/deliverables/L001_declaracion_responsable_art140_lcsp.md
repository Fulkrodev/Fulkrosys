---
codigo_documento: "L-001"
titulo: "Modelo de Declaración Responsable conforme al Artículo 140 de la Ley 9/2017 de Contratos del Sector Público"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · uso licitación"
norma_aplicable: "Ley 9/2017 LCSP · Art. 140"
---

# DECLARACIÓN RESPONSABLE

{% set rep_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[Nombre representante legal]' %}
{% set rep_dni = cliente.representante.dni if cliente.representante and cliente.representante.dni else '[DNI]' %}
{% set rep_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[Cargo]' %}
{% set expediente = licitacion.numero_expediente if licitacion and licitacion.numero_expediente else '[NÚMERO DE EXPEDIENTE]' %}
{% set organo_contratante = licitacion.organo_contratante if licitacion and licitacion.organo_contratante else '[ÓRGANO DE CONTRATACIÓN]' %}
{% set objeto_contrato = licitacion.objeto if licitacion and licitacion.objeto else '[OBJETO DEL CONTRATO]' %}

(De conformidad con el artículo 140 de la Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público)

---

**Don/Doña {{ rep_nombre }}**, con DNI/NIE **{{ rep_dni }}**, en calidad de **{{ rep_cargo }}** y en representación de **{{ cliente.razon_social }}**, con NIF **{{ cliente.nif }}** y domicilio en **{{ cliente.domicilio if cliente.domicilio else '[domicilio]' }}**, debidamente facultado para actuar en nombre de la sociedad,

**en relación con el expediente** {{ expediente }}, **convocado por** {{ organo_contratante }} **y cuyo objeto es** {{ objeto_contrato }},

**DECLARA BAJO SU RESPONSABILIDAD**:

## PRIMERO — Personalidad jurídica y representación

Que la entidad a la que representa **tiene plena capacidad de obrar** y se encuentra debidamente constituida conforme a la legislación española, y que el firmante **dispone de la representación legal suficiente** para vincular a la entidad respecto del presente procedimiento de contratación, conforme a los artículos 65 y 84 de la Ley 9/2017.

## SEGUNDO — Cumplimiento de las condiciones de aptitud

Que la entidad **cumple todas las condiciones legalmente establecidas para contratar** con el sector público conforme a los artículos 65 y siguientes de la Ley 9/2017, incluyendo las condiciones de personalidad, capacidad, no incursión en causas de prohibición de contratar, solvencia económica, financiera y técnica o profesional exigidas en el pliego de cláusulas administrativas particulares.

## TERCERO — No incursión en prohibiciones de contratar

Que ni la entidad ni sus administradores o representantes **se encuentran incursos en ninguna de las prohibiciones de contratar** previstas en el artículo 71 de la Ley 9/2017, ni en las causas de incompatibilidad establecidas en la Ley 53/1984, de 26 de diciembre, de Incompatibilidades del Personal al Servicio de las Administraciones Públicas, ni en la normativa autonómica que resulte aplicable.

## CUARTO — Obligaciones tributarias y de Seguridad Social

Que la entidad **se halla al corriente en el cumplimiento de las obligaciones tributarias** con la Agencia Estatal de Administración Tributaria y con la Hacienda autonómica y local correspondiente, así como **al corriente en el cumplimiento de las obligaciones con la Seguridad Social**, impuestas por las disposiciones vigentes.

## QUINTO — Solvencia económica, financiera y técnica o profesional

Que la entidad **dispone de la solvencia económica, financiera y técnica o profesional exigida en el pliego** del presente procedimiento de contratación, en los términos previstos en los artículos 86 a 91 de la Ley 9/2017, y se compromete a acreditarla documentalmente si, propuesta como adjudicataria, le es requerido por el órgano de contratación conforme al artículo 150.2 LCSP.

## SEXTO — Aceptación del pliego

Que la entidad **conoce y acepta íntegramente** el contenido del pliego de cláusulas administrativas particulares, el pliego de prescripciones técnicas y los anexos del expediente {{ expediente }}, en los términos en que han sido publicados.

## SÉPTIMO — Conformidad con el Esquema Nacional de Seguridad

{% if licitacion.exige_ens %}
Que la entidad **cumple los requisitos exigidos por el Esquema Nacional de Seguridad** (Real Decreto 311/2022) en la categoría **{{ licitacion.categoria_ens if licitacion.categoria_ens else 'MEDIA' }}** exigida por el pliego, o se compromete a alcanzar dicha conformidad en el plazo máximo establecido en el mismo, según se acreditará en su momento mediante la correspondiente Declaración o Certificación de Conformidad.
{% else %}
Que, en cumplimiento de las exigencias generales aplicables a los proveedores del sector público en materia de seguridad de la información, la entidad **dispone de medidas técnicas y organizativas adecuadas** a la naturaleza del contrato objeto del expediente.
{% endif %}

## OCTAVO — Sometimiento a la jurisdicción española

Que la entidad **se somete expresamente a la jurisdicción de los Juzgados y Tribunales españoles** de cualquier orden, para todas las incidencias que, de modo directo o indirecto, pudieran surgir del contrato, con renuncia, en su caso, al fuero jurisdiccional extranjero que pudiera corresponderle.

## NOVENO — Notificaciones

Que la entidad designa, a efectos de notificaciones durante el procedimiento de contratación y la posterior ejecución del contrato, en su caso, la siguiente dirección electrónica habilitada:

| Concepto | Datos |
|----------|-------|
| Correo electrónico para notificaciones | {{ cliente.email_notificaciones if cliente.email_notificaciones else cliente.contacto_compliance.email if cliente.contacto_compliance and cliente.contacto_compliance.email else '[email]' }} |
| Persona de contacto | {{ cliente.persona_contacto_licitaciones.nombre if cliente.persona_contacto_licitaciones and cliente.persona_contacto_licitaciones.nombre else '—' }} |
| Teléfono | {{ cliente.persona_contacto_licitaciones.telefono if cliente.persona_contacto_licitaciones and cliente.persona_contacto_licitaciones.telefono else '—' }} |

---

Y para que conste a los efectos oportunos, firma la presente Declaración Responsable en el lugar y fecha indicados al pie.

| Concepto | Datos |
|----------|-------|
| Lugar | {{ licitacion.lugar_firma if licitacion and licitacion.lugar_firma else '—' }} |
| Fecha | {{ licitacion.fecha_firma if licitacion and licitacion.fecha_firma else '—' }} |
| Firma | |

**Don/Doña {{ rep_nombre }}**
**{{ rep_cargo }}**
**{{ cliente.razon_social }} — NIF {{ cliente.nif }}**

---

*Documento L-001 · Declaración Responsable Art. 140 LCSP · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*

*Nota: este modelo es aplicable a procedimientos abiertos, restringidos y de licitación con negociación. En procedimientos sujetos a regulación armonizada (umbral UE), el órgano de contratación podrá exigir la presentación del Documento Europeo Único de Contratación (DEUC · modelo L-002), en cuyo caso el DEUC sustituye o complementa la presente Declaración Responsable.*
