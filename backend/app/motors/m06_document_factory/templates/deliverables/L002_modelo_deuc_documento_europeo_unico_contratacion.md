---
codigo_documento: "L-002"
titulo: "Modelo Declarativo Equivalente DEUC + Guía Cumplimentación Visor eDEUC"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "PÚBLICA · ENTREGABLE LICITACIÓN"
norma_aplicable: "Reglamento de Ejecución (UE) 2016/7 · Directiva 2014/24/UE · LCSP 9/2017 Arts. 140-141"
formulario_oficial: "Documento Europeo Único de Contratación (DEUC)"
visor_oficial: "https://visor.registrodelicitadores.gob.es/"
naturaleza: "Anexo interno al expediente del licitador · complementa DEUC oficial sin sustituirlo"
---

# MODELO DECLARATIVO EQUIVALENTE AL DOCUMENTO EUROPEO ÚNICO DE CONTRATACIÓN (DEUC) Y GUÍA DE CUMPLIMENTACIÓN DEL VISOR eDEUC

**Documento L-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set licit_exige_ens = licitacion.exige_ens if licitacion and licitacion.exige_ens is defined else False %}
{% set licit_categoria = licitacion.categoria_ens if licitacion and licitacion.categoria_ens else 'No aplica' %}
{% set licit_permite_sub = licitacion.permite_subcontratacion if licitacion and licitacion.permite_subcontratacion is defined else False %}
{% set tiene_subcontratistas = cliente.subcontratistas_previstos and cliente.subcontratistas_previstos | length > 0 %}
{% set tiene_referencias = cliente.referencias_proyectos and cliente.referencias_proyectos | length > 0 %}
{% set tiene_equipo = cliente.equipo_responsable and cliente.equipo_responsable | length > 0 %}
{% set tiene_certif = cliente.certificaciones_vigentes and cliente.certificaciones_vigentes | length > 0 %}
{% set contrato_ref = contrato.referencia if contrato and contrato.referencia else '[REFERENCIA EXPEDIENTE]' %}
{% set representante_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[REPRESENTANTE LEGAL]' %}
{% set representante_dni = cliente.representante.dni if cliente.representante and cliente.representante.dni else '[DNI]' %}
{% set representante_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[CARGO]' %}

## 1. OBJETO Y MARCO NORMATIVO

El presente documento constituye el **modelo declarativo equivalente** al Documento Europeo Único de Contratación (en adelante, "DEUC") presentado por **{{ cliente.razon_social }}** (en adelante, "el Operador Económico") a los efectos del procedimiento de contratación con referencia **{{ contrato_ref }}**.

Este modelo se elabora conforme a:

- **Reglamento de Ejecución (UE) 2016/7** de la Comisión, de 5 de enero de 2016, por el que se establece el formulario normalizado del DEUC.
- **Directiva 2014/24/UE** del Parlamento Europeo y del Consejo, de 26 de febrero de 2014, sobre contratación pública.
- **Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público** (LCSP), artículos 140 y 141 sobre declaración responsable y DEUC.
- **Orden HFP/1499/2021** de 28 de diciembre, sobre presentación telemática del DEUC mediante el servicio eDEUC.

**Naturaleza del documento:**
Este modelo constituye **anexo interno al expediente** del Operador Económico y se presenta como complemento al DEUC oficialmente cumplimentado en el visor estatal eDEUC. **No sustituye al DEUC oficial**, cuya cumplimentación se realiza obligatoriamente en la herramienta autoritativa de la Administración (sección 9 de este documento).

## 2. ACERCA DEL DEUC

El Documento Europeo Único de Contratación es la **declaración formal del operador económico** que sirve como **prueba preliminar** de:

a) No incurrir en ninguna de las situaciones de exclusión previstas en los artículos 71 a 73 de la LCSP y artículo 57 de la Directiva 2014/24/UE.

b) Cumplir los criterios de selección establecidos por el órgano de contratación en el pliego del procedimiento.

c) Cuando proceda, cumplir las normas y criterios objetivos establecidos para la reducción del número de candidatos cualificados.

El DEUC sustituye, en los procedimientos sujetos a regulación armonizada de la UE, a las certificaciones individuales emitidas por autoridades nacionales hasta el momento de la adjudicación, en que el adjudicatario propuesto deberá aportar los documentos justificativos en original.

## 3. PARTE I — INFORMACIÓN SOBRE EL PROCEDIMIENTO Y EL PODER ADJUDICADOR

| Campo | Valor declarado |
|-------|-----------------|
| Identificación del procedimiento | {{ contrato_ref }} |
| Objeto del contrato | {{ contrato.objeto if contrato and contrato.objeto else '[Objeto según pliego]' }} |
| Poder adjudicador | {{ contrato.poder_adjudicador if contrato and contrato.poder_adjudicador else '[Órgano de contratación según pliego]' }} |
| Tipo de procedimiento | {{ contrato.tipo_procedimiento if contrato and contrato.tipo_procedimiento else '[Abierto / Restringido / Negociado / etc.]' }} |
| Anuncio en DOUE | {{ contrato.referencia_doue if contrato and contrato.referencia_doue else '[Referencia DOUE si SARA]' }} |
| Anuncio en BOE / Plataforma Contratación Sector Público | {{ contrato.referencia_pcsp if contrato and contrato.referencia_pcsp else '[Referencia PCSP]' }} |

## 4. PARTE II — INFORMACIÓN SOBRE EL OPERADOR ECONÓMICO

### 4.1 Apartado II.A — Identificación

| Campo | Declaración |
|-------|-------------|
| Denominación social | **{{ cliente.razon_social }}** |
| NIF | **{{ cliente.nif }}** |
| Domicilio social | {{ cliente.domicilio if cliente.domicilio else '[Domicilio social]' }} |
| Forma jurídica | {{ cliente.forma_juridica if cliente.forma_juridica else 'Sociedad mercantil española' }} |
| Persona de contacto | {{ cliente.persona_contacto_licitaciones if cliente.persona_contacto_licitaciones else '[Persona de contacto]' }} |
| Correo electrónico para notificaciones | {{ cliente.email_notificaciones if cliente.email_notificaciones else '[email notificaciones]' }} |
| Número EORI (operadores no UE) | No aplica · operador establecido en España |
| Inscripción en el Registro Oficial de Licitadores y Empresas Clasificadas del Sector Público (ROLECE) | {{ cliente.inscripcion_rolece if cliente.inscripcion_rolece else '[Sí / No · indicar nº de inscripción]' }} |
| Condición de PYME | {{ cliente.condicion_pyme if cliente.condicion_pyme else '[Sí · pequeña/mediana · indicar]' }} |

### 4.2 Apartado II.B — Información sobre los representantes

| Campo | Declaración |
|-------|-------------|
| Nombre y apellidos del representante legal | **{{ representante_nombre }}** |
| DNI / Documento equivalente | **{{ representante_dni }}** |
| Cargo en la entidad | **{{ representante_cargo }}** |
| Tipo de poder | {{ cliente.representante.tipo_poder if cliente.representante and cliente.representante.tipo_poder else 'Poder solidario para representación en procedimientos de contratación pública · escritura notarial' }} |

### 4.3 Apartado II.C — Confianza en las capacidades de otras entidades

{{ "El Operador Económico **NO se basa** en las capacidades de otras entidades para satisfacer los criterios de selección establecidos en el pliego." if not cliente.entidades_apoyo else "El Operador Económico **SÍ se basa** en las capacidades de otras entidades para satisfacer los criterios de selección. Las entidades sobre cuyas capacidades se basa se identifican en documento anexo, y cada una de ellas presentará el DEUC correspondiente." }}

### 4.4 Apartado II.D — Información relativa a los subcontratistas

{% if tiene_subcontratistas %}
El Operador Económico declara que **prevé subcontratar** las siguientes actividades:

| Subcontratista | Actividad | % previsto |
|----------------|-----------|-----------:|
{% for sub in cliente.subcontratistas_previstos %}| {{ sub.razon_social }} | {{ sub.actividad }} | {{ sub.porcentaje if sub.porcentaje else '—' }}% |
{% endfor %}

Cada uno de los subcontratistas anteriores cumple con las condiciones de aptitud exigidas por la LCSP y los pliegos. El presente DEUC se aporta sin perjuicio de la documentación adicional que pueda requerirse en fase de adjudicación.
{% else %}
El Operador Económico declara **no prever la subcontratación** de prestaciones objeto del contrato. En caso de que durante la ejecución surgiera la necesidad de subcontratar, se comunicará al órgano de contratación conforme al artículo 215 LCSP y al pliego.
{% endif %}

## 5. PARTE III — MOTIVOS DE EXCLUSIÓN

El Operador Económico declara, bajo su responsabilidad, **NO encontrarse incurso** en ninguno de los siguientes motivos de exclusión:

### 5.1 Apartado III.A — Motivos referidos a condenas penales

- No haber sido condenado mediante sentencia firme por delitos de terrorismo, blanqueo de capitales, financiación del terrorismo, trata de seres humanos, corrupción, fraude, delitos contra la Hacienda Pública o la Seguridad Social, prevaricación, cohecho, tráfico de influencias, malversación, fraudes y exacciones ilegales, delitos urbanísticos, contra los recursos naturales y el medio ambiente, contra la salud pública, asociación ilícita, organización criminal o cualesquiera otros delitos comprendidos en el artículo 71.1.a) LCSP y 57.1 Directiva 2014/24/UE.

### 5.2 Apartado III.B — Motivos referidos al pago de impuestos o cotizaciones sociales

- Hallarse al corriente en el cumplimiento de las obligaciones tributarias estatales y autonómicas.
- Hallarse al corriente en el cumplimiento de las obligaciones con la Seguridad Social.
- No tener deudas en período ejecutivo con la Administración Tributaria salvo que hubieren sido satisfechas o garantizadas en los términos legalmente establecidos.

### 5.3 Apartado III.C — Motivos referidos a insolvencia, conflictos de intereses o falta profesional

- No haberse declarado el concurso, no haber instado el mismo o no encontrarse declarado insolvente.
- No haber sido sancionado, con carácter firme, por infracción grave en materia profesional, falsedad, manifiesta negligencia profesional o por violación de las normas reguladoras del sector.
- No estar afectado por situaciones de conflicto de intereses no resueltas previstas en el artículo 64 LCSP.
- No haber sido el agente contratante ni el operador económico en participación previa en la preparación del procedimiento de contratación, salvo que la distorsión a la competencia haya sido resuelta conforme al artículo 70 LCSP.
- No haber resuelto culpablemente contratos celebrados con cualquier Administración Pública.

### 5.4 Apartado III.D — Otros motivos de exclusión LCSP

- No estar incurso en ninguna de las prohibiciones para contratar contempladas en el artículo 71 LCSP.
- Cumplir con la cuota legal de reserva de puestos de trabajo a personas con discapacidad conforme al Real Decreto Legislativo 1/2013 (si la entidad tiene 50 o más trabajadores).
- Disponer de un Plan de Igualdad efectivo, conforme al Real Decreto 901/2020 (si la entidad tiene 50 o más trabajadores).
- {% if licit_exige_ens %}Cumplir las obligaciones específicas relativas al **Esquema Nacional de Seguridad** conforme al **Real Decreto 311/2022, de 3 de mayo**, exigible por el pliego del presente procedimiento en su nivel **{{ licit_categoria }}**. {% else %}No procede declaración específica adicional ENS para este procedimiento.{% endif %}

## 6. PARTE IV — CRITERIOS DE SELECCIÓN

### 6.1 Apartado IV.A — Idoneidad para el ejercicio de la actividad profesional

El Operador Económico declara estar inscrito en el Registro Mercantil con CIF **{{ cliente.nif }}**, encontrándose habilitado para el ejercicio de las actividades objeto del contrato, conforme a su objeto social y a la normativa sectorial aplicable.

### 6.2 Apartado IV.B — Solvencia económica y financiera

El Operador Económico cumple los requisitos de solvencia económica y financiera establecidos en el pliego, conforme al artículo 87 LCSP, mediante:

| Medio acreditativo | Indicador |
|--------------------|-----------|
| Volumen anual de negocios | {{ cliente.volumen_negocios if cliente.volumen_negocios else '[Volumen últimos 3 ejercicios]' }} |
| Patrimonio neto | {{ cliente.patrimonio_neto if cliente.patrimonio_neto else '[Patrimonio neto al cierre del último ejercicio]' }} |
| Seguro de responsabilidad civil profesional | {{ cliente.seguro_rc if cliente.seguro_rc else '[Compañía + capital asegurado]' }} |

La documentación justificativa se aportará en fase de adjudicación.

### 6.3 Apartado IV.C — Capacidad técnica y profesional

El Operador Económico cumple los requisitos de solvencia técnica establecidos en el pliego, conforme a los artículos 89 a 91 LCSP, mediante:

{% if tiene_referencias %}
**Referencias de proyectos ejecutados en los últimos tres (3) años:**

| Cliente | Proyecto | Importe (€) | Fecha |
|---------|----------|------------:|-------|
{% for ref in cliente.referencias_proyectos %}
| {{ ref.cliente }} | {{ ref.descripcion }} | {{ ref.importe }} | {{ ref.fecha }} |
{% endfor %}
{% endif %}

{% if tiene_equipo %}
**Equipo profesional adscrito al contrato:**

| Persona | Cargo | Experiencia |
|---------|-------|-------------|
{% for miembro in cliente.equipo_responsable %}
| {{ miembro.nombre }} | {{ miembro.cargo }} | {{ miembro.experiencia_descripcion }} |
{% endfor %}
{% endif %}

{% if tiene_certif %}
**Certificaciones vigentes acreditativas de calidad y seguridad:**

| Certificación | Norma | Entidad emisora | Vigencia |
|---------------|-------|-----------------|----------|
{% for cert in cliente.certificaciones_vigentes %}
| {{ cert.nombre }} | {{ cert.norma }} | {{ cert.entidad }} | {{ cert.vigencia }} |
{% endfor %}
{% endif %}

**Medios técnicos y materiales:** {{ cliente.medios_tecnicos_descripcion if cliente.medios_tecnicos_descripcion else '[Descripción de medios técnicos]' }}

### 6.4 Apartado IV.D — Sistemas de aseguramiento de la calidad y normas de gestión medioambiental

El Operador Económico dispone de los siguientes sistemas de gestión, cuya certificación se acreditará documentalmente:

- Sistema de gestión de la calidad conforme a normas equivalentes a UNE-EN ISO 9001 (cuando proceda).
- Sistema de gestión ambiental conforme a normas equivalentes a UNE-EN ISO 14001 o registro EMAS (cuando proceda).
- {% if licit_exige_ens %}Sistema de gestión de la seguridad de la información conforme al **Esquema Nacional de Seguridad** (RD 311/2022) categoría **{{ licit_categoria }}**, acreditado mediante certificación o declaración de conformidad según corresponda.{% else %}Sistemas adicionales conforme al pliego del procedimiento.{% endif %}

### 6.5 Apartado IV.α — Indicación global para los criterios de selección (alternativa simplificada)

Cuando el pliego habilite la alternativa simplificada del apartado IV.α del DEUC, el Operador Económico podrá declarar de forma global el cumplimiento de los criterios sin detallar cada apartado. Esta declaración no exime de la aportación de la documentación justificativa requerida en fase de adjudicación.

## 7. PARTE V — REDUCCIÓN DEL NÚMERO DE CANDIDATOS CUALIFICADOS (cuando proceda)

Únicamente cumplimentada cuando el procedimiento sea restringido, negociado con publicidad, de diálogo competitivo o de asociación para la innovación, y el pliego prevea una reducción del número de candidatos. En su caso, se aportarán los criterios y méritos objetivos aplicables conforme al pliego.

## 8. PARTE VI — DECLARACIÓN FINAL

El Operador Económico, mediante el presente documento:

a) **Declara formalmente** que la información facilitada en las Partes II a V es **exacta, completa y veraz**.

b) **Declara conocer** las consecuencias legales de la presentación de declaraciones falsas o inexactas, incluyendo la exclusión del procedimiento, la responsabilidad por daños y perjuicios y la posible incoación de procedimientos penales por falsedad documental.

c) **Se compromete** a aportar, a requerimiento del órgano de contratación y en fase de adjudicación, los documentos justificativos originales acreditativos de las declaraciones contenidas en el presente DEUC, conforme al artículo 140.3 LCSP.

d) **Autoriza** al órgano de contratación a verificar la información declarada mediante el acceso a las bases de datos electrónicas oficiales (Registro Mercantil, AEAT, TGSS, ROLECE, etc.) cuando ello sea posible.

e) **Confirma** que la presentación del DEUC oficialmente cumplimentado en el visor eDEUC (sección 9) se realiza en idéntica fecha y con el contenido sustancialmente coincidente con el presente modelo declarativo equivalente.

---

## 9. GUÍA DE CUMPLIMENTACIÓN DEL VISOR eDEUC OFICIAL

La cumplimentación oficial del DEUC se realiza obligatoriamente en el visor estatal disponible en:

**URL oficial:** `https://visor.registrodelicitadores.gob.es/`

El servicio eDEUC, gestionado por la Junta Consultiva de Contratación Pública del Estado del Ministerio de Hacienda y Función Pública, es el sistema autoritativo para la generación, firma electrónica e impresión del DEUC en formato XML conforme a la norma técnica eForms 2024.

### Procedimiento paso a paso

**Paso 1 — Acceso al visor eDEUC**
Acceder a `https://visor.registrodelicitadores.gob.es/` desde un navegador con certificado electrónico instalado (DNI electrónico, certificado FNMT-RCM, certificado cualificado de prestador de servicios de confianza UE eIDAS).

**Paso 2 — Importación del DEUC publicado por el órgano de contratación**
Localizar en el expediente del procedimiento publicado en la Plataforma de Contratación del Sector Público el archivo XML del DEUC pre-cumplimentado por el órgano de contratación. Importarlo en el visor mediante la opción "Importar DEUC".

**Paso 3 — Selección de rol "Operador Económico"**
En el visor, indicar que la cumplimentación se realiza en condición de operador económico (no de órgano de contratación).

**Paso 4 — Cumplimentación Parte II — Información sobre el Operador Económico**
Trasladar al visor los datos de la **sección 4** del presente documento (Apartados II.A, II.B, II.C y II.D).

**Paso 5 — Cumplimentación Parte III — Motivos de exclusión**
Confirmar en el visor cada una de las declaraciones negativas de la **sección 5** del presente documento (Apartados III.A a III.D).

**Paso 6 — Cumplimentación Parte IV — Criterios de selección**
Trasladar al visor los apartados IV.A, IV.B, IV.C y IV.D de la **sección 6** del presente documento. Cuando el pliego lo permita, se podrá optar por la alternativa simplificada IV.α.

**Paso 7 — Cumplimentación Parte V (si procede)**
Únicamente si el procedimiento es restringido, negociado con publicidad o de diálogo competitivo con reducción de candidatos.

**Paso 8 — Cumplimentación Parte VI — Declaración final**
Confirmar las declaraciones finales detalladas en la **sección 8** del presente documento.

**Paso 9 — Generación del archivo XML**
Una vez cumplimentadas todas las partes, generar el archivo XML conforme a eForms 2024 mediante la opción "Generar DEUC". El visor producirá un archivo `.xml` y, opcionalmente, una versión en PDF para verificación visual.

**Paso 10 — Firma electrónica**
Firmar el archivo XML mediante el sistema integrado del visor o mediante aplicación externa de firma electrónica avanzada o cualificada (Autofirma, Adobe Sign Acrobat, etc.), con certificado del representante legal **{{ representante_nombre }}**.

**Paso 11 — Presentación telemática en la Plataforma de Contratación del Sector Público**
Adjuntar el archivo `.xml` firmado al sobre electrónico correspondiente del procedimiento, en la Plataforma de Contratación del Sector Público (PCSP), conforme a los plazos y condiciones del pliego.

**Paso 12 — Archivado interno**
Conservar copia del archivo `.xml` firmado, del PDF de verificación y del presente modelo declarativo equivalente (L-002) en el expediente interno del Operador Económico, junto con el sello de presentación de la PCSP.

### Checklist final de verificación

| Verificación | OK |
|--------------|:--:|
| Certificado electrónico del representante legal vigente y operativo | ☐ |
| DEUC pre-cumplimentado por el órgano descargado de la PCSP e importado en el visor | ☐ |
| Partes II a VI cumplimentadas conforme al presente modelo L-002 | ☐ |
| Apartado II.D Subcontratistas cumplimentado coherente con secciones 4.4 de L-002 | ☐ |
| Apartado IV.C Capacidad técnica coherente con L-004 (acreditación solvencia) | ☐ |
| {% if licit_exige_ens %}Declaración ENS RD 311/2022 categoría {{ licit_categoria }} confirmada en III.D y IV.D{% else %}Apartados ENS no aplicables{% endif %} | ☐ |
| Archivo `.xml` firmado electrónicamente con firma avanzada o cualificada | ☐ |
| Archivo `.xml` y PDF verificación adjuntados al sobre electrónico PCSP | ☐ |
| Copia archivo y modelo L-002 archivados en expediente interno | ☐ |
| Fecha de presentación dentro del plazo del pliego | ☐ |

---

## 10. RESERVAS Y ADVERTENCIAS

a) El presente modelo declarativo **complementa** al DEUC oficialmente cumplimentado en el visor eDEUC. En caso de discrepancia entre el contenido del archivo XML oficial y el presente documento, **prevalece el archivo XML oficial firmado electrónicamente**.

b) Las declaraciones contenidas en este modelo se entienden hechas bajo la responsabilidad del Operador Económico conforme al artículo 140 LCSP, con las consecuencias previstas legalmente para el caso de inexactitud.

c) El Operador Económico se compromete a comunicar al órgano de contratación cualquier alteración sobrevenida de las circunstancias declaradas durante la tramitación del procedimiento, conforme al artículo 140.4 LCSP.

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[FECHA]' }}.**

**{{ representante_nombre }}**
{{ representante_cargo }}
{{ cliente.razon_social }}
NIF: {{ cliente.nif }}
DNI representante: {{ representante_dni }}

---

**Documento L-002 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: PÚBLICA · ENTREGABLE LICITACIÓN**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}*
