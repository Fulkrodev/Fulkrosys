# DOCUMENTO C-001 — CONTRATO DE PRESTACIÓN DE SERVICIOS DE CONSULTORÍA ENS

```jinja
---
codigo_documento: "C-001"
titulo: "Contrato de Prestación de Servicios Profesionales de Consultoría ENS"
version: "{{ contrato.version | default('1.0') }}"
fecha_firma: "{{ contrato.fecha_firma }}"
clasificacion: "CONFIDENCIAL — Cliente"
---

# CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES DE CONSULTORÍA EN MATERIA DE ESQUEMA NACIONAL DE SEGURIDAD

**Contrato C-001 · Versión {{ contrato.version | default('1.0') }}**

En {{ contrato.lugar_firma | default('Madrid') }}, a {{ contrato.fecha_firma }}.

---

## REUNIDOS

**De una parte,** D. Marcos Mata García, mayor de edad, con N.I.F. {{ marcos.nif }}, y domicilio profesional a efectos del presente contrato en {{ marcos.domicilio }} (en adelante, **"FULKRO"** o **"el Consultor"**), actuando en su propio nombre y derecho como profesional autónomo dado de alta en el Régimen Especial de Trabajadores Autónomos de la Seguridad Social y en el Impuesto de Actividades Económicas, epígrafe correspondiente a actividades de consultoría informática.

**Y de otra parte,** {{ cliente.razon_social }}, con N.I.F. {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }}, debidamente representada en este acto por D./Dña. {{ cliente.firmante.nombre_completo }}, mayor de edad, con N.I.F. {{ cliente.firmante.nif }}, en su condición de {{ cliente.firmante.cargo }}, en virtud de poder bastante al efecto que declara vigente y en uso (en adelante, **"el Cliente"**).

Ambas partes (en adelante, conjuntamente, **"las Partes"**) se reconocen mutuamente la capacidad legal necesaria para suscribir el presente contrato, y a tal efecto

## EXPONEN

**I.** Que el Cliente tiene la condición de entidad obligada o voluntariamente sujeta al cumplimiento del Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, de 3 de mayo, y se encuentra interesado en obtener la certificación de conformidad con dicho marco normativo respecto del sistema de información que ha definido como alcance.

**II.** Que el Consultor es un profesional independiente especializado en la prestación de servicios de consultoría en materia de cumplimiento del Esquema Nacional de Seguridad y otras normativas conexas de seguridad de la información, y dispone de los conocimientos, experiencia y medios necesarios para acompañar al Cliente en su proceso de adecuación y certificación.

**III.** Que con fecha {{ propuesta.fecha_emision }} el Consultor remitió al Cliente la Propuesta P-001, cuya copia constituye el **Anexo I** del presente contrato, en la que se describen los servicios ofertados, el alcance, las fases del proyecto, la duración estimada y la inversión propuesta. Dicha Propuesta ha sido aceptada por el Cliente.

**IV.** Que el Consultor ha informado al Cliente, y este expresamente reconoce, de que conforme a la norma UNE-EN ISO/IEC 17065:2012 y a la guía CCN-CERT IC-01/19 sobre Criterios Generales de Auditoría y Certificación del ENS, la entidad consultora que asiste al Cliente en su adecuación **no puede simultáneamente ser la entidad certificadora** que verifica formalmente dicho cumplimiento, debiendo el Cliente contratar la auditoría externa de certificación con una entidad acreditada por ENAC distinta del Consultor.

**V.** Que las Partes desean formalizar la relación jurídica derivada de la prestación de los servicios profesionales descritos, sometiéndola a las siguientes

## CLÁUSULAS

### PRIMERA — OBJETO DEL CONTRATO

1.1. El objeto del presente contrato es la prestación, por parte del Consultor al Cliente, de servicios profesionales de consultoría destinados a alcanzar la certificación de conformidad con el Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, en la categoría **{{ contrato.categoria_ens }}** y respecto del alcance descrito en la Propuesta P-001 incorporada como Anexo I.

1.2. Los servicios profesionales objeto del contrato comprenden, con carácter no limitativo, las actividades descritas en la sección 5 de la Propuesta P-001, agrupadas en las fases descritas en dicho documento.

1.3. **Quedan expresamente excluidos** del objeto del presente contrato:

a) La auditoría externa de certificación a realizar por una entidad acreditada por ENAC, cuya contratación corresponde directamente al Cliente.

b) La adquisición e implantación técnica de productos, herramientas o servicios tecnológicos que pudieran ser necesarios para el cumplimiento de las medidas del ENS.

c) El asesoramiento jurídico especializado en otras materias distintas del cumplimiento del ENS.

d) Los servicios continuados de mantenimiento del SGSI con posterioridad a la obtención del certificado, que serán objeto, en su caso, de un contrato de retainer separado (modelo C-003).

### SEGUNDA — DURACIÓN DEL CONTRATO

2.1. El presente contrato entrará en vigor en la fecha de su firma y tendrá una duración estimada de **{{ contrato.duracion_meses }} meses** desde el inicio efectivo de los trabajos, conforme al cronograma detallado en la Propuesta P-001.

2.2. La duración estimada podrá prorrogarse de mutuo acuerdo entre las Partes cuando concurran circunstancias objetivas que así lo justifiquen, en particular:

a) Retrasos imputables al Cliente en la entrega de información o en la disponibilidad de su personal.

b) Modificaciones sustanciales del alcance solicitadas por el Cliente.

c) Detección durante el diagnóstico de un nivel de madurez significativamente inferior al inicialmente declarado.

d) Causas de fuerza mayor.

2.3. Cualquier prórroga deberá formalizarse por escrito mediante adenda al presente contrato, especificando la nueva duración estimada y, en su caso, la modificación de los honorarios profesionales correspondiente.

### TERCERA — HONORARIOS PROFESIONALES Y CONDICIONES DE PAGO

3.1. **Honorarios.** El Cliente abonará al Consultor en concepto de honorarios profesionales la cantidad total de **{{ contrato.honorarios_eur }} euros más el IVA aplicable**, conforme al desglose y condiciones de la Propuesta P-001.

3.2. **Modalidad de facturación.** Los honorarios se facturarán siguiendo la modalidad de **{{ contrato.modalidad_pago }}** establecida en la sección 7.5 de la Propuesta P-001.

3.3. **Plazo de pago.** Las facturas emitidas por el Consultor se abonarán por transferencia bancaria a la cuenta que se indique en la propia factura, en el plazo máximo de **30 días naturales** desde la fecha de emisión.

3.4. **Demora en el pago.** El retraso en el pago de las facturas devengará automáticamente y sin necesidad de previo requerimiento los intereses de demora previstos en la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales.

3.5. **Suspensión de los servicios.** El Consultor podrá suspender la prestación de los servicios cuando el Cliente incurra en demora en el pago superior a 30 días naturales sobre el plazo establecido, previo aviso por escrito con cinco días hábiles de antelación. La suspensión no exime al Cliente de su obligación de pago de los servicios ya prestados.

3.6. **Trabajos adicionales.** Cualquier trabajo solicitado por el Cliente que exceda del alcance descrito en la Propuesta P-001 deberá ser objeto de presupuesto específico previamente aceptado por escrito antes de su ejecución. En ningún caso el Consultor estará obligado a realizar trabajos no incluidos en el alcance sin la correspondiente aceptación expresa.

### CUARTA — OBLIGACIONES DEL CONSULTOR

4.1. El Consultor se obliga a:

a) Prestar los servicios profesionales con la diligencia, profesionalidad y conocimientos técnicos exigibles a un consultor especializado en cumplimiento del Esquema Nacional de Seguridad, conforme a las buenas prácticas del sector.

b) Cumplir con el cronograma establecido en la Propuesta P-001, salvo causas justificadas o imputables al Cliente.

c) Comunicar al Cliente cualquier circunstancia que pudiera afectar al desarrollo normal del proyecto.

d) Mantener la confidencialidad de toda la información a la que acceda en el ejercicio de sus funciones, conforme a la cláusula séptima.

e) Aplicar las medidas de seguridad necesarias para proteger la información del Cliente que se encuentre bajo su custodia.

f) Suscribir y mantener vigente durante toda la duración del contrato un seguro de responsabilidad civil profesional con cobertura suficiente para los riesgos derivados de la prestación de los servicios.

g) Cumplir con sus obligaciones tributarias y de Seguridad Social, exonerando expresamente al Cliente de cualquier responsabilidad al respecto.

4.2. El Consultor presta sus servicios como **profesional autónomo independiente**, sin que del presente contrato pueda derivarse en ningún caso relación laboral ni de dependencia con el Cliente. El Consultor organiza libremente su tiempo y sus medios para el cumplimiento del objeto del contrato.

### QUINTA — OBLIGACIONES DEL CLIENTE

5.1. El Cliente se obliga a:

a) Facilitar al Consultor toda la información, documentación, accesos y recursos necesarios para la correcta prestación de los servicios, en los plazos que razonablemente se le soliciten.

b) Designar un **interlocutor único** con capacidad de decisión, que actuará como punto de contacto principal con el Consultor durante la duración del proyecto.

c) Garantizar la disponibilidad del personal del Cliente que deba intervenir en las distintas fases del proyecto, en particular en las reuniones de trabajo y entrevistas previstas.

d) Adoptar oportunamente las decisiones que correspondan a su ámbito de competencia para no obstaculizar el avance del proyecto.

e) Asumir directamente los costes de la auditoría externa de certificación, así como los de cualquier inversión técnica que resulte necesaria para el cumplimiento de las medidas del ENS.

f) Abonar los honorarios profesionales en los términos pactados.

5.2. Las decisiones que correspondan al Cliente en su ámbito propio de gobierno (aprobación de políticas, asignación de roles, autorización de excepciones, asunción de riesgos residuales, contratación de la entidad certificadora) son de su exclusiva responsabilidad. El Consultor proporcionará el asesoramiento técnico necesario, pero la decisión final corresponderá siempre al Cliente.

### SEXTA — INCOMPATIBILIDAD AUDITOR-CONSULTOR

6.1. Las Partes reconocen expresamente que, conforme a lo dispuesto en la norma **UNE-EN ISO/IEC 17065:2012**, en la guía **CCN-CERT IC-01/19** del Centro Criptológico Nacional y en los principios generales aplicables a las entidades de certificación acreditadas por ENAC, **existe una incompatibilidad estructural** entre las funciones de consultoría y las funciones de auditoría externa de certificación, en garantía de la imparcialidad y objetividad del proceso de certificación.

6.2. En consecuencia, el Consultor **no podrá**, ni durante la vigencia del presente contrato ni con posterioridad a su finalización, actuar como auditor externo de certificación del Cliente respecto del mismo sistema de información objeto del presente contrato. Queda expresamente excluida la posibilidad de que el Consultor preste servicios de certificación al Cliente.

6.3. La auditoría externa de certificación del sistema deberá ser contratada por el Cliente, de forma directa e independiente, con una entidad acreditada por ENAC y distinta del Consultor. El Consultor podrá facilitar al Cliente información orientativa sobre las entidades acreditadas, pero no actuará como intermediario en la contratación ni recibirá compensación alguna de las entidades certificadoras.

6.4. El Cliente reconoce haber sido informado de esta limitación con anterioridad a la firma del presente contrato y la acepta expresamente.

### SÉPTIMA — CONFIDENCIALIDAD

7.1. Las Partes se comprometen a mantener la más estricta confidencialidad sobre toda la información, datos, documentos, conocimientos técnicos, planes estratégicos, datos comerciales y cualquier otra información de carácter confidencial a la que accedan como consecuencia de la ejecución del presente contrato, así como a no utilizarla para fines distintos de los previstos en el mismo.

7.2. La obligación de confidencialidad subsistirá durante la vigencia del contrato y durante un período de **cinco (5) años** a contar desde su extinción, por cualquier causa.

7.3. La obligación de confidencialidad no se extenderá a la información que:

a) Sea o llegue a ser de dominio público sin culpa de la parte receptora.

b) Fuera ya conocida por la parte receptora antes de su recepción, debiendo poderlo acreditar fehacientemente.

c) Fuera obtenida lícitamente de un tercero sin obligación de confidencialidad.

d) Deba ser comunicada en cumplimiento de una obligación legal o de un requerimiento de autoridad competente, en cuyo caso la parte obligada lo notificará a la otra de forma previa siempre que sea legalmente posible.

7.4. El incumplimiento de esta cláusula será considerado incumplimiento esencial del contrato y dará derecho a la parte perjudicada a su resolución, sin perjuicio de la indemnización por daños y perjuicios que corresponda.

### OCTAVA — PROTECCIÓN DE DATOS PERSONALES

8.1. En la medida en que la prestación de los servicios objeto del presente contrato implique para el Consultor el acceso a datos personales de los que el Cliente sea responsable del tratamiento, el Consultor tendrá la condición de **encargado del tratamiento** conforme al artículo 28 del Reglamento (UE) 2016/679 (RGPD).

8.2. La regulación específica de la relación entre responsable y encargado del tratamiento se contiene en el **Anexo II** al presente contrato (Acuerdo de Encargo del Tratamiento), que las Partes suscriben como parte integrante e inseparable del contrato.

8.3. Sin perjuicio de lo anterior, el Consultor:

a) Tratará los datos personales del Cliente exclusivamente conforme a las instrucciones documentadas del Cliente.

b) Garantizará que las personas autorizadas a tratar los datos personales se han comprometido a respetar la confidencialidad.

c) Adoptará las medidas técnicas y organizativas apropiadas para garantizar un nivel de seguridad adecuado al riesgo.

d) No subcontratará a terceros el tratamiento sin la autorización previa por escrito del Cliente.

e) Asistirá al Cliente en la respuesta al ejercicio de los derechos de los interesados.

f) Notificará al Cliente, sin dilación indebida, cualquier violación de la seguridad de los datos personales.

g) A elección del Cliente, suprimirá o devolverá todos los datos personales una vez finalizada la prestación de los servicios.

### NOVENA — PROPIEDAD INTELECTUAL E INDUSTRIAL

9.1. **Plataforma FULKRO.** Las Partes reconocen expresamente que la plataforma FULKRO, su software, sus plantillas maestras, su metodología y, en general, todos los elementos que la componen, son propiedad exclusiva del Consultor. El presente contrato no transfiere al Cliente ningún derecho sobre la plataforma FULKRO ni sobre los elementos que la integran.

9.2. **Documentos generados específicamente para el Cliente.** Los documentos generados específicamente para el Cliente en el marco del presente contrato (políticas, procedimientos, instrucciones técnicas, informes, registros) son entregados al Cliente para su uso interno y operativo. El Cliente adquiere sobre dichos documentos un **derecho de uso perpetuo, no exclusivo y gratuito** para los fines internos de su organización, incluyendo el derecho a modificarlos, adaptarlos y conservarlos.

9.3. **Limitación.** El Cliente no podrá, sin consentimiento expreso y por escrito del Consultor:

a) Comercializar los documentos generados.
b) Cederlos a terceros para su uso comercial.
c) Utilizarlos como base para la prestación de servicios de consultoría a terceros.
d) Utilizarlos en perjuicio del prestigio o intereses legítimos del Consultor.

9.4. **Propiedad intelectual del Cliente.** El Consultor reconoce y respeta la propiedad intelectual e industrial del Cliente sobre la información y los activos a los que acceda en el ejercicio de sus funciones, sin que del presente contrato se derive cesión alguna de derechos sobre los mismos.

### DÉCIMA — LIMITACIÓN DE RESPONSABILIDAD

10.1. El Consultor responderá ante el Cliente por los daños directos que le cause como consecuencia del incumplimiento doloso o gravemente negligente de las obligaciones derivadas del presente contrato.

10.2. La responsabilidad total del Consultor frente al Cliente, por cualquier causa o concepto derivado del presente contrato, **no podrá exceder en ningún caso del importe total de los honorarios efectivamente percibidos** por el Consultor en el marco del mismo, salvo que la legislación aplicable establezca expresamente lo contrario.

10.3. El Consultor **no responderá en ningún caso** por:

a) Daños indirectos, lucro cesante, pérdida de oportunidades de negocio, daño reputacional, o daños consecuenciales de cualquier naturaleza.

b) Decisiones adoptadas por el Cliente en su ámbito propio de competencia, aun cuando hayan sido tomadas con asesoramiento del Consultor.

c) La no obtención del certificado de conformidad ENS por causas no imputables exclusivamente al Consultor, incluyendo, entre otras, decisiones discrecionales del auditor externo, cambios normativos sobrevenidos, deficiencias técnicas no subsanadas por el Cliente o falta de cooperación del Cliente.

d) Incidentes de seguridad o incumplimientos normativos del Cliente derivados de la actuación de su propio personal o de terceros ajenos al Consultor.

e) Daños causados por fuerza mayor, caso fortuito o acontecimientos extraordinarios fuera del control razonable del Consultor.

10.4. **Compromiso del Consultor.** No obstante lo anterior, el Consultor se compromete a aplicar todos sus conocimientos y diligencia profesional para alcanzar el objetivo del proyecto. Si por causas imputables exclusivamente al Consultor el Cliente no obtiene el certificado de conformidad ENS, el Consultor se compromete a continuar prestando los servicios necesarios para alcanzarlo, sin coste adicional, hasta su efectiva obtención o hasta la fecha en que el Cliente decida fundadamente abandonar el intento.

### UNDÉCIMA — RESOLUCIÓN DEL CONTRATO

11.1. El presente contrato podrá resolverse por las siguientes causas:

a) **Mutuo acuerdo** entre las Partes, formalizado por escrito.

b) **Cumplimiento del objeto** del contrato, con la entrega del Informe Final de Adecuación y el cierre del proyecto.

c) **Incumplimiento esencial** de las obligaciones contractuales por cualquiera de las Partes, previo requerimiento por escrito a la parte incumplidora otorgándole un plazo de quince (15) días hábiles para subsanar el incumplimiento.

d) **Demora en el pago** superior a 60 días sobre el plazo establecido, a instancia del Consultor.

e) **Imposibilidad sobrevenida** de cumplir con el objeto del contrato por causas de fuerza mayor.

f) **Concurso, liquidación o cese de actividad** de cualquiera de las Partes.

11.2. **Efectos de la resolución.** En caso de resolución anticipada del contrato:

a) El Consultor facturará al Cliente los servicios efectivamente prestados hasta la fecha de la resolución, conforme a las horas dedicadas y a la tarifa horaria pactada.

b) El Cliente abonará dichos servicios en el plazo establecido en la cláusula tercera.

c) El Consultor entregará al Cliente todos los entregables completados hasta la fecha de la resolución.

d) Subsistirán las obligaciones de confidencialidad, las relativas a la protección de datos personales y las de propiedad intelectual.

### DUODÉCIMA — NOTIFICACIONES

12.1. Cualquier comunicación entre las Partes derivada del presente contrato se realizará por escrito, dirigida a las direcciones indicadas en el encabezamiento o a las que las Partes designen en el futuro mediante notificación a la otra parte.

12.2. Se considerarán medios válidos de notificación:

a) El correo electrónico dirigido a las direcciones designadas, con confirmación de lectura.
b) El correo postal certificado con acuse de recibo.
c) Cualquier otro medio que deje constancia fehaciente de la recepción.

### DECIMOTERCERA — LEGISLACIÓN APLICABLE Y JURISDICCIÓN

13.1. El presente contrato se regirá e interpretará conforme a la legislación española.

13.2. Para la resolución de cualquier controversia derivada de la interpretación o ejecución del presente contrato, las Partes, con renuncia expresa a su propio fuero, se someten a la jurisdicción de los **Juzgados y Tribunales de la ciudad de Madrid**.

13.3. Sin perjuicio de lo anterior, las Partes podrán, si así lo acuerdan, someter las controversias a mediación previa ante un mediador profesional registrado en el Ministerio de Justicia.

### DECIMOCUARTA — INTEGRIDAD DEL ACUERDO

14.1. El presente contrato, junto con sus Anexos, constituye el acuerdo completo entre las Partes en relación con su objeto, sustituyendo cualquier acuerdo, propuesta, comunicación o entendimiento anterior, verbal o escrito.

14.2. Cualquier modificación del presente contrato deberá realizarse por escrito y firmada por ambas Partes para ser válida.

14.3. La nulidad de alguna de las cláusulas del presente contrato no afectará a la validez del resto, que continuarán siendo plenamente eficaces.

---

Y para que así conste, las Partes firman el presente contrato en dos ejemplares y a un solo efecto, en el lugar y fecha indicados al principio.

| Por FULKRO | Por {{ cliente.razon_social }} |
|---|---|
| | |
| Fdo.: D. Marcos Mata García | Fdo.: D./Dña. {{ cliente.firmante.nombre_completo }} |
| N.I.F.: {{ marcos.nif }} | Cargo: {{ cliente.firmante.cargo }} |

---

## ANEXOS AL CONTRATO

- **Anexo I:** Propuesta P-001 íntegra (incorporada por referencia)
- **Anexo II:** Acuerdo de Encargo del Tratamiento de Datos Personales (art. 28 RGPD)
- **Anexo III:** Definición detallada del alcance del proyecto
- **Anexo IV:** Cronograma detallado y matriz de hitos
{% if pricing_resumen %}- **Apéndice Económico:** Desglose económico detallado y plan de hitos de facturación
{% endif %}
{% if cliente.is_aapp %}- **Anexo A:** Cláusulas adicionales de contratación del Sector Público (Ley 9/2017 LCSP)
{% endif %}

{% if pricing_resumen %}
---

## APÉNDICE ECONÓMICO

Este apéndice detalla el desglose económico del presente contrato de conformidad con la Propuesta P-001 aceptada.

### 1. Importe total del contrato

| Concepto | Importe |
|----------|---------|
| Precio base categoría {{ pricing_resumen.categoria }} | {{ pricing_resumen.base | format_currency_es }} |
{% for extra in pricing_resumen.extras %}| {{ extra.description }} | +{{ extra.amount | format_currency_es }} |
{% endfor %}
{% if pricing_resumen.urgency_surcharge > 0 %}| Recargo por urgencia (+30% por plazo inferior a 6 semanas) | +{{ pricing_resumen.urgency_surcharge | format_currency_es }} |
{% endif %}
| **Subtotal** | **{{ pricing_resumen.subtotal | format_currency_es }}** |
{% if descuento_aplicado %}| Descuento aplicado: {{ descuento_aplicado.description }} | -{{ descuento_aplicado.amount | format_currency_es }} |
{% endif %}
| **TOTAL CONTRATO (IVA no incluido)** | **{{ pricing_resumen.total_neto | format_currency_es }}** |
| IVA 21 % | {{ pricing_resumen.iva_importe | format_currency_es }} |
| **TOTAL CON IVA** | **{{ pricing_resumen.total_con_iva | format_currency_es }}** |

### 2. Hitos de facturación

Los hitos de facturación se corresponden con entregables identificables del proyecto. El Consultor emitirá factura al completar cada hito previa aceptación del cliente o ausencia de objeción en el plazo acordado.

| Hito | Concepto | % | Importe |
|------|----------|---|---------|
{% for hito in hitos_apendice %}| {{ hito.codigo }} | {{ hito.descripcion }} | {{ hito.porcentaje_display }} % | {{ hito.importe | format_currency_es }} |
{% endfor %}
| **TOTAL** | | **100 %** | **{{ pricing_resumen.total_neto | format_currency_es }}** |

### 3. Garantía de servicio

{{ pricing_resumen.garantia }}

### 4. Condiciones de facturación

{% if cliente.is_aapp %}Conforme al régimen de contratación del Sector Público (Ley 9/2017 LCSP):

- **Plazo de pago:** 30 días naturales desde la conformidad de la factura electrónica (art. 198.4 LCSP), ampliable hasta 60 días según la disposición adicional 32 LCSP.
- **Formato de factura:** Facturae 3.2.x remitida a través de la plataforma FACe o del punto general de entrada de facturas electrónicas del organismo cliente.
- **Código DIR3:** a proporcionar por el cliente como parte de los datos de facturación.
{% else %}Régimen de contratación privada:

- **Plazo de pago:** 30 días naturales desde la emisión de la factura.
- **Método de pago preferente:** transferencia bancaria SEPA a la cuenta que se indicará en la factura.
- **Demora:** aplicable la Ley 3/2004 de lucha contra la morosidad en operaciones comerciales.
{% endif %}
{% endif %}
{% if cliente.is_aapp %}
---

## ANEXO A — CLÁUSULAS ADICIONALES DE CONTRATACIÓN DEL SECTOR PÚBLICO

Este contrato se suscribe al amparo de la **Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público** (LCSP), por transposición de las Directivas 2014/23/UE y 2014/24/UE, con las siguientes particularidades en atención a la condición de poder adjudicador del Cliente:

### A.1 Tipología contractual

{% if contrato.honorarios_eur and contrato.honorarios_eur|float < 15000 %}El presente contrato se califica como **contrato menor de servicios** conforme al artículo 118 LCSP (importe inferior a 15.000 euros sin IVA, plazo no superior a un año). Su tramitación se ajusta a lo dispuesto en dicho precepto.{% else %}El presente contrato se califica como **contrato de servicios** conforme al artículo 17 LCSP, objeto y cuantía determinados en la cláusula tercera.{% endif %}

### A.2 Plazo de pago y factura electrónica

1. El plazo de pago será de **treinta (30) días naturales** desde la fecha de aprobación de la conformidad de la factura electrónica, de acuerdo con el artículo 198.4 LCSP. Este plazo prevalece sobre el indicado en la cláusula tercera del cuerpo principal si resulta aplicable el régimen de contratación pública.
2. Excepcionalmente, el plazo podrá extenderse hasta **sesenta (60) días naturales** cuando concurran las circunstancias previstas en la **Disposición Adicional 32ª LCSP**, previa notificación por escrito al Consultor.
3. La facturación será **electrónica obligatoria** conforme a la **Ley 25/2013, de 27 de diciembre**, de impulso de la factura electrónica. El formato será **Facturae 3.2.x** y se presentará a través de **FACe** o del punto general de entrada de facturas electrónicas del organismo Cliente.

### A.3 Responsable del contrato

Conforme al artículo 62 LCSP, el Cliente designa como **responsable del contrato** a:

- Nombre: **{{ cliente.responsable_contrato.nombre | default('A designar por el Cliente en el acta de inicio') }}**
- Cargo: **{{ cliente.responsable_contrato.cargo | default('') }}**

El responsable del contrato supervisará la ejecución, propondrá certificaciones de conformidad y cursará las instrucciones necesarias para el correcto cumplimiento.

### A.4 Solvencia técnica y profesional

El Consultor acredita su solvencia técnica conforme al artículo 90 LCSP mediante las referencias de proyectos análogos ejecutados y la titulación y experiencia profesional. Se adjunta, a requerimiento del Cliente, el documento **E-046 Certificación de Solvencia Técnica** con el detalle correspondiente.

### A.5 Prohibición de subcontratación no autorizada

Conforme al artículo 215 LCSP, el Consultor **no subcontratará ningún servicio** objeto de este contrato sin autorización previa y por escrito del responsable del contrato. El Consultor responderá solidariamente con el subcontratista ante el Cliente cuando, previa autorización, exista subcontratación.

### A.6 Publicidad contractual

Este contrato y sus modificaciones, cuando corresponda, serán objeto de publicación en la **Plataforma de Contratación del Sector Público** conforme al artículo 63 LCSP. El Consultor consiente expresamente dicha publicación.

### A.7 Protección de datos — régimen reforzado AAPP

Cuando el Cliente sea Administración Pública sujeta al ENS (RD 311/2022), la cláusula octava del presente contrato se interpretará conjuntamente con la **Ley 40/2015 LRJSP** en lo relativo al régimen jurídico del tratamiento de datos por entidades del sector público y con el artículo 77 LOPDGDD (Tratamientos en el ámbito del sector público), en particular cuando el Cliente actúe como responsable y FULKRO como encargado.

### A.8 Régimen de recursos

Las cuestiones litigiosas derivadas del presente contrato, en tanto sea de aplicación la LCSP, podrán ser objeto del **recurso especial en materia de contratación** previsto en los artículos 44 y siguientes LCSP, cuando concurran los requisitos legales.

### A.9 Prevalencia normativa

En caso de conflicto entre una cláusula del cuerpo principal y una disposición imperativa de la LCSP u otra normativa de contratación pública aplicable al Cliente, **prevalecerá la norma imperativa sobre la cláusula contractual**, que se tendrá por no puesta o por modificada en la medida estrictamente necesaria para respetar la legalidad.
{% endif %}

```

---
