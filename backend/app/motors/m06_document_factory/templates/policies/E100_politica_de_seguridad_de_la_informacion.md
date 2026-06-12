# DOCUMENTO E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN

**Es la política madre.** Sin ella aprobada y firmada por el órgano superior, no hay SGSI ENS posible. Es el primer documento que pide cualquier auditor ENAC y el primero que mira la guía CCN-STIC 805. Esta versión está alineada con el artículo 12 del RD 311/2022 (Política de seguridad y requisitos mínimos) y con CCN-STIC 805 v2025.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-100"
titulo: "Política de Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }}**

---

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción del cambio | Aprobado por |
|---|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.responsable_seguridad.nombre }} | Versión inicial. Aprobación primera del SGSI conforme al RD 311/2022. | {{ cliente.organo_aprobador_politicas }} |

## REGISTRO DE APROBACIÓN

La presente Política de Seguridad de la Información ha sido elaborada por {{ responsables.responsable_seguridad.nombre }}, en su condición de {{ responsables.responsable_seguridad.cargo }} de {{ cliente.razon_social }}, revisada por el Comité de Seguridad de la Información de la entidad y aprobada formalmente por {{ cliente.organo_aprobador_politicas }} en la sesión celebrada el {{ proyecto.fecha_aprobacion_inicial }}.

| Rol | Nombre | Cargo | Firma | Fecha |
|---|---|---|---|---|
| Elaboración | {{ responsables.responsable_seguridad.nombre }} | {{ responsables.responsable_seguridad.cargo }} | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |
| Revisión | {{ responsables.comite_seguridad.presidente }} | Presidente Comité de Seguridad | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |
| Aprobación | _En representación del_ {{ cliente.organo_aprobador_politicas }} | _____________ | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |

---

## 1. INTRODUCCIÓN Y DECLARACIÓN INSTITUCIONAL

{{ cliente.razon_social }}, con NIF {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }} (en adelante, **"la Entidad"**), consciente de su dependencia de los sistemas y servicios de información para el desarrollo de sus actividades, y comprometida con la protección efectiva de los datos personales, la información corporativa y los servicios prestados a sus partes interesadas, mediante la presente Política manifiesta su compromiso firme e inequívoco con la seguridad de la información.

La seguridad de la información, entendida como la preservación de la confidencialidad, la integridad, la disponibilidad, la autenticidad y la trazabilidad de la información tratada y de los servicios prestados por sus sistemas, constituye un objetivo estratégico de la Entidad y forma parte integral de su modelo de gobernanza.

A tal efecto, la Entidad adopta esta Política como norma fundamental de su Sistema de Gestión de la Seguridad de la Información (en adelante, **"SGSI"**), conformado conforme a lo dispuesto en el Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (en adelante, **"ENS"**), y, supletoriamente, conforme a las buenas prácticas reconocidas internacionalmente, en particular las recogidas en la norma UNE-EN ISO/IEC 27001:2022.

## 2. OBJETO Y FINALIDAD

La presente Política tiene por objeto establecer el marco general de gobernanza, principios, objetivos y responsabilidades en materia de seguridad de la información en {{ cliente.razon_social }}, garantizando que:

a) La información y los servicios prestados estén protegidos frente a amenazas internas o externas, deliberadas o accidentales, que puedan comprometer su confidencialidad, integridad, disponibilidad, autenticidad o trazabilidad.

b) El cumplimiento de las obligaciones legales, reglamentarias y contractuales aplicables a la Entidad en materia de protección de la información, en particular las derivadas del Real Decreto 311/2022, del Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales y a la libre circulación de estos datos (Reglamento General de Protección de Datos, en adelante "RGPD"), y de la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales (en adelante "LOPDGDD"), entre otras normas aplicables.

c) Los riesgos a los que está expuesta la información se identifiquen, valoren, traten y supervisen de forma sistemática y continua.

d) Existan los recursos humanos, organizativos, técnicos y financieros suficientes para implantar y mantener las medidas de seguridad necesarias.

e) Toda persona, interna o externa, que acceda a los sistemas o a la información de la Entidad conozca sus obligaciones y responsabilidades en materia de seguridad y actúe en consecuencia.

## 3. ÁMBITO DE APLICACIÓN

### 3.1 Ámbito subjetivo

La presente Política es de obligado cumplimiento para:

a) Todo el personal de {{ cliente.razon_social }}, con independencia de su régimen jurídico de relación laboral o funcionarial, su categoría profesional, su antigüedad o su modalidad de contratación, incluyendo personal directivo, técnico, administrativo, becarios y personal en prácticas.

b) Las personas físicas o jurídicas que, en virtud de cualquier relación contractual, presten servicios a la Entidad o accedan a sus sistemas de información o a información por ella tratada, incluyendo proveedores, contratistas, subcontratistas y consultores externos.

c) Cualquier tercero que, de forma puntual o continuada, acceda a los recursos de información de la Entidad, debiendo en tal caso suscribir los compromisos de confidencialidad que correspondan.

### 3.2 Ámbito objetivo

Esta Política se aplica a la totalidad de los activos de información titularidad de la Entidad o sobre los que ejerza responsabilidad, incluyendo, con carácter no limitativo:

a) La información en cualquier formato (electrónico, impreso, audiovisual u otros) y en cualquier estado (en tránsito, en uso o almacenada).

b) Los sistemas de información que dan soporte a los servicios y procesos de la Entidad.

c) Las infraestructuras tecnológicas, redes, equipos, dispositivos, software y servicios cloud que componen el entorno tecnológico de la Entidad.

d) Las instalaciones físicas que albergan los activos anteriores.

e) El personal y los procesos vinculados a la operación, mantenimiento, supervisión y mejora de todo lo anterior.

### 3.3 Alcance específico para la conformidad con el ENS

A los efectos de la conformidad con el Real Decreto 311/2022, el alcance del Sistema de Gestión de la Seguridad de la Información comprende:

> **{{ proyecto.alcance.descripcion }}**

Los servicios incluidos en este alcance son: {{ proyecto.alcance.servicios_incluidos | join(", ") }}.

{% if proyecto.alcance.exclusiones %}
**Exclusiones expresas:** {{ proyecto.alcance.exclusiones }}
{% endif %}

La categoría de seguridad asignada al sistema, conforme al procedimiento descrito en el Anexo I del ENS y en la guía CCN-STIC 803, es **{{ proyecto.categoria_ens }}**.

## 4. MARCO NORMATIVO DE REFERENCIA

La presente Política se fundamenta y ha de interpretarse en el marco de las siguientes disposiciones, en su versión vigente en cada momento, así como en cuantas otras le resulten de aplicación:

### 4.1 Normativa nacional

a) Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad.

b) Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales.

c) Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las Administraciones Públicas.

d) Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público.

e) Resolución de 13 de octubre de 2016, de la Secretaría de Estado de Administraciones Públicas, por la que se aprueba la Instrucción Técnica de Seguridad de conformidad con el Esquema Nacional de Seguridad (BOE-A-2016-10109).

f) Resolución de 13 de octubre de 2016, de la Secretaría de Estado de Administraciones Públicas, por la que se aprueba la Instrucción Técnica de Seguridad de Informe del Estado de la Seguridad (BOE-A-2016-10108).

g) Resolución de 27 de marzo de 2018, de la Secretaría de Estado de Función Pública, por la que se aprueba la Instrucción Técnica de Seguridad de Auditoría de la Seguridad de los Sistemas de Información (BOE-A-2018-4573).

h) Resolución de 13 de abril de 2018, de la Secretaría de Estado de Función Pública, por la que se aprueba la Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad (BOE-A-2018-5370).

### 4.2 Normativa europea

a) Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD).

b) Directiva (UE) 2022/2555 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, relativa a las medidas destinadas a garantizar un elevado nivel común de ciberseguridad en toda la Unión (NIS2).

c) Reglamento (UE) 910/2014 del Parlamento Europeo y del Consejo, de 23 de julio de 2014, relativo a la identificación electrónica y los servicios de confianza para las transacciones electrónicas en el mercado interior (eIDAS).

{% if cliente.sector_actividad in ["fintech", "servicios financieros", "banca", "seguros"] %}
d) Reglamento (UE) 2022/2554 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, sobre la resiliencia operativa digital del sector financiero (DORA).
{% endif %}

### 4.3 Estándares y guías técnicas de referencia

a) Norma UNE-EN ISO/IEC 27001:2022 — Sistemas de Gestión de la Seguridad de la Información — Requisitos.

b) Norma UNE-EN ISO/IEC 27002:2022 — Controles de seguridad de la información.

c) Serie de guías CCN-STIC 800 emitidas por el Centro Criptológico Nacional, y en particular:

- CCN-STIC 800 — Glosario de términos y abreviaturas del ENS.
- CCN-STIC 802 — Guía de auditoría del ENS.
- CCN-STIC 803 — Valoración de los sistemas en el ENS.
- CCN-STIC 805 — Política de Seguridad de la Información.
- CCN-STIC 806 — Plan de Adecuación al ENS.
- CCN-STIC 808 — Verificación del cumplimiento del ENS.

d) Metodología MAGERIT versión 3 — Metodología de Análisis y Gestión de Riesgos de los Sistemas de Información, del Consejo Superior de Administración Electrónica.

## 5. PRINCIPIOS BÁSICOS DE LA SEGURIDAD DE LA INFORMACIÓN

De conformidad con el artículo 5 del ENS, la presente Política y el SGSI de la Entidad se rigen por los siguientes principios básicos:

**5.1. Seguridad como proceso integral.** La seguridad se entiende como un proceso continuo que abarca todos los elementos humanos, materiales, técnicos, jurídicos y organizativos relacionados con el sistema, y no como un estado puntual ni como una mera implementación tecnológica.

**5.2. Gestión de la seguridad basada en los riesgos.** El análisis y la gestión de los riesgos constituyen una parte esencial del proceso de seguridad. La Entidad mantendrá un proceso de análisis y gestión de riesgos continuo y proporcional a la naturaleza y categoría del sistema, conforme a la metodología MAGERIT.

**5.3. Prevención, detección, respuesta y conservación.** La Entidad implantará medidas que eviten razonablemente la materialización de las amenazas, detecten los incidentes con prontitud, permitan responder de forma eficaz y conserven la información necesaria para su análisis posterior.

**5.4. Existencia de líneas de defensa.** El sistema dispondrá de una estrategia de protección constituida por múltiples capas de seguridad, dispuestas de modo que, cuando una de ellas falle, otras permitan ganar tiempo para una reacción adecuada y reducir la probabilidad de que el sistema se vea comprometido en su conjunto.

**5.5. Vigilancia continua y reevaluación periódica.** La Entidad establecerá mecanismos de vigilancia continua que permitan detectar cualquier actividad anómala y reaccionar ante ella, así como mecanismos de reevaluación periódica que permitan adaptar la estrategia de seguridad a las nuevas circunstancias.

**5.6. Diferenciación de responsabilidades.** Las funciones y responsabilidades en materia de seguridad estarán claramente diferenciadas entre el responsable de la información, el responsable del servicio, el responsable de la seguridad y el responsable del sistema, conforme se establece en el Anexo de Roles del presente documento (Roles, Responsabilidades y Autoridades de Seguridad).

## 6. REQUISITOS MÍNIMOS DE SEGURIDAD

En cumplimiento de los requisitos mínimos establecidos en el artículo 12 y siguientes del ENS, la Entidad garantizará el cumplimiento, al menos, de los siguientes requisitos:

a) **Organización e implantación del proceso de seguridad**, mediante la formalización del Comité de Seguridad y la designación de los roles definidos en el Anexo de Roles del presente documento.

b) **Análisis y gestión de los riesgos**, mediante la aplicación sistemática de la metodología MAGERIT v3 y la elaboración del correspondiente Análisis de Riesgos, que se revisará al menos con carácter anual y siempre que se produzcan cambios significativos en el sistema.

c) **Gestión de personal**, asegurando que todas las personas con acceso al sistema conozcan sus responsabilidades en materia de seguridad y reciban la formación y concienciación adecuadas.

d) **Profesionalidad**, garantizando que los responsables del sistema cuentan con la capacitación técnica y la experiencia necesarias.

e) **Autorización y control de los accesos**, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-101 (Política de Control de Acceso).

f) **Protección de las instalaciones**, mediante medidas físicas y ambientales proporcionales al riesgo identificado.

g) **Adquisición de productos y servicios de seguridad**, atendiendo, cuando proceda, a las disposiciones del Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y la Comunicación (CPSTIC) del Centro Criptológico Nacional.

h) **Mínimo privilegio**, otorgando a cada usuario únicamente los derechos de acceso estrictamente necesarios para el desempeño de sus funciones.

i) **Integridad y actualización del sistema**, manteniendo el inventario de activos actualizado y aplicando un proceso formal de gestión de cambios y de actualizaciones de seguridad.

j) **Protección de la información almacenada y en tránsito**, mediante el uso de mecanismos criptográficos adecuados al nivel de seguridad exigible.

k) **Prevención ante otros sistemas de información interconectados**, mediante el establecimiento de los controles de interconexión necesarios.

l) **Registro de la actividad y detección de código dañino**, garantizando la trazabilidad de las acciones y la protección frente a software malicioso.

m) **Incidentes de seguridad**, mediante la implantación del proceso descrito en el documento {{ proyecto.codigo_documento_base }}-108 (Política de Gestión de Incidentes de Seguridad).

n) **Continuidad de la actividad**, mediante el plan descrito en el documento {{ proyecto.codigo_documento_base }}-109 (Política de Continuidad del Servicio).

o) **Mejora continua del proceso de seguridad**, mediante el ciclo PDCA aplicado al SGSI y la revisión periódica de la presente Política.

## 7. ESTRUCTURA ORGANIZATIVA DE LA SEGURIDAD

### 7.1 Comité de Seguridad de la Información

La Entidad constituye un Comité de Seguridad de la Información, en adelante "el Comité", como órgano colegiado responsable del seguimiento, supervisión y coordinación del SGSI.

El Comité estará presidido por {{ responsables.comite_seguridad.presidente }}, y estará integrado por las siguientes personas o por quienes en cada momento ocupen los cargos indicados:

{% for miembro in responsables.comite_seguridad.miembros %}
- {{ miembro }}
{% endfor %}

Actuará como secretario del Comité {{ responsables.comite_seguridad.secretario }}, quien levantará acta de las sesiones celebradas. El Comité se reunirá con carácter ordinario {{ responsables.comite_seguridad.frecuencia_reuniones }} y, con carácter extraordinario, cuando sea convocado por su presidente o lo soliciten al menos dos de sus miembros.

Son funciones del Comité, entre otras:

a) Aprobar las directrices generales en materia de seguridad de la información y elevar al órgano superior las propuestas de modificación de la presente Política.

b) Coordinar la elaboración, revisión y actualización de la normativa interna de seguridad.

c) Revisar el resultado del análisis de riesgos y aprobar el plan de tratamiento.

d) Supervisar la implantación de las medidas de seguridad.

e) Analizar los incidentes de seguridad relevantes y velar por la adopción de medidas correctivas.

f) Conocer los resultados de las auditorías internas y externas y velar por la subsanación de las no conformidades detectadas.

g) Informar al órgano superior sobre el estado del SGSI con la periodicidad que se determine.

### 7.2 Roles operativos

La estructura operativa de la seguridad descansa sobre los cuatro roles previstos en el artículo 11 del ENS, cuyo nombramiento, funciones y responsabilidades se desarrollan en el Anexo de Roles del presente documento.

| Rol | Persona designada | Cargo |
|---|---|---|
| Responsable de la Información | {{ responsables.responsable_informacion.nombre }} | {{ responsables.responsable_informacion.cargo }} |
| Responsable del Servicio | {{ responsables.responsable_servicio.nombre }} | {{ responsables.responsable_servicio.cargo }} |
| Responsable de la Seguridad | {{ responsables.responsable_seguridad.nombre }} | {{ responsables.responsable_seguridad.cargo }} |
| Responsable del Sistema | {{ responsables.responsable_sistema.nombre }} | {{ responsables.responsable_sistema.cargo }} |

## 8. GESTIÓN DE LOS DATOS PERSONALES

Cuando los sistemas de información de la Entidad traten datos de carácter personal, se aplicarán las medidas de seguridad correspondientes al RGPD y a la LOPDGDD, de modo coordinado con las medidas del presente SGSI, conforme a lo dispuesto en el artículo 3 del ENS y en el documento {{ proyecto.codigo_documento_base }}-105 (Política de Privacidad y Protección de Datos Personales).

La interlocución con la Agencia Española de Protección de Datos, así como las funciones propias del Delegado de Protección de Datos cuando este exista, corresponderán a {{ responsables.delegado_proteccion_datos.nombre }}, en su condición de {{ responsables.delegado_proteccion_datos.cargo }}.

## 9. GESTIÓN DE EXCEPCIONES

Excepcionalmente, y siempre por causa debidamente justificada, podrá autorizarse el incumplimiento temporal o parcial de alguno de los requisitos establecidos en la normativa interna de seguridad. Toda excepción habrá de:

a) Estar formalmente documentada y motivada.

b) Identificar el riesgo asumido y, en su caso, las medidas compensatorias adoptadas.

c) Ser autorizada por escrito por el Responsable de la Seguridad, previo informe favorable, cuando el riesgo asumido sea significativo, del Comité de Seguridad.

d) Tener una vigencia temporal definida, no superior a doce meses, susceptible de prórroga motivada.

e) Quedar registrada en el correspondiente Registro de Excepciones, gestionado por el Responsable de la Seguridad.

## 10. INCUMPLIMIENTO

El incumplimiento de la presente Política o de la normativa interna de seguridad que de ella se deriva podrá dar lugar a la apertura del correspondiente expediente disciplinario, conforme a lo previsto en la legislación laboral o administrativa aplicable y en el régimen disciplinario interno de la Entidad, sin perjuicio de las responsabilidades civiles, administrativas o penales en las que pudiera incurrirse.

En el caso de personal externo, el incumplimiento podrá dar lugar a la resolución del contrato y a la exigencia de las responsabilidades contractuales que correspondan.

## 11. COMUNICACIÓN, FORMACIÓN Y CONCIENCIACIÓN

La Entidad garantizará que la presente Política y la normativa interna de seguridad sean comunicadas, conocidas y comprendidas por todo el personal afectado por su ámbito de aplicación.

A tal efecto:

a) La Política será publicada en la intranet corporativa y, en su caso, en la sede electrónica de la Entidad.

b) Se notificará individualmente al personal de nueva incorporación durante el proceso de acogida, requiriéndose su acuse de recibo.

c) Se desarrollará un plan anual de formación y concienciación en seguridad de la información, dirigido a todo el personal según el rol que desempeñe.

d) Se realizarán acciones específicas de concienciación tras la notificación de incidentes relevantes o la actualización significativa de la normativa interna.

## 12. REVISIÓN Y ACTUALIZACIÓN

La presente Política será revisada con carácter ordinario al menos una vez al año, y con carácter extraordinario cuando concurra alguna de las siguientes circunstancias:

a) Modificaciones significativas en la normativa legal o reglamentaria aplicable.

b) Cambios sustanciales en la estructura organizativa, en los servicios prestados o en los sistemas de información de la Entidad.

c) Resultados del análisis de riesgos que evidencien la insuficiencia de los principios o requisitos establecidos.

d) Incidentes de seguridad de impacto significativo cuyo análisis aconseje su revisión.

e) Conclusiones de auditorías internas o externas que así lo recomienden.

Las modificaciones serán propuestas por el Responsable de la Seguridad, revisadas por el Comité de Seguridad y aprobadas por {{ cliente.organo_aprobador_politicas }}.

La próxima revisión ordinaria está prevista para el {{ proyecto.proxima_revision }}.

## 13. ENTRADA EN VIGOR

La presente Política entrará en vigor el día siguiente al de su aprobación por {{ cliente.organo_aprobador_politicas }}, esto es, el día siguiente al {{ proyecto.fecha_aprobacion_inicial }}, y permanecerá vigente hasta su derogación, modificación o sustitución por una versión posterior debidamente aprobada.

---

**Aprobado por {{ cliente.organo_aprobador_politicas }}** en sesión celebrada el {{ proyecto.fecha_aprobacion_inicial }}.

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

---

# ROLES, RESPONSABILIDADES Y AUTORIDADES DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 · Anexo de Roles — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento desarrolla y concreta lo dispuesto en el apartado 7 de la Política de Seguridad de la Información ({{ proyecto.codigo_documento_base }}-100), estableciendo de forma detallada los roles, responsabilidades y autoridades en materia de seguridad de la información de {{ cliente.razon_social }}, así como los procedimientos para su designación, sustitución y rendición de cuentas.

Su objetivo es garantizar la separación de funciones exigida por el artículo 11 del Real Decreto 311/2022, asegurando que ninguna persona acumule responsabilidades incompatibles entre sí, especialmente en lo relativo a la operación del sistema, la decisión sobre los riesgos asumidos y la verificación independiente del cumplimiento.

## 2. ÁMBITO DE APLICACIÓN

El presente documento es de aplicación a todas las personas que desempeñen, con carácter formal o funcional, cualquiera de los roles de seguridad descritos, así como a quienes les apoyen o sustituyan en sus funciones.

## 3. PRINCIPIOS DE LA ESTRUCTURA DE ROLES

### 3.1 Diferenciación de responsabilidades

De conformidad con el artículo 11 del ENS, en los sistemas de información en el ámbito de aplicación del Esquema Nacional de Seguridad se diferenciará al **responsable de la información**, al **responsable del servicio**, al **responsable de la seguridad** y al **responsable del sistema**.

Estos cuatro roles son **incompatibles entre sí**, en el sentido de que ninguna persona podrá acumular simultáneamente más de uno de ellos, salvo en aquellos casos excepcionales en los que la dimensión y complejidad de la Entidad lo justifiquen y se hayan adoptado las medidas compensatorias necesarias para garantizar la objetividad de las decisiones.

{% if (cliente.numero_empleados | default(50, true)) < 50 %}
**Nota sobre dimensión de la Entidad:** dado que {{ cliente.razon_social }} cuenta con {{ cliente.numero_empleados }} empleados, la separación estricta de los cuatro roles podría exigir la asunción excepcional de más de un rol por la misma persona. En tal caso se aplicará el régimen excepcional descrito en el apartado 4.6.
{% endif %}

### 3.2 Independencia del responsable de la seguridad

El Responsable de la Seguridad será **funcionalmente independiente** del Responsable del Sistema, evitando que el responsable de operar y mantener el sistema sea, a su vez, el encargado de verificar su seguridad. Esta independencia funcional es condición necesaria para la objetividad del SGSI.

### 3.3 Cadena de autoridad

La autoridad última en materia de seguridad de la información reside en {{ cliente.organo_aprobador_politicas }}, quien delega su ejercicio operativo en el Comité de Seguridad de la Información y, a través de él, en el Responsable de la Seguridad.

## 4. ROLES DE SEGURIDAD

### 4.1 Responsable de la Información

**4.1.1 Definición.** El Responsable de la Información es la persona que determina los requisitos de la información tratada, atendiendo a su sensibilidad, importancia y necesidades de protección.

**4.1.2 Designación.** A los efectos del SGSI, se designa como Responsable de la Información a {{ responsables.responsable_informacion.nombre }}, en su condición de {{ responsables.responsable_informacion.cargo }}, con dirección de correo electrónico {{ responsables.responsable_informacion.email }}.

**4.1.3 Funciones y responsabilidades.** Son funciones específicas del Responsable de la Información:

a) Establecer los requisitos de seguridad aplicables a la información, teniendo en cuenta su naturaleza, las obligaciones legales, las expectativas de las partes interesadas y los riesgos asociados.

b) Determinar y aprobar la valoración de la información en las dimensiones de confidencialidad, integridad, autenticidad y trazabilidad, conforme a los criterios del Anexo I del ENS y de la guía CCN-STIC 803.

c) Aprobar las normas y procedimientos relativos al ciclo de vida de la información (creación, clasificación, etiquetado, uso, conservación, transferencia, eliminación).

d) Autorizar los flujos de información hacia el exterior de la Entidad o hacia sistemas distintos de los originalmente autorizados.

e) Conocer y aceptar los riesgos residuales relativos a la información.

f) Recibir información periódica sobre los incidentes que afecten a la información de su responsabilidad.

### 4.2 Responsable del Servicio

**4.2.1 Definición.** El Responsable del Servicio es la persona que determina los requisitos de los servicios prestados por el sistema de información, en particular en cuanto a su disponibilidad y calidad de servicio.

**4.2.2 Designación.** Se designa como Responsable del Servicio a {{ responsables.responsable_servicio.nombre }}, en su condición de {{ responsables.responsable_servicio.cargo }}, con dirección de correo electrónico {{ responsables.responsable_servicio.email }}.

**4.2.3 Funciones y responsabilidades.**

a) Establecer los requisitos de seguridad aplicables a los servicios, atendiendo a su criticidad y a las expectativas de las partes interesadas.

b) Determinar y aprobar la valoración del servicio en la dimensión de disponibilidad, conforme a los criterios del Anexo I del ENS.

c) Definir los acuerdos de nivel de servicio (SLA) aplicables y velar por su cumplimiento.

d) Aprobar los planes de continuidad del servicio y los objetivos de tiempo y punto de recuperación (RTO/RPO).

e) Conocer y aceptar los riesgos residuales relativos a la disponibilidad del servicio.

f) Recibir información periódica sobre los incidentes que afecten a los servicios de su responsabilidad.

### 4.3 Responsable de la Seguridad

**4.3.1 Definición.** El Responsable de la Seguridad es la persona encargada de definir, mantener y supervisar la implantación del SGSI de la Entidad, así como de garantizar el cumplimiento de la normativa de seguridad de la información aplicable.

**4.3.2 Designación.** Se designa como Responsable de la Seguridad a {{ responsables.responsable_seguridad.nombre }}, en su condición de {{ responsables.responsable_seguridad.cargo }}, con dirección de correo electrónico {{ responsables.responsable_seguridad.email }}.

El Responsable de la Seguridad reporta directamente a {{ cliente.organo_aprobador_politicas }} y dispone de acceso directo al órgano de gobierno superior de la Entidad para todas aquellas cuestiones relacionadas con la seguridad de la información que requieran su atención.

**4.3.3 Funciones y responsabilidades.**

a) Elaborar y mantener actualizada la normativa interna de seguridad, así como proponer su aprobación al Comité de Seguridad.

b) Coordinar el análisis y la gestión de riesgos del sistema, conforme a la metodología MAGERIT v3.

c) Elaborar y mantener actualizada la Declaración de Aplicabilidad y el Plan de Adecuación al ENS.

d) Definir los requisitos de seguridad aplicables a los productos, servicios y proveedores que intervienen en el sistema.

e) Supervisar la implantación de las medidas de seguridad y verificar su eficacia.

f) Coordinar la respuesta ante los incidentes de seguridad y, en particular, ejercer las funciones de interlocución con el CCN-CERT a través de la herramienta LUCIA, cuando proceda conforme a la Instrucción Técnica de Seguridad de Notificación de Incidentes (BOE-A-2018-5370).

g) Promover y supervisar las actividades de formación y concienciación en seguridad.

h) Coordinar las auditorías internas de seguridad y supervisar la subsanación de las no conformidades detectadas en las auditorías externas.

i) Reportar al Comité de Seguridad y, a través de él, a {{ cliente.organo_aprobador_politicas }}, sobre el estado del SGSI con la periodicidad que se establezca, y en todo caso al menos una vez al año.

j) Mantener una posición funcionalmente independiente del Responsable del Sistema, evitando cualquier conflicto de interés en el ejercicio de sus funciones.

**4.3.4 Capacitación.** El Responsable de la Seguridad deberá acreditar formación específica en seguridad de la información y, deseablemente, certificaciones profesionales reconocidas internacionalmente (CISA, CISM, CISSP, ISO 27001 Lead Implementer, ISO 27001 Lead Auditor, o equivalentes).

### 4.4 Responsable del Sistema

**4.4.1 Definición.** El Responsable del Sistema es la persona encargada de la operación, mantenimiento y disponibilidad técnica del sistema de información, así como de la implantación de las medidas técnicas de seguridad bajo la supervisión del Responsable de la Seguridad.

**4.4.2 Designación.** Se designa como Responsable del Sistema a {{ responsables.responsable_sistema.nombre }}, en su condición de {{ responsables.responsable_sistema.cargo }}, con dirección de correo electrónico {{ responsables.responsable_sistema.email }}.

**4.4.3 Funciones y responsabilidades.**

a) Garantizar el correcto funcionamiento del sistema de información en condiciones de seguridad.

b) Implantar y operar las medidas de seguridad técnicas determinadas en el Plan de Adecuación y en la Declaración de Aplicabilidad.

c) Mantener actualizado el inventario de activos del sistema.

d) Aplicar las normas y procedimientos operativos de seguridad y supervisar su cumplimiento por el personal técnico bajo su responsabilidad.

e) Coordinar la gestión de cambios y de actualizaciones de seguridad del sistema.

f) Detectar y notificar al Responsable de la Seguridad los incidentes de seguridad de los que tenga conocimiento.

g) Facilitar al Responsable de la Seguridad y a los auditores internos y externos la información, evidencia y acceso al sistema necesarios para el ejercicio de sus funciones.

h) Proponer al Comité de Seguridad las mejoras técnicas que estime necesarias para reforzar la seguridad del sistema.

### 4.5 Delegado de Protección de Datos

Cuando la Entidad esté obligada a designar Delegado de Protección de Datos conforme al artículo 37 del RGPD, o cuando voluntariamente decida hacerlo, este rol corresponderá a {{ responsables.delegado_proteccion_datos.nombre }}, en su condición de {{ responsables.delegado_proteccion_datos.cargo }}, y se ejercerá con plena independencia funcional respecto del resto de roles, conforme a lo previsto en los artículos 38 y 39 del RGPD.

El Delegado de Protección de Datos colaborará estrechamente con el Responsable de la Seguridad en todos los asuntos que afecten al tratamiento de datos personales, sin perjuicio del carácter independiente de sus funciones.

### 4.6 Régimen excepcional de acumulación de roles

{% if (cliente.numero_empleados | default(50, true)) < 50 %}
Atendiendo a la dimensión actual de la Entidad ({{ cliente.numero_empleados }} empleados), y siempre con carácter excepcional y temporal, podrá autorizarse que una misma persona acumule simultáneamente más de uno de los roles descritos, con las siguientes limitaciones absolutas:

a) **El Responsable de la Seguridad nunca podrá acumular el rol de Responsable del Sistema**, por exigencia expresa del artículo 11 del ENS y por la imposibilidad de auto-supervisarse.

b) La acumulación deberá ser autorizada formalmente por {{ cliente.organo_aprobador_politicas }}, previa propuesta motivada del Comité de Seguridad.

c) Se documentarán las medidas compensatorias adoptadas para mitigar el riesgo derivado de la acumulación, en particular el recurso a apoyo externo independiente para las funciones de auditoría.

d) La acumulación tendrá vigencia máxima de doce meses, transcurridos los cuales deberá revisarse y, en su caso, prorrogarse mediante nueva autorización expresa.

e) Toda acumulación quedará registrada en el Registro de Excepciones gestionado por el Responsable de la Seguridad.
{% else %}
Atendiendo a la dimensión actual de la Entidad ({{ cliente.numero_empleados | default('—', true) }} empleados), no se considera necesaria la acumulación excepcional de roles. Cada uno de los cuatro roles del artículo 11 del ENS recae en una persona distinta, garantizando la separación de funciones exigida por la normativa.
{% endif %}

## 5. SUSTITUCIONES Y SUPLENCIAS

Para garantizar la continuidad operativa del SGSI en ausencia temporal o definitiva de las personas designadas, se establece el siguiente régimen de sustituciones:

a) En caso de **ausencia temporal** (vacaciones, baja por enfermedad, comisión de servicio) de cualquiera de las personas designadas, sus funciones serán asumidas por la persona suplente designada formalmente al efecto, que constará en el correspondiente acta del Comité de Seguridad.

b) En caso de **ausencia definitiva** (cese en el cargo, finalización de la relación laboral o contractual), {{ cliente.organo_aprobador_politicas }} procederá a la designación de la nueva persona titular en un plazo máximo de treinta días naturales. Hasta entonces, las funciones serán asumidas por el suplente designado.

c) Toda sustitución, temporal o definitiva, será comunicada al Comité de Seguridad y, en su caso, a las partes interesadas externas que corresponda.

## 6. RENDICIÓN DE CUENTAS

Cada uno de los roles descritos rendirá cuentas de sus actuaciones, según el siguiente esquema:

| Rol | Rinde cuentas a | Periodicidad |
|---|---|---|
| Responsable de la Seguridad | Comité de Seguridad y {{ cliente.organo_aprobador_politicas }} | Trimestral (Comité) y anual ({{ cliente.organo_aprobador_politicas }}) |
| Responsable del Sistema | Responsable de la Seguridad | Mensual |
| Responsable de la Información | Comité de Seguridad | Semestral |
| Responsable del Servicio | Comité de Seguridad | Semestral |
| Delegado de Protección de Datos | Órgano superior, conforme al art. 38 RGPD | Anual |

Los informes de rendición de cuentas se documentarán y conservarán en el repositorio documental del SGSI conforme al procedimiento {{ proyecto.codigo_documento_base }}-221 (Procedimiento de Gestión de la Información Documentada).

## 7. RESPONSABILIDADES TRAS EL CESE EN EL CARGO

Las personas que cesen en cualquiera de los roles descritos seguirán sujetas a las obligaciones de confidencialidad asumidas durante su ejercicio, conforme a lo previsto en el contrato laboral, en el código ético de la Entidad y en la legislación aplicable.

Asimismo, deberán colaborar de buena fe con su sucesor durante un período razonable de transición, facilitando el traspaso ordenado de las funciones, la documentación y los conocimientos necesarios.

## 8. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-100 · Anexo de Roles — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**
```
