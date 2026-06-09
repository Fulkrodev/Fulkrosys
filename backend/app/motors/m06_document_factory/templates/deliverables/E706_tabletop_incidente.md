# INFORME DE EJERCICIO TABLETOP DE GESTIÓN DE INCIDENTE DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-706 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Ejercicio Tabletop ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Informe documenta un ejercicio Tabletop de gestión de un incidente de seguridad sobre el sistema {{ proyecto.sistema_principal }}, ejecutado para validar la eficacia de:

- **Política de Gestión de Incidentes (E-103)**.
- **Procedimiento de Gestión de Incidentes (E-204)**.
- Cumplimiento de plazos de notificación a autoridades.

Marco normativo aplicable:

- **RD 311/2022 Anexo II** medida **op.exp.7 Gestión de incidentes**.
- **RGPD Art. 33** (notificación de brecha a AEPD ≤ 72 horas) y **Art. 34** (comunicación a interesados ante alto riesgo).
- **Directiva NIS2 Art. 23** (alerta inicial < 24h · notificación detallada < 72h · informe final ≤ 1 mes).
- **DORA Art. 19** (si aplica al sector financiero).
- **Herramienta LUCIA** del CCN-CERT para gestión y notificación de incidentes.

Este Informe se diferencia del **E-406 Informe de Pruebas de Continuidad** en que este ejercicio se centra exclusivamente en la **gestión del incidente** (detección, contención, comunicación, plazos legales) y no en la continuidad de negocio agregada.

## 2. FICHA DEL EJERCICIO

| Campo | Valor |
|---|---|
| Tipo | Tabletop de gestión de incidentes |
| Fecha de ejecución | {{ ejercicio.fecha }} |
| Hora de inicio | {{ ejercicio.hora_inicio }} |
| Hora de finalización | {{ ejercicio.hora_fin }} |
| Duración total | {{ ejercicio.duracion }} |
| Modalidad | {{ ejercicio.modalidad }} |
| Facilitador | {{ ejercicio.facilitador }} |
| Observadores | {{ ejercicio.observadores }} |
| Escenario | {{ ejercicio.escenario_resumen }} |

## 3. ESCENARIO PLANTEADO

{{ ejercicio.escenario_completo }}

El escenario incorpora características que activan **simultáneamente** las obligaciones de notificación a múltiples autoridades, con el fin de evaluar la capacidad de coordinación.

## 4. INYECCIONES PRESENTADAS DURANTE EL EJERCICIO

| Tiempo (T+) | Inyección | Reacción esperada |
|---|---|---|
{% for iny in inyecciones %}| {{ iny.tiempo }} | {{ iny.descripcion }} | {{ iny.reaccion_esperada }} |
{% endfor %}

## 5. PARTICIPANTES

| Nombre | Rol en el ejercicio | Función habitual | Asistencia |
|---|---|---|:---:|
{% for p in participantes %}| {{ p.nombre }} | {{ p.rol_ejercicio }} | {{ p.funcion_habitual }} | {{ p.asistencia }} |
{% endfor %}

## 6. CRONOLOGÍA DE LAS DECISIONES TOMADAS

{% for evento in cronologia %}- **{{ evento.timestamp }}** — {{ evento.descripcion }}.
{% endfor %}

## 7. MÉTRICAS DEL EJERCICIO · CUMPLIMIENTO DE PLAZOS LEGALES

| Plazo | Objetivo normativo | Logrado en el ejercicio | Cumplimiento |
|---|:---:|:---:|:---:|
| Notificación inicial a AEPD (RGPD Art. 33) | ≤ 72 h | {{ plazos.aepd_real }} | {{ plazos.aepd_estado }} |
| Notificación inicial NIS2 (Art. 23) | ≤ 24 h | {{ plazos.nis2_inicial }} | {{ plazos.nis2_inicial_estado }} |
| Notificación detallada NIS2 | ≤ 72 h | {{ plazos.nis2_detallada }} | {{ plazos.nis2_detallada_estado }} |
| Comunicación a interesados (RGPD Art. 34) | Sin dilación indebida | {{ plazos.interesados }} | {{ plazos.interesados_estado }} |
| Registro en LUCIA / CCN-CERT | Conforme guía | {{ plazos.lucia }} | {{ plazos.lucia_estado }} |
| Notificación DORA Art. 19 (si aplica) | Según plazos DORA | {{ plazos.dora }} | {{ plazos.dora_estado }} |

## 8. EFICACIA DEL PROCEDIMIENTO E-204

| Apartado del E-204 | Aplicado | Eficaz | Comentario |
|---|:---:|:---:|---|
{% for ap in eficacia_e204 %}| {{ ap.apartado }} | {{ ap.aplicado }} | {{ ap.eficaz }} | {{ ap.comentario }} |
{% endfor %}

## 9. OBSERVACIONES Y HALLAZGOS

### 9.1 Qué funcionó correctamente

{% for obs in observaciones.positivas %}- {{ obs }}
{% endfor %}

### 9.2 Qué falló o presentó dificultades

{% for obs in observaciones.negativas %}- {{ obs }}
{% endfor %}

### 9.3 Sorpresas y hallazgos no esperados

{% for obs in observaciones.sorpresas %}- {{ obs }}
{% endfor %}

## 10. GAPS IDENTIFICADOS Y PLAN DE ACCIÓN

| Gap | Severidad | Procedimiento afectado | Acción correctiva | Responsable | Plazo |
|---|:---:|---|---|---|:---:|
{% for gap in gaps %}| {{ gap.descripcion }} | {{ gap.severidad }} | {{ gap.procedimiento }} | {{ gap.accion }} | {{ gap.responsable }} | {{ gap.plazo }} |
{% endfor %}

## 11. CONCLUSIONES Y RECOMENDACIONES

**Valoración global del ejercicio**: {{ valoracion }}.

{{ conclusion_texto }}

Recomendaciones:

{% for rec in recomendaciones %}- {{ rec }}
{% endfor %}

## 12. ANEXOS

- **Anexo A**: Plantillas de notificación a autoridades empleadas durante el ejercicio.
- **Anexo B**: Mensajes intercambiados durante el ejercicio (intra-equipo).
- **Anexo C**: Hoja de asistencia firmada.
- **Anexo D**: Logs del escenario y de las inyecciones.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
