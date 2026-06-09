# DOCUMENTO E-105 — POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES (RGPD)

**Política totalmente nueva. Materializa mp.info.1 del Anexo II del ENS y coordina el cumplimiento del RGPD y la LOPDGDD con el SGSI. Es la política que el auditor pide para verificar que la protección de datos personales está integrada en el SGSI y no es un silo separado.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-105"
titulo: "Política de Tratamiento de Datos Personales"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-105 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios, obligaciones y medidas organizativas que {{ cliente.razon_social }} aplica al tratamiento de datos personales, garantizando el cumplimiento del Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD), y de la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD), de forma coordinada con el Sistema de Gestión de la Seguridad de la Información implantado conforme al Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

Se aplica a todo tratamiento de datos personales realizado por la Entidad, ya actúe como responsable del tratamiento, como encargado del tratamiento por cuenta de terceros, o en régimen de corresponsabilidad, y con independencia del medio utilizado (automatizado o no).

## 3. PRINCIPIOS DEL TRATAMIENTO

De conformidad con el artículo 5 del RGPD, todo tratamiento de datos personales realizado por la Entidad se regirá por los siguientes principios:

**3.1. Licitud, lealtad y transparencia.** Los datos se tratarán de manera lícita, leal y transparente en relación con el interesado.

**3.2. Limitación de la finalidad.** Los datos se recogerán con fines determinados, explícitos y legítimos y no serán tratados ulteriormente de manera incompatible con dichos fines.

**3.3. Minimización de datos.** Los datos serán adecuados, pertinentes y limitados a lo necesario en relación con los fines para los que son tratados.

**3.4. Exactitud.** Los datos serán exactos y, si fuera necesario, actualizados, adoptándose las medidas razonables para que se supriman o rectifiquen sin dilación los inexactos.

**3.5. Limitación del plazo de conservación.** Los datos se conservarán durante no más tiempo del necesario para los fines del tratamiento, salvo obligación legal que exija su conservación.

**3.6. Integridad y confidencialidad.** Los datos se tratarán de manera que se garantice una seguridad adecuada, incluida la protección contra el tratamiento no autorizado o ilícito y contra su pérdida, destrucción o daño accidental.

**3.7. Responsabilidad proactiva.** La Entidad será responsable del cumplimiento de los principios anteriores y capaz de demostrarlo.

## 4. BASES DE LEGITIMACIÓN

Todo tratamiento de datos personales se fundamentará en al menos una de las bases de legitimación del artículo 6 del RGPD. El Registro de Actividades de Tratamiento documentará la base legitimadora de cada actividad de tratamiento.

## 5. CATEGORÍAS ESPECIALES DE DATOS

El tratamiento de datos de las categorías especiales del artículo 9 del RGPD (origen étnico, opiniones políticas, convicciones religiosas, afiliación sindical, datos genéticos, datos biométricos, datos de salud, vida sexual u orientación sexual) queda **expresamente prohibido** salvo que concurra alguna de las excepciones previstas en dicho artículo. Cualquier tratamiento excepcional requerirá la autorización previa y por escrito del Delegado de Protección de Datos y del Responsable de la Seguridad.

## 6. DELEGADO DE PROTECCIÓN DE DATOS

{% if responsables.delegado_proteccion_datos %}
La Entidad ha designado como Delegado de Protección de Datos a {{ responsables.delegado_proteccion_datos.nombre }}, {{ responsables.delegado_proteccion_datos.cargo }}, con dirección de contacto {{ responsables.delegado_proteccion_datos.email }}.

El DPO ejercerá sus funciones con plena independencia funcional conforme a los artículos 38 y 39 del RGPD y coordinará estrechamente con el Responsable de la Seguridad en todos los asuntos que afecten a la seguridad de los datos personales.
{% else %}
A la fecha de aprobación de la presente Política, la Entidad no ha designado Delegado de Protección de Datos al no concurrir las circunstancias del artículo 37 del RGPD. Esta situación se revisará anualmente y siempre que cambien las actividades de tratamiento de la Entidad.
{% endif %}

## 7. REGISTRO DE ACTIVIDADES DE TRATAMIENTO

La Entidad mantendrá un **Registro de Actividades de Tratamiento** conforme al artículo 30 del RGPD, que documentará para cada actividad: denominación, responsable, finalidades, categorías de interesados y datos, destinatarios, transferencias internacionales, plazos de conservación y medidas de seguridad.

El Registro se revisará al menos semestralmente por el DPO y el Responsable de la Seguridad.

## 8. DERECHOS DE LOS INTERESADOS

La Entidad garantizará el ejercicio efectivo de los derechos de acceso, rectificación, supresión, limitación del tratamiento, portabilidad y oposición previstos en los artículos 15 a 22 del RGPD, en los plazos y con las garantías establecidos en la normativa aplicable.

Las solicitudes de ejercicio de derechos se canalizarán a través del DPO (o, en su defecto, del Responsable de la Seguridad) y se resolverán en el plazo máximo de un mes desde su recepción, prorrogable dos meses en casos de especial complejidad.

## 9. EVALUACIONES DE IMPACTO (EIPD)

Cuando un tratamiento, por su naturaleza, alcance, contexto o fines, entrañe un alto riesgo para los derechos y libertades de las personas físicas, se realizará con carácter previo una **Evaluación de Impacto en la Protección de Datos** conforme al artículo 35 del RGPD, con la participación del DPO.

## 10. ENCARGADOS DEL TRATAMIENTO

Cuando la Entidad encomiende el tratamiento de datos personales a un tercero (encargado del tratamiento), se suscribirá el correspondiente contrato de encargo conforme al artículo 28.3 del RGPD, que incluirá las instrucciones documentadas del responsable, las medidas de seguridad exigibles, las obligaciones de confidencialidad, las condiciones de subcontratación, la asistencia en el ejercicio de derechos y la obligación de supresión o devolución al término de la prestación.

## 11. BRECHAS DE DATOS PERSONALES

Las brechas de seguridad que afecten a datos personales se gestionarán conforme a la Política de Respuesta a Brechas de Datos Personales ({{ proyecto.codigo_documento_base }}-119) y al procedimiento de gestión de incidentes ({{ proyecto.codigo_documento_base }}-204), garantizando la notificación a la AEPD en el plazo de 72 horas y, cuando proceda, la comunicación a los interesados afectados.

## 12. TRANSFERENCIAS INTERNACIONALES

Las transferencias de datos personales fuera del Espacio Económico Europeo se realizarán exclusivamente cuando exista una decisión de adecuación de la Comisión Europea, se hayan adoptado garantías adecuadas conforme a los artículos 46-49 del RGPD o concurra alguna de las excepciones previstas.

## 13. COORDINACIÓN CON EL SGSI ENS

La protección de datos personales no es un sistema de gestión paralelo sino una **dimensión integrada** en el SGSI implantado conforme al ENS. Las medidas de seguridad del Anexo II del RD 311/2022 se aplican también a la protección de los datos personales tratados por los sistemas del alcance, conforme al artículo 3 del ENS.

El Responsable de la Seguridad y el DPO mantendrán reuniones de coordinación al menos trimestrales para verificar la coherencia entre las medidas del SGSI y las exigencias del RGPD.

## 14. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se modifique el RGPD, la LOPDGDD o las actividades de tratamiento de la Entidad.

---

**Documento {{ proyecto.codigo_documento_base }}-105 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
