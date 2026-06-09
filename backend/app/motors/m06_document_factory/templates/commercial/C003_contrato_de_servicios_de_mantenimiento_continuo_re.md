# DOCUMENTO C-003 — CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO (RETAINER POST-CERTIFICACIÓN)

```jinja
---
codigo_documento: "C-003"
titulo: "Contrato de Servicios de Mantenimiento del SGSI ENS (Retainer)"
version: "{{ contrato.version | default('1.0') }}"
fecha_firma: "{{ contrato.fecha_firma }}"
clasificacion: "CONFIDENCIAL — Cliente"
---

# CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO DEL SISTEMA DE GESTIÓN DE LA SEGURIDAD DE LA INFORMACIÓN (SGSI ENS)

**Contrato C-003 · Modalidad RETAINER · Versión {{ contrato.version | default('1.0') }}**

En {{ contrato.lugar_firma | default('Madrid') }}, a {{ contrato.fecha_firma }}.

---

## REUNIDOS

**De una parte,** D. Marcos Mata García, con N.I.F. {{ marcos.nif }}, y domicilio profesional en {{ marcos.domicilio }}, en su condición de profesional autónomo independiente (en adelante, **"FULKRO"** o **"el Consultor"**).

**Y de otra parte,** {{ cliente.razon_social }}, con N.I.F. {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }}, debidamente representada por D./Dña. {{ cliente.firmante.nombre_completo }}, en su condición de {{ cliente.firmante.cargo }} (en adelante, **"el Cliente"**).

## EXPONEN

**I.** Que con fecha {{ contrato.fecha_contrato_anterior }} las Partes suscribieron un Contrato de Prestación de Servicios Profesionales de Consultoría ENS (referencia C-001), cuyo objeto era la adecuación del Cliente al Esquema Nacional de Seguridad y la obtención del correspondiente certificado de conformidad.

**II.** Que con fecha {{ contrato.fecha_certificacion }} el Cliente obtuvo el certificado de conformidad ENS expedido por {{ contrato.entidad_certificadora }}, en categoría {{ contrato.categoria_ens }}, con vigencia hasta {{ contrato.fecha_caducidad_certificado }}.

**III.** Que el certificado de conformidad ENS, de acuerdo con la normativa aplicable, requiere ser renovado con periodicidad bienal mediante la realización de una nueva auditoría de certificación. Adicionalmente, el mantenimiento de la conformidad exige la realización continua de actividades de gobernanza, supervisión y mejora del SGSI implantado.

**IV.** Que el Cliente desea contar con el acompañamiento profesional continuo del Consultor para el mantenimiento del SGSI durante el período de validez del certificado y para la preparación de la futura auditoría de renovación.

**V.** Que las Partes desean formalizar la prestación de los servicios de mantenimiento continuo conforme a las siguientes

## CLÁUSULAS

### PRIMERA — OBJETO

1.1. El objeto del presente contrato es la prestación, por parte del Consultor al Cliente, de servicios profesionales continuados destinados al **mantenimiento del Sistema de Gestión de la Seguridad de la Información** del Cliente conforme al ENS, durante el período de validez de su certificado de conformidad y, en particular, hasta la próxima auditoría de renovación.

1.2. Los servicios incluidos en el presente contrato comprenden:

a) **Soporte continuo** por correo electrónico y teléfono para resolución de consultas operativas del Cliente sobre el SGSI.

b) **Revisión documental anual** de las políticas, procedimientos e instrucciones técnicas del SGSI, con propuesta de actualización de los documentos cuya vigencia lo requiera.

c) **Acompañamiento en la actualización del Análisis de Riesgos** anual conforme al procedimiento E-200.

d) **Acompañamiento en la realización de la auditoría interna** anual del SGSI conforme al procedimiento E-234, con asistencia opcional como auditor independiente.

e) **Vigilancia regulatoria continua**: notificación al Cliente de cualquier cambio normativo significativo (RD 311/2022, ITS, guías CCN-STIC, RGPD, NIS2, DORA en su caso) que pueda afectar al SGSI, con propuesta de las acciones necesarias para mantener el cumplimiento.

f) **Análisis de incidentes de seguridad** notificados por el Cliente, con propuesta de medidas correctivas.

g) **Preparación específica de la auditoría de renovación** durante los tres meses anteriores a su realización, incluyendo revisión documental, simulacro de auditoría y acompañamiento durante la auditoría externa.

h) **Reuniones periódicas de seguimiento** del SGSI conforme a la cláusula segunda.

### SEGUNDA — RÉGIMEN DE PRESTACIÓN

2.1. Los servicios se prestarán bajo modalidad de **retainer mensual con horas dedicadas predefinidas**, garantizando al Cliente la disponibilidad del Consultor para los servicios objeto del presente contrato.

2.2. El nivel de servicio contratado por el Cliente, conforme a la propuesta P-001-R que se adjunta como Anexo I, es:

| Concepto | Detalle |
|---|---|
| Modalidad | {{ retainer.modalidad }} |
| Horas mensuales incluidas | {{ retainer.horas_mensuales }} h/mes |
| Horas anuales incluidas | {{ retainer.horas_anuales }} h/año |
| Reuniones periódicas presenciales o por videoconferencia | {{ retainer.frecuencia_reuniones }} |
| Tiempo de respuesta a consultas urgentes | {{ retainer.sla_respuesta_urgente | default('4 horas hábiles') }} |
| Tiempo de respuesta a consultas ordinarias | {{ retainer.sla_respuesta_ordinaria | default('24 horas hábiles') }} |

2.3. **Horas no consumidas.** Las horas no consumidas en un mes podrán acumularse al mes siguiente hasta un máximo del **doble del cupo mensual**. Las horas acumuladas que excedan dicho límite se perderán al final del mes correspondiente.

2.4. **Horas adicionales.** Cuando el Cliente requiera servicios que excedan del cupo de horas contratado, el Consultor presentará presupuesto específico previo para las horas adicionales, que serán facturadas a la tarifa horaria de **{{ retainer.tarifa_hora_adicional }} €/h + IVA**.

2.5. **Servicios excluidos.** Los siguientes servicios no están incluidos en el retainer y, en su caso, serán objeto de presupuesto específico:

a) Implantación técnica de nuevos controles o tecnologías.
b) Adecuación a normativas distintas del ENS (incorporación de ISO 27001, ISO 22301, NIS2, DORA, etc.).
c) Ampliación significativa del alcance del certificado.
d) Respuesta a incidentes de seguridad graves que requieran dedicación intensiva (más de 8 horas en un solo incidente).
e) Asesoramiento jurídico especializado.
f) Auditorías internas extraordinarias fuera del calendario anual ordinario.

### TERCERA — DURACIÓN

3.1. El presente contrato tendrá una duración inicial de **veinticuatro (24) meses**, contados desde la fecha de su firma, coincidiendo con el período de validez del certificado de conformidad ENS del Cliente.

3.2. **Renovación automática.** Al término del período inicial, el contrato se renovará automáticamente por períodos sucesivos de doce (12) meses, salvo que cualquiera de las Partes comunique a la otra su voluntad de no renovar con una antelación mínima de **dos (2) meses** a la fecha de finalización del período en curso.

3.3. **Resolución anticipada.** Cualquiera de las Partes podrá resolver anticipadamente el presente contrato preavisando por escrito con una antelación mínima de **tres (3) meses**. La parte que resuelva anticipadamente sin causa justificada no estará obligada a indemnización, pero deberá abonar los servicios efectivamente prestados hasta la fecha de la resolución.

### CUARTA — CONTRAPRESTACIÓN ECONÓMICA

4.1. **Cuota mensual.** El Cliente abonará al Consultor en concepto de cuota mensual de retainer la cantidad de **{{ retainer.cuota_mensual_eur }} euros más el IVA aplicable**.

4.2. **Facturación.** La cuota mensual se facturará por anticipado dentro de los cinco primeros días naturales de cada mes y deberá ser abonada en el plazo máximo de quince días naturales desde la fecha de emisión.

4.3. **Revisión anual.** La cuota mensual será revisada anualmente conforme a la variación del Índice de Precios al Consumo publicado por el Instituto Nacional de Estadística para el período anual anterior, sin que en ningún caso pueda producirse una revisión a la baja.

4.4. **Demora en el pago.** El retraso en el pago de las cuotas mensuales devengará automáticamente los intereses de demora previstos en la Ley 3/2004, y facultará al Consultor a suspender la prestación de los servicios previo aviso de cinco días hábiles.

### QUINTA — OBLIGACIONES DE LAS PARTES Y MARCO CONTRACTUAL

#### 5.1 Marco contractual previo

{% if contrato.contrato_implantacion_previo %}
Este contrato de retainer se suscribe como **continuación del Contrato de Implantación ENS (C-001)** firmado entre las Partes con fecha {{ contrato.contrato_implantacion_previo.fecha_firma | default(contrato.fecha_contrato_anterior) }} (ref. {{ contrato.contrato_implantacion_previo.numero | default('C-001') }}).

Las obligaciones, garantías, confidencialidad, protección de datos personales (art. 28 RGPD), propiedad intelectual y limitación de responsabilidad definidas en el contrato de implantación previo se **mantienen vigentes** y son de aplicación al presente contrato de retainer, salvo en lo que explícitamente se modifique a continuación. En particular, se mantienen vigentes sin modificación:

- Cláusula SEXTA de C-001 — Incompatibilidad auditor-consultor (UNE-EN ISO/IEC 17065:2012, CCN-CERT IC-01/19).
- Cláusula SÉPTIMA de C-001 — Confidencialidad durante 5 años post-contrato.
- Cláusula OCTAVA de C-001 — Protección de datos personales (DPA art. 28 RGPD) incluido el Anexo II.
- Cláusula NOVENA de C-001 — Propiedad intelectual e industrial.
- Cláusula DÉCIMA de C-001 — Limitación de responsabilidad al importe efectivamente percibido.
- Cláusula 10.4 de C-001 — Compromiso de continuidad si no se obtiene el certificado.
- Cláusula DECIMOTERCERA de C-001 — Legislación española aplicable y fuero competente.

{% else %}
Este contrato de retainer se suscribe **de forma autónoma**, sin contrato de implantación previo con las Partes. En consecuencia, se aplicarán las siguientes obligaciones específicas directamente en este contrato:

- **Confidencialidad**: ambas Partes se obligan a la estricta confidencialidad sobre la información intercambiada durante la vigencia del retainer y por un plazo de **cinco (5) años** tras su extinción.
- **Protección de datos personales**: en la medida en que la prestación implique acceso por el Consultor a datos personales de los que el Cliente sea responsable, el Consultor asumirá la condición de **encargado del tratamiento** conforme al artículo 28 RGPD y firmará Anexo III DPA al presente contrato.
- **Propiedad intelectual**: los documentos revisados o actualizados durante el retainer son entregados al Cliente con derecho de uso perpetuo, no exclusivo y gratuito para fines internos. La plataforma FULKRO, plantillas maestras y metodología son propiedad exclusiva del Consultor.
- **Limitación de responsabilidad**: la responsabilidad total del Consultor por cualquier causa derivada del presente contrato no podrá exceder del importe total de las cuotas efectivamente percibidas en los doce meses anteriores a la fecha del evento.
- **Incompatibilidad auditor-consultor**: el Consultor no podrá actuar como auditor certificador del Cliente conforme a UNE-EN ISO/IEC 17065 y CCN-CERT IC-01/19.
- **Legislación aplicable**: legislación española, fuero de los Juzgados y Tribunales de {{ cliente.domicilio.ciudad | default('Madrid') }}.
{% endif %}

#### 5.2 Obligaciones del Consultor (FULKRO)

El Consultor se obliga específicamente a:

a) **Cumplir los SLA de respuesta** según el tier contratado:

| Tier | SLA respuesta urgente | SLA respuesta ordinaria |
|------|----------------------|-------------------------|
| R_MICRO    | best effort              | 120 horas hábiles |
| R_LITE     | 72 horas hábiles         | 72 horas hábiles  |
| R_STD      | 48 horas hábiles         | 48 horas hábiles  |
| R_PLUS     | 24 horas hábiles         | 24 horas hábiles  |
| R_CRITICAL | 8 horas hábiles (24/7)   | 8 horas hábiles   |

Para el tier actualmente contratado (**{{ retainer.modalidad }}**), el SLA aplicable es de **{{ retainer.sla_respuesta_urgente | default('según tabla superior') }}** para consultas urgentes y **{{ retainer.sla_respuesta_ordinaria | default('según tabla superior') }}** para consultas ordinarias.

b) **Mantener la confidencialidad** conforme al artículo 5 LOPDGDD 3/2018 y a la cláusula 5.1 del presente contrato.

c) **Notificar incidencias de seguridad detectadas** en activos del Cliente en un plazo máximo de **24 horas desde la detección**. Sin perjuicio del plazo regulatorio de 72 horas del artículo 33 RGPD para notificación a la AEPD, cuya obligación recae en el Cliente como responsable del tratamiento.

d) **Elaborar y compartir informes mensuales** de actividad del retainer, incluyendo: consultas atendidas, horas consumidas vs disponibles, riesgos detectados y acciones pendientes.

e) **Aplicar la diligencia profesional** propia de un consultor especializado en cumplimiento ENS conforme al artículo 1.104 del Código Civil y a las buenas prácticas del sector.

#### 5.3 Obligaciones del Cliente

El Cliente se obliga específicamente a:

a) **Designar un interlocutor único** con capacidad de decisión para la operativa del retainer, que actuará como punto de contacto principal con el Consultor. Cualquier cambio de interlocutor se comunicará por escrito con **5 días hábiles** de antelación.

b) **Proporcionar acceso razonable** a sistemas, documentación y personal necesarios para la ejecución de las actividades de mantenimiento del SGSI.

c) **Abonar las cuotas mensuales** dentro del plazo establecido en la cláusula cuarta.

d) **Notificar cambios materiales** (nuevas sedes, externalizaciones significativas, nuevos sistemas críticos, recategorización ENS, cambio legal representante) en un plazo máximo de **15 días naturales** desde producirse, para que FULKRO pueda evaluar su impacto sobre el SGSI y, en su caso, disparar el flujo de cambio material M27 previsto en el artículo 29 RD 311/2022.

e) **Ejecutar las decisiones** de su propio ámbito de gobierno (aprobación de políticas actualizadas, autorización de excepciones, asunción de riesgos residuales, respuesta formal ante requerimientos de la autoridad de control).

#### 5.4 Fuero competente

Para cualquier controversia derivada de la interpretación o ejecución del presente contrato, las Partes, con renuncia expresa a cualquier otro fuero que pudiera corresponderles, se someten a la jurisdicción de los **Juzgados y Tribunales de {{ cliente.domicilio.ciudad | default('Madrid') }}**. Sin perjuicio de lo anterior, las Partes podrán someter previamente la controversia a mediación profesional.

### SEXTA — COMPROMISO REFORZADO ANTE LA AUDITORÍA DE RENOVACIÓN

6.1. El Consultor se compromete a aplicar toda la diligencia profesional necesaria durante los tres meses anteriores a la auditoría de renovación para asegurar que el Cliente llega a dicha auditoría en condiciones óptimas para superarla.

6.2. Si la auditoría de renovación detectara no conformidades imputables exclusivamente al Consultor por defectos en el mantenimiento del SGSI durante el periodo del retainer, el Consultor se obliga a colaborar gratuitamente en su subsanación, dentro del cupo de horas del propio retainer, hasta su completa resolución.

---

Y para que así conste, las Partes firman el presente contrato en dos ejemplares y a un solo efecto, en el lugar y fecha indicados al principio.

| Por FULKRO | Por {{ cliente.razon_social }} |
|---|---|
| | |
| Fdo.: D. Marcos Mata García | Fdo.: D./Dña. {{ cliente.firmante.nombre_completo }} |

---

## ANEXOS

- **Anexo I:** Propuesta P-001-R (oferta de retainer)
- **Anexo II:** Calendario anual de actividades de mantenimiento

```

---

**Fin del Entregable F3.1.**

3 plantillas comerciales reales en español jurídico-comercial: propuesta maestra (P-001), contrato principal de consultoría (C-001) con las 14 cláusulas críticas incluyendo incompatibilidad auditor/consultor, y contrato retainer post-certificación (C-003). En el bloque F3.2 cierro los 4 entregables del proyecto: ficha resumen ejecutivo (E-001), informe final de adecuación (E-040), informe de auditoría interna (E-050) y BIA (E-400).
