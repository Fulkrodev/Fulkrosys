# DOCUMENTO E-204 — PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD

**Es el procedimiento operativo que ejecuta la política E-108.** Mientras la política dice qué hay que notificar y a quién, este procedimiento dice exactamente qué hace cada persona desde el minuto cero hasta el cierre del incidente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-204"
titulo: "Procedimiento de Gestión de Incidentes de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
---

# PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-204 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas concretas que deben realizarse desde la detección de un incidente o sospecha de incidente de seguridad de la información hasta su cierre formal y la incorporación de las lecciones aprendidas, en desarrollo de la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108).

## 2. ALCANCE

Este procedimiento se aplica a todo evento o incidente de seguridad que afecte o pueda afectar a los activos comprendidos en el alcance del SGSI, sin perjuicio de los procedimientos específicos que pudieran existir para tipologías concretas de incidente.

## 3. CANALES DE NOTIFICACIÓN INTERNA

Cualquier persona que detecte un evento o incidente de seguridad **debe notificarlo de inmediato** a través de uno de los siguientes canales, en orden de preferencia:

1. **Buzón corporativo de incidentes:** `seguridad@{{ cliente.nombre_corto | lower | replace(" ", "") }}.es` (gestionado en horario laboral por el Responsable de la Seguridad).

2. **Teléfono de incidentes 24x7:** {{ responsables.responsable_seguridad.email }} (en horario no laboral, contactar mediante el directorio de emergencia del SGSI).

3. **Comunicación directa al Responsable del Sistema** ({{ responsables.responsable_sistema.nombre }}) o al Responsable de la Seguridad ({{ responsables.responsable_seguridad.nombre }}).

4. **Formulario web interno** disponible en la intranet corporativa.

**Toda notificación, sea cual sea el canal, debe incluir como mínimo:**

- Nombre y datos de contacto de quien notifica.
- Fecha, hora y lugar de detección.
- Descripción breve de lo observado.
- Sistemas, servicios o información posiblemente afectados.
- Acciones ya emprendidas, si las hubiera.

## 4. FLUJO OPERATIVO

### Fase 1 — Recepción y registro inicial (T+0 a T+30 minutos)

**Responsable:** Responsable de la Seguridad o persona de guardia designada.

**Acciones:**

1. Registrar el incidente en el **Sistema de Gestión de Incidentes** del SGSI, asignando un identificador único en formato `INC-AAAA-NNNN` (donde AAAA es el año y NNNN un correlativo).

2. Cumplimentar el formulario inicial del Anexo I con la información disponible.

3. Realizar una **clasificación preliminar** del incidente conforme a la escala del apartado 4 de la Política {{ proyecto.codigo_documento_base }}-108 (niveles BAJO, MEDIO, ALTO, MUY ALTO o CRÍTICO).

4. Activar el Equipo de Respuesta a Incidentes (ERI) correspondiente al nivel:

| Nivel | Activación |
|---|---|
| BAJO / MEDIO | ERI mínimo: Responsable Seguridad + Responsable Sistema |
| ALTO | ERI ampliado: + Asesor legal + DPO si aplica |
| MUY ALTO / CRÍTICO | ERI completo + Comité de Crisis |

5. Si la clasificación preliminar es **MUY ALTO** o **CRÍTICO**, notificar inmediatamente a {{ responsables.comite_seguridad.presidente }}.

### Fase 2 — Triaje y análisis inicial (T+30 minutos a T+4 horas)

**Responsable:** Coordinador del ERI (Responsable de la Seguridad).

**Acciones:**

6. Recopilar la información disponible sobre el incidente: logs, alertas del SIEM, informes técnicos, capturas de pantalla, mensajes recibidos.

7. **Iniciar la cadena de custodia** de las evidencias conforme al procedimiento {{ proyecto.codigo_documento_base }}-204-A, registrando:

- Origen de cada evidencia.
- Persona que la recopila.
- Fecha y hora exactas.
- Hash SHA-256 si es información digital.
- Cadena de manipulaciones posteriores.

8. **Determinar el alcance** del incidente: qué sistemas, servicios o información están afectados, número aproximado de personas o registros implicados.

9. **Confirmar o reclasificar** el nivel del incidente.

10. Si afecta a **datos personales**, valorar si constituye una **brecha de seguridad de datos personales** conforme a la guía AEPD y notificar al DPO ({{ responsables.delegado_proteccion_datos.nombre }}).

11. Decidir si procede activar el **Plan de Continuidad del Servicio** ({{ proyecto.codigo_documento_base }}-109).

### Fase 3 — Contención (T+4 horas a T+24 horas)

**Responsable:** Responsable del Sistema, bajo dirección del Coordinador del ERI.

**Acciones:**

12. Aplicar las medidas de contención necesarias para detener la propagación del incidente y limitar su impacto. Las medidas concretas dependen del tipo de incidente y se documentan en las **Instrucciones Técnicas IT-204-XX** asociadas a cada categoría:

| Tipo de incidente | Instrucción Técnica de contención |
|---|---|
| Compromiso de credenciales | IT-204-01 |
| Infección por malware / ransomware | IT-204-02 |
| Acceso no autorizado a sistemas | IT-204-03 |
| Filtración o exfiltración de datos | IT-204-04 |
| Denegación de servicio | IT-204-05 |
| Compromiso de cuenta privilegiada | IT-204-06 |
| Phishing dirigido (spear-phishing) | IT-204-07 |
| Pérdida o sustracción de equipo | IT-204-08 |

13. Documentar todas las acciones realizadas, sus resultados y los responsables de su ejecución.

14. Mantener informado al Coordinador del ERI cada 2 horas durante la fase de contención de incidentes ALTO o superior.

### Fase 4 — Notificación externa (en paralelo a la contención)

**Responsable:** Responsable de la Seguridad, en coordinación con DPO y asesor legal.

**Acciones:**

{% if cliente.sector_aplicacion == 'publico' %}
15. **Notificación al CCN-CERT vía LUCIA**, cuando proceda, en los plazos establecidos en el apartado 6.1 de la Política {{ proyecto.codigo_documento_base }}-108:

- CRÍTICO: en 1 hora
- MUY ALTO: en 6 horas
- ALTO: en 24 horas

La notificación se realiza accediendo a la herramienta LUCIA del CCN con el certificado digital corporativo y cumplimentando el formulario oficial. La interlocución posterior se gestiona también desde LUCIA.
{% else %}
15. **Notificación al CCN-CERT**, cuando proceda conforme al apartado 6.1 de la Política {{ proyecto.codigo_documento_base }}-108. Para sector privado bajo ENS, la notificación se canaliza directamente al CCN-CERT (LUCIA con carácter recomendado · obligatoria si el incidente afecta a servicios prestados a la Administración Pública), respetando los plazos: CRÍTICO 1 h · MUY ALTO 6 h · ALTO 24 h desde la detección.
{% endif %}

16. **Notificación de brecha de datos personales a la AEPD**, si procede, en el plazo máximo de **72 horas** desde el conocimiento, mediante el formulario electrónico de la sede electrónica de la AEPD (https://sedeaepd.gob.es). La notificación incluirá:

- Naturaleza de la brecha y categorías de datos afectados.
- Número aproximado de personas afectadas y de registros.
- Datos de contacto del DPO.
- Posibles consecuencias.
- Medidas adoptadas o propuestas.

17. **Comunicación a las personas afectadas**, cuando la brecha entrañe riesgo alto para sus derechos y libertades, conforme al artículo 34 del RGPD.

18. **Notificación a clientes y partes interesadas afectadas** según las obligaciones contractuales aplicables.

19. **Comunicación al equipo directivo y, en su caso, a {{ cliente.organo_aprobador_politicas }}** en incidentes CRÍTICO o MUY ALTO.

### Fase 5 — Erradicación y recuperación

**Responsable:** Responsable del Sistema, bajo dirección del Coordinador del ERI.

**Acciones:**

20. **Eliminar la causa raíz** del incidente: limpieza de sistemas comprometidos, aplicación de parches, eliminación de cuentas no autorizadas, reconfiguración de controles.

21. **Restaurar los servicios afectados** desde copias de seguridad verificadas, en el orden de prioridad determinado por el BIA del Plan de Continuidad.

22. **Verificar la integridad** de los sistemas restaurados antes de devolverlos a producción.

23. **Monitorizar activamente** los sistemas afectados durante un periodo mínimo de 72 horas tras la recuperación, para detectar posibles reapariciones.

### Fase 6 — Cierre y aprendizaje (T+15 días desde el cierre técnico)

**Responsable:** Responsable de la Seguridad.

**Acciones:**

24. Elaborar el **Informe Post-Incidente** conforme a la plantilla del Anexo II, que incluirá:

- Resumen ejecutivo.
- Cronología detallada del incidente con marcas de tiempo.
- Causa raíz identificada.
- Vector de ataque (cuando proceda) mapeado al MITRE ATT&CK.
- Impacto real producido.
- Acciones de contención, erradicación y recuperación realizadas y su eficacia.
- Notificaciones externas realizadas.
- **Lecciones aprendidas y recomendaciones de mejora.**
- Acciones correctivas a implantar, con responsables y plazos.

25. Presentar el Informe Post-Incidente al **Comité de Seguridad** en su siguiente reunión ordinaria.

26. Para incidentes CRÍTICO o MUY ALTO, presentar resumen al órgano superior {{ cliente.organo_aprobador_politicas }}.

27. **Cerrar formalmente el incidente** en el Sistema de Gestión de Incidentes, manteniendo accesible toda la documentación durante el periodo de conservación establecido en el procedimiento {{ proyecto.codigo_documento_base }}-221.

## 5. EQUIPO DE RESPUESTA A INCIDENTES (ERI)

| Rol | Persona designada | Funciones |
|---|---|---|
| Coordinador del ERI | {{ responsables.responsable_seguridad.nombre }} | Coordinación general, decisiones, interlocución autoridades |
| Líder técnico | {{ responsables.responsable_sistema.nombre }} | Análisis técnico, contención, erradicación, recuperación |
| Asesor legal | _A designar contractualmente_ | Valoración jurídica, obligaciones de notificación |
| DPO | {{ responsables.delegado_proteccion_datos.nombre }} | Asesoramiento sobre brechas de datos personales |
| Comunicación | _A designar_ | Comunicación interna, externa y reputacional |

Para incidentes CRÍTICOS, el ERI activa el **Comité de Crisis** presidido por {{ responsables.comite_seguridad.presidente }}.

## 6. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Formulario inicial de notificación | 6 años |
| Cadena de custodia de evidencias | 6 años o plazo de prescripción aplicable |
| Logs y evidencias técnicas | 6 años |
| Notificaciones a autoridades (LUCIA, AEPD) | 6 años |
| Informe Post-Incidente | 6 años |
| Acta de cierre | 6 años |

## 7. INDICADORES DE CONTROL

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Tiempo medio de detección (MTTD) | media de horas desde origen hasta detección | < 24h |
| Tiempo medio de respuesta (MTTR) | media de horas desde detección hasta contención | < 4h para ALTO+ |
| Cumplimiento plazos notificación LUCIA | (notificaciones en plazo / total) × 100 | 100% |
| Cumplimiento plazo 72h brecha AEPD | (notificaciones en plazo / total) × 100 | 100% |
| Recurrencia de incidentes mismo origen | nº incidentes con misma causa raíz en 12 meses | ≤ 1 |

## 8. ANEXOS

- **Anexo I:** Formulario inicial de notificación de incidente
- **Anexo II:** Plantilla del Informe Post-Incidente
- **Anexo III:** Directorio de emergencia 24x7
- **Anexo IV:** Mapeo de tipologías de incidente con tácticas y técnicas MITRE ATT&CK
- **Anexo V:** Plantilla de comunicación a personas afectadas (RGPD art. 34)

---

**Documento {{ proyecto.codigo_documento_base }}-204 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
