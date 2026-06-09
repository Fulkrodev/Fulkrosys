# E-604 · ADENDA CONTRACTUAL DE CUMPLIMIENTO ENS / RGPD / NIS2 / DORA

{% set codigo = documento.codigo if documento.codigo else 'E-604' %}
{% set version = documento.version if documento.version else '1.0' %}
{% set fecha_emision = documento.fecha_emision if documento.fecha_emision else '—' %}
{% set normativas = proveedor.normativas_aplicables if proveedor.normativas_aplicables else ['ENS'] %}
{% set incluir_rgpd = 'RGPD' in normativas %}
{% set incluir_nis2 = 'NIS2' in normativas %}
{% set incluir_dora = 'DORA' in normativas %}
{% set addendum_code = adenda.addendum_code if adenda.addendum_code else '[CÓDIGO ADENDA]' %}
{% set contrato_ref = adenda.contract_ref if adenda.contract_ref else '[REFERENCIA CONTRATO BASE]' %}
{% set fecha_vigor = adenda.fecha_vigor if adenda.fecha_vigor else fecha_emision %}
{% set vencimiento = adenda.vencimiento if adenda.vencimiento else '—' %}

**Adenda nº:** {{ addendum_code }}
**Documento base:** {{ codigo }} · versión {{ version }}
**Fecha de emisión:** {{ fecha_emision }}
**Fecha entrada en vigor:** {{ fecha_vigor }}
**Vencimiento:** {{ vencimiento }}
**Contrato base de referencia:** {{ contrato_ref }}
**Normativas cubiertas:** {{ normativas | join(' · ') }}
**Clasificación:** Confidencial — entre las Partes

---

## 1. IDENTIFICACIÓN DE LAS PARTES

**DE UNA PARTE,** {{ cliente.razon_social }}, con NIF {{ cliente.nif }}, con domicilio en {% if cliente.domicilio %}{{ cliente.domicilio }}{% else %}[domicilio]{% endif %}, representada en este acto por {% if cliente.representante %}{{ cliente.representante.nombre }}, en su condición de {{ cliente.representante.cargo }}{% else %}[representante]{% endif %} (en adelante, "**LA ENTIDAD**").

**Y DE OTRA PARTE,** {{ proveedor.razon_social }}, con NIF/CIF {{ proveedor.nif }}, con domicilio en {% if proveedor.domicilio %}{{ proveedor.domicilio }}{% else %}[domicilio]{% endif %}, representada en este acto por {% if proveedor.representante %}{{ proveedor.representante.nombre }}, en su condición de {{ proveedor.representante.cargo }}{% else %}[representante]{% endif %} (en adelante, "**EL PROVEEDOR**").

Ambas partes se reconocen mutuamente capacidad legal suficiente para suscribir la presente Adenda y, a tal efecto,

## 2. ANTECEDENTES

I. Que con fecha {% if contrato_base.fecha %}{{ contrato_base.fecha }}{% else %}[fecha contrato base]{% endif %}, LA ENTIDAD y EL PROVEEDOR suscribieron el contrato identificado como **{{ contrato_ref }}** cuyo objeto es {% if contrato_base.objeto %}{{ contrato_base.objeto }}{% else %}la prestación al cliente de los servicios de {{ proveedor.servicio_descripcion }}{% endif %} (en adelante, el "**CONTRATO BASE**").

II. Que LA ENTIDAD presta servicios a entidades del sector público español sujetas al **Esquema Nacional de Seguridad (ENS)** regulado por el Real Decreto 311/2022, de 3 de mayo, lo que la obliga a trasladar a sus proveedores las exigencias de seguridad de la información derivadas del referido marco normativo, conforme al artículo 18 y la medida `op.ext.1` del Anexo II del citado Real Decreto.

III. Que, adicionalmente, el servicio objeto del CONTRATO BASE puede implicar el tratamiento de datos personales por cuenta de LA ENTIDAD y/o quedar afectado por otras normas sectoriales de cumplimiento obligatorio relacionadas con la seguridad de la información.

IV. Que, en consecuencia, las Partes acuerdan formalizar la presente Adenda al CONTRATO BASE para regular las obligaciones específicas de seguridad de la información que asume EL PROVEEDOR durante la vigencia del servicio.

## 3. OBJETO DE LA ADENDA

La presente Adenda tiene por objeto:

a) Sujetar a EL PROVEEDOR al cumplimiento de las medidas del Esquema Nacional de Seguridad equivalentes al alcance del servicio prestado, conforme al artículo 18 del RD 311/2022.

{% if incluir_rgpd %}
b) Regular el tratamiento de datos personales que EL PROVEEDOR realice por cuenta de LA ENTIDAD como **encargado de tratamiento**, conforme al artículo 28 del Reglamento (UE) 2016/679 (RGPD) y la Ley Orgánica 3/2018 (LOPDGDD).
{% endif %}

{% if incluir_nis2 %}
c) Establecer las obligaciones de gestión de riesgos de ciberseguridad derivadas del régimen de la Directiva (UE) 2022/2555 (NIS2) que afectan a la cadena de suministro de LA ENTIDAD, conforme a su artículo 21.2.d).
{% endif %}

{% if incluir_dora %}
d) Adaptar el CONTRATO BASE a los requisitos contractuales mínimos exigidos por el Reglamento (UE) 2022/2554 (DORA), conforme a su artículo 30, cuando aplica.
{% endif %}

e) Regular los derechos de auditoría, supervisión y resolución de LA ENTIDAD asociados al cumplimiento de las obligaciones anteriores.

f) Regular el procedimiento de salida ordenada del PROVEEDOR al término del servicio.

La presente Adenda **complementa** al CONTRATO BASE. En caso de contradicción entre ambos documentos, prevalecerá lo dispuesto en la presente Adenda en todo lo relativo a las materias aquí reguladas.

## 4. DEFINICIONES

A efectos de la presente Adenda:

- **ENS:** Esquema Nacional de Seguridad regulado por el RD 311/2022.
- **Anexo II:** catálogo de medidas técnicas y organizativas del ENS.
- **Incidente significativo:** suceso que vulnera o pone en riesgo la confidencialidad, integridad, disponibilidad, autenticidad o trazabilidad de la información o los sistemas afectados, conforme a los criterios del ENS y, en su caso, de NIS2.
- **CCN-CERT:** Capacidad de Respuesta a Incidentes del Centro Criptológico Nacional.
- **AEPD:** Agencia Española de Protección de Datos.

## 5. OBLIGACIONES DE CUMPLIMIENTO ENS

### 5.1 Sujeción al Anexo II del RD 311/2022

EL PROVEEDOR declara conocer las medidas del Anexo II del RD 311/2022 y se compromete a implantar y mantener en su organización las medidas técnicas y organizativas equivalentes a la categoría del servicio prestado, en la proporción que corresponda al alcance del CONTRATO BASE.

A los efectos de la presente cláusula, LA ENTIDAD ha categorizado el servicio prestado como **{% if proveedor.categoria_servicio_ens %}{{ proveedor.categoria_servicio_ens }}{% else %}MEDIA{% endif %}** conforme a los criterios del Anexo I del RD 311/2022.

### 5.2 Acreditación del cumplimiento

EL PROVEEDOR acreditará el cumplimiento de la presente cláusula mediante:

a) **Declaración de Conformidad ENS vigente** para el servicio objeto, o

b) **Certificación equivalente** (ISO/IEC 27001:2022 + alcance, SOC 2 Type II o esquema sectorial reconocido) acompañada de la matriz de equivalencias con el Anexo II del ENS.

EL PROVEEDOR remitirá a LA ENTIDAD evidencia documental actualizada de los apartados anteriores con periodicidad anual y siempre que se produzca renovación, suspensión o pérdida de las certificaciones acreditadas.

### 5.3 Personal asignado al servicio

EL PROVEEDOR garantizará que el personal asignado al servicio:

a) Cuenta con formación documentada en seguridad de la información acorde a su función.

b) Está sujeto a deberes contractuales de confidencialidad equivalentes a los aquí establecidos.

c) Conoce y aplica los procedimientos internos del PROVEEDOR alineados con el Anexo II del ENS.

{% if incluir_rgpd %}
## 6. TRATAMIENTO DE DATOS PERSONALES — ENCARGO DE TRATAMIENTO (RGPD Art. 28)

### 6.1 Naturaleza del encargo

EL PROVEEDOR actuará como encargado de tratamiento de los datos personales que trate por cuenta de LA ENTIDAD en el marco del servicio prestado. El presente apartado constituye el contrato de encargo de tratamiento exigido por el artículo 28 del RGPD.

### 6.2 Finalidad y objeto del tratamiento

EL PROVEEDOR únicamente tratará los datos personales para las finalidades estrictamente necesarias para la prestación del servicio objeto del CONTRATO BASE. Cualquier tratamiento con finalidad distinta requerirá autorización expresa, escrita y previa de LA ENTIDAD.

### 6.3 Subencargados

EL PROVEEDOR no podrá subcontratar parte alguna del tratamiento sin autorización específica, previa y por escrito de LA ENTIDAD. Cuando se autorice la subcontratación, EL PROVEEDOR:

a) Suscribirá con el subencargado un contrato que imponga obligaciones equivalentes a las de la presente cláusula.

b) Mantendrá registro actualizado de los subencargados autorizados y lo pondrá a disposición de LA ENTIDAD.

c) Responderá ante LA ENTIDAD del cumplimiento del subencargado.

### 6.4 Transferencias internacionales de datos

EL PROVEEDOR no transferirá datos personales fuera del Espacio Económico Europeo sin garantía adecuada conforme a los artículos 44 a 49 del RGPD y sin notificación previa por escrito a LA ENTIDAD con identificación expresa del país destino y la garantía aplicada.

### 6.5 Medidas de seguridad y deber de asistencia

EL PROVEEDOR implantará medidas técnicas y organizativas apropiadas (Art. 32 RGPD), prestará asistencia a LA ENTIDAD en el ejercicio de los derechos de los interesados (Arts. 12-22 RGPD) y en las evaluaciones de impacto cuando sean requeridas.

### 6.6 Notificación de violaciones de seguridad

EL PROVEEDOR notificará a LA ENTIDAD toda violación de seguridad que afecte a los datos personales tratados en el marco del servicio en un plazo máximo de **{% if adenda.notificacion_horas_rgpd %}{{ adenda.notificacion_horas_rgpd }}{% else %}24{% endif %} horas** desde su detección, aportando la información necesaria para que LA ENTIDAD pueda cumplir sus obligaciones de notificación a la AEPD y a los interesados.

### 6.7 Destino de los datos al término del servicio

Al término del servicio o de la presente Adenda, EL PROVEEDOR procederá, conforme a la opción que indique LA ENTIDAD, a:

a) Devolver los datos personales en formato estructurado, o

b) Suprimirlos de forma segura,

y aportará certificación documental del destino dado a los datos, incluyendo los obrantes en copias de seguridad, en plazo máximo de treinta (30) días naturales desde la solicitud.
{% endif %}

{% if incluir_nis2 %}
## 7. OBLIGACIONES DE CIBERSEGURIDAD NIS2

### 7.1 Gestión de riesgos en la cadena de suministro

EL PROVEEDOR aplicará a la prestación del servicio prácticas de gestión de riesgos de ciberseguridad equivalentes a las exigidas por el artículo 21 de la Directiva (UE) 2022/2555, en particular:

a) Análisis de riesgos formalizado del servicio prestado.

b) Plan de continuidad de negocio documentado y probado.

c) Gestión de la propia cadena de suministro del PROVEEDOR aplicada al servicio.

d) Cifrado y autenticación robusta en los flujos de información con LA ENTIDAD.

e) Formación y concienciación en ciberseguridad del personal asignado.

### 7.2 Notificación de incidentes significativos

Cuando un incidente que afecte al servicio prestado tuviera consideración de **incidente significativo** conforme a la NIS2, EL PROVEEDOR notificará a LA ENTIDAD en un plazo máximo de **{% if adenda.notificacion_horas_nis2 %}{{ adenda.notificacion_horas_nis2 }}{% else %}12{% endif %} horas** desde su detección y colaborará con LA ENTIDAD en las notificaciones obligatorias a la autoridad competente.
{% endif %}

{% if incluir_dora %}
## 8. ACUERDOS TIC BAJO DORA (Art. 30)

### 8.1 Inclusión en el registro DORA

EL PROVEEDOR acepta que LA ENTIDAD incluya la presente relación contractual en el registro de información de acuerdos TIC al que se refiere el artículo 28.3 del Reglamento (UE) 2022/2554, aportando la información que LA ENTIDAD le requiera a tal efecto.

### 8.2 Derechos de acceso, inspección y auditoría

EL PROVEEDOR garantiza a LA ENTIDAD, a las autoridades competentes y, en su caso, a los terceros designados por estas, derechos de acceso, inspección y auditoría sobre los aspectos del servicio relevantes para la resiliencia operativa digital.

### 8.3 Estrategias de salida y planes de continuidad

EL PROVEEDOR dispondrá de planes documentados de continuidad operativa con objetivos RTO/RPO declarables a LA ENTIDAD, y colaborará con LA ENTIDAD en la elaboración y prueba de las estrategias de salida exigidas por el artículo 28.8 DORA.
{% endif %}

## 9. AUDITORÍA Y DERECHOS DE INSPECCIÓN

EL PROVEEDOR acepta que LA ENTIDAD, o terceros independientes designados por esta, pueda realizar:

a) Revisiones documentales periódicas, con la frecuencia que se determine en el Plan de Supervisión E-603 vigente.

b) Auditorías presenciales o remotas sobre el alcance del servicio, con preaviso mínimo de quince (15) días naturales salvo en supuestos de incidente o sospecha razonable de incumplimiento.

c) Pruebas técnicas (test de penetración, escaneo de vulnerabilidades) sobre los activos del PROVEEDOR que soportan el servicio, previa coordinación operativa.

EL PROVEEDOR pondrá a disposición de LA ENTIDAD la documentación, accesos y recursos razonables para la efectiva realización de las anteriores actuaciones.

## 10. NOTIFICACIÓN DE INCIDENTES (CLÁUSULA GENERAL)

Sin perjuicio de las obligaciones específicas RGPD y NIS2 anteriores, EL PROVEEDOR notificará a LA ENTIDAD todo incidente que afecte o pueda afectar al servicio prestado o a la información tratada en un plazo máximo de **{% if adenda.notificacion_horas %}{{ adenda.notificacion_horas }}{% else %}24{% endif %} horas desde su detección**, dirigiendo la notificación al contacto operativo de LA ENTIDAD ({% if cliente.contacto_compliance %}{{ cliente.contacto_compliance.email }}{% else %}[contacto compliance]{% endif %}).

Cuando el incidente sea significativo conforme al ENS, EL PROVEEDOR colaborará con LA ENTIDAD en la cumplimentación de los formularios y notificaciones obligatorias a CCN-CERT y, en su caso, en las comunicaciones al INES.

## 11. CONFIDENCIALIDAD

Toda información que EL PROVEEDOR conozca o trate en el marco del servicio tendrá carácter confidencial. EL PROVEEDOR se obliga a:

a) No divulgar, ceder ni comunicar la información a terceros sin autorización expresa de LA ENTIDAD.

b) Imponer el mismo deber de confidencialidad a todo personal y subcontratista que acceda a la información.

c) Mantener la confidencialidad durante la vigencia del servicio y durante los cinco (5) años siguientes a la finalización del mismo, sin perjuicio de obligaciones legales de mayor duración.

## 12. RESPONSABILIDAD Y SEGUROS

EL PROVEEDOR responderá frente a LA ENTIDAD por los daños y perjuicios derivados del incumplimiento de las obligaciones de la presente Adenda, incluyendo expresamente las sanciones administrativas que pudieran imponerse a LA ENTIDAD como consecuencia de actuaciones u omisiones imputables al PROVEEDOR.

EL PROVEEDOR mantendrá durante toda la vigencia del servicio una póliza de **seguro de responsabilidad civil profesional o ciberseguridad** con cuantía mínima de {% if adenda.seguro_cuantia_eur %}{{ adenda.seguro_cuantia_eur }} euros{% else %}[cuantía a definir por LA ENTIDAD] euros{% endif %}, aportando copia vigente cuando LA ENTIDAD lo requiera.

## 13. VIGENCIA, PRÓRROGAS Y RESOLUCIÓN

### 13.1 Vigencia

La presente Adenda entrará en vigor en la fecha de su firma por ambas Partes y mantendrá su eficacia mientras subsista el CONTRATO BASE.

### 13.2 Causas específicas de resolución

Sin perjuicio de las causas previstas en el CONTRATO BASE y en la legislación aplicable, LA ENTIDAD podrá resolver la presente Adenda y, en consecuencia, el CONTRATO BASE, cuando concurra alguna de las siguientes circunstancias:

a) Incumplimiento material por parte del PROVEEDOR de las obligaciones ENS, RGPD, NIS2 o DORA reguladas en la presente Adenda.

b) Pérdida o suspensión sobrevenida de las certificaciones acreditativas del cumplimiento ENS sin reposición en un plazo razonable.

c) Subcontratación no autorizada o reiterada falta de información sobre subencargados.

d) Incidentes graves repetidos imputables al PROVEEDOR.

e) Negativa injustificada del PROVEEDOR a someterse a las auditorías o pruebas técnicas previstas en la presente Adenda.

## 14. PROCEDIMIENTO DE SALIDA ORDENADA

Al término del servicio, EL PROVEEDOR colaborará con LA ENTIDAD en el procedimiento de salida ordenada conforme a las siguientes obligaciones mínimas:

a) Plan de transición documentado con tareas, plazos y responsables.

b) Entrega de la información, configuraciones, registros y documentación operativa que LA ENTIDAD requiera.

c) Soporte al proveedor entrante o al equipo interno de LA ENTIDAD durante el periodo de transición.

d) Devolución o destrucción acreditada de la información en plazo máximo de **treinta (30) días naturales** desde la solicitud, conforme a lo dispuesto en la cláusula 6.7 cuando aplique.

## 15. JURISDICCIÓN Y LEY APLICABLE

La presente Adenda se rige por la legislación española. Para la resolución de cualquier controversia derivada de la misma, las Partes se someten a los Juzgados y Tribunales que correspondan al domicilio de LA ENTIDAD, con renuncia expresa a cualquier otro fuero que pudiera corresponderles.

## 16. FIRMAS

Y en prueba de conformidad con cuanto antecede, las Partes firman la presente Adenda, por duplicado y a un solo efecto, en el lugar y fecha indicados en el encabezamiento.

| Parte | Nombre y apellidos | Cargo | Fecha | Firma |
|-------|--------------------|-------|-------|-------|
| **POR LA ENTIDAD** | {% if cliente.representante %}{{ cliente.representante.nombre }}{% else %}[representante entidad]{% endif %} | {% if cliente.representante %}{{ cliente.representante.cargo }}{% else %}—{% endif %} | {{ fecha_vigor }} | |
| **POR EL PROVEEDOR** | {% if proveedor.representante %}{{ proveedor.representante.nombre }}{% else %}[representante proveedor]{% endif %} | {% if proveedor.representante %}{{ proveedor.representante.cargo }}{% else %}—{% endif %} | | |

---

*Documento generado por FULKRO · plataforma de gestión ENS · {{ fecha_emision }}*
*Trazabilidad: vinculado al `provider_addendum_id={{ adenda.id if adenda.id else '—' }}` · `provider_id={{ proveedor.id if proveedor.id else '—' }}` · `project_id={{ cliente.project_id if cliente.project_id else '—' }}`. Normativas materializadas: {{ normativas | join(', ') }}.*
