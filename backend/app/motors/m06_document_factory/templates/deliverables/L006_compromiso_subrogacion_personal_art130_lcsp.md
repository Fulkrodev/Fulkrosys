---
codigo_documento: "L-006"
titulo: "Compromiso de Subrogación de Personal · Art. 130 LCSP"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "PÚBLICA · ENTREGABLE LICITACIÓN"
norma_aplicable: "Ley 9/2017 LCSP Art. 130 · Estatuto de los Trabajadores Art. 44"
naturaleza: "Compromiso formal del licitador adjudicatario"
---

# COMPROMISO DE SUBROGACIÓN DEL PERSONAL ADSCRITO A LA EJECUCIÓN DEL CONTRATO

**Documento L-006 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set contrato_ref = contrato.referencia if contrato and contrato.referencia else '[REFERENCIA EXPEDIENTE]' %}
{% set contrato_objeto = contrato.objeto if contrato and contrato.objeto else '[Objeto del contrato según pliego]' %}
{% set poder_adj = contrato.poder_adjudicador if contrato and contrato.poder_adjudicador else '[Órgano de contratación según pliego]' %}
{% set subro_aplica = subrogacion.aplica if subrogacion and subrogacion.aplica is defined else False %}
{% set convenio = subrogacion.convenio_colectivo_aplicable if subrogacion and subrogacion.convenio_colectivo_aplicable else '[Convenio colectivo aplicable según pliego]' %}
{% set organo_info = subrogacion.organo_facilitador_info if subrogacion and subrogacion.organo_facilitador_info else 'el órgano de contratación' %}
{% set fecha_info = subrogacion.fecha_info_recibida if subrogacion and subrogacion.fecha_info_recibida else '[fecha]' %}
{% set centro = subrogacion.centro_trabajo_destino if subrogacion and subrogacion.centro_trabajo_destino else '[Centro de trabajo]' %}
{% set representante_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[REPRESENTANTE LEGAL]' %}
{% set representante_dni = cliente.representante.dni if cliente.representante and cliente.representante.dni else '[DNI]' %}
{% set representante_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[CARGO]' %}

## 1. IDENTIFICACIÓN DEL PROCEDIMIENTO

| Campo | Valor |
|-------|-------|
| Referencia del expediente | **{{ contrato_ref }}** |
| Objeto del contrato | {{ contrato_objeto }} |
| Poder adjudicador | {{ poder_adj }} |
| Centro de trabajo objeto de la subrogación | {{ centro }} |
| Convenio colectivo aplicable | **{{ convenio }}** |

## 2. MARCO NORMATIVO

El presente compromiso se formula al amparo de:

- **Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público** (LCSP), artículo 130 sobre información a los licitadores en supuestos de subrogación de personal.
- **Real Decreto Legislativo 2/2015, de 23 de octubre**, por el que se aprueba el texto refundido de la Ley del Estatuto de los Trabajadores (ET), artículo 44 sobre la sucesión de empresa.
- El **convenio colectivo aplicable** referenciado en la sección 1.
- El **pliego del procedimiento** referenciado en la sección 1, en cuanto exige el presente compromiso conforme al artículo 130 LCSP.

## 3. COMPROMISO FORMAL DEL LICITADOR

**{{ cliente.razon_social }}** (en adelante, "el Licitador"), con NIF **{{ cliente.nif }}** y domicilio en {{ cliente.domicilio if cliente.domicilio else '[domicilio social]' }}, representada por **{{ representante_nombre }}**, con DNI **{{ representante_dni }}** y en su condición de **{{ representante_cargo }}**, mediante el presente documento:

a) **Declara conocer** la información facilitada por {{ organo_info }} en fecha **{{ fecha_info }}**, relativa al personal afectado por la eventual subrogación en el supuesto de resultar adjudicataria del procedimiento referenciado en la sección 1.

b) **Asume formalmente el compromiso** de, en caso de resultar adjudicataria del contrato y serle de aplicación la subrogación conforme al convenio colectivo y al artículo 44 del Estatuto de los Trabajadores, **subrogarse como nueva empleadora** del personal incluido en el listado del documento L-007 anexo, en las mismas condiciones laborales y contractuales que ostentaban con la empresa cedente.

c) **Reconoce expresamente** que la subrogación, cuando proceda, implica la continuidad del vínculo laboral del personal afectado sin solución de continuidad y la conservación de los derechos adquiridos, incluyendo la antigüedad acumulada y las condiciones económicas vigentes.

## 4. INFORMACIÓN VERIFICADA POR EL LICITADOR

El Licitador declara haber verificado la información facilitada por {{ organo_info }} en los términos del artículo 130.3 LCSP, incluyendo:

a) Identificación y categoría profesional del personal afectado.

b) Antigüedad acumulada en la prestación del servicio.

c) Tipo de contrato y jornada anual.

d) Retribución íntegra anual y complementos salariales.

e) Convenio colectivo aplicable.

f) Cualesquiera otras circunstancias relevantes para la determinación de los derechos laborales objeto de subrogación.

El detalle individualizado de las personas afectadas y de sus condiciones se contiene en el **anexo L-007** del presente expediente.

## 5. GARANTÍAS LABORALES

El Licitador se compromete a:

a) **Respetar íntegramente las condiciones laborales** vigentes del personal subrogado en el momento de la subrogación, incluyendo retribución, jornada, antigüedad, complementos y categoría profesional.

b) **No introducir modificaciones sustanciales** en las condiciones de trabajo sin seguir los procedimientos legalmente previstos en los artículos 39 a 41 del Estatuto de los Trabajadores y, cuando proceda, en la negociación con la representación legal de los trabajadores.

c) **Cumplir las obligaciones de información y consulta** con la representación legal de los trabajadores conforme al artículo 44.6 a 44.10 del Estatuto de los Trabajadores.

d) **Asumir las obligaciones laborales y de Seguridad Social** del personal subrogado desde la fecha efectiva de inicio de ejecución del contrato, incluyendo cotizaciones, retenciones y aportaciones a sistemas de previsión social complementaria cuando existan.

e) **Mantener al personal afectado por la subrogación** durante toda la vigencia del contrato, salvo los supuestos legalmente previstos para la extinción individual o colectiva, que en cualquier caso requerirán seguir los procedimientos del Estatuto de los Trabajadores.

## 6. CARÁCTER DECLARATIVO · VERIFICACIÓN DOCUMENTAL EN FASE DE ADJUDICACIÓN

El presente compromiso tiene carácter declarativo a los efectos del procedimiento de contratación. El Licitador se compromete a:

a) Aportar, a requerimiento del órgano de contratación y en fase previa a la formalización del contrato, los documentos justificativos que acrediten las declaraciones contenidas en este compromiso.

b) Comunicar al órgano de contratación cualquier alteración sobrevenida de las circunstancias declaradas durante la tramitación del procedimiento.

## 7. RESPONSABILIDAD DEL LICITADOR · LIMITACIÓN POR INFORMACIÓN FACILITADA

El Licitador asume el presente compromiso sobre la base de la información facilitada por {{ organo_info }} conforme al artículo 130 LCSP. Conforme al apartado 6 del citado artículo, **la falta de comunicación o la comunicación incompleta o inexacta** de la información sobre las condiciones de los contratos de los trabajadores por parte del órgano de contratación o de la empresa anterior **no podrá imputarse al Licitador adjudicatario** a efectos de exigirle el cumplimiento de obligaciones laborales no comunicadas.

En caso de discrepancia material entre la información facilitada y la realidad efectiva del personal en el momento de la subrogación, el Licitador se reserva el derecho a poner el hecho en conocimiento del órgano de contratación a los efectos legales oportunos.

## 8. DECLARACIÓN FINAL

El Licitador, mediante la firma del presente documento, declara:

a) **Aceptar formalmente** el compromiso de subrogación detallado en las secciones precedentes.

b) **Conocer** las consecuencias legales y contractuales derivadas del incumplimiento del presente compromiso.

c) **Acompañar** al presente documento el anexo L-007 con el detalle individualizado del personal afectado, conforme a la información facilitada por {{ organo_info }}.

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[FECHA]' }}.**

**{{ representante_nombre }}**
{{ representante_cargo }}
{{ cliente.razon_social }}
NIF: {{ cliente.nif }}
DNI representante: {{ representante_dni }}

---

**Documento L-006 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: PÚBLICA · ENTREGABLE LICITACIÓN**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}*
