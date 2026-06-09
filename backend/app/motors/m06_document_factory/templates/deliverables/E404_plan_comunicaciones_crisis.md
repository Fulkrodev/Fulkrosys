# PLAN DE COMUNICACIONES EN CRISIS DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-404 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Plan de Comunicaciones en Crisis ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Plan establece la estrategia, los canales, los responsables y las plantillas para gestionar la comunicación de {{ cliente.razon_social }} durante una crisis o un incidente de seguridad significativo, en cumplimiento de:

- **Esquema Nacional de Seguridad** (RD 311/2022, medida **op.exp.7 Gestión de incidentes**).
- **RGPD Art. 33** (notificación de brecha a AEPD en 72h) y **Art. 34** (comunicación a interesados ante alto riesgo).
- **Directiva NIS2 Art. 23** (notificación de incidentes significativos: alerta inicial < 24h, notificación detallada < 72h, informe final ≤ 1 mes).
- **Reglamento DORA Art. 19** si la Entidad opera en el sector financiero o como proveedor TIC crítico financiero.

## 2. MATRIZ DE STAKEHOLDERS

| Stakeholder | Prioridad | Canal principal | Responsable interno | Plantilla mensaje | Plazo objetivo |
|---|:---:|---|---|---|---|
{% for sh in stakeholders %}| {{ sh.tipo }} | {{ sh.prioridad }} | {{ sh.canal }} | {{ sh.responsable_interno }} | {{ sh.plantilla_ref }} | {{ sh.plazo }} |
{% endfor %}

Stakeholders típicos a considerar (la matriz anterior los concreta para esta Entidad):

- **Internos**: empleados, dirección, Comité de Continuidad.
- **Clientes**: usuarios del servicio afectado.
- **Proveedores y partners**: prestadores de servicio crítico.
- **Autoridades**: AEPD, CCN-CERT, INCIBE-CERT, Banco de España/CNMV (si DORA aplica).
- **Medios de comunicación**: prensa especializada y generalista.
- **Reguladores sectoriales**: cuando aplique según el sector de la Entidad.

## 3. PLANTILLAS DE MENSAJE POR AUDIENCIA

### 3.1 Comunicación interna a empleados

Asunto: Activación del Plan de Continuidad — Información para el equipo

Mensaje: descripción objetiva del evento, instrucciones operativas (continuar / suspender ciertos servicios), canales de soporte habilitados, designación del portavoz único y prohibición expresa de comunicación externa sin autorización.

### 3.2 Comunicación a clientes (servicio afectado)

Asunto: Incidencia en el servicio — Información actualizada

Mensaje: descripción del impacto desde la perspectiva del cliente, estimación inicial de tiempo de resolución (RTO), canal de soporte para consultas, compromiso de comunicación de actualizaciones periódicas y disculpa formal cuando proceda.

### 3.3 Comunicación a autoridades

**3.3.1 AEPD (RGPD Art. 33)**: notificación de brecha de datos personales en plazo de 72 horas desde el conocimiento si supone riesgo para los derechos de las personas. Formato: formulario oficial de la AEPD. Contenido mínimo: naturaleza de la brecha, categorías y nº aproximado de afectados, consecuencias probables, medidas adoptadas, datos de contacto del DPO.

**3.3.2 CCN-CERT / INCIBE-CERT (NIS2)**: si la Entidad está incluida en el ámbito de aplicación de NIS2 (entidad esencial o importante), notificación inicial en plazo de 24 horas tras conocimiento del incidente significativo. Notificación detallada en 72 horas. Informe final en plazo no superior a un mes.

**3.3.3 Banco de España / CNMV (DORA)**: si la Entidad es entidad financiera o proveedor TIC crítico, notificación inicial conforme a los plazos y formatos establecidos en el Reglamento DORA Art. 19.

### 3.4 Comunicación a interesados (RGPD Art. 34)

Cuando la brecha entrañe alto riesgo para los derechos y libertades de las personas, se notifica directamente a los afectados sin dilación indebida, en lenguaje claro y por canal accesible. Contenido mínimo: naturaleza de la brecha, contacto del DPO, consecuencias probables, medidas adoptadas y recomendaciones para mitigar efectos.

### 3.5 Comunicación a medios

Solo en caso de impacto público o requerimiento informativo, exclusivamente a través del portavoz designado. Mensaje preparado en consenso del Comité de Continuidad. Tono profesional, transparencia sobre lo conocido, evitar especulación y datos no confirmados.

## 4. CANALES DE COMUNICACIÓN

### 4.1 Canales corporativos habituales

- Correo electrónico corporativo.
- Intranet y herramientas internas de mensajería.
- Web pública y portal de cliente.
- Teléfono directo y centralita.

### 4.2 Canales alternativos en caso de caída de los primarios

- Lista de teléfonos móviles personales del personal clave (consentimiento previo documentado).
- Grupo de mensajería de emergencia en aplicación móvil acordada (con respaldo en aplicación alternativa).
- Web pública de respaldo en CDN externo.
- Cuentas oficiales en redes sociales con acceso pre-aprobado.

### 4.3 Política de redes sociales en crisis

Durante una crisis, la comunicación en redes sociales se ejecuta exclusivamente desde cuentas oficiales y por el portavoz designado o por personal expresamente autorizado por el Comité de Continuidad. El resto del personal se abstiene de publicar contenido relacionado con la crisis.

## 5. PORTAVOCES AUTORIZADOS

| Función | Titular | Suplente | Audiencia |
|---|---|---|---|
{% for pv in portavoces %}| {{ pv.funcion }} | {{ pv.titular }} | {{ pv.suplente }} | {{ pv.audiencia }} |
{% endfor %}

Los portavoces reciben formación específica en gestión de comunicación en crisis con periodicidad mínima anual.

## 6. PROTOCOLO DE ESCALADO INTERNO

1. Cualquier empleado que detecte un evento significativo notifica a su responsable directo o a {{ responsables.responsable_seguridad.nombre }} a través de los canales definidos.
2. El responsable de seguridad evalúa el evento y activa, si procede, al Comité de Continuidad.
3. El Comité decide el nivel de comunicación necesario (interno, clientes, autoridades, público) y autoriza los mensajes.
4. El portavoz designado ejecuta la comunicación conforme a las plantillas y canales.

## 7. NOTIFICACIONES OBLIGATORIAS A AUTORIDADES

Autoridades aplicables a la Entidad según su naturaleza y sector:

{% for aut in autoridades_aplicables %}- **{{ aut.nombre }}** ({{ aut.regulacion }}): {{ aut.cuando }}. Canal: {{ aut.canal }}. Plazo: {{ aut.plazo }}.
{% endfor %}

## 8. COMUNICACIÓN POST-CRISIS

Una vez declarado el fin de la activación, se ejecutan las siguientes acciones de comunicación:

- **Lecciones aprendidas**: comunicación interna del resumen del incidente y de las mejoras identificadas.
- **Informe ejecutivo**: documento dirigido al órgano de gobierno con cronología, impacto, decisiones tomadas y eficacia de la respuesta.
- **Comunicación a clientes**: cierre formal cuando proceda, agradecimiento por la paciencia y resumen de medidas adoptadas para evitar recurrencia.
- **Comunicación a autoridades**: informe final si así lo requieren los plazos NIS2/DORA.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
