---
title: Registro de Activos de Información
codigo: FULKRO-ISMS-ASSET-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Semestral mínima
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor ISO 27001
referencia_normativa: ISO/IEC 27001:2022 Anexo A.5.9 (Inventario de activos)
---

# Registro de Activos de Información de FULKRO

## 1. Propósito y mantenimiento

El presente Registro de Activos de Información tiene por objeto la identificación, clasificación y caracterización sistemática de los activos de información sobre los que descansa la operación de FULKRO, en cumplimiento del control A.5.9 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

La revisión del Registro tiene carácter semestral mínimo. Procederá la revisión extraordinaria con ocasión de la incorporación o baja de cualquier activo cuya criticidad sea igual o superior a 3 sobre 5, así como ante cualquier modificación sustancial de la arquitectura de la plataforma.

El propietario único de todos los activos identificados en el presente Registro es Marcos Mata García, en su condición de titular único de la actividad.

La criticidad de cada activo se evalúa conforme a una escala de uno a cinco, donde el valor 1 corresponde a una criticidad despreciable y el valor 5 a una criticidad máxima.

## 2. Activos de información (datos)

### 2.1 Datos personales de cliente

Datos identificativos de personas físicas vinculadas a las organizaciones cliente (nombre, apellidos, dirección de correo electrónico profesional, identificador societario, cargo). FULKRO no procesa categorías especiales de datos personales conforme al artículo 9 del Reglamento (UE) 2016/679, por exclusión expresa de diseño.

**Clasificación**: Confidencial · **Criticidad**: 5

### 2.2 Datos de negocio

Tarifas comerciales, propuestas profesionales, contratos de servicios, condiciones particulares y comunicaciones de naturaleza precontractual y contractual.

**Clasificación**: Confidencial · **Criticidad**: 4

### 2.3 Datos operacionales

Registros de auditoría, métricas operacionales, registros de acceso, copias de seguridad e información derivada del sistema de Self-Monitoring.

**Clasificación**: Interno · **Criticidad**: 4

## 3. Activos software (aplicaciones)

### 3.1 Backend FULKRO

Aplicación de backend desarrollada en lenguaje Python versión 3.12 sobre el framework FastAPI versión 0.116.

**Clasificación**: Confidencial · **Criticidad**: 5

### 3.2 Frontend FULKRO

Aplicación de frontend desarrollada en lenguaje TypeScript sobre el framework Next.js versión 15, con biblioteca React, Tailwind CSS y componentes shadcn/ui.

**Clasificación**: Confidencial · **Criticidad**: 4

### 3.3 Base de datos relacional

PostgreSQL versión 16, con extensiones pgvector (búsqueda semántica), Apache AGE (grafo de conocimiento) y pgAudit (auditoría continua).

**Clasificación**: Confidencial · **Criticidad**: 5

### 3.4 Almacenamiento de objetos

Servicio MinIO autoalojado sobre infraestructura Hetzner, sin intermediación de proveedor tercero.

**Clasificación**: Confidencial · **Criticidad**: 4

### 3.5 Cola de tareas asíncronas y caché distribuida

Celery con broker Redis para procesamiento asíncrono y caché compartida entre procesos.

**Clasificación**: Interno · **Criticidad**: 3

### 3.6 Motores funcionales

Treinta motores funcionales identificados como M01 a M30, así como el motor M31 de integración con WhatsApp Business y el motor M32 de Capabilities.

**Clasificación**: Confidencial · **Criticidad**: 5

## 4. Activos de infraestructura

### 4.1 Servidores de producción

Infraestructura virtualizada Hetzner CCX, ubicada en el centro de datos de Falkenstein, Alemania (Espacio Económico Europeo).

**Clasificación**: Interno · **Criticidad**: 5

### 4.2 Dominio y servicio de nombres

Dominio fulkro.es, con prestación de servicios DNS por parte de Cloudflare.

**Clasificación**: Interno · **Criticidad**: 5

### 4.3 Almacenamiento de objetos

Cubos MinIO destinados a (i) datos de cliente, (ii) informes de cumplimiento, (iii) copias de seguridad y (iv) evidencias documentales.

**Clasificación**: Confidencial · **Criticidad**: 5

## 5. Activos de servicios (sub-procesadores SaaS)

### 5.1 Postmark

Servicio transaccional de envío de correo electrónico (encargado de tratamiento), proporcionado por ActiveCampaign Inc. con región de datos seleccionada en la Unión Europea (Fráncfort).

**Clasificación**: Confidencial · **Criticidad**: 4

### 5.2 Anthropic Claude API

Servicio de inteligencia artificial generativa (encargado de tratamiento), proporcionado por Anthropic PBC, con aplicación de seudonimización previa al envío de datos.

**Clasificación**: Confidencial · **Criticidad**: 3

### 5.3 360dialog

Servicio de integración con WhatsApp Business API (Business Solution Provider), proporcionado por 360dialog GmbH con sede en Alemania.

**Clasificación**: Confidencial · **Criticidad**: 4

### 5.4 Hetzner

Servicio de infraestructura como servicio (IaaS), proporcionado por Hetzner Online GmbH con sede en Alemania.

**Clasificación**: Interno · **Criticidad**: 5

## 6. Activos criptográficos

### 6.1 Claves Ed25519 de firma

Pares de claves criptográficas Ed25519 utilizadas por el sistema M5 de firma documental con efectos jurídicos frente al cliente.

**Clasificación**: Confidencial · **Criticidad**: 5

### 6.2 Secretos de firma JWT

Claves utilizadas para la firma de tokens JWT empleados en el flujo de autenticación de la plataforma.

**Clasificación**: Confidencial · **Criticidad**: 5

### 6.3 Sales de bcrypt

Material criptográfico empleado para el cifrado de las contraseñas almacenadas mediante la función bcrypt.

**Clasificación**: Confidencial · **Criticidad**: 4

### 6.4 Tokens de API de sub-procesadores

Credenciales de acceso a las APIs de Anthropic, Postmark, 360dialog y Hetzner.

**Clasificación**: Confidencial · **Criticidad**: 5

### 6.5 Secretos compartidos TOTP

Secretos compartidos para la generación de códigos de doble factor temporal (TOTP) del administrador y, en su caso, de los usuarios cliente que habiliten esta capa de seguridad.

**Clasificación**: Confidencial · **Criticidad**: 4

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión semestral
