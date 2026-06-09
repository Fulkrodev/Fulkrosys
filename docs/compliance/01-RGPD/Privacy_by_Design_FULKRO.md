---
title: Política de Privacidad desde el Diseño y por Defecto
codigo: FULKRO-RGPD-PBD-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Delegado de Protección de Datos (interim)
clasificacion: Público · Trust Center · Auditor · Interno
marco_normativo:
  - Reglamento (UE) 2016/679 (RGPD) Artículo 25
---

# Política de Privacidad desde el Diseño y por Defecto de FULKRO

La presente Política desarrolla los principios establecidos en el artículo 25 del Reglamento (UE) 2016/679, "Protección de datos desde el diseño y por defecto", documentando la implantación efectiva en la arquitectura de FULKRO de los siete principios fundamentales que se exponen a continuación.

## 1. Minimización de datos (artículo 5.1.c RGPD)

La recopilación de datos personales se limita estrictamente a los datos necesarios para la finalidad de cada tratamiento, conforme al inventario documentado en el Registro de Actividades de Tratamiento.

El Registro de Actividades de Tratamiento integra diez tratamientos identificados como T001 a T010.

FULKRO no procesa categorías especiales de datos personales conforme al artículo 9 del Reglamento (UE) 2016/679. Esta exclusión se ha implantado de manera expresa en el diseño de la plataforma, mediante la verificación de la inexistencia de campos destinados al almacenamiento de datos de salud, datos genéticos, datos biométricos, datos relativos al origen racial o étnico, opiniones políticas, convicciones religiosas o filosóficas, afiliación sindical, datos relativos a la vida sexual o orientación sexual.

## 2. Limitación de la finalidad (artículo 5.1.b RGPD)

Para cada uno de los tratamientos identificados en el Registro de Actividades de Tratamiento, FULKRO documenta de manera explícita:

a) La finalidad específica perseguida.

b) La base legal aplicable, conforme al artículo 6 del Reglamento (UE) 2016/679.

c) Las categorías de datos tratados.

d) Las categorías de destinatarios.

e) El plazo de conservación aplicable.

No se admite la reutilización de los datos para finalidades distintas de las originalmente declaradas, sin la concurrencia previa de una nueva base legal válida y, en su caso, de la correspondiente comunicación al interesado conforme al artículo 13 del Reglamento (UE) 2016/679.

## 3. Limitación del plazo de conservación (artículo 5.1.e RGPD)

El plazo máximo de retención de los registros de auditoría se establece en siete años, en cumplimiento del artículo 24.1 del Real Decreto 311/2022 (Esquema Nacional de Seguridad).

Transcurrido el plazo de retención aplicable, se aplica el procedimiento de tombstone anonymization conforme al cual se sustituyen los identificadores personales por tokens anonimizados, preservando la integridad de la cadena de auditoría exigida por la normativa de aplicación.

El detalle pormenorizado del régimen de retención se encuentra recogido en el documento FULKRO-RGPD-RET-001 (Política de Retención de Datos).

## 4. Configuración predeterminada respetuosa con la privacidad (artículo 25.2 RGPD)

FULKRO implanta como configuración predeterminada las opciones más respetuosas con la privacidad del interesado:

### 4.1 Consentimiento de cookies

El consentimiento se encuentra desactivado por defecto. El banner de cookies presenta tres opciones con prominencia visual idéntica, conforme a la Guía de Cookies de la Agencia Española de Protección de Datos publicada en 2020.

### 4.2 Analítica de marketing

La analítica de marketing opera exclusivamente en régimen de opt-in (consentimiento expreso), con verificación continua mediante el control `check_marketing_analytics_opt_in_only` del sistema Self-Monitoring.

### 4.3 Suscripción a notificaciones

Las suscripciones a notificaciones operan exclusivamente en régimen de opt-in.

### 4.4 Digest WhatsApp para clientes

El digest diario por WhatsApp ofrecido a clientes de nivel MEDIA opera exclusivamente en régimen de opt-in.

## 5. Seudonimización

### 5.1 Aplicación al servicio de inteligencia artificial

Los datos enviados al sub-procesador Anthropic PBC, en el ejercicio del servicio de inteligencia artificial generativa, se someten a seudonimización previa al envío, garantizándose la ausencia de identificadores personales en la información transferida.

### 5.2 Aplicación a los registros de auditoría

Los registros de auditoría se someten al procedimiento de tombstone anonymization una vez expirado el plazo de retención obligatoria, preservando la integridad de la cadena auditable.

### 5.3 Aplicación a la analítica

Los datos analíticos se procesan exclusivamente en forma agregada, sin información identificable a nivel de fila individual.

## 6. Cifrado

### 6.1 Cifrado en tránsito

El cifrado en tránsito se garantiza mediante la utilización obligatoria del protocolo TLS versión 1.3 en la totalidad del tráfico de red.

### 6.2 Cifrado en reposo

a) Bases de datos: Transparent Data Encryption en PostgreSQL.

b) Almacenamiento de objetos: AES-256 en MinIO.

### 6.3 Firma criptográfica extremo a extremo

El sistema de firma documental M5 utiliza pares de claves Ed25519, garantizando la integridad y autenticidad de los documentos firmados sin posibilidad de acceso de FULKRO al contenido firmado por el cliente.

## 7. Transparencia (artículos 12 a 14 RGPD)

### 7.1 Política de Privacidad

FULKRO mantiene una Política de Privacidad pública que cumple los requisitos de información establecidos en los artículos 13 y 14 del Reglamento (UE) 2016/679.

### 7.2 Lista de sub-procesadores

Se publica de manera pública la lista actualizada de sub-procesadores, conforme al documento FULKRO-SUB-LIST-001.

### 7.3 Trust Center

Se mantiene un Trust Center público con el Whitepaper de Seguridad y los indicadores de cumplimiento por norma aplicable.

### 7.4 Banner de cookies

El banner de cookies proporciona información detallada por cada categoría de cookies utilizada, conforme a la Guía de la Agencia Española de Protección de Datos publicada en 2020.

### 7.5 Endpoints de ejercicio de derechos

Se ofrecen endpoints específicos para el ejercicio de los derechos reconocidos en los artículos 15, 17 y 20 del Reglamento (UE) 2016/679 (derecho de acceso, derecho de supresión y derecho a la portabilidad de los datos).

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
