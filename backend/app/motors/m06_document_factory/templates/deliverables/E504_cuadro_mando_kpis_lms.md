# CUADRO DE MANDO DE KPIs DEL PROGRAMA DE FORMACIÓN Y CONCIENCIACIÓN DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-504 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Cuadro de Mando de KPIs ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

Este Cuadro consolida los indicadores del programa de formación y concienciación y constituye la evidencia agregada de cumplimiento de las medidas **mp.per.3** y **mp.per.4** del Anexo II del RD 311/2022.

## 1. PERIODO REPORTADO

| Campo | Valor |
|---|---|
| Trimestre | {{ periodo.trimestre }} |
| Año | {{ periodo.anyo }} |
| Fecha de cierre | {{ periodo.fecha_cierre }} |
| Audiencia del informe | Comité de Seguridad de {{ cliente.razon_social }} |
| Documentos fuente | E-501 (catálogo) · E-502 (asistencia) · E-503 (phishing) · LMS {{ lms.plataforma }} |

## 2. RESUMEN EJECUTIVO

Durante el periodo reportado, el programa ha alcanzado los siguientes resultados consolidados:

- Cobertura del Plan Anual: **{{ kpis.cobertura_plan_pct }}%** (objetivo ≥ 95%).
- Cumplimiento de la sesión de acogida en plazo: **{{ kpis.acogida_pct }}%** (objetivo 100%).
- Horas mínimas G3-G4 cumplidas: **{{ kpis.g3g4_horas_pct }}%** (objetivo ≥ 90%).
- Tasa de click en simulacros de phishing: **{{ kpis.phishing_click_pct }}%** (objetivo < 10%, ideal 5%).
- Tasa de reporte correcto de phishing: **{{ kpis.phishing_reporte_pct }}%** (objetivo ≥ 50%).
- Tasa de aprobado en quizzes: **{{ kpis.quiz_aprobado_pct }}%** (objetivo ≥ 70% por módulo).

**Estado global del programa**: {{ kpis.estado_global }}.

## 3. KPIs DETALLADOS

### 3.1 Cobertura del Plan Anual

| Grupo | Empleados con plan asignado | Empleados con plan completado | Cobertura | Estado |
|:---:|:---:|:---:|:---:|:---:|
{% for g in cobertura_por_grupo %}| {{ g.grupo }} | {{ g.asignados }} | {{ g.completados }} | {{ g.cobertura_pct }}% | {{ g.estado }} |
{% endfor %}

### 3.2 Sesión de Acogida en plazo

- Nuevas incorporaciones en el periodo: **{{ kpis.acogida.nuevos }}**.
- Acogidas completadas en ≤ 30 días: **{{ kpis.acogida.completadas }}**.
- Acogidas fuera de plazo: **{{ kpis.acogida.fuera_plazo }}**.
- Estado del KPI: **{{ kpis.acogida.estado }}**.

### 3.3 Horas mínimas grupos técnicos G3-G4

| Empleado | Grupo | Horas plan | Horas reales | % cumplimiento | Estado |
|---|:---:|:---:|:---:|:---:|:---:|
{% for emp in g3g4_detalle %}| {{ emp.nombre }} | {{ emp.grupo }} | {{ emp.plan }} | {{ emp.real }} | {{ emp.pct }}% | {{ emp.estado }} |
{% endfor %}

### 3.4 Simulacros de phishing

| Campaña | Fecha | Destinatarios | Tasa click | Tasa reporte |
|---|---|:---:|:---:|:---:|
{% for c in phishing_campanias %}| {{ c.nombre }} | {{ c.fecha }} | {{ c.destinatarios }} | {{ c.tasa_click }}% | {{ c.tasa_reporte }}% |
{% endfor %}

**Tendencia trimestral**: {{ kpis.phishing_tendencia }}.

### 3.5 Evaluaciones (quizzes)

| Módulo | Participantes | Puntuación media | Tasa aprobado (≥ 70%) |
|---|:---:|:---:|:---:|
{% for q in quizzes %}| {{ q.modulo }} | {{ q.participantes }} | {{ q.media }} | {{ q.tasa_aprobado }}% |
{% endfor %}

## 4. CONCLUSIONES DEL PERIODO

{{ conclusiones_texto }}

## 5. ÁREAS DE MEJORA IDENTIFICADAS

{% for mejora in areas_mejora %}- **{{ mejora.area }}**: {{ mejora.descripcion }}. Acción propuesta: {{ mejora.accion }}.
{% endfor %}

## 6. ACCIONES PARA EL SIGUIENTE PERIODO

| ID | Acción | Responsable | Plazo | Estado |
|---|---|---|---|:---:|
{% for ac in acciones_siguiente %}| {{ ac.id }} | {{ ac.descripcion }} | {{ ac.responsable }} | {{ ac.plazo }} | {{ ac.estado }} |
{% endfor %}

## 7. ELEVACIÓN AL COMITÉ DE SEGURIDAD

Los siguientes puntos requieren decisión o supervisión del Comité de Seguridad:

{% for elev in elevaciones_comite %}- {{ elev }}
{% endfor %}

## 8. ANEXOS

- **Anexo A**: detalle individualizado de cumplimiento por empleado (E-502 referenciado).
- **Anexo B**: detalle de cada campaña de phishing (E-503 referenciado).
- **Anexo C**: histórico anual de KPIs para análisis de tendencia.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
