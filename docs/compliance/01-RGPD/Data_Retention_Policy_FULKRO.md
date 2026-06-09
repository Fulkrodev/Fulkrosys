---
title: Política de Retención de Datos
codigo: FULKRO-RGPD-RET-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Delegado de Protección de Datos (interim)
clasificacion: Público · Trust Center · Auditor · Interno
marco_normativo:
  - Reglamento (UE) 2016/679 (RGPD) Artículo 5.1.e), Artículo 17, Artículo 30.4
  - Real Decreto 311/2022 (ENS) Artículo 24.1
---

# Política de Retención de Datos de FULKRO

## 1. Principios de retención

### 1.1 Principio de minimización temporal

Los datos personales se retienen exclusivamente durante el plazo necesario para el cumplimiento de la finalidad para la que fueron recabados, conforme al artículo 5.1.e) del Reglamento (UE) 2016/679.

### 1.2 Cumplimiento de la obligación de retención del Esquema Nacional de Seguridad

El plazo mínimo de retención de los registros de auditoría es de siete años, en cumplimiento del artículo 24.1 del Real Decreto 311/2022.

### 1.3 Anonimización en lugar de eliminación

FULKRO aplica con carácter general el procedimiento de tombstone anonymization en lugar de la eliminación material de los datos, a fin de preservar la integridad de la cadena de auditoría conforme a las exigencias normativas, sin perjuicio del cumplimiento de las solicitudes de supresión presentadas por los interesados conforme al artículo 17 del Reglamento (UE) 2016/679 en los términos previstos en la sección 3.

## 2. Retención por categoría de datos

| Categoría de datos | Plazo de retención | Base legal |
|-------------------|-------------------|------------|
| Datos identificables de cliente | Vigencia del contrato + procedimiento de tombstone tras su extinción | Artículo 6.1.b del Reglamento (UE) 2016/679 |
| Registros de auditoría | Siete años de manera continua | Artículo 24.1 del Real Decreto 311/2022 |
| Comunicaciones por correo electrónico y mensajería WhatsApp | Siete años | Artículo 6.1.c del Reglamento (UE) 2016/679 y artículo 24.1 del Real Decreto 311/2022 |
| Intentos de firma criptográfica (cadena Ed25519) | Siete años | Validez jurídica de los documentos firmados y retención exigida por el Esquema Nacional de Seguridad |
| Copias de seguridad diarias | Treinta días en régimen rotatorio | Capacidad operativa de recuperación |
| Copias de seguridad archivadas mensualmente | Un año | Capacidad operativa de recuperación extendida |
| Copias de seguridad en almacenamiento en frío | Siete años | Cumplimiento del Esquema Nacional de Seguridad |
| Informes de cumplimiento por norma | Siete años | Artículo 5.2 del Reglamento (UE) 2016/679 (principio de responsabilidad proactiva) |
| Datos de analítica de marketing con opt-in | Durante la vigencia del consentimiento + un año | Artículo 7 del Reglamento (UE) 2016/679 y previsión de revocación |
| Registros de consentimiento de cookies | Veinticuatro meses con renovación | Guía de Cookies de la Agencia Española de Protección de Datos publicada en 2020 |

## 3. Procedimiento de tombstone anonymization

### 3.1 Activadores

El procedimiento de tombstone anonymization se ejecuta en los siguientes supuestos:

a) Atención de solicitudes de supresión presentadas por el interesado al amparo del artículo 17 del Reglamento (UE) 2016/679, con las salvedades previstas en el apartado 3 de dicho artículo y, en particular, con la preservación de la cadena de auditoría conforme al artículo 24.1 del Real Decreto 311/2022.

b) Expiración del plazo de retención aplicable a la categoría de datos correspondiente.

### 3.2 Sustituciones aplicadas

| Campo original | Sustitución |
|----------------|-------------|
| Dirección de correo electrónico | anonymised_{uuid}@removed.fulkro.local |
| Nombre y apellidos | "[anonimizado]" |
| Documento nacional de identidad o equivalente | NULL |
| Número de teléfono | NULL |

### 3.3 Elementos preservados

Se preservan, sin modificación, los siguientes elementos:

a) Los registros de auditoría, conforme al artículo 24.1 del Real Decreto 311/2022 y al artículo 30.4 del Reglamento (UE) 2016/679.

b) La cadena de intentos de firma criptográfica Ed25519, en garantía de la validez jurídica de los documentos firmados.

## 4. Detalle del régimen de copias de seguridad

### 4.1 Copias diarias

Se realizan copias de seguridad con periodicidad diaria, con retención en régimen rotatorio de treinta días. La eliminación automática de las copias excedentes se realiza mediante proceso automatizado.

### 4.2 Archivo mensual

Se conservan copias archivadas mensualmente, durante un período máximo de doce meses, comprimidas y cifradas.

### 4.3 Almacenamiento en frío trimestral

Se realiza almacenamiento en frío con periodicidad trimestral, con retención de siete años en cumplimiento de la obligación de retención del Esquema Nacional de Seguridad. El almacenamiento en frío se realiza en soporte cifrado y desconectado del entorno de producción.

### 4.4 Verificación de integridad

Se realiza verificación de la integridad de las copias de seguridad con periodicidad semestral.

### 4.5 Restauración

Se realiza ensayo trimestral de restauración de copias de seguridad, en el marco de los ejercicios programados de recuperación ante desastre.

## 5. Retención de registros de auditoría

### 5.1 Plazo

Se establece un plazo de retención de siete años, sin interrupciones, en cumplimiento del artículo 24.1 del Real Decreto 311/2022.

### 5.2 Verificación de continuidad

El sistema Self-Monitoring ejecuta de manera continua el control `check_audit_logs_continuity`, que verifica la ausencia de discontinuidades en la cadena de registros.

### 5.3 Soporte técnico

Los registros se almacenan en la tabla audit_logs de PostgreSQL, con la extensión pgAudit como mecanismo complementario de registro a nivel de la propia base de datos.

### 5.4 Tratamiento post-retención

Una vez expirado el plazo de siete años, se aplica el procedimiento de tombstone anonymization en lugar de la eliminación material, preservando la integridad de la cadena.

## 6. Retención de comunicaciones

### 6.1 Correo electrónico

Las comunicaciones por correo electrónico tramitadas a través del sub-procesador Postmark se conservan durante un período de siete años, comprendiendo los metadatos de envío, entrega y apertura.

### 6.2 Mensajería WhatsApp

Las comunicaciones por WhatsApp Business tramitadas a través del sub-procesador 360dialog se conservan durante un período de siete años, comprendiendo las comunicaciones entrantes y salientes.

### 6.3 Almacenamiento interno

El almacenamiento interno de las comunicaciones se realiza en MinIO, cifrado en reposo conforme al protocolo AES-256.

## 7. Retención de intentos de firma criptográfica

### 7.1 Plazo mínimo

La cadena de intentos de firma Ed25519 se conserva durante un plazo mínimo de siete años, en garantía de la validez jurídica de los documentos firmados por los clientes.

### 7.2 Tratamiento post-retención

Una vez expirado el plazo de retención, se aplica anonimización a los identificadores personales del firmante, preservando la integridad criptográfica de la cadena.

## 8. Revisión y actualización

### 8.1 Revisión periódica

La presente Política se revisa con periodicidad anual obligatoria.

### 8.2 Revisión extraordinaria

Procederá la revisión extraordinaria de la presente Política en los siguientes supuestos:

a) Modificación del marco normativo aplicable.

b) Modificación sustancial de la cadena de sub-procesadores.

c) Incorporación de cliente perteneciente a sector con régimen sectorial específico de retención.

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
