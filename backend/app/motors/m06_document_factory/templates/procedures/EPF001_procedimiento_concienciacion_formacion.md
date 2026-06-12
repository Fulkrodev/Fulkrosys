# DOCUMENTO E-PF-001 — PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD

**Materializa las medidas mp.per.3 (Concienciación) y mp.per.4 (Formación) del Anexo II del ENS** y los controles A.6.3 (Information security awareness, education and training) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con registros de asistencia y resultados de tests.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-PF-001"
titulo: "Procedimiento de Concienciación y Formación en Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100, {{ proyecto.codigo_documento_base }}-103"
---

# PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-PF-001 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} planifica, ejecuta, mide y mejora las actividades de concienciación y formación en seguridad de la información dirigidas a su personal y a los terceros con acceso a sus sistemas, en cumplimiento de las medidas **mp.per.3 (Concienciación)** y **mp.per.4 (Formación)** del Anexo II del Real Decreto 311/2022 y conforme al **Plan Anual de Concienciación y Formación** aprobado por el Comité de Seguridad.

## 2. ALCANCE

Aplica a:

a) Todo el personal de la Entidad, con independencia de su régimen jurídico, categoría profesional o modalidad de contratación.

b) Personal externo y proveedores con acceso a sistemas de la Entidad, en la medida que sus contratos lo establezcan.

c) Personal de nueva incorporación, durante el proceso de acogida.

d) Becarios, personal en prácticas y personal eventual.

## 3. SEGMENTACIÓN DE LA AUDIENCIA

A los efectos del presente procedimiento, el personal se segmenta en los siguientes grupos, cada uno con necesidades formativas específicas:

| Grupo | Perfil | Foco principal de formación |
|---|---|---|
| **G1 — General** | Todo el personal sin perfil técnico ni privilegiado | Higiene digital, phishing, contraseñas, uso aceptable, RGPD básico |
| **G2 — Funcional con datos personales** | Personal que trata datos personales en su día a día | RGPD avanzado, brechas, derechos de los interesados, secreto profesional |
| **G3 — Técnico** | Personal del departamento TI con responsabilidades operativas | Gestión segura, hardening, gestión de incidentes, vulnerabilidades |
| **G4 — Privilegiado** | Administradores con privilegios elevados | Seguridad avanzada, defensa en profundidad, threat hunting, response |
| **G5 — Directivo** | Personal directivo y miembros del órgano de gobierno | Riesgos estratégicos, gobernanza, obligaciones legales del cargo |
| **G6 — Roles ENS** | Personas designadas como roles del art. 11 ENS | Marco normativo ENS, MAGERIT, gestión del SGSI |

## 4. PLAN ANUAL DE CONCIENCIACIÓN Y FORMACIÓN

### 4.1 Elaboración

**Paso 1.** Durante el mes de enero de cada año, el Responsable de la Seguridad elabora el **Plan Anual de Concienciación y Formación** que incluirá:

- Objetivos generales y específicos por grupo.
- Acciones formativas previstas con su contenido, modalidad y duración.
- Calendario de ejecución.
- Audiencia objetivo de cada acción.
- Mecanismos de evaluación previstos.
- Indicadores de éxito.
- Recursos necesarios (presupuesto, formadores, plataforma).

**Paso 2.** El Plan se eleva al Comité de Seguridad para aprobación en su primera reunión ordinaria del año.

### 4.2 Contenidos mínimos exigibles

Por cada grupo de audiencia, el Plan deberá contemplar como mínimo las siguientes acciones formativas anuales:

| Grupo | Acciones mínimas anuales | Horas mínimas/año |
|---|---|---|
| G1 — General | Sesión inicial + 2 píldoras + simulacro phishing | 2 h |
| G2 — Datos personales | Sesión específica RGPD + actualización normativa | 4 h |
| G3 — Técnico | Formación técnica especializada | 16 h |
| G4 — Privilegiado | Formación avanzada + ejercicios prácticos | 24 h |
| G5 — Directivo | Sesión ejecutiva + briefing trimestral | 4 h |
| G6 — Roles ENS | Formación específica ENS + actualización normativa | 16 h |

## 5. ACCIONES DE CONCIENCIACIÓN

### 5.1 Sesión de acogida

**Paso 3.** Toda persona de nueva incorporación recibirá, durante su primera semana, una **sesión de acogida en seguridad** de duración mínima 2 horas que cubra:

- Presentación del SGSI y de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100).
- Lectura y firma de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103).
- Normas básicas de higiene digital.
- Procedimiento para la notificación de incidentes.
- Datos de contacto del Responsable de la Seguridad.

**Paso 4.** La sesión se documenta con **registro de asistencia firmado** y queda incorporada al expediente del trabajador.

### 5.2 Píldoras formativas

**Paso 5.** Con periodicidad **trimestral**, el Responsable de la Seguridad distribuye **píldoras formativas** breves (vídeos de 3-5 minutos, infografías, casos prácticos) sobre temas concretos:

- Reconocimiento de phishing y suplantación.
- Gestión segura de contraseñas y MFA.
- Uso seguro de redes Wi-Fi públicas.
- Protección de información en desplazamientos.
- Cifrado de dispositivos y soportes.
- Ingeniería social telefónica (vishing).
- Detección de mensajes fraudulentos (smishing).
- Riesgos de redes sociales corporativas.

### 5.3 Simulacros de phishing

**Paso 6.** Con periodicidad **trimestral**, el Responsable de la Seguridad ejecutará **simulacros de phishing controlados** dirigidos a toda la audiencia G1, G2, G3, G4 y G5.

**Paso 7.** Los simulacros utilizarán plantillas de mensajes que reproduzcan tácticas reales observadas (suplantación de marca, urgencia falsa, premios falsos, falsas notificaciones administrativas).

**Paso 8.** Los resultados se analizarán identificando:

- Tasa de apertura del mensaje.
- Tasa de clic en enlaces.
- Tasa de introducción de credenciales.
- Tasa de notificación al equipo de seguridad.

**Paso 9.** Las personas que caigan en el simulacro reciben formación correctiva específica, sin carácter sancionador en una primera ocasión, y los resultados agregados se elevan al Comité de Seguridad.

### 5.4 Campañas temáticas

**Paso 10.** La Entidad participará al menos una vez al año en una campaña temática alineada con eventos como el **Mes Europeo de la Ciberseguridad** (octubre), distribuyendo material divulgativo y organizando charlas o jornadas internas.

## 6. ACCIONES DE FORMACIÓN ESPECÍFICA

### 6.1 Formación técnica especializada

**Paso 11.** El personal de los grupos G3 y G4 recibirá formación técnica especializada en:

- Hardening de sistemas operativos y bases de datos.
- Gestión segura de configuraciones cloud.
- Análisis de logs y detección de anomalías.
- Respuesta a incidentes y análisis forense básico.
- Uso seguro de herramientas de administración remota.

**Paso 12.** Esta formación podrá impartirse mediante cursos externos certificados, formación interna o plataformas de e-learning especializadas.

### 6.2 Formación específica para roles ENS

**Paso 13.** Las personas designadas como roles del artículo 11 del ENS recibirán formación específica que cubra:

- Marco normativo del ENS y guías CCN-STIC aplicables.
- Metodología MAGERIT v3 para análisis de riesgos.
- Herramientas oficiales del CCN (PILAR, INES, AMPARO, LUCIA).
- Proceso de adecuación y certificación.
- Funciones y responsabilidades específicas del rol.

**Paso 14.** Para el Responsable de la Seguridad se valorará la obtención de certificaciones profesionales reconocidas internacionalmente (CISA, CISM, CISSP, ISO 27001 Lead Implementer/Auditor).

### 6.3 Formación específica para directivos

**Paso 15.** El personal directivo y los miembros del órgano de gobierno superior recibirán **briefings ejecutivos** semestrales sobre:

- Estado del SGSI y métricas clave.
- Riesgos estratégicos detectados.
- Cambios normativos relevantes.
- Tendencias de amenazas en el sector.
- Obligaciones legales del cargo en materia de ciberseguridad y protección de datos.

## 7. EVALUACIÓN DEL APRENDIZAJE

**Paso 16.** Cada acción formativa relevante incluirá un mecanismo de evaluación del aprendizaje, que podrá consistir en:

- Test de conocimientos al finalizar la formación.
- Casos prácticos o ejercicios.
- Simulacros operativos.
- Evaluaciones tipo *security hygiene assessment*.

**Paso 17.** El umbral mínimo para considerar superada una acción formativa será del **70% de aciertos** en las evaluaciones objetivas.

**Paso 18.** Las personas que no superen una evaluación recibirán formación de refuerzo y volverán a ser evaluadas. Tres no superaciones consecutivas serán comunicadas al responsable jerárquico para análisis de la situación.

## 8. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Plan Anual de Concienciación y Formación | Vida del SGSI |
| Registro de asistencia a sesiones de acogida | Vida laboral del empleado + 4 años |
| Registro de asistencia a formaciones específicas | 5 años |
| Resultados de evaluaciones del aprendizaje | 5 años |
| Informe trimestral de simulacros de phishing | 5 años |
| Informe anual de cumplimiento del Plan | Vida del SGSI |

## 9. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cobertura del Plan Anual (personal formado / total) | ≥ 95% |
| Personal nuevo con sesión de acogida en plazo | 100% |
| Personal G3-G4 con horas mínimas anuales completadas | ≥ 90% |
| Tasa de clic en simulacros de phishing | < 10% (objetivo final 5%) |
| Tasa de notificación correcta de simulacros de phishing | ≥ 50% |
| Personal con tres no superaciones consecutivas | 0 |

## 10. ANEXOS

- **Anexo I:** Plantilla del Plan Anual de Concienciación y Formación
- **Anexo II:** Material de la sesión de acogida
- **Anexo III:** Catálogo de píldoras formativas vigentes
- **Anexo IV:** Registro de asistencia
- **Anexo V:** Plantilla de evaluación del aprendizaje
- **Anexo VI:** Plantilla del informe trimestral de phishing

---

**Documento {{ proyecto.codigo_documento_base }}-PF-001 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**
```
