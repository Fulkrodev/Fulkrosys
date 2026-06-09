---
codigo_documento: "L-004"
titulo: "Acreditación de Solvencia Técnica y Profesional (Artículos 89-91 LCSP)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · uso licitación"
norma_aplicable: "Ley 9/2017 LCSP · Arts. 89-91"
---

# ACREDITACIÓN DE SOLVENCIA TÉCNICA Y PROFESIONAL

{% set rep_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[Nombre representante legal]' %}
{% set rep_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[Cargo]' %}
{% set expediente = licitacion.numero_expediente if licitacion and licitacion.numero_expediente else '[NÚMERO DE EXPEDIENTE]' %}
{% set organo_contratante = licitacion.organo_contratante if licitacion and licitacion.organo_contratante else '[ÓRGANO DE CONTRATACIÓN]' %}

**Entidad licitadora:** {{ cliente.razon_social }} (NIF: {{ cliente.nif }})
**Expediente:** {{ expediente }}
**Órgano de contratación:** {{ organo_contratante }}

(De conformidad con los artículos 89 a 91 de la Ley 9/2017 de Contratos del Sector Público)

---

## 1. OBJETO

La presente documentación acredita la **solvencia técnica y profesional** de {{ cliente.razon_social }} para la ejecución del contrato objeto del expediente {{ expediente }}, conforme a los criterios exigidos en el pliego de cláusulas administrativas particulares y a los artículos 89 a 91 LCSP.

## 2. RELACIÓN DE PRINCIPALES SERVICIOS REALIZADOS

Se relacionan a continuación los principales servicios prestados por la entidad en los **últimos {{ licitacion.anios_referencia if licitacion and licitacion.anios_referencia else 5 }} años**, en el ámbito de actividad afín al objeto del contrato, conforme al artículo 90.1.a) LCSP:

| # | Cliente | Objeto del servicio | Importe (€) | Fecha inicio | Fecha fin |
|---|---------|--------------------|-------------|--------------|-----------|
{% if cliente.referencias_proyectos %}
{% for p in cliente.referencias_proyectos %}
| {{ loop.index }} | {{ p.cliente }} | {{ p.objeto }} | {{ p.importe }} | {{ p.fecha_inicio }} | {{ p.fecha_fin }} |
{% endfor %}
{% else %}
| 1 | [Cliente 1] | [Objeto servicio] | [Importe] | [Inicio] | [Fin] |
| 2 | [Cliente 2] | [Objeto servicio] | [Importe] | [Inicio] | [Fin] |
| 3 | [Cliente 3] | [Objeto servicio] | [Importe] | [Inicio] | [Fin] |
{% endif %}

La acreditación documental de los servicios anteriores se realizará, conforme al artículo 90.1.a) párrafo segundo LCSP, mediante:

- Certificados expedidos o visados por el órgano competente cuando el destinatario haya sido una entidad del sector público.
- Certificados expedidos por el comprador o, a falta de los mismos, mediante declaración del empresario, cuando el destinatario haya sido un sujeto privado.

Estos certificados se aportarán como **Anexo I** a la presente Acreditación o, en su caso, a requerimiento del órgano de contratación conforme al artículo 150.2 LCSP.

## 3. TITULACIONES ACADÉMICAS Y PROFESIONALES DEL PERSONAL RESPONSABLE

Conforme al artículo 90.1.e) LCSP, se relacionan las titulaciones académicas y profesionales del **personal responsable de la ejecución** del contrato:

| Perfil | Titulaciones | Certificaciones profesionales | Años experiencia |
|--------|--------------|------------------------------|------------------|
{% if cliente.equipo_responsable %}
{% for p in cliente.equipo_responsable %}
| {{ p.perfil }} | {{ p.titulaciones }} | {{ p.certificaciones }} | {{ p.anios }} |
{% endfor %}
{% else %}
| [Director proyecto] | [Titulación universitaria] | [Certificaciones relevantes] | [Años] |
| [Consultor senior] | [Titulación universitaria] | [Certificaciones] | [Años] |
| [Consultor / técnico] | [Titulación] | [Certificaciones] | [Años] |
{% endif %}

## 4. CERTIFICACIONES DE LA ENTIDAD

Conforme al artículo 93 LCSP, la entidad acredita las siguientes **certificaciones vigentes** emitidas por organismos independientes:

{% if cliente.certificaciones_vigentes %}
{% for c in cliente.certificaciones_vigentes %}
- **{{ c.norma }}** · Alcance: {{ c.alcance }} · Entidad certificadora: {{ c.entidad }} · Vigencia: {{ c.vigencia }}
{% endfor %}
{% else %}
- [ISO/IEC 27001 · Alcance: ___ · Entidad: ___ · Vigencia: ___]
- [Esquema Nacional de Seguridad · Categoría: ___ · Entidad: ___ · Vigencia: ___ · cuando proceda]
- [Otras certificaciones aplicables al objeto del contrato]
{% endif %}

Los certificados se aportan como **Anexo II** a la presente Acreditación.

## 5. INSTALACIONES Y MEDIOS TÉCNICOS

Conforme al artículo 90.1.d) LCSP, la entidad dispone de los siguientes medios técnicos relevantes para la ejecución del contrato:

{% if cliente.medios_tecnicos_descripcion %}
{{ cliente.medios_tecnicos_descripcion }}
{% else %}
- Infraestructura tecnológica suficiente para la prestación del servicio en los niveles de servicio exigidos.
- Herramientas profesionales propias o licenciadas correspondientes al ámbito de la actividad contratada.
- Sistemas seguros de gestión de la información, conformes al Esquema Nacional de Seguridad cuando aplique al servicio.
- Procesos documentados de control de calidad de los servicios prestados.
{% endif %}

## 6. PROCEDIMIENTOS DE GESTIÓN DE LA CALIDAD

La entidad aplica procedimientos formales de gestión de la calidad para la prestación de sus servicios, descritos en su sistema de gestión interno, y se compromete a aplicar dichos procedimientos a la ejecución del presente contrato.

## 7. SUBCONTRATISTAS

{% if licitacion.permite_subcontratacion and cliente.subcontratistas_previstos %}
Para determinadas prestaciones accesorias se prevé el recurso a los siguientes subcontratistas, dentro de los límites previstos en el pliego:

| Subcontratista | Prestación | Importe estimado (€) |
|----------------|-----------|---------------------|
{% for s in cliente.subcontratistas_previstos %}
| {{ s.nombre }} | {{ s.prestacion }} | {{ s.importe }} |
{% endfor %}
{% else %}
La entidad no prevé recurrir a subcontratación para la ejecución del contrato, salvo autorización expresa del órgano de contratación.
{% endif %}

---

**Don/Doña {{ rep_nombre }}**
**{{ rep_cargo }}**
**{{ cliente.razon_social }} — NIF {{ cliente.nif }}**

Lugar y fecha: {{ licitacion.lugar_firma if licitacion and licitacion.lugar_firma else '—' }}, {{ licitacion.fecha_firma if licitacion and licitacion.fecha_firma else '—' }}

Firma:

---

*Documento L-004 · Solvencia técnica y profesional Arts. 89-91 LCSP · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
