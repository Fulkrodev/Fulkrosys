---
title: Política de Control de Accesos
codigo: FULKRO-ISMS-ACL-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Semestral
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor ISO 27001
referencia_normativa: ISO/IEC 27001:2022 Anexo A.8 (Controles tecnológicos)
---

# Política de Control de Accesos de FULKRO

## 1. Principios

El control de accesos en FULKRO se rige por los siguientes principios fundamentales:

a) **Principio de necesidad de conocer (need-to-know)**: el acceso a la información se otorga exclusivamente a quien lo precise para el cumplimiento de su función legítima.

b) **Principio de mínimo privilegio (least privilege)**: los privilegios concedidos se limitan al mínimo estrictamente imprescindible para el cumplimiento de la función asignada.

c) **Principio de segregación de funciones (segregation of duties)**: aplicable de manera limitada conforme a las restricciones estructurales propias de una micro-organización con titular único, sin perjuicio del plan de delegación documentado para el cuarto trimestre del año 2026.

d) **Principio de defensa en profundidad (defense in depth)**: las medidas de control se estratifican en capas sucesivas comprendiendo el cifrado del transporte, la autenticación, la autorización a nivel de fila y la auditoría continua.

## 2. Autenticación

### 2.1 Administrador único

El acceso del administrador único, Marcos Mata García, a la plataforma se realiza mediante autenticación de doble factor obligatoria. El segundo factor se implementa mediante el estándar TOTP (Time-based One-Time Password) conforme al control A.8.5 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

### 2.2 Usuarios de portal cliente

El acceso al portal cliente se realiza mediante credenciales individuales (correo electrónico y contraseña almacenada con bcrypt). La habilitación de doble factor temporal TOTP se ofrece de manera opcional al usuario cliente, encontrándose previsto su carácter obligatorio para perfiles que accedan a información de máxima sensibilidad.

### 2.3 Acceso de sub-procesadores

El acceso programático de sub-procesadores se realiza mediante claves de API. Se establece un objetivo de rotación periódica con frecuencia trimestral, en el marco del plan de automatización de gestión de credenciales.

### 2.4 Enlaces criptográficos a terceros legítimos

Se preserva el uso de enlaces criptográficos basados en firma Ed25519 con vigencia limitada a ocho horas, aplicables exclusivamente a los flujos de firma con tercero externo (motor M5), notificación a proveedor de pentest (motor M8) y proceso de declaración de conformidad ENS (motor M27), por concurrir en estos supuestos justificación operativa específica.

## 3. Autorización

### 3.1 Aislamiento multi-tenant

El aislamiento de los datos entre organizaciones cliente se implementa mediante el mecanismo Row Level Security (RLS) de PostgreSQL, conforme al control A.8.3 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

La cobertura actual de RLS sobre tablas con datos identificables de cliente se sitúa en el sesenta y dos por ciento del inventario total. Se ha establecido como objetivo operativo alcanzar el setenta por ciento de cobertura tras el bloque cuatro del Sprint Polish Máximo en curso, y el cien por ciento en el módulo MB-12 de hardening de seguridad.

### 3.2 Roles dinámicos por organización

La aplicación define roles dinámicos a nivel de organización cliente, permitiendo la asignación granular de privilegios a usuarios individuales en función de su pertenencia organizativa.

## 4. Gestión de usuarios

### 4.1 Administrador único

Existe un único usuario con privilegios de administración: Marcos Mata García. No se admite la creación de cuentas administrativas adicionales sin la previa modificación de la presente Política.

### 4.2 Usuarios de portal cliente

El alta de usuarios cliente se realiza de forma manual por el administrador, previa verificación de la solicitud. No se admite el registro automático mediante formularios de auto-registro.

### 4.3 Revisión periódica

La revisión del padrón de usuarios y de sus privilegios se realiza con periodicidad trimestral.

### 4.4 Baja de usuario y tratamiento de datos

La baja de un usuario cliente conlleva el procedimiento de tombstone anonymization, conforme al cual los identificadores personales se sustituyen por tokens anonimizados preservando la integridad de la cadena de auditoría, en cumplimiento de los artículos 17 y 30.4 del Reglamento (UE) 2016/679 y del artículo 24.1 del Real Decreto 311/2022.

## 5. Acceso privilegiado

### 5.1 Punto único de autoridad

Como consecuencia de la estructura de micro-organización con titular único, Marcos Mata García concentra el acceso privilegiado completo a todos los activos de información, situación expresamente documentada y reconocida como limitación estructural mitigada mediante el plan de delegación.

### 5.2 Acceso privilegiado de sub-procesadores

Los sub-procesadores acceden a la información exclusivamente bajo el principio de mínimo privilegio, conforme a los términos específicos de cada Acuerdo de Encargo de Tratamiento (DPA).

### 5.3 Plan de procedimiento break-glass

Se contempla la implantación de un procedimiento break-glass para el cuarto trimestre del año 2026, en el marco de la designación de Delegado de Protección de Datos externo certificado. Dicho procedimiento permitirá el acceso de emergencia a sistemas críticos en supuestos de incapacitación del administrador único.

## 6. Auditoría de accesos

### 6.1 Registro continuo

Los registros de auditoría se almacenan en la tabla audit_logs de PostgreSQL, con retención mínima de siete años en cumplimiento del artículo 24.1 del Real Decreto 311/2022. La extensión pgAudit refuerza la capacidad de auditoría a nivel de la propia base de datos.

### 6.2 Monitorización continua

El sistema Self-Monitoring implementa el control check_admin_actions_audit_logged, que verifica de manera continua la consignación íntegra en el registro de auditoría de las acciones administrativas.

### 6.3 Cumplimiento ISO 27001:2022

Los mecanismos descritos satisfacen los requisitos del control A.8.15 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022 (Registros de eventos).

## 7. Revisión semestral

La presente Política se revisará con periodicidad semestral. Adicionalmente, procederá la revisión extraordinaria con ocasión de cualquier incidente de seguridad que afecte al sistema de control de accesos o que evidencie la necesidad de modificación de los principios o procedimientos aquí establecidos.

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión semestral
