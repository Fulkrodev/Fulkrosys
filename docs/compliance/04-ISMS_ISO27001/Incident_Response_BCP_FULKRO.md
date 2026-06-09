---
title: Plan de Respuesta ante Incidentes y Plan de Continuidad del Negocio
codigo: FULKRO-ISMS-IR-BCP-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Anual + post-incidente
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor ISO 27001
referencia_normativa: ISO/IEC 27001:2022 Anexo A.5.24 a A.5.30 (Gestión de incidentes y continuidad)
---

# Plan de Respuesta ante Incidentes y Plan de Continuidad del Negocio

El presente documento integra dos planes funcionalmente vinculados: el Plan de Respuesta ante Incidentes de Seguridad de la Información (Parte I) y el Plan de Continuidad del Negocio (Parte II). Su contenido satisface los requisitos de los controles A.5.24 a A.5.30 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

# Parte I · Plan de Respuesta ante Incidentes

## 1. Clasificación de severidad

Los incidentes de seguridad se clasifican en tres niveles de severidad, conforme a los siguientes criterios:

### 1.1 Severidad HIGH

Comprende, entre otros supuestos:

a) Brecha confirmada de datos personales con riesgo para los derechos y libertades de los interesados, en los términos del artículo 33 del Reglamento (UE) 2016/679.

b) Interrupción prolongada del servicio (superior a cuatro horas).

c) Compromiso confirmado de credenciales del administrador o de claves criptográficas críticas.

d) Compromiso del repositorio de código fuente.

### 1.2 Severidad MEDIUM

Comprende, entre otros supuestos:

a) Degradación del servicio que no constituya interrupción prolongada.

b) Alerta de seguridad confirmada que no haya resultado en compromiso material.

c) Expiración inminente o no renovada de Acuerdo de Encargo de Tratamiento con sub-procesador.

d) Tentativas reiteradas de acceso no autorizado.

### 1.3 Severidad LOW

Comprende anomalías menores y eventos meramente informativos que requieran documentación pero no acción inmediata.

## 2. Equipo de respuesta

### 2.1 Líder único

Marcos Mata García asume la dirección única del equipo de respuesta ante incidentes, en su condición de Responsable de Seguridad de la Información.

### 2.2 Escalado a autoridades externas

Procederá el escalado a las siguientes autoridades en función del tipo de incidente:

a) Agencia Española de Protección de Datos (AEPD): brechas de seguridad con afectación de datos personales, conforme al artículo 33 del Reglamento (UE) 2016/679.

b) INCIBE-CERT: incidentes con relevancia bajo la Directiva (UE) 2022/2555 (NIS2), conforme a procedimiento voluntario detallado en el documento FULKRO-NIS2-NOT-001.

### 2.3 Coordinación con sub-procesadores

En caso de incidentes que afecten a la cadena de sub-procesadores, procederá la notificación bilateral inmediata al sub-procesador afectado, conforme a los términos de cada Acuerdo de Encargo de Tratamiento.

## 3. Procedimiento en cinco fases

### 3.1 Detección

La detección de incidentes se realiza mediante:

a) Sistema Self-Monitoring de FULKRO, con diecisiete o más controles continuos en arquitectura de plugins.

b) Alertas remitidas por sub-procesadores.

c) Comunicaciones procedentes de investigadores de seguridad a través del canal security@fulkro.es.

d) Notificaciones de autoridades competentes.

### 3.2 Contención

Las medidas de contención inmediatas comprenden, entre otras:

a) Revocación de credenciales potencialmente comprometidas.

b) Aislamiento de sistemas afectados.

c) Bloqueo de tráfico de origen identificado como malicioso.

d) Activación de planes específicos según el tipo de incidente.

### 3.3 Erradicación

Comprende el análisis de causa raíz del incidente, la identificación y subsanación de las vulnerabilidades explotadas y la aplicación de los parches o reconfiguraciones precisas.

### 3.4 Recuperación

Comprende la restauración de los sistemas afectados a partir de copias de seguridad íntegras, la verificación de la integridad del sistema recuperado y el restablecimiento progresivo del servicio.

### 3.5 Lecciones aprendidas

Toda intervención de respuesta concluirá con la documentación formal de la lección aprendida, conforme al patrón de cementación documental LECCIÓN-OPS. Las lecciones aprendidas alimentan la revisión continua de la presente Política y de los procedimientos asociados, integrándose en el ciclo de mejora continua del Sistema de Gestión.

## 4. Comunicación con grupos de interés

### 4.1 Notificación a interesados

Procederá la notificación a los interesados afectados cuando concurran las circunstancias previstas en el artículo 34 del Reglamento (UE) 2016/679, en el plazo establecido y a través del canal habilitado al efecto. El formato de la comunicación seguirá la plantilla MJML de notificación de brecha implementada en el motor M18.

### 4.2 Notificación a la AEPD

La notificación a la Agencia Española de Protección de Datos se realizará en el plazo máximo de setenta y dos horas desde el momento en que el responsable tenga conocimiento del incidente, conforme al artículo 33 del Reglamento (UE) 2016/679, a través de la Sede Electrónica de la AEPD.

### 4.3 Notificación a INCIBE-CERT

Para los supuestos de incidentes relevantes bajo NIS2, se observará el procedimiento detallado en el documento FULKRO-NIS2-NOT-001, con el siguiente cadenciado: alerta temprana (veinticuatro horas), notificación formal (setenta y dos horas) e informe final (un mes).

### 4.4 Notificación a sub-procesadores

Procederá la notificación bilateral inmediata a cualquier sub-procesador afectado por el incidente, conforme a los términos del correspondiente Acuerdo de Encargo de Tratamiento.

## 5. Revisión post-incidente

Toda intervención de respuesta ante incidente concluirá con la realización de las siguientes actuaciones:

a) Elaboración de un informe documental de la incidencia y su tratamiento.

b) Actualización de las políticas y procedimientos cuando proceda.

c) Diseño y, en su caso, ejecución de escenarios de prueba derivados del incidente.

d) Comunicación a los grupos de interés que proceda sobre las medidas correctivas implantadas.

# Parte II · Plan de Continuidad del Negocio

## 1. Objetivos de recuperación

### 1.1 Tiempo Objetivo de Recuperación (RTO)

El Tiempo Objetivo de Recuperación se establece en cuatro horas. Este objetivo se justifica conforme a la escala de operación actual (micro-organización con clientes piloto) y a las características del servicio prestado.

### 1.2 Punto Objetivo de Recuperación (RPO)

El Punto Objetivo de Recuperación se establece en veinticuatro horas, lo que se garantiza mediante el régimen de copias de seguridad diarias.

## 2. Escenarios de desastre contemplados

### 2.1 Interrupción del hosting principal

Escenario: interrupción del servicio Hetzner Falkenstein.

Respuesta: activación del procedimiento de conmutación a la región secundaria Hetzner Helsinki, con restauración desde copias de seguridad replicadas.

### 2.2 Compromiso de credenciales API

Escenario: compromiso confirmado de credenciales de sub-procesador.

Respuesta: rotación inmediata de credenciales, revisión de registros de actividad y notificación bilateral al sub-procesador.

### 2.3 Incapacitación del titular

Escenario: incapacitación temporal o permanente de Marcos Mata García.

Respuesta: activación del plan de sucesión previsto. Con vigencia desde el cuarto trimestre del año 2026 se establecerá un mecanismo de custodia externa de credenciales críticas (key escrow).

### 2.4 Interrupción del proveedor de correo

Escenario: interrupción del servicio Postmark.

Respuesta: activación de proveedor SMTP secundario para el envío de comunicaciones críticas.

### 2.5 Interrupción del proveedor de inteligencia artificial

Escenario: interrupción del servicio Anthropic.

Respuesta: paso a modo degradado con respuestas en caché para funcionalidades dependientes, manteniendo la operación esencial mediante mecanismos deterministas.

### 2.6 Interrupción del proveedor de mensajería

Escenario: interrupción del servicio 360dialog.

Respuesta: comunicaciones únicamente por correo electrónico mientras se restablece el canal WhatsApp Business.

## 3. Procedimientos de recuperación

### 3.1 Esquema de copias de seguridad

a) Copias diarias cifradas, con replicación a región geográfica distinta del entorno de producción.

b) Archivo mensual con retención de doce meses.

c) Almacenamiento en frío trimestral con retención de siete años en cumplimiento de la obligación de retención del artículo 24.1 del Real Decreto 311/2022.

### 3.2 Restauración

La restauración se realizará conforme al runbook documentado, con verificación obligatoria de integridad mediante comparación con sumas hash registradas.

## 4. Pruebas periódicas

### 4.1 Ensayo semestral de recuperación ante desastre

Se realizará un ensayo semestral de recuperación ante desastre, fijándose el próximo para el tercer trimestre del año 2026.

### 4.2 Ensayo trimestral de restauración de copias

Se realizará un ensayo trimestral de restauración de copias de seguridad, con verificación de integridad y registro documental del resultado.

## 5. Aprobación

**Firma**: Marcos Mata García
**Cargo**: Responsable de Seguridad de la Información (interim)
**Fecha**: 12 de mayo de 2026

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
