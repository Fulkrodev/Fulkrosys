# PLAN ANUAL DE FORMACIÓN Y CONCIENCIACIÓN DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-500 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Plan Anual de Formación y Concienciación ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Plan establece el programa anual de formación y concienciación en seguridad de la información de {{ cliente.razon_social }} aplicable al sistema {{ proyecto.sistema_principal }}, en cumplimiento de:

- **Esquema Nacional de Seguridad** (Real Decreto 311/2022), Anexo II, medidas **mp.per.3 Concienciación** y **mp.per.4 Formación**.
- **RGPD Art. 32** (medidas técnicas y organizativas, incluyendo formación).
- **Directiva NIS2 Art. 20** y **Art. 21.2** (formación en ciberseguridad para órganos de dirección y personal).
- **CCN-STIC-481** Guía de concienciación bajo el ENS.

Este Plan se complementa con los catálogos de materiales (E-501), los registros de asistencia y evaluación (E-502), los informes de simulacros de phishing (E-503) y el cuadro de mando de KPIs (E-504).

## 2. ALCANCE

El Plan aplica a la totalidad del personal de {{ cliente.razon_social }} con acceso a sistemas, datos o instalaciones bajo el alcance ENS, incluyendo:

- Personal en plantilla (empleados con contrato laboral).
- Personal externo con acceso continuado (consultores, becarios, proveedores).
- Órganos de dirección y administración.
- Roles ENS designados (Responsables de Seguridad, Sistema, Servicio, Información).

Se excluyen visitantes puntuales sin acceso a sistemas, quienes reciben información mínima de seguridad conforme al procedimiento E-229.

## 3. GRUPOS DE AUDIENCIA G1-G6

La formación se organiza por seis grupos de audiencia conforme al perfil de exposición a riesgos y a las responsabilidades del rol:

| Grupo | Audiencia | Horas mínimas/año | Frecuencia | Contenido |
|:---:|---|:---:|:---:|---|
| **G1** | Todos los empleados | Sesión de acogida 2h + píldoras trimestrales | Trimestral | Concienciación general · phishing awareness · higiene de credenciales · clean desk · uso aceptable de recursos |
| **G2** | Personal con acceso a datos personales | 4h/año | Anual | RGPD aplicado · Registro de Actividades de Tratamiento (ROPA) · responsabilidades · gestión de brechas |
| **G3** | Personal técnico (operaciones, sistemas, desarrollo) | 16h/año | Trimestral | Configuración segura · gestión de vulnerabilidades · operación segura diaria · respuesta técnica a incidentes |
| **G4** | Personal con accesos privilegiados (administradores, DevOps, SRE) | 24h/año | Trimestral | Gestión de accesos privilegiados (PAM) · hardening avanzado · DevSecOps · principios de forensics |
| **G5** | Ejecutivos y miembros del Comité de Dirección | 4h/año | Semestral | Briefings ejecutivos · responsabilidades legales (ENS, RGPD, NIS2 si aplica, DORA si aplica) · gobernanza · gestión de crisis |
| **G6** | Roles ENS designados | 16h/año | Trimestral | Esquema Nacional de Seguridad · responsabilidades específicas · auditorías · gestión formal de incidentes |

Cada empleado se asigna al grupo principal correspondiente a su rol. Un empleado puede pertenecer simultáneamente a varios grupos (p. ej., un administrador de sistemas pertenece a G1 + G3 + G4).

## 4. SESIÓN DE ACOGIDA OBLIGATORIA

Toda persona que se incorpore a {{ cliente.razon_social }} en una posición con acceso a sistemas o datos bajo el alcance ENS debe completar la **Sesión de Acogida** dentro de su primer mes de incorporación. Duración mínima: 2 horas. Contenidos:

- Política de Seguridad (E-100) — 15 minutos.
- Política de Uso Aceptable (E-109) — 15 minutos.
- Gestión de identidades y credenciales — 30 minutos.
- Procedimiento de reporte de incidentes (E-204) — 15 minutos.
- Concienciación frente al phishing — 30 minutos.
- Firma digital de la asistencia y compromiso de cumplimiento — 15 minutos.

El cumplimiento de la sesión de acogida en plazo (100% de los nuevos empleados) es un KPI clave del Plan.

## 5. CALENDARIO ANUAL DE ACTIVIDADES

| Trimestre | Actividades planificadas |
|:---:|---|
| **Q1** | Sesión de acogida (continua) · Píldora G1 · Sesión G3 · Sesión G4 · Sesión G6 · Simulacro de phishing trimestral · Briefing G5 (semestral) |
| **Q2** | Sesión de acogida (continua) · Píldora G1 · Sesión G3 · Sesión G4 · Sesión G6 · Simulacro de phishing trimestral · Curso G2 (anual) |
| **Q3** | Sesión de acogida (continua) · Píldora G1 · Sesión G3 · Sesión G4 · Sesión G6 · Simulacro de phishing trimestral · Briefing G5 (semestral) |
| **Q4** | Sesión de acogida (continua) · Píldora G1 · Sesión G3 · Sesión G4 · Sesión G6 · Simulacro de phishing trimestral · Auditoría interna del Plan · Revisión KPIs (E-504) |

El calendario detallado con fechas específicas se publica en el portal interno y se mantiene actualizado por el responsable de formación.

## 6. KPIs DE SEGUIMIENTO

| KPI | Objetivo | Método de medida | Reportado a |
|---|:---:|---|---|
| Cobertura del Plan Anual | ≥ 95% | (Empleados con plan completado / total empleados con plan asignado) × 100 | E-504 trimestral |
| Sesión de acogida en plazo | 100% | (Nuevos empleados con acogida completada en 30 días / total nuevos empleados) × 100 | E-504 trimestral |
| Horas mínimas G3-G4 | ≥ 90% | (Empleados G3/G4 que cumplen horas anuales / total) × 100 | E-504 anual |
| Tasa de click en phishing | < 10% (objetivo) · 5% (ideal) | Resultados de campañas E-503 | E-504 trimestral |
| Notificación correcta de phishing | ≥ 50% | (Empleados que reportan phishing a IT-Sec / total receptores) × 100 | E-504 trimestral |
| Aprobación de quiz por módulo | ≥ 70% threshold | Puntuación media por módulo | E-502 continuo |

## 7. RESPONSABILIDADES

- **Comité de Seguridad**: aprueba el Plan, supervisa los KPIs y autoriza desviaciones.
- **{{ responsables.responsable_seguridad.nombre }}** ({{ responsables.responsable_seguridad.cargo }}): coordina la ejecución global del Plan, mantiene los catálogos E-501 y reporta KPIs en E-504.
- **Responsables de área**: garantizan que su equipo completa las horas asignadas dentro de plazo.
- **Empleados**: completan las actividades asignadas dentro de los plazos comunicados.
- **DPO** (cuando aplique): supervisa los contenidos de los módulos G2 y la coherencia con el RGPD.

## 8. PLATAFORMA DE FORMACIÓN

La impartición y el seguimiento de la formación se gestionan mediante la plataforma externa **{{ lms.plataforma }}**. Los simulacros de phishing se ejecutan mediante **{{ lms.phishing_plataforma }}**.

FULKRO mantiene la trazabilidad documental del Plan, captura las evidencias generadas por la plataforma externa y produce los documentos E-501 a E-504 de cara a auditoría.

## 9. PRESUPUESTO Y RECURSOS

El Plan dispone de partida presupuestaria específica en el ejercicio en curso, que cubre:

- Licencias de la plataforma LMS y de simulación de phishing.
- Materiales y módulos especializados (G2 RGPD, G4 DevSecOps, G6 ENS).
- Formación externa cuando se requiera (cursos certificados, conferencias sectoriales).
- Horas internas dedicadas a impartir píldoras y a auditar la asistencia.

## 10. REVISIÓN Y ACTUALIZACIÓN DEL PLAN

El Plan se revisa con periodicidad **anual** dentro del primer trimestre del año y se actualiza siempre que:

- Cambie la plantilla relevante o se incorporen nuevos roles bajo el alcance ENS.
- Los resultados de campañas de phishing E-503 evidencien necesidades específicas.
- Se materialicen incidentes de seguridad con causa raíz formativa.
- Cambie la normativa aplicable (ENS, RGPD, NIS2, DORA).
- Los KPIs queden por debajo del objetivo durante dos trimestres consecutivos.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
