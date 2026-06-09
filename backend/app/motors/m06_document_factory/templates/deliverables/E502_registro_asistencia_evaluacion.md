# REGISTRO DE ASISTENCIA Y EVALUACIÓN DE LA FORMACIÓN DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-502 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Registro de Asistencia y Evaluación ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

Este Registro constituye evidencia auditable del cumplimiento de las medidas **mp.per.3 Concienciación** y **mp.per.4 Formación** del Anexo II del RD 311/2022.

## 1. PERIODO REPORTADO

| Campo | Valor |
|---|---|
| Trimestre | {{ periodo.trimestre }} |
| Año | {{ periodo.anyo }} |
| Fecha de cierre | {{ periodo.fecha_cierre }} |
| Plataforma de origen | {{ lms.plataforma }} |
| Periodo cubierto | {{ periodo.fecha_inicio }} a {{ periodo.fecha_fin }} |

## 2. RESUMEN EJECUTIVO

Durante el periodo reportado se han impartido **{{ resumen.num_sesiones }}** sesiones formativas con **{{ resumen.num_asistencias }}** asistencias registradas, cubriendo a **{{ resumen.num_empleados_distintos }}** empleados distintos.

Tasa global de cumplimiento del Plan E-500 en el periodo: **{{ resumen.tasa_cumplimiento_pct }}%** (objetivo ≥ 95%).

## 3. SESIONES IMPARTIDAS

| Fecha | Módulo | Grupo | Convocados | Asistentes | Tasa | Facilitador |
|---|---|:---:|:---:|:---:|:---:|---|
{% for s in sesiones %}| {{ s.fecha }} | {{ s.modulo }} | {{ s.grupo }} | {{ s.convocados }} | {{ s.asistentes }} | {{ s.tasa }}% | {{ s.facilitador }} |
{% endfor %}

## 4. ASISTENCIA INDIVIDUAL POR EMPLEADO

A continuación se muestra el detalle individual. Los empleados con cumplimiento incompleto se identifican explícitamente para activar acciones correctivas conforme al punto 8.

| Empleado | Rol | Grupo principal | Horas planificadas | Horas completadas | Cumplimiento | Estado |
|---|---|:---:|:---:|:---:|:---:|:---:|
{% for emp in empleados %}| {{ emp.nombre }} | {{ emp.rol }} | {{ emp.grupo }} | {{ emp.horas_plan }} | {{ emp.horas_completadas }} | {{ emp.cumplimiento_pct }}% | {{ emp.estado }} |
{% endfor %}

## 5. SESIÓN DE ACOGIDA · NUEVAS INCORPORACIONES

| Empleado | Fecha alta | Fecha acogida | En plazo (≤ 30 días) |
|---|---|---|:---:|
{% for nuevo in nuevas_incorporaciones %}| {{ nuevo.nombre }} | {{ nuevo.fecha_alta }} | {{ nuevo.fecha_acogida }} | {{ nuevo.en_plazo }} |
{% endfor %}

**Cumplimiento del KPI "Sesión de acogida en plazo"**: {{ kpi_acogida_pct }}% (objetivo 100%).

## 6. EVALUACIONES Y PUNTUACIONES

Resultados de los quizzes asociados a los módulos impartidos durante el periodo:

| Módulo | Nº participantes | Puntuación media | Tasa de aprobado (≥ 70%) |
|---|:---:|:---:|:---:|
{% for ev in evaluaciones %}| {{ ev.modulo }} | {{ ev.num_participantes }} | {{ ev.puntuacion_media }}/100 | {{ ev.tasa_aprobado }}% |
{% endfor %}

Los empleados que no superen el umbral de aprobado en un módulo deben repetirlo en un plazo máximo de **15 días naturales** desde la primera tentativa.

## 7. ANÁLISIS DE BRECHAS DE FORMACIÓN

Empleados o grupos identificados con **incumplimiento parcial o total** que requieren acción específica:

{% for brecha in brechas %}- **{{ brecha.empleado_o_grupo }}** ({{ brecha.grupo }}): {{ brecha.descripcion_brecha }}. Acción propuesta: {{ brecha.accion_correctiva }}. Plazo: {{ brecha.plazo }}.
{% endfor %}

## 8. ACCIONES CORRECTIVAS

| ID | Acción | Empleado / Grupo | Responsable | Plazo | Estado |
|---|---|---|---|---|:---:|
{% for ac in acciones_correctivas %}| {{ ac.id }} | {{ ac.descripcion }} | {{ ac.afectado }} | {{ ac.responsable }} | {{ ac.plazo }} | {{ ac.estado }} |
{% endfor %}

## 9. EVIDENCIAS DOCUMENTALES CONSERVADAS

Para cada sesión impartida se conservan, durante un mínimo de **5 años**, las siguientes evidencias en el repositorio documental del SGSI:

- Lista de asistencia firmada digitalmente por los participantes.
- Material impartido (presentaciones, grabaciones cuando proceda).
- Resultados individuales del quiz asociado.
- Certificados emitidos a los empleados.
- Registro de la sesión en el LMS corporativo (timestamp, duración real).

## 10. OBSERVACIONES Y RECOMENDACIONES

{{ observaciones_responsable }}

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
