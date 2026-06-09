# DOCUMENTO E-108 — POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD

**Materializa la medida op.exp.7 del Anexo II del ENS** y cumple las obligaciones de notificación al CCN-CERT vía LUCIA (Resolución BOE-A-2018-5370) + las obligaciones de notificación de brechas a la AEPD del artículo 33 del RGPD (72 horas).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-108"
titulo: "Política de Gestión de Incidentes de Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-108 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece el marco general para la **detección, notificación, valoración, contención, erradicación, recuperación y aprendizaje** ante los incidentes de seguridad que afecten o puedan afectar a los sistemas de información, redes, servicios, instalaciones e información de {{ cliente.razon_social }}, así como las obligaciones de notificación a las autoridades competentes y a las partes interesadas afectadas.

Esta Política da cumplimiento a la medida **op.exp.7 (Gestión de incidentes)** del Anexo II del Real Decreto 311/2022, a la **Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad** (Resolución de 13 de abril de 2018, BOE-A-2018-5370) y, en lo que respecta a las brechas de seguridad de datos personales, a los **artículos 33 y 34 del Reglamento (UE) 2016/679** (RGPD) y a la **Guía para la notificación de brechas de datos personales** publicada por la Agencia Española de Protección de Datos.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todo incidente, real o sospechado, que pueda afectar a la confidencialidad, integridad, disponibilidad, autenticidad o trazabilidad de la información o de los servicios prestados por los sistemas comprendidos en el alcance del SGSI, con independencia del origen del incidente (interno o externo, deliberado o accidental, técnico o procedimental).

Es de obligado cumplimiento para todo el personal de la Entidad y para los terceros con acceso a sus sistemas, incluidos proveedores y subcontratistas.

## 3. DEFINICIONES OPERATIVAS

A los efectos del presente documento, se entenderá por:

a) **Evento de seguridad**: cualquier ocurrencia identificada en un sistema, servicio o red que indica una posible violación de la política de seguridad o un fallo en los controles, así como cualquier situación previamente desconocida que pueda ser relevante para la seguridad.

b) **Incidente de seguridad**: uno o varios eventos de seguridad relacionados, no deseados o inesperados, que tienen una probabilidad significativa de comprometer la operación de los sistemas o de la información y de amenazar la seguridad de la información.

c) **Brecha de seguridad de datos personales**: toda violación de la seguridad que ocasione la destrucción, pérdida o alteración accidental o ilícita de datos personales transmitidos, conservados o tratados de otra forma, o la comunicación o acceso no autorizados a dichos datos, conforme al artículo 4.12 del RGPD.

d) **Crisis de seguridad**: incidente de impacto crítico que requiere la activación del comité de crisis y, eventualmente, del Plan de Continuidad del Servicio.

## 4. CLASIFICACIÓN DE INCIDENTES

Los incidentes de seguridad se clasificarán, a efectos de su gestión y notificación, conforme a la siguiente escala, alineada con la guía CCN-CERT IA-04/19 sobre tipología de incidentes:

| Nivel | Categoría | Criterio | Plazo máximo de notificación interna |
|---|---|---|---|
| **5 — CRÍTICO** | Crisis | Compromiso total del sistema, exfiltración masiva, indisponibilidad prolongada de servicios esenciales | Inmediato (15 minutos) |
| **4 — MUY ALTO** | Alto impacto | Compromiso significativo, afectación a servicios esenciales, brecha de datos personales con riesgo alto | 1 hora |
| **3 — ALTO** | Impacto relevante | Compromiso parcial, afectación a servicios no esenciales, brecha de datos personales con riesgo bajo | 4 horas |
| **2 — MEDIO** | Impacto moderado | Detección de actividad anómala con afectación limitada | 24 horas |
| **1 — BAJO** | Impacto menor | Eventos aislados sin afectación significativa | 72 horas |

La clasificación inicial será realizada por la persona que detecte el incidente y revisada inmediatamente por el Responsable de la Seguridad, quien podrá reclasificarlo en función de la información disponible.

## 5. CICLO DE GESTIÓN DEL INCIDENTE

La gestión de cualquier incidente seguirá las siguientes fases, conforme al modelo NIST SP 800-61 adaptado al contexto del ENS:

### 5.1 Detección

Los incidentes pueden ser detectados por:

a) Sistemas automáticos de monitorización (SIEM, IDS/IPS, antimalware, herramientas DLP) operados conforme al documento {{ proyecto.codigo_documento_base }}-118.

b) Personal interno o externo que observe una anomalía o sospeche de un compromiso.

c) Notificaciones recibidas de terceros (CCN-CERT, INCIBE-CERT, partes interesadas, proveedores).

d) Auditorías internas o externas.

Toda persona, sea del personal interno o externo, que detecte un evento o incidente de seguridad **tiene la obligación** de notificarlo de inmediato al Responsable de la Seguridad o, en su defecto, al Responsable del Sistema, mediante los canales establecidos en el procedimiento {{ proyecto.codigo_documento_base }}-204 (Procedimiento de Gestión de Incidentes).

### 5.2 Notificación interna y registro

Recibida la notificación, el Responsable de la Seguridad procederá inmediatamente a:

a) Registrar el incidente en el **Registro de Incidentes** del SGSI, asignándole un identificador único, fecha y hora exactas, persona notificadora y descripción inicial.

b) Realizar la clasificación preliminar conforme al apartado 4.

c) Activar el equipo de respuesta correspondiente al nivel del incidente.

### 5.3 Análisis y valoración

El equipo de respuesta procederá a:

a) Recopilar toda la información disponible sobre el incidente, preservando la cadena de custodia de las evidencias conforme al procedimiento {{ proyecto.codigo_documento_base }}-204-A (Recopilación y Custodia de Evidencias).

b) Determinar el alcance, naturaleza y causa probable del incidente.

c) Valorar el impacto real o potencial sobre la confidencialidad, integridad, disponibilidad, autenticidad y trazabilidad de la información y los servicios.

d) Determinar si el incidente afecta a datos personales y, en su caso, valorar el riesgo conforme a los criterios de la guía AEPD para la notificación de brechas de datos personales.

e) Confirmar o reclasificar el nivel del incidente.

### 5.4 Contención

El equipo de respuesta adoptará las medidas necesarias para contener el incidente, evitando su propagación y limitando su impacto. Estas medidas podrán incluir, entre otras, el aislamiento de sistemas afectados, la suspensión de cuentas de usuario, el bloqueo de comunicaciones o la activación de copias de respaldo.

Las medidas de contención serán aprobadas por el Responsable de la Seguridad y ejecutadas por el Responsable del Sistema o por el personal técnico bajo su supervisión.

### 5.5 Erradicación

Una vez contenido el incidente, se procederá a eliminar la causa raíz del mismo, lo que podrá incluir la limpieza de sistemas comprometidos, la aplicación de parches, la eliminación de cuentas no autorizadas, la reconfiguración de controles de seguridad o cualquier otra medida correctiva necesaria.

### 5.6 Recuperación

Eliminada la causa raíz, se procederá a la restauración del servicio en condiciones de seguridad, mediante el procedimiento adecuado a cada caso y, cuando proceda, mediante la activación de los planes de continuidad descritos en el documento {{ proyecto.codigo_documento_base }}-109.

La recuperación se considerará completada cuando los sistemas afectados operen con normalidad y se haya verificado la ausencia de actividad anómala residual.

### 5.7 Aprendizaje (lecciones aprendidas)

Tras el cierre del incidente, y en un plazo máximo de quince días naturales para incidentes de niveles 3 a 5, el Responsable de la Seguridad elaborará un **informe post-incidente** que incluirá, al menos:

a) Cronología detallada del incidente.

b) Causa raíz identificada.

c) Impacto real producido.

d) Eficacia de las medidas de contención, erradicación y recuperación adoptadas.

e) Lecciones aprendidas y recomendaciones de mejora para los controles, los procedimientos o la formación.

f) Acciones correctivas a implantar, con responsables y plazos.

El informe post-incidente será elevado al Comité de Seguridad y, en función de su gravedad, a {{ cliente.organo_aprobador_politicas }}.

## 6. NOTIFICACIÓN A AUTORIDADES Y PARTES INTERESADAS

### 6.1 Notificación al CCN-CERT vía LUCIA

{% if cliente.sector_aplicacion == 'publico' or proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Conforme a la Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad (BOE-A-2018-5370), los incidentes de niveles **CRÍTICO** y **MUY ALTO**, y en general aquellos que afecten significativamente a los servicios esenciales o a la información clasificada, serán notificados al CCN-CERT mediante la herramienta **LUCIA**, en los siguientes plazos máximos:

| Nivel del incidente | Plazo de notificación inicial al CCN-CERT |
|---|---|
| CRÍTICO | 1 hora desde la detección |
| MUY ALTO | 6 horas desde la detección |
| ALTO | 24 horas desde la detección |

La notificación inicial se complementará con notificaciones de seguimiento durante la gestión del incidente y con el informe final de cierre.

La interlocución con el CCN-CERT corresponde al Responsable de la Seguridad o a la persona en quien delegue formalmente.
{% else %}
Atendiendo a la naturaleza privada de la Entidad y a la categoría {{ proyecto.categoria_ens }} del sistema, la notificación al CCN-CERT vía LUCIA tendrá carácter **voluntario** salvo en aquellos casos en que el incidente afecte a un servicio prestado a la Administración Pública, en cuyo caso se notificará en los plazos establecidos en el apartado anterior.
{% endif %}

### 6.2 Notificación de brechas a la AEPD

Cuando el incidente constituya una brecha de seguridad de datos personales, conforme a la definición del artículo 4.12 del RGPD, y exista probabilidad de riesgo para los derechos y libertades de las personas físicas, la Entidad procederá a su notificación a la Agencia Española de Protección de Datos en el plazo máximo de **72 horas desde su conocimiento**, conforme al artículo 33 del RGPD.

La notificación se realizará a través del **formulario electrónico de la sede electrónica de la AEPD** disponible en https://sedeaepd.gob.es y contendrá, al menos:

a) Naturaleza de la brecha y, cuando sea posible, las categorías y el número aproximado de personas afectadas y de registros de datos personales afectados.

b) Datos de contacto del Delegado de Protección de Datos o del punto de contacto donde pueda obtenerse más información.

c) Posibles consecuencias de la brecha.

d) Medidas adoptadas o propuestas para poner remedio a la brecha y, en su caso, mitigar sus posibles efectos.

Cuando la brecha entrañe **riesgo alto** para los derechos y libertades de las personas físicas, se procederá adicionalmente a la **comunicación a las personas afectadas** sin dilación indebida, conforme al artículo 34 del RGPD.

La interlocución con la AEPD corresponde al Delegado de Protección de Datos en coordinación con el Responsable de la Seguridad.

{% if cliente.sector_actividad in ["fintech", "servicios financieros", "banca", "seguros"] %}
### 6.3 Notificación bajo DORA

Adicionalmente, conforme al Reglamento (UE) 2022/2554 (DORA), los incidentes graves relacionados con las TIC serán notificados a la autoridad competente en los plazos y con el contenido establecidos en dicho Reglamento y en sus actos delegados.
{% endif %}

### 6.4 Notificación a partes interesadas afectadas

Cuando el incidente afecte a clientes, proveedores o terceros que mantengan relaciones contractuales con la Entidad, se les notificará conforme a las obligaciones contractuales o legales aplicables, en los plazos y por los canales establecidos.

## 7. EQUIPO DE RESPUESTA A INCIDENTES

La Entidad constituye un **Equipo de Respuesta a Incidentes** (en adelante, "ERI"), cuya composición y funciones serán las siguientes:

| Rol en el ERI | Persona designada | Responsabilidades |
|---|---|---|
| Coordinador del ERI | {{ responsables.responsable_seguridad.nombre }} | Coordinación general, interlocución con autoridades |
| Analista técnico líder | {{ responsables.responsable_sistema.nombre }} | Análisis técnico, contención y erradicación |
| Asesor legal | _A designar_ | Asesoramiento jurídico, valoración de obligaciones de notificación |
| Comunicación | _A designar_ | Comunicación interna y externa, gestión reputacional |
| Delegado de Protección de Datos | {{ responsables.delegado_proteccion_datos.nombre }} | Asesoramiento sobre brechas de datos personales y notificación a la AEPD |

Para incidentes de nivel **CRÍTICO**, el ERI activará el **Comité de Crisis**, presidido por {{ responsables.comite_seguridad.presidente }} y, en su defecto, por la persona en quien delegue {{ cliente.organo_aprobador_politicas }}.

## 8. EJERCICIOS Y SIMULACROS

Con periodicidad al menos **anual**, la Entidad realizará ejercicios y simulacros de gestión de incidentes que permitan evaluar la eficacia del proceso descrito en el presente documento, identificar áreas de mejora y mantener entrenado al ERI.

Los resultados de los ejercicios serán documentados y elevados al Comité de Seguridad.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo, y en todo caso tras cualquier incidente de nivel CRÍTICO o MUY ALTO.

---

**Documento {{ proyecto.codigo_documento_base }}-108 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
