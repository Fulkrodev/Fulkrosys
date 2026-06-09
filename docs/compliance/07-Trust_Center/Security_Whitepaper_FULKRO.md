---
title: Whitepaper de Seguridad de FULKRO
codigo: FULKRO-TRUST-WP-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Público · Trust Center · Due diligence cliente
---

# Whitepaper de Seguridad de FULKRO

## 1. Visión general de la arquitectura

FULKRO se construye sobre la siguiente pila tecnológica:

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI 0.116 sobre Python 3.12 con ejecución asíncrona |
| Frontend | Next.js 15 sobre React, con Tailwind CSS y biblioteca shadcn/ui |
| Base de datos | PostgreSQL 16 con extensiones pgvector, Apache AGE y pgAudit |
| Almacenamiento | MinIO autoalojado sobre Hetzner Alemania, con URLs firmadas de vigencia temporal limitada |
| Tareas asíncronas | Celery con broker Redis (caché distribuida entre procesos) |
| Orquestación | Docker Compose |
| Alojamiento | Hetzner CCX en Falkenstein, Alemania |
| Dominio y DNS | fulkro.es servido a través de Cloudflare |

## 2. Controles de seguridad (mapeo a ISO/IEC 27001:2022 Anexo A)

| Control Anexo A | Implementación en FULKRO |
|-----------------|--------------------------|
| A.8.5 (Autenticación segura) | Doble factor TOTP obligatorio para el administrador · bcrypt y JWT con firma Ed25519 para los usuarios cliente |
| A.8.3 (Restricción de acceso a la información) | Row Level Security multi-tenant sobre PostgreSQL |
| A.8.20 (Seguridad de las redes) | TLS 1.3 obligatorio en el transporte de la totalidad del tráfico |
| A.8.24 (Uso de criptografía) | Cifrado en reposo mediante Transparent Data Encryption en PostgreSQL · AES-256 en MinIO · TLS 1.3 a través de Cloudflare |
| A.8.15 (Registros de eventos) | audit_logs continuos · pgAudit · retención mínima de 7 años conforme al artículo 24.1 del Real Decreto 311/2022 |
| A.8.13 (Copias de seguridad) | Diarias cifradas · archivo mensual durante 12 meses · almacenamiento en frío trimestral durante 7 años |

## 3. Soberanía de los datos

### 3.1 Sub-procesadores en territorio del Espacio Económico Europeo

a) Hetzner: Falkenstein (Alemania).

b) Postmark: región de datos UE Fráncfort.

c) 360dialog: Alemania.

d) MinIO: autoalojado sobre Hetzner Alemania.

### 3.2 Mitigación de transferencia internacional

Para los servicios prestados por Anthropic PBC, con residencia primaria en Estados Unidos de América, FULKRO aplica de manera acumulativa los siguientes mecanismos de mitigación:

a) Suscripción del Acuerdo de Encargo de Tratamiento conforme al modelo del proveedor.

b) Suscripción de las Cláusulas Contractuales Tipo aprobadas por Decisión de Ejecución (UE) 2021/914 de la Comisión Europea.

c) Adhesión al Trans-Atlantic Data Privacy Framework como marco complementario.

d) Aplicación de seudonimización a los datos enviados al sub-procesador, garantizándose la ausencia de identificadores personales en la información transferida.

### 3.3 Plan de contingencia Schrems III

Se documenta plan de migración prospectiva a AWS Bedrock con región Fráncfort para el supuesto de invalidación judicial del Trans-Atlantic Data Privacy Framework, conforme al documento de decisión arquitectónica que constituye la base del análisis.

## 4. Criptografía

| Mecanismo | Aplicación |
|-----------|------------|
| Ed25519 | Sistema de firma documental M5 · tokens JWT de autenticación |
| bcrypt | Almacenamiento seguro de contraseñas de usuarios cliente |
| AES-256 | Cifrado en reposo de objetos en MinIO |
| TLS 1.3 | Cifrado del transporte de la totalidad del tráfico de red |
| SHA-256 | Integridad de los registros de auditoría |

## 5. Trazabilidad y auditoría

### 5.1 Registros continuos

Los registros de auditoría se almacenan en PostgreSQL, con extensión pgAudit y tabla audit_logs, conforme al control A.8.15 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

### 5.2 Retención

La retención mínima de los registros de auditoría es de siete años, en cumplimiento del artículo 24.1 del Real Decreto 311/2022 (Esquema Nacional de Seguridad).

### 5.3 Anonimización post-retención

Una vez expirado el plazo de retención obligatoria, se aplica el procedimiento de tombstone anonymization conforme al cual se sustituyen los identificadores personales por tokens anonimizados, preservando la integridad de la cadena de auditoría conforme al artículo 17 del Reglamento (UE) 2016/679 reconciliado con el artículo 30.4 del mismo Reglamento.

### 5.4 Monitorización continua

El sistema Self-Monitoring ejecuta de manera continua el control `check_audit_logs_continuity`, verificando la ausencia de discontinuidades en la cadena de registros de auditoría.

## 6. Respuesta ante incidentes

### 6.1 Capacidad de detección

El sistema Self-Monitoring opera con arquitectura de plugins, integrando diecisiete o más controles de monitorización continua.

### 6.2 Flujo de notificación NIS2

Se mantiene operativo el flujo de notificación con cadenciado 24h + 72h + 1 mes, conforme al artículo 23 de la Directiva (UE) 2022/2555.

### 6.3 Plantillas de notificación

Plantilla operativa de notificación de brecha a la Agencia Española de Protección de Datos, conforme al artículo 33 del Reglamento (UE) 2016/679, con contenido conforme al artículo 33.3.

Plantilla operativa de notificación al interesado afectado, conforme al artículo 34 del Reglamento (UE) 2016/679.

## 7. Estado de cumplimiento normativo

| Norma | Estado |
|-------|--------|
| Reglamento (UE) 2016/679 (RGPD) | Implantado · Política de Privacidad, Registro de Actividades, Acuerdo de Encargo, endpoints de ejercicio de derechos artículos 15, 17 y 20, flujo de brecha de 72 horas |
| Ley Orgánica 3/2018 (LOPDGDD) | Implantado · Designación de DPO interim y procedimiento ante la Agencia Española de Protección de Datos |
| Ley 34/2002 (LSSI-CE) | Implantado · Aviso Legal y condiciones generales con correo de contacto y CIF |
| Guía AEPD Cookies 2020 | Implantado · Banner de tres categorías con renovación cada 24 meses |
| Directiva (UE) 2022/2555 (NIS2) | Alineación voluntaria · análisis de clasificación, procedimiento de notificación, seguridad de la cadena de suministro y fichero security.txt |
| ISO/IEC 27001:2022 | Preparedness · documentación del Sistema de Gestión de la Seguridad de la Información completa · certificación prevista para el primer trimestre del año 2027 |

## 8. Datos de contacto

| Canal | Dirección |
|-------|-----------|
| Delegado de Protección de Datos | dpo@fulkro.es |
| Seguridad y vulnerabilidades | security@fulkro.es |
| Contacto general | marcosmataga@fulkro.es |
| Trust Center | https://fulkro.es/trust (operativo tras el despliegue en producción) |

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
