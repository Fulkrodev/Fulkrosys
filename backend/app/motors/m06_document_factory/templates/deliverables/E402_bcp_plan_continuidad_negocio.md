# PLAN DE CONTINUIDAD DEL NEGOCIO DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-402 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Plan de Continuidad del Negocio (BCP) ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO

El presente Plan establece las acciones que {{ cliente.razon_social }} debe ejecutar cuando se produce una disrupción mayor que compromete la operación normal del sistema {{ proyecto.sistema_principal }}, con el fin de:

- Preservar la vida y la seguridad de las personas.
- Restaurar los procesos críticos en los plazos definidos en el BIA E-400.
- Limitar los impactos económicos, reputacionales, legales y operativos.
- Cumplir las obligaciones del Esquema Nacional de Seguridad (RD 311/2022, medida **op.cont.2 Plan de Continuidad**) y normas concurrentes (UNE-ISO 22301:2020).

## 2. ALCANCE

El BCP aplica al sistema {{ proyecto.sistema_principal }} en su alcance {{ proyecto.alcance }} y al conjunto de procesos críticos identificados en el E-400 BIA. Cubre disrupciones originadas por causas naturales, técnicas, humanas, de cadena de suministro o ciberataque.

Quedan fuera del BCP los procedimientos técnicos detallados de recuperación de sistemas TIC, desarrollados en el Plan de Recuperación de Desastres (E-403 DRP).

## 3. ESTRUCTURA ORGANIZATIVA DE LA CONTINUIDAD

### 3.1 Comité de Continuidad

Órgano de gobierno responsable de la activación, dirección y desactivación del BCP. Composición:

- **Presidente**: {{ responsables.comite_seguridad.presidente }} ({{ cliente.organo_aprobador_politicas }}).
- **Secretario**: {{ responsables.comite_seguridad.secretario }}.
- **Miembros**: {{ responsables.comite_seguridad.miembros|join(', ') }}.

Decisiones cubiertas: declaración formal del incidente como activador del BCP, asignación de recursos extraordinarios, comunicación a stakeholders externos y declaración de fin de la crisis.

### 3.2 Equipo de Coordinación BCP

Lidera la ejecución operativa del BCP bajo el mandato del Comité. Roles:

- **Coordinador BCP**: {{ responsables.responsable_seguridad.nombre }}. Conduce la ejecución diaria.
- **Coordinador TIC**: {{ responsables.responsable_sistema.nombre }}. Lidera la recuperación técnica conforme al DRP.
- **Coordinador Operaciones**: {{ responsables.responsable_servicio.nombre }}. Gestiona los procesos de negocio en modo contingencia.
- **Coordinador Comunicación**: designado conforme al E-404.

### 3.3 Equipos Operativos por Proceso Crítico

Cada proceso crítico del E-400 BIA cuenta con un equipo operativo designado, con titular y suplente, capaz de ejecutar el procedimiento de contingencia correspondiente.

## 4. CRITERIOS DE ACTIVACIÓN

Se considera activador del BCP cualquier evento que cumpla uno o más de los siguientes criterios:

- Indisponibilidad estimada de un proceso crítico superior a su RTO objetivo definido en el BIA.
- Pérdida total o parcial de la ubicación principal de operaciones.
- Ciberataque masivo o brecha de seguridad que afecte a sistemas críticos del alcance ENS.
- Indisponibilidad simultánea de personal clave que impida la continuidad operativa.
- Indisponibilidad mantenida de un proveedor crítico sin sustituto inmediato.
- Crisis sanitaria, climática o de seguridad pública declarada por las autoridades.

## 5. PROTOCOLO DE ACTIVACIÓN

La activación del BCP se ejecuta conforme a las siguientes fases:

### Fase 1 · Detección y notificación inicial (0-30 min)

Cualquier empleado o sistema de monitorización (SIEM/SOC) que detecte un evento que cumpla los criterios anteriores debe notificar inmediatamente a {{ responsables.responsable_seguridad.nombre }} a través de los canales definidos.

### Fase 2 · Evaluación preliminar (30-90 min)

El Coordinador BCP evalúa el alcance del evento y determina si procede convocar al Comité de Continuidad.

### Fase 3 · Declaración formal (en 2 horas máximo)

El Comité de Continuidad, reunido presencialmente o por canal alterno, declara formalmente la activación del BCP. La declaración incluye:

- Identificación del evento activador.
- Procesos críticos afectados.
- Designación del Coordinador BCP en funciones.
- Autorización para ejecutar recursos extraordinarios.

### Fase 4 · Comunicación inicial

Conforme al Plan de Comunicaciones en Crisis E-404 se notifica a stakeholders internos y, en su caso, externos.

### Fase 5 · Ejecución operativa

Los equipos operativos ejecutan los procedimientos de contingencia correspondientes a cada proceso crítico. El Coordinador TIC, en paralelo, activa el DRP E-403.

## 6. PROCEDIMIENTOS OPERATIVOS POR PROCESO

Para cada proceso crítico identificado, el siguiente apartado documenta los pasos en modo contingencia:

{% for serv in servicios_criticos %}### 6.{{ loop.index }} · {{ serv.nombre }}

- **RTO objetivo**: {{ serv.rto }}.
- **Responsable contingencia**: {{ serv.responsable }}.
- **Procedimiento**: {{ serv.procedimiento }}.
- **Recursos requeridos**: {{ serv.recursos }}.
{% endfor %}

El detalle técnico de la recuperación TIC se desarrolla en el E-403 DRP.

## 7. COMUNICACIÓN DURANTE LA CRISIS

La comunicación interna y externa durante la activación del BCP se rige por el Plan de Comunicaciones en Crisis (E-404), que incluye:

- Stakeholders matrix con prioridades y canales.
- Plantillas de comunicación por audiencia.
- Designación de portavoces autorizados.
- Notificación obligatoria a autoridades cuando proceda (AEPD 72h, CCN-CERT/INCIBE-CERT bajo NIS2, Banco de España/CNMV bajo DORA si aplica).

## 8. RECUPERACIÓN POR FASES

La vuelta a la normalidad se ejecuta en tres fases:

### Fase A · Estabilización (primeras 24-72h)

- Confirmación de la seguridad de las personas.
- Operación de procesos críticos en modo contingencia.
- Comunicación a stakeholders prioritarios.
- Documentación inicial del incidente para informe posterior.

### Fase B · Normalización (días 3-15)

- Restauración progresiva de procesos no críticos.
- Sustitución de soluciones temporales por la operación habitual.
- Análisis de impacto económico y reputacional.

### Fase C · Vuelta a la normalidad (días 15-30)

- Operación al 100% en condiciones normales.
- Conciliación de pérdidas y reclamaciones a seguros y terceros si procede.
- Identificación de lecciones aprendidas.

## 9. DESACTIVACIÓN DEL BCP Y LECCIONES APRENDIDAS

El Comité de Continuidad declara formalmente el fin de la activación una vez restituido el servicio normal.

Dentro de los **30 días naturales** siguientes a la desactivación se emite un Informe de Lecciones Aprendidas que incluye:

- Cronología detallada del incidente.
- Métricas reales de RTO y RPO alcanzados vs objetivos.
- Eficacia de las estrategias activadas.
- Gaps detectados en personas, procesos o tecnología.
- Plan de acción correctivo.

Las lecciones aprendidas se incorporan a la revisión anual del BIA, BCP, DRP y estrategias.

## 10. MANTENIMIENTO DEL PLAN

El presente BCP se revisa con periodicidad **anual** y se actualiza siempre que:

- Se incorpore o retire un proceso del catálogo de críticos.
- Se modifique la estructura organizativa relevante.
- Se incorpore o retire un proveedor crítico.
- Se obtengan lecciones aprendidas tras un ejercicio (E-406) o incidente real.

## 11. ANEXOS

- **Anexo A**: Lista de contactos críticos internos (24/7).
- **Anexo B**: Lista de proveedores críticos y contactos de emergencia.
- **Anexo C**: Ubicaciones alternas y procedimientos de activación.
- **Anexo D**: Mapa de dependencias entre procesos críticos.
- **Anexo E**: Plantillas de actas del Comité de Continuidad.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
