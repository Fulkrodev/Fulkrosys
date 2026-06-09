# PLAN DE PRUEBAS DE CONTINUIDAD DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-405 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Plan de Pruebas de Continuidad ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Plan establece el calendario, los tipos, los criterios de éxito, los participantes y la documentación de los ejercicios de prueba que validan la eficacia del Plan de Continuidad del Negocio (E-402 BCP) y del Plan de Recuperación de Desastres TIC (E-403 DRP) de {{ cliente.razon_social }}, en cumplimiento de:

- **Esquema Nacional de Seguridad** (RD 311/2022, medida **op.cont.4 Medios alternativos**, en su requerimiento de pruebas periódicas).
- **UNE-ISO 22301:2020** Cláusula 8.5 (Ejercicios y pruebas).
- **DORA Art. 24** (Programa de pruebas de resiliencia operativa digital) si aplica al sector financiero.
- **NIS2** (Medidas de gestión de riesgos · pruebas periódicas).

## 2. CALENDARIO ANUAL DE EJERCICIOS

El programa anual de pruebas contempla, como mínimo, los siguientes ejercicios:

| Tipo de ejercicio | Frecuencia | Trimestre objetivo | Categoría ENS aplicable |
|---|---|---|---|
| Tabletop BCP | Semestral (2/año) | Q1 + Q3 | B/M/A |
| Tabletop DRP técnico | Anual | Q2 | M/A |
| Simulacro técnico failover | Anual | Q3 o Q4 | M/A |
| Prueba completa de restauración desde backup | Anual | Q4 | B/M/A |
| Prueba parcial de restauración granular | Trimestral | Cada trimestre | M/A |
| Simulacro de phishing (vinculado al LMS) | Trimestral o mensual | Calendario LMS | B/M/A |
| TLPT / Red Team (Threat-Led Penetration Testing) | Cada 3 años | Plan plurianual | A (o DORA significativa) |

El calendario detallado del ejercicio se planifica en el cuarto trimestre del año anterior y se aprueba por {{ cliente.organo_aprobador_politicas }}.

## 3. TIPOS DE PRUEBAS · DESCRIPCIÓN

### 3.1 Tabletop (escritorio)

**Descripción**: ejercicio sin impacto operativo en el que los participantes analizan un escenario hipotético y discuten las acciones que ejecutarían.

**Objetivo**: validar que los participantes conocen sus responsabilidades, los procedimientos y los recursos disponibles.

**Duración**: 2-4 horas.

**Participantes**: Comité de Continuidad + coordinadores BCP/DRP/Operaciones/Comunicación.

### 3.2 Simulacro técnico de failover

**Descripción**: ejecución real de un failover sobre un componente o sistema crítico, ya sea en producción (con ventana planificada) o en entorno equivalente aislado.

**Objetivo**: validar que la arquitectura de recuperación funciona conforme a lo diseñado y que el RTO técnico es alcanzable.

**Duración**: variable según sistema (típicamente entre 4 y 24 horas).

**Participantes**: equipo TIC, coordinador DRP, observadores designados.

### 3.3 Prueba de restauración desde backup

**Descripción**: restauración real desde copia de seguridad en un entorno aislado, con validación de integridad de los datos.

**Objetivo**: validar la calidad del backup, el procedimiento de restauración y la consistencia de los datos.

**Duración**: variable (típicamente entre 2 y 12 horas).

**Participantes**: equipo de operación TIC + propietario funcional del dato cuando aplique.

### 3.4 Simulacro de phishing

**Descripción**: envío controlado de un correo simulado de phishing a un grupo o a la totalidad del personal.

**Objetivo**: medir el nivel de concienciación y la eficacia de la formación impartida.

**Duración**: campaña típicamente de 7-14 días con seguimiento de métricas.

**Participantes**: gestionado desde el LMS conforme a la política E-103 + E-105.

### 3.5 TLPT / Red Team

**Descripción**: ejercicio de pentest dirigido por inteligencia de amenazas, ejecutado por un proveedor externo cualificado.

**Objetivo**: medir la resiliencia ante un adversario con tácticas, técnicas y procedimientos realistas (TTPs).

**Frecuencia**: cada 3 años en categoría ALTA o cuando lo exija DORA en entidades financieras significativas.

## 4. CRITERIOS DE ÉXITO

Cada ejercicio define previamente sus criterios de éxito, alineados con los objetivos definidos en el BIA. Indicadores típicos:

- **RTO real ≤ RTO objetivo** para el componente o proceso ejercitado.
- **RPO real ≤ RPO objetivo** medido en el ejercicio.
- **Porcentaje de checklist completado**: ≥ 90% considerado éxito.
- **Participación**: ≥ 90% de los asistentes convocados.
- **Detección de gaps**: cualquier ejercicio que detecte gaps significativos es valioso por aprendizaje, aunque no cumpla otros indicadores.

## 5. ROLES EN LAS PRUEBAS

| Rol | Responsabilidad |
|---|---|
| **Facilitador** | Diseña el escenario, conduce el ejercicio, mantiene el ritmo |
| **Observadores** | Toman notas objetivas del comportamiento, las decisiones y los tiempos |
| **Participantes operativos** | Ejecutan los procedimientos como lo harían en una crisis real |
| **Coordinador post-mortem** | Lidera la sesión de lecciones aprendidas y redacta el informe E-406 |
| **Patrocinador ejecutivo** | Aprueba el ejercicio y respalda la asignación de recursos |

## 6. RECURSOS REQUERIDOS

Para cada ejercicio se planifican los recursos necesarios:

- **Recursos técnicos**: entornos aislados, capacidad de cómputo, ventanas de mantenimiento, herramientas de monitorización.
- **Recursos humanos**: liberación de los participantes durante la duración del ejercicio, formación previa cuando aplique.
- **Recursos financieros**: presupuesto asignado dentro de la partida anual de continuidad.
- **Recursos documentales**: runbooks, BIA, BCP, DRP accesibles a los participantes durante el ejercicio.

## 7. CAPTURA DE EVIDENCIAS

Durante el ejercicio se capturan:

- **Logs técnicos**: del sistema bajo prueba, del SIEM, de los sistemas de monitorización.
- **Capturas de pantalla** de los pasos clave.
- **Cronología detallada** con timestamps de cada decisión y acción.
- **Hoja de asistencia** firmada por los participantes.
- **Observaciones cualitativas** de los observadores designados.

Toda la documentación se conserva en el repositorio de evidencias del BCMS conforme a la política documental.

## 8. APROVECHAMIENTO DE RESULTADOS

Los resultados de cada ejercicio se documentan en un **Informe de Pruebas (E-406)** que incluye los gaps detectados y un plan de acción correctivo con responsable y plazo.

Los gaps se incorporan al **registro de no conformidades** del SGSI y son objeto de seguimiento hasta su cierre. Los gaps no cerrados se reportan al Comité de Seguridad y a {{ cliente.organo_aprobador_politicas }}.

Los aprendizajes alimentan la revisión anual del BIA, BCP, DRP y de las estrategias E-401.

## 9. COMUNICACIÓN PREVIA AL EJERCICIO

Salvo en simulacros de phishing (cuya eficacia depende del factor sorpresa para el participante), todos los ejercicios se comunican con antelación a los participantes con la siguiente información:

- Fecha y duración del ejercicio.
- Tipo de prueba y alcance.
- Participantes convocados.
- Objetivos generales.

**No se comunica** el escenario específico, las inyecciones que se introducirán durante el ejercicio, ni las decisiones que se evalúan, para preservar la capacidad de medir la reacción real.

## 10. CALENDARIO PLANIFICADO PARA EL EJERCICIO EN CURSO

| Ejercicio | Fecha planificada | Responsable | Alcance |
|---|---|---|---|
{% for ej in ejercicios_planificados %}| {{ ej.tipo }} | {{ ej.fecha }} | {{ ej.responsable }} | {{ ej.alcance }} |
{% endfor %}

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
