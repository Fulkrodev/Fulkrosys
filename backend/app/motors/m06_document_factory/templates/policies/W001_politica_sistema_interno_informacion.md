---
codigo_documento: "W-001"
titulo: "Política del Sistema Interno de Información (Canal de Denuncias)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_compliance.cargo if responsables.responsable_compliance and responsables.responsable_compliance.cargo else 'Responsable de Compliance' }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas if cliente.organo_aprobador_politicas else 'Órgano de gobierno' }}"
norma_aplicable: "Ley 2/2023, de 20 de febrero (transposición Directiva UE 2019/1937)"
---

# POLÍTICA DEL SISTEMA INTERNO DE INFORMACIÓN (CANAL DE DENUNCIAS) DE {{ cliente.razon_social | upper }}

**Documento W-001 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set num_empleados = cliente.numero_empleados if cliente.numero_empleados is defined else 0 %}
{% set obligacion_aplica = num_empleados >= 50 %}
{% set tramo_grande = num_empleados >= 250 %}
{% set responsable_sii_nombre = responsables.responsable_sii.nombre if responsables.responsable_sii and responsables.responsable_sii.nombre else '[A DESIGNAR]' %}
{% set responsable_sii_cargo = responsables.responsable_sii.cargo if responsables.responsable_sii and responsables.responsable_sii.cargo else 'Responsable del Sistema Interno de Información' %}
{% set responsable_sii_fecha = responsables.responsable_sii.fecha_designacion if responsables.responsable_sii and responsables.responsable_sii.fecha_designacion else '—' %}

## 1. OBJETO

La presente Política regula el **Sistema Interno de Información** de {{ cliente.razon_social }} (en adelante, "la Entidad"), conforme a las exigencias de la **Ley 2/2023, de 20 de febrero, reguladora de la protección de las personas que informen sobre infracciones normativas y de lucha contra la corrupción** (en adelante, "Ley 2/2023"), por la que se transpone al ordenamiento jurídico español la Directiva (UE) 2019/1937, del Parlamento Europeo y del Consejo, de 23 de octubre de 2019.

El Sistema Interno de Información (en adelante, "SII") constituye el cauce institucional preferente para la recepción, tramitación y resolución de las comunicaciones de información a las que se refiere el artículo 2 de la Ley 2/2023, y garantiza la protección de las personas informantes frente a posibles represalias.

## 2. MARCO NORMATIVO

- **Ley 2/2023**, de 20 de febrero · norma aplicable principal
- **Directiva (UE) 2019/1937** del Parlamento Europeo y del Consejo de 23 de octubre de 2019 · norma traspuesta
- **Reglamento (UE) 2016/679 (RGPD)** y **Ley Orgánica 3/2018 (LOPDGDD)** · tratamiento de datos personales asociado al SII
- **Estatuto de los Trabajadores** y normativa laboral aplicable · garantías al informante en el ámbito laboral
- Normativa interna de la Entidad: Código Ético · Política Disciplinaria · resto del cuerpo normativo del SGSI

## 3. ÁMBITO DE APLICACIÓN

### 3.1 Ámbito subjetivo

La presente Política se aplica a:

a) Personal con relación laboral o estatutaria con la Entidad, incluyendo empleo a tiempo completo, parcial, temporal, en prácticas y becarios.

b) Personal autónomo que preste servicios a la Entidad.

c) Accionistas y miembros de los órganos de administración, dirección o supervisión.

d) Personas que trabajen bajo la supervisión y dirección de contratistas, subcontratistas y proveedores.

e) Personas cuya relación laboral con la Entidad haya finalizado o que estén en proceso de selección.

f) Representantes legales de los trabajadores.

### 3.2 Ámbito material

Son susceptibles de comunicación a través del SII las acciones u omisiones que pudieran constituir:

a) Infracciones del Derecho de la Unión Europea, en los términos del artículo 2.1.a) y Anexo de la Directiva (UE) 2019/1937.

b) Acciones u omisiones que puedan ser constitutivas de infracción penal o administrativa grave o muy graves.

c) Cualquier infracción grave del marco normativo interno de la Entidad, incluyendo el Código Ético y las políticas que lo desarrollan.

### 3.3 Obligatoriedad del SII para la Entidad

{% if obligacion_aplica %}
La Entidad cuenta con **{{ num_empleados }} personas empleadas** y se halla por tanto **obligada** a disponer de un SII conforme al artículo 10 de la Ley 2/2023. {% if tramo_grande %}Al superar las 249 personas, la fecha límite de implantación fue el **1 de diciembre de 2023**.{% else %}Por hallarse en el tramo de 50 a 249 personas, la fecha límite de implantación fue el **17 de diciembre de 2023**.{% endif %}
{% else %}
La Entidad cuenta con **{{ num_empleados }} personas empleadas** y, en principio, no se halla obligada por el artículo 10 de la Ley 2/2023 a disponer de un SII. No obstante, la Entidad implanta el presente Sistema con carácter voluntario por compromiso ético, por exigencias contractuales con clientes y por su valor en el marco de su programa de cumplimiento.
{% endif %}

## 4. DEFINICIONES

A los efectos de la presente Política:

- **Informante:** persona física que comunica o revela públicamente información sobre infracciones obtenida en el contexto laboral o profesional.
- **Información sobre infracciones:** información, incluidas sospechas razonables, sobre infracciones reales o potenciales.
- **Sistema Interno de Información (SII):** conjunto de canales y procedimientos establecidos por la Entidad para la recepción y tratamiento de información sobre infracciones.
- **Canal interno de información:** medio dispuesto en el seno del SII para la recepción de comunicaciones.
- **Responsable del SII:** persona designada por el órgano de administración de la Entidad para la gestión del Sistema con las garantías de independencia y autonomía que exige la Ley 2/2023.
- **Comité del SII (cuando aplique):** órgano colegiado al que el Responsable puede acudir para la gestión de comunicaciones complejas.
- **Persona afectada:** persona física o jurídica a la que se refiere la información comunicada.
- **Represalia:** cualquier acto u omisión que pueda causar perjuicio injustificado al informante por su actividad informativa.

## 5. PRINCIPIOS DEL SII

El SII se rige por los siguientes principios, conforme al artículo 5 de la Ley 2/2023:

a) **Confidencialidad** de la identidad del informante, de las personas afectadas y de cualquier tercero mencionado, con las únicas excepciones legalmente previstas.

b) **Independencia** del Responsable del SII en el ejercicio de sus funciones.

c) **Accesibilidad** del canal interno a todas las personas comprendidas en el ámbito subjetivo.

d) **Protección efectiva** del informante frente a represalias.

e) **Trazabilidad** documental de todas las actuaciones, respetando el principio anterior.

f) **Independencia funcional** del Sistema respecto de las áreas funcionales objeto de las comunicaciones, evitando conflictos de interés.

g) **Proporcionalidad y mínima injerencia** en el tratamiento de datos personales, conforme al RGPD.

## 6. RESPONSABLE DEL SISTEMA INTERNO DE INFORMACIÓN

### 6.1 Designación

El órgano de administración de la Entidad designó a **{{ responsable_sii_nombre }}**, en su condición de **{{ responsable_sii_cargo }}**, como Responsable del SII, con efectos desde **{{ responsable_sii_fecha }}**.

La designación se ha comunicado a la Autoridad Independiente de Protección al Informante (AAI) en los términos legalmente previstos y se ha registrado en el Libro Registro de Designaciones del Responsable del SII de la Entidad.

### 6.2 Perfil e independencia

El Responsable del SII reúne las condiciones legales exigidas:

a) Es directivo o cargo de la Entidad.

b) Desempeña sus funciones de forma independiente y autónoma, sin recibir instrucciones de tipo alguno respecto del ejercicio de las mismas.

c) Cuenta con los recursos humanos y materiales necesarios para desarrollar adecuadamente sus funciones.

d) Tiene acceso directo al órgano de administración y rinde cuentas ante él periódicamente.

e) Su mandato tiene una duración no inferior a **tres (3) años**, prorrogable.

### 6.3 Funciones

Corresponde al Responsable del SII:

a) Recibir y tramitar las comunicaciones que lleguen al canal interno.

b) Garantizar la confidencialidad de la identidad del informante y de los datos del expediente.

c) Decidir motivadamente sobre la admisión o inadmisión a trámite de las comunicaciones.

d) Dirigir las actuaciones de investigación conforme al procedimiento W-002.

e) Adoptar o proponer las medidas correctivas que procedan.

f) Mantener comunicación con el informante en los términos previstos legalmente.

g) Coordinarse con otras unidades de la Entidad cuando proceda y con la Autoridad competente cuando legalmente sea exigible.

h) Elaborar y aprobar el informe anual de actividad del SII, que se eleva al órgano de administración.

i) Velar por la actualización de la presente Política y del procedimiento W-002.

## 7. CANALES DEL SII

### 7.1 Canal interno preferente

La Entidad dispone de un canal interno único de información, configurado con las garantías exigidas por la Ley 2/2023, accesible mediante las siguientes modalidades:

a) **Escrita electrónica:** a través del formulario seguro alojado en {% if cliente.canal_denuncias_url %}{{ cliente.canal_denuncias_url }}{% else %}[URL del canal a publicar internamente]{% endif %}, con cifrado en tránsito y separación lógica del resto de sistemas de la Entidad.

b) **Escrita postal:** mediante envío al apartado de correos específico habilitado al efecto, identificado en la nota informativa pública sobre el SII.

c) **Verbal:** mediante reunión presencial o por videoconferencia con el Responsable del SII, previa solicitud, levantándose acta de la sesión conforme al procedimiento W-002.

### 7.2 Anonimato

El canal interno admite **comunicaciones anónimas**, sin perjuicio de que la Entidad fomente la identificación voluntaria del informante para favorecer el desarrollo de las actuaciones de investigación, garantizando en todo caso la confidencialidad de su identidad.

### 7.3 Canal externo

Sin perjuicio del canal interno, el informante podrá optar libremente por dirigir su comunicación a la **Autoridad Independiente de Protección al Informante (AAI)** o a las autoridades autonómicas equivalentes, en los términos del Título III de la Ley 2/2023. La Entidad informa expresamente sobre esta posibilidad en la nota informativa pública sobre el SII.

## 8. GARANTÍAS AL INFORMANTE

### 8.1 Confidencialidad

La identidad del informante se mantendrá confidencial frente a toda persona ajena al procedimiento. Únicamente podrá ser revelada cuando exista obligación legal en el marco de una investigación judicial o procedimiento sancionador, en cuyo caso el informante será notificado previamente salvo que ello pueda comprometer la investigación.

### 8.2 Protección frente a represalias

Conforme a los artículos 36 a 41 de la Ley 2/2023, la Entidad **prohíbe expresamente** cualquier represalia contra el informante, incluyendo, con carácter no limitativo:

a) Despido, no renovación del contrato, suspensión o degradación.

b) Imposición de medidas disciplinarias o sanciones.

c) Modificación sustancial de las condiciones de trabajo.

d) Cualquier otro acto de carácter laboral, profesional o reputacional que pueda perjudicar al informante.

Las medidas adoptadas por la Entidad en perjuicio del informante en los **dos años siguientes** a la comunicación se presumirán represalia salvo prueba en contrario, conforme al artículo 38 de la Ley 2/2023.

### 8.3 Asistencia y apoyo

La Entidad facilitará al informante información sobre los recursos legales y de apoyo a su disposición, incluyendo la posibilidad de dirigirse a la AAI.

### 8.4 Tratamiento de datos personales

El tratamiento de datos personales asociado al SII se rige por el RGPD, la LOPDGDD y los artículos 30 a 35 de la Ley 2/2023. La base de licitimación del tratamiento es el cumplimiento de una obligación legal de la Entidad (artículo 6.1.c) RGPD). Los datos se conservarán únicamente durante el tiempo necesario para decidir sobre la procedencia de iniciar una investigación y, en su caso, durante el desarrollo de esta. La conservación máxima en el sistema es de **diez (10) años** desde la finalización de la investigación, salvo que sea necesario un plazo superior para acreditar el funcionamiento del Sistema ante autoridades competentes.

## 9. RÉGIMEN DISCIPLINARIO Y SANCIONADOR INTERNO

### 9.1 Por incumplimiento del informante

La presentación deliberada de comunicaciones manifiestamente falsas constituirá infracción grave en el marco interno de la Entidad y podrá ser sancionada conforme a la normativa laboral aplicable, sin perjuicio de las responsabilidades civiles, penales o administrativas que pudieran derivarse para el informante.

### 9.2 Por incumplimiento de la prohibición de represalias

La adopción de represalias contra el informante constituirá infracción **muy grave** en el marco interno de la Entidad, sin perjuicio del régimen sancionador establecido en el Título VIII de la Ley 2/2023 que la Autoridad competente pueda imponer.

### 9.3 Recordatorio del régimen sancionador externo (Ley 2/2023)

La Ley 2/2023 contempla un régimen sancionador propio, gestionado por la AAI, con sanciones para las personas físicas y jurídicas que incurran en infracciones del régimen de protección al informante, cuyas cuantías pueden alcanzar hasta **un millón (1.000.000) de euros** en el caso de infracciones muy graves cometidas por personas jurídicas.

## 10. APROBACIÓN, REVISIÓN Y VIGENCIA

La presente Política ha sido aprobada por {{ cliente.organo_aprobador_politicas if cliente.organo_aprobador_politicas else 'el órgano de administración de la Entidad' }} el {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha]' }}.

Será objeto de revisión **al menos cada dos (2) años**, así como cuando se produzcan cambios normativos relevantes o cambios materiales en la organización que afecten al funcionamiento del SII.

---

**Documento W-001 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}*
