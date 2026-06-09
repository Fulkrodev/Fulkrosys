---
codigo_documento: "L-003"
titulo: "Compromiso de Adscripción de Medios al Contrato (Artículo 76.2 LCSP)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · uso licitación"
norma_aplicable: "Ley 9/2017 LCSP · Art. 76.2"
---

# COMPROMISO DE ADSCRIPCIÓN DE MEDIOS PERSONALES Y MATERIALES

{% set rep_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[Nombre representante legal]' %}
{% set rep_dni = cliente.representante.dni if cliente.representante and cliente.representante.dni else '[DNI]' %}
{% set rep_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[Cargo]' %}
{% set expediente = licitacion.numero_expediente if licitacion and licitacion.numero_expediente else '[NÚMERO DE EXPEDIENTE]' %}
{% set organo_contratante = licitacion.organo_contratante if licitacion and licitacion.organo_contratante else '[ÓRGANO DE CONTRATACIÓN]' %}

(De conformidad con el artículo 76.2 de la Ley 9/2017 de Contratos del Sector Público)

---

**Don/Doña {{ rep_nombre }}**, con DNI/NIE **{{ rep_dni }}**, en su condición de **{{ rep_cargo }}** y en representación de **{{ cliente.razon_social }}** (NIF: **{{ cliente.nif }}**), debidamente facultado,

**en relación con el expediente** {{ expediente }} **convocado por** {{ organo_contratante }},

**SE COMPROMETE FORMALMENTE**:

## PRIMERO — Adscripción de medios

A **adscribir a la ejecución del contrato** los medios personales y materiales que se relacionan en el presente compromiso, manteniéndolos disponibles durante toda la vigencia del contrato y de sus posibles prórrogas, conforme a las exigencias del pliego de cláusulas administrativas particulares y del pliego de prescripciones técnicas del expediente.

## SEGUNDO — Medios personales adscritos al contrato

Se adscriben al contrato los siguientes perfiles profesionales:

| # | Perfil profesional | Cualificación / Titulación | Experiencia mínima | Dedicación |
|---|-------------------|---------------------------|-------------------|------------|
{% if licitacion.medios_personales %}
{% for m in licitacion.medios_personales %}
| {{ loop.index }} | {{ m.perfil }} | {{ m.cualificacion }} | {{ m.experiencia }} | {{ m.dedicacion }} |
{% endfor %}
{% else %}
| 1 | [Director de proyecto] | [Titulación universitaria + certificación] | [Años] | [Tiempo dedicado] |
| 2 | [Consultor senior] | [Titulación + certificaciones] | [Años] | [Tiempo dedicado] |
| 3 | [Consultor / técnico] | [Titulación + certificaciones] | [Años] | [Tiempo dedicado] |
{% endif %}

La identificación nominal del personal adscrito se facilitará al órgano de contratación con anterioridad al inicio efectivo de la ejecución del contrato.

## TERCERO — Medios materiales adscritos al contrato

Se adscriben al contrato los siguientes medios materiales:

{% if licitacion.medios_materiales %}
{% for m in licitacion.medios_materiales %}
- {{ m }}
{% endfor %}
{% else %}
- Infraestructura técnica suficiente para la prestación del servicio en los niveles de servicio exigidos.
- Herramientas tecnológicas, licencias y software profesional necesarios para la ejecución.
- Sistemas de información seguros conformes al Esquema Nacional de Seguridad cuando aplique.
- Espacios físicos adecuados cuando la naturaleza del contrato lo requiera.
{% endif %}

## CUARTO — Acreditación y verificación

A **acreditar documentalmente la disponibilidad efectiva de los medios** descritos a requerimiento del órgano de contratación, en cualquier momento durante la vigencia del contrato, mediante la aportación de:

a) Contratos laborales o mercantiles que vinculen al personal con la entidad.
b) Currículos del personal adscrito.
c) Títulos académicos y certificaciones profesionales relevantes.
d) Documentación acreditativa de la disponibilidad de los medios materiales.

## QUINTO — Carácter esencial del compromiso

A reconocer que el cumplimiento del presente compromiso de adscripción de medios **tiene carácter esencial**, en los términos del artículo 76.2 LCSP, por lo que su incumplimiento podrá ser causa de resolución del contrato conforme a lo establecido en el pliego.

## SEXTO — Sustituciones

Que cualquier **sustitución del personal adscrito** durante la ejecución del contrato:

a) Se notificará previamente al órgano de contratación con la antelación razonable.
b) El nuevo personal acreditará un perfil profesional **equivalente o superior** al sustituido.
c) Se aportará al órgano de contratación la documentación acreditativa correspondiente.

## SÉPTIMO — Subcontratación

{% if licitacion.permite_subcontratacion %}
Que, en la medida en que el pliego lo permita, la entidad podrá subcontratar prestaciones accesorias hasta el límite máximo establecido, en cuyo caso el subcontratista quedará obligado a aplicar los mismos estándares de cumplimiento del presente compromiso al personal y medios adscritos por su parte.
{% else %}
Que la entidad asumirá íntegramente la ejecución del contrato sin recurrir a subcontratación, salvo autorización expresa previa del órgano de contratación.
{% endif %}

---

Y para que conste y surta los efectos oportunos en el procedimiento de contratación del expediente {{ expediente }}, firma el presente Compromiso de Adscripción de Medios.

| Concepto | Datos |
|----------|-------|
| Lugar y fecha | {{ licitacion.lugar_firma if licitacion and licitacion.lugar_firma else '—' }}, {{ licitacion.fecha_firma if licitacion and licitacion.fecha_firma else '—' }} |
| Firma | |

**Don/Doña {{ rep_nombre }}**
**{{ rep_cargo }}**
**{{ cliente.razon_social }} — NIF {{ cliente.nif }}**

---

*Documento L-003 · Compromiso adscripción medios Art. 76.2 LCSP · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
