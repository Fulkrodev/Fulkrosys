---
title: Evaluación de Riesgos del Sistema de Gestión de la Seguridad de la Información
codigo: FULKRO-ISMS-RISK-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor ISO 27001
metodologia: MAGERIT v3 + UNE-EN ISO/IEC 27005:2022
---

# Evaluación de Riesgos del SGSI de FULKRO

## 1. Alcance de la evaluación de riesgos

La presente evaluación de riesgos comprende:

a) Los activos de información de la plataforma FULKRO en su totalidad, conforme al inventario consolidado en el documento FULKRO-ISMS-ASSET-001 (Asset Register).

b) Los procesos críticos para la operación: autenticación, sistema de firma criptográfica, comunicaciones (correo electrónico transaccional y mensajería WhatsApp Business), procesamiento de datos personales y mecanismos de notificación a interesados y autoridades.

c) Las relaciones contractuales con los sub-procesadores que se encuentran en el camino crítico de la operación: Hetzner Online GmbH, Postmark, Anthropic PBC, 360dialog GmbH y la infraestructura propia MinIO autoalojada.

## 2. Metodología

### 2.1 Marcos metodológicos de referencia

La presente evaluación se realiza conforme a los siguientes marcos metodológicos:

a) MAGERIT versión 3.0, "Metodología de Análisis y Gestión de Riesgos de los Sistemas de Información", del Centro Criptológico Nacional, en lo relativo a la catalogación de activos, amenazas y salvaguardas.

b) Norma UNE-EN ISO/IEC 27005:2022, en lo relativo al proceso de gestión de riesgos.

c) Cláusula A.5.7 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022, en lo relativo a la integración de inteligencia de amenazas.

### 2.2 Escala de cuantificación

La cuantificación del riesgo se realiza mediante el producto de la probabilidad de ocurrencia por el impacto resultante, aplicándose una escala discreta de cinco niveles para cada factor:

| Nivel | Probabilidad | Impacto |
|-------|--------------|---------|
| 1 | Muy baja (despreciable) | Despreciable |
| 2 | Baja | Bajo |
| 3 | Media | Moderado |
| 4 | Alta | Alto |
| 5 | Muy alta | Crítico |

### 2.3 Criterios de tratamiento

Conforme al producto Probabilidad × Impacto, los criterios de tratamiento del riesgo son los siguientes:

a) **Score igual o inferior a 6**: riesgo aceptable. No requiere tratamiento adicional, sin perjuicio de la monitorización ordinaria.

b) **Score entre 7 y 15**: riesgo tolerable con medidas de mitigación. Requiere la implantación de salvaguardas específicas.

c) **Score igual o superior a 16**: riesgo inaceptable. Requiere medidas inmediatas de tratamiento mediante mitigación, transferencia o eliminación.

## 3. Inventario de activos críticos

El inventario detallado de activos se mantiene en el documento FULKRO-ISMS-ASSET-001 (Asset Register), al que se remite expresamente. Para los efectos de la presente evaluación, se han considerado los activos categorizados con criticidad igual o superior a 3 sobre 5.

## 4. Identificación de amenazas

### 4.1 Amenazas de origen externo

a) Ataques de denegación de servicio distribuida (DDoS) dirigidos contra la plataforma.

b) Campañas de phishing y spear phishing dirigidas al titular o a usuarios cliente.

c) Despliegue de software malicioso de tipo ransomware.

d) Explotación de vulnerabilidades en la capa de API o en componentes de terceros.

e) Ataques de fuerza bruta o relleno de credenciales (credential stuffing).

### 4.2 Amenazas de origen interno

a) Error humano en operaciones de mantenimiento, configuración o despliegue.

b) Configuración incorrecta de sistemas o servicios (misconfiguration).

c) Acceso indebido por inadecuada gestión de credenciales.

### 4.3 Amenazas asociadas a sub-procesadores

a) Interrupción del servicio por parte de proveedores críticos.

b) Compromiso de credenciales API de sub-procesadores.

c) Cese de actividad o cambio sustancial de condiciones contractuales por parte de un sub-procesador.

d) Modificación del marco jurídico aplicable a transferencias internacionales de datos.

## 5. Análisis de riesgos · Tabla de doce riesgos principales

| ID | Riesgo identificado | Activo afectado | Probabilidad | Impacto | Score | Tratamiento |
|----|---------------------|------------------|--------------|---------|-------|-------------|
| R01 | Compromiso de credenciales del administrador único | Sistema de autenticación | 2 | 5 | 10 | Mitigar mediante autenticación de doble factor TOTP obligatoria |
| R02 | Interrupción del servicio de hosting Hetzner Falkenstein | Infraestructura de alojamiento | 2 | 4 | 8 | Mitigar mediante copias de seguridad en regiones diferenciadas y procedimiento de failover documentado |
| R03 | Brecha de seguridad con afectación de datos personales de cliente | Base de datos de clientes | 2 | 5 | 10 | Mitigar mediante aislamiento RLS, cifrado en reposo y procedimiento de notificación de 72 horas |
| R04 | Compromiso de la clave de API del proveedor de inteligencia artificial | Integración LLM Anthropic | 2 | 3 | 6 | Aceptar con monitorización continua y rotación periódica de credenciales |
| R05 | Pérdida de las claves criptográficas Ed25519 de firma | Sistema de firma M5 | 1 | 5 | 5 | Mitigar mediante procedimiento de custodia (key escrow) y duplicado offline |
| R06 | Campaña de phishing dirigida contra el titular | Múltiples sistemas y datos | 3 | 5 | 15 | Mitigar mediante autenticación de doble factor, formación específica anti-phishing y verificación cruzada de comunicaciones financieras |
| R07 | Invalidación del Trans-Atlantic Data Privacy Framework por resolución judicial | Transferencia internacional a Anthropic | 2 | 4 | 8 | Plan de contingencia documentado de migración a AWS Bedrock con región Fráncfort |
| R08 | No renovación de Acuerdo de Encargo de Tratamiento por parte de sub-procesador | Cumplimiento normativo | 1 | 4 | 4 | Monitorización anual mediante check_sub_processor_dpa_expirations |
| R09 | Fallo en la integridad de copias de seguridad | Capacidad de recuperación | 2 | 5 | 10 | Mitigar mediante verificación semestral de integridad y ensayos trimestrales de restauración |
| R10 | Inyección SQL a través de capa frontend | Acceso a datos | 1 | 5 | 5 | Mitigar mediante uso obligatorio de ORM con consultas parametrizadas y revisión de código previa a despliegue |
| R11 | Incapacitación temporal o permanente del titular único | Continuidad operacional | 2 | 5 | 10 | Mitigar mediante plan de sucesión documentado y custodia externa de credenciales críticas a partir del cuarto trimestre de 2026 |
| R12 | Compromiso del repositorio de código fuente | Propiedad intelectual y secretos | 2 | 4 | 8 | Mitigar mediante autenticación de doble factor en proveedor de control de versiones, auditoría de accesos y rotación de tokens de despliegue |

## 6. Plan de tratamiento de riesgos

Para cada riesgo identificado en la sección 5, se establece el siguiente plan de tratamiento, con asignación de la salvaguarda correspondiente del Anexo A de la norma UNE-EN ISO/IEC 27001:2022, plazo de implantación, responsable y indicador clave de seguimiento:

| ID | Salvaguarda Anexo A 27001:2022 | Plazo implantación | Responsable | Indicador clave |
|----|-------------------------------|--------------------|-------------|-----------------|
| R01 | A.8.5 (autenticación segura) | Implantado | Marcos Mata García | Cobertura 100% TOTP en cuentas admin |
| R02 | A.8.13 (copias de seguridad) | Implantado | Marcos Mata García | RTO 4h verificado en último ensayo |
| R03 | A.8.3, A.8.24 (control acceso, cifrado) | Implantado y en hardening continuo | Marcos Mata García | Cobertura RLS sobre tablas tenant-sensitive |
| R04 | A.5.16 (gestión de identidades) | Implantado | Marcos Mata García | Rotación trimestral de claves API |
| R05 | A.8.24 (uso de criptografía) | Implantado | Marcos Mata García | Procedimiento de custodia documentado y verificado |
| R06 | A.6.3 (concienciación) | Implantado | Marcos Mata García | Auditoría de remitentes verificada semestralmente |
| R07 | A.5.31 (requisitos legales) | Plan de contingencia documentado | Marcos Mata García | Documento FULKRO-ARCH-PIVOT-001 vigente |
| R08 | A.5.19 (proveedores) | Implantado | Marcos Mata García | check_sub_processor_dpa_expirations diario |
| R09 | A.8.13 (copias de seguridad) | Implantado | Marcos Mata García | Ensayo trimestral de restauración |
| R10 | A.8.28 (codificación segura) | Implantado | Marcos Mata García | Revisión de pull request obligatoria |
| R11 | A.5.30 (preparación TIC para continuidad) | Plan de sucesión en preparación | Marcos Mata García | Custodia externa operativa Q4 2026 |
| R12 | A.5.16, A.8.34 (autenticación, protección código) | Implantado | Marcos Mata García | Auditoría de accesos al repositorio |

## 7. Revisión periódica

La presente evaluación se revisará con carácter anual obligatorio, fijándose la próxima revisión ordinaria para el mes de mayo de 2027.

Procederá la revisión extraordinaria cuando se materialice cualquiera de los siguientes supuestos:

a) Acaecimiento de un incidente de seguridad de severidad HIGH.

b) Modificación sustancial de la arquitectura técnica de FULKRO.

c) Incorporación de un nuevo sub-procesador o sustitución de un sub-procesador existente.

d) Cambios en el marco regulatorio aplicable.

e) Identificación de nuevas amenazas relevantes a través de fuentes de inteligencia de amenazas.

## 8. Aprobación

**Firma**: Marcos Mata García
**Cargo**: Responsable de Seguridad de la Información (interim)
**Fecha**: 12 de mayo de 2026

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
