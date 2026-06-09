# E-601 · CUESTIONARIO DE EVALUACIÓN INICIAL DEL PROVEEDOR

{% set doc_codigo = documento.codigo if documento.codigo else 'E-601' %}
{% set doc_version = documento.version if documento.version else '1.0' %}
{% set doc_fecha = documento.fecha_emision if documento.fecha_emision else '—' %}
{% set prov_razon = proveedor.razon_social if proveedor.razon_social else '[A CUMPLIMENTAR]' %}
{% set prov_nif = proveedor.nif if proveedor.nif else '[A CUMPLIMENTAR]' %}
{% set prov_servicio = proveedor.servicio_descripcion if proveedor.servicio_descripcion else '[A CUMPLIMENTAR]' %}
{% set contacto_compliance_email = cliente.contacto_compliance.email if cliente.contacto_compliance and cliente.contacto_compliance.email else '—' %}
{% set plazo_respuesta_dias = proveedor.plazo_respuesta_dias if proveedor.plazo_respuesta_dias else 15 %}

**Documento:** {{ doc_codigo }}
**Versión:** {{ doc_version }}
**Fecha de emisión:** {{ doc_fecha }}
**Entidad solicitante:** {{ cliente.razon_social }} ({{ cliente.nif }})
**Proveedor evaluado:** {{ prov_razon }}
**NIF/CIF proveedor:** {{ prov_nif }}
**Servicio objeto:** {{ prov_servicio }}
**Clasificación documento:** Confidencial — uso entre Entidad y Proveedor

---

## 1. OBJETO DEL CUESTIONARIO

{{ cliente.razon_social }} (en adelante, "la Entidad"), en el marco del Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, se halla obligada a evaluar formalmente las capacidades de seguridad de la información de los terceros que prestan servicios sobre sus sistemas o información en ámbito ENS.

El presente cuestionario tiene por objeto recabar la información necesaria para:

a) Determinar la **idoneidad** del proveedor para prestar el servicio objeto.

b) Establecer el **nivel de criticidad** del proveedor en el inventario de la Entidad (E-600).

c) Identificar las **medidas adicionales** que la Entidad deba imponer contractualmente (vía adenda E-604).

d) Documentar el cumplimiento de las exigencias derivadas del **ENS Art. 18** y de la medida **`op.ext.1` del Anexo II** del RD 311/2022, así como, cuando aplique, del **RGPD Art. 28**, de la **NIS2 Art. 21.2.d)** y del **Reglamento DORA**.

Este cuestionario forma parte del procedimiento **E-216** (Gestión Operativa de Proveedores) y su resultado se documenta en el Informe **E-602** (Informe de Evaluación de Proveedor).

## 2. INSTRUCCIONES DE CUMPLIMENTACIÓN

a) El cuestionario deberá cumplimentarse en su integridad y firmarse por persona apoderada del proveedor con capacidad para vincular a la entidad jurídica.

b) Las respuestas deberán ser **veraces y verificables**. La Entidad se reserva el derecho a solicitar evidencia documental de cualquier afirmación realizada.

c) Cuando una sección no resulte aplicable al servicio prestado, deberá indicarse "**No aplica**" con justificación breve, en lugar de dejar la sección en blanco.

d) Las preguntas marcadas con **(*)** son de respuesta obligatoria. Su ausencia detendrá el proceso de onboarding.

e) El cuestionario, una vez cumplimentado, deberá remitirse al contacto operativo de la Entidad ({{ contacto_compliance_email }}) en un plazo no superior a **{{ plazo_respuesta_dias }} días naturales** desde su recepción.

## 3. SECCIÓN A — IDENTIFICACIÓN DEL PROVEEDOR

| Campo | Respuesta |
|-------|-----------|
| Razón social completa (*) | |
| NIF/CIF (*) | |
| Domicilio social (*) | |
| País sede principal (*) | |
| Año constitución | |
| Forma jurídica | |
| Representante legal (nombre y DNI) (*) | |
| Apoderado firmante del cuestionario (*) | |
| Persona contacto operativo (nombre, cargo, email, teléfono) (*) | |
| Persona contacto seguridad / DPO (nombre, email) | |
| Plantilla total (nº empleados) | |
| Plantilla dedicada al servicio objeto | |
| Ubicación física de los recursos asignados (país/región) (*) | |
| Subcontrataciones previstas para prestar el servicio (Sí/No) (*) | |

## 4. SECCIÓN B — CUMPLIMIENTO ENS (RD 311/2022)

### B.1 Conformidad ENS directa o equivalente (*)

a) ¿El proveedor dispone de **Declaración de Conformidad ENS** vigente para el servicio objeto? [ ] Sí [ ] No

b) En caso afirmativo:
- Nivel: [ ] BÁSICO [ ] MEDIO [ ] ALTO
- Fecha emisión:
- Entidad de certificación:
- Aporte como anexo la Declaración (Anexo B.1).

c) En caso negativo, ¿dispone de **certificación o esquema equivalente** que cubra los controles del ENS para el servicio objeto?
- [ ] ISO/IEC 27001:2022 + alcance del servicio
- [ ] SOC 2 Type II del servicio
- [ ] Esquema sectorial reconocido (especificar):
- [ ] Otro (especificar):

d) Adjunte certificados o reportes que avalen la respuesta anterior (Anexo B.1.d).

### B.2 Medidas técnicas del Anexo II aplicables al servicio (*)

Para cada medida del Anexo II del RD 311/2022 aplicable al servicio prestado, indique el grado de implantación:

| Familia de medidas | Implantadas en su organización | Aplicables al servicio | Evidencia disponible |
|--------------------|-------------------------------|------------------------|---------------------|
| `org` Marco organizativo | [ ] Sí [ ] Parcial [ ] No | [ ] Sí [ ] No | |
| `op` Marco operacional | [ ] Sí [ ] Parcial [ ] No | [ ] Sí [ ] No | |
| `mp` Medidas de protección | [ ] Sí [ ] Parcial [ ] No | [ ] Sí [ ] No | |

### B.3 Capacidad de respuesta ante incidentes ENS (*)

a) ¿Dispone de procedimiento documentado de gestión de incidentes? [ ] Sí [ ] No

b) Compromiso de notificación a la Entidad ante un incidente que afecte al servicio:
- Tiempo máximo desde detección (horas): __________ (la Entidad exigirá ≤ 24h para nivel CRÍTICO/ALTO)
- Canal de notificación previsto:

c) ¿Acepta colaborar con la Entidad en la cumplimentación obligatoria del formulario INES y notificaciones al CCN-CERT cuando proceda? [ ] Sí [ ] No

### B.4 Auditoría y supervisión

a) ¿Acepta la realización de **auditorías de cumplimiento** por parte de la Entidad o por terceros designados? [ ] Sí [ ] Sí con preaviso ≥ ___ días [ ] No

b) ¿Acepta la realización de **pruebas técnicas** (test de penetración, escaneo) sobre el servicio prestado, previa coordinación? [ ] Sí [ ] No

c) Frecuencia mínima de revisiones formales que acepta: [ ] Trimestral [ ] Semestral [ ] Anual

## 5. SECCIÓN C — TRATAMIENTO DE DATOS PERSONALES (RGPD)

### C.1 Naturaleza del tratamiento (*)

a) ¿El servicio implica tratamiento de datos personales por cuenta de la Entidad? [ ] Sí [ ] No

Si la respuesta es "No", continúe en la Sección D. Si es "Sí", complete las preguntas C.2 a C.7.

### C.2 Categorías de datos personales tratados

| Categoría | Marque si aplica |
|-----------|------------------|
| Datos identificativos (nombre, DNI, contacto) | [ ] |
| Datos de contacto profesional | [ ] |
| Datos económicos / financieros | [ ] |
| Datos categorías especiales Art. 9 RGPD (salud, biometría, ideología, etc.) | [ ] |
| Datos de menores (< 14 años) | [ ] |
| Datos de tráfico, localización u otros derivados | [ ] |

### C.3 Volumen aproximado de interesados

[ ] < 1.000 [ ] 1.000–10.000 [ ] 10.000–100.000 [ ] > 100.000

### C.4 Subencargados previstos (*)

a) ¿Pretende subcontratar parte del tratamiento? [ ] Sí [ ] No

b) Si "Sí", relacione los subencargados previstos:

| Subencargado | NIF/País | Servicio prestado |
|-------------|----------|-------------------|
| | | |
| | | |

### C.5 Transferencias internacionales (*)

a) ¿Existen transferencias de datos personales fuera del Espacio Económico Europeo (EEE)? [ ] Sí [ ] No

b) Si "Sí", indique países destino y garantías aplicadas (decisión de adecuación, cláusulas tipo, BCR, derogaciones):

### C.6 Medidas técnicas y organizativas RGPD Art. 32

Marque las medidas implantadas relevantes para el servicio:

- [ ] Cifrado en tránsito (TLS 1.2+)
- [ ] Cifrado en reposo
- [ ] Pseudonimización
- [ ] Control de acceso basado en roles
- [ ] Registro de accesos (logs auditables)
- [ ] Copias de seguridad periódicas
- [ ] Procedimiento de restauración probado
- [ ] Política de retención y supresión
- [ ] Análisis de impacto (DPIA) realizado para este servicio

### C.7 Disponibilidad DPO

Datos del Delegado de Protección de Datos (si procede): __________

## 6. SECCIÓN D — CIBERSEGURIDAD NIS2 (cuando aplique)

a) ¿El proveedor está sujeto al ámbito de aplicación de la Directiva NIS2 (entidad esencial o importante)? [ ] Sí [ ] No [ ] Desconocido

b) Si "Sí", aporte evidencia de la inscripción en el registro nacional correspondiente o de la designación competente (Anexo D.b).

c) Indique las **prácticas de gestión de riesgos de ciberseguridad** documentadas conforme al Art. 21 NIS2:

- [ ] Análisis de riesgos formalizado
- [ ] Plan de continuidad de negocio
- [ ] Gestión de la cadena de suministro propia
- [ ] Cifrado y autenticación robusta
- [ ] Formación y concienciación en ciberseguridad
- [ ] Notificación de incidentes significativos a la autoridad competente

## 7. SECCIÓN E — DORA (sólo si la Entidad es entidad financiera UE o el servicio es TIC crítico para una)

a) ¿El servicio prestado se enmarca como **servicio TIC** en el sentido del Reglamento (UE) 2022/2554 (DORA)? [ ] Sí [ ] No

b) Si "Sí", responda:

- ¿Acepta los requisitos contractuales mínimos del Art. 30 DORA (derecho de acceso, auditoría, asistencia ante incidentes, planes de salida)? [ ] Sí [ ] No
- ¿Dispone de planes documentados de continuidad operativa con objetivos RTO/RPO declarables? [ ] Sí [ ] No
- ¿Acepta la inclusión en el registro de información de la Entidad relativo a acuerdos contractuales TIC? [ ] Sí [ ] No

## 8. SECCIÓN F — CAPACIDADES TÉCNICAS Y CERTIFICACIONES

a) Certificaciones vigentes (marque las que apliquen y aporte como anexos):

- [ ] ISO/IEC 27001 (alcance: __________)
- [ ] ISO/IEC 27017 / 27018
- [ ] ISO/IEC 22301 Continuidad de negocio
- [ ] ISO 9001
- [ ] SOC 2 Type II
- [ ] PCI-DSS
- [ ] Esquema Nacional de Seguridad (nivel: __________)
- [ ] Otros: __________

b) Aporte como anexo F.b copia electrónica vigente de cada certificación marcada.

c) Personal técnico asignado al servicio (sin nombres propios — sólo cualificación y nº):

| Perfil | Nº personas | Cualificación |
|--------|-------------|---------------|
| | | |

d) Seguro de responsabilidad civil profesional o ciber: [ ] Sí, cuantía: __________ EUR [ ] No

## 9. SECCIÓN G — CONTINUIDAD Y PROCEDIMIENTO DE SALIDA

a) ¿Dispone de plan documentado de continuidad para el servicio objeto? [ ] Sí [ ] No

b) RTO comprometido (Recovery Time Objective): __________ horas

c) RPO comprometido (Recovery Point Objective): __________ horas

d) ¿Acepta los procedimientos de **salida ordenada** definidos por la Entidad, incluyendo devolución o destrucción acreditada de información en plazo máximo de 30 días naturales tras la terminación? [ ] Sí [ ] No

## 10. DECLARACIÓN RESPONSABLE

La persona firmante declara, bajo su responsabilidad, que las respuestas contenidas en el presente cuestionario son **veraces, completas y precisas** en la fecha de su firma, y se compromete a notificar a {{ cliente.razon_social }} cualquier cambio material que afecte a las respuestas aportadas durante toda la vigencia del servicio prestado.

Asimismo, autoriza a {{ cliente.razon_social }} al tratamiento de los datos contenidos en el cuestionario para los fines exclusivos de evaluación, supervisión y mantenimiento del registro de proveedores en el marco del cumplimiento normativo de la Entidad.

## 11. FIRMAS

| Concepto | Datos |
|----------|-------|
| Nombre y apellidos del firmante | |
| DNI/NIE/Pasaporte | |
| Cargo en el proveedor | |
| Capacidad para vincular a la entidad (Sí/No + base jurídica) | |
| Lugar y fecha | |
| Firma manuscrita o electrónica cualificada | |

---

## ANEXOS QUE DEBEN ADJUNTARSE

- Anexo B.1 — Declaración de Conformidad ENS (si aplica)
- Anexo B.1.d — Certificaciones equivalentes (si aplica)
- Anexo C — Modelo de contrato de encargado de tratamiento RGPD Art. 28 (cuando aplique)
- Anexo D.b — Evidencia inscripción NIS2 (cuando aplique)
- Anexo F.b — Copias de certificaciones marcadas
- Anexo G — Plan de continuidad operativa (resumen ejecutivo)

---

*Documento generado por FULKRO · plataforma de gestión ENS · {{ doc_fecha }}*
*Una vez cumplimentado y firmado por el proveedor, este cuestionario se incorpora a la tabla `provider_assessments` del sistema FULKRO y constituye el insumo principal para el Informe de Evaluación E-602.*
